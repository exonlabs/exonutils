# -*- coding: utf-8 -*-
import os
import copy
import signal

try:
    from gunicorn.app.base import BaseApplication
    from gunicorn.glogging import Logger
    from gunicorn.arbiter import Arbiter
    from gunicorn.pidfile import Pidfile
    from gunicorn import sock, systemd, util
except ImportError:
    raise RuntimeError("`gunicorn` package not installed")

try:
    from setproctitle import setproctitle
    util._setproctitle = lambda t: setproctitle(
        t[8:-1] if 'master' in t else ('%s+' % t[8:-1]))
except ImportError:
    pass

__all__ = []


# extended web server application
class ExtWebServer(BaseApplication):

    def __init__(self, websrv, options={}):
        self.websrv = websrv
        self.options = copy.deepcopy(options or {})
        super(ExtWebServer, self).__init__()

    def load_config(self):
        # setup loggers
        errlogger = self.websrv.log
        reqlogger = self.websrv.reqlog

        class _Logger(Logger):
            def __init__(self, *args, **kw):
                super(_Logger, self).__init__(*args, **kw)
                self.error_log = errlogger
                self.access_log = reqlogger

        # check engine options
        self.options.update({
            'reuse_port': True,
            'workers': self.options.get('workers', 0) or os.cpu_count(),
            'worker_class': self.options.get('worker_class', 'sync'),
            'logger_class': _Logger,
            'accesslog': '-',
            'access_log_format': self.options.get(
                'access_log_format',
                '%({x-forwarded-for}i)s %(u)s %(t)s "%(r)s" ' +
                '%(s)s %(b)s "%(f)s" "%(a)s" %(D)s'),
            'timeout': self.options.get('timeout', 0),
            'graceful_timeout': self.options.get('graceful_timeout', 0),
            'max_requests': self.options.get('max_requests', 0),
            'max_requests_jitter':
                self.options.get('max_requests_jitter', 0),
            'proc_name': str(self.websrv.proctitle or
                             self.websrv.name).strip().lower(),
        })

        # set engine options
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key, value)

    def load(self):
        return self.websrv.app


class WebArbiter(Arbiter):

    SIGNALS = [getattr(signal, "SIG%s" % x)
               for x in "HUP QUIT INT TERM USR1".split()]

    def setup(self, app):
        self.app = app
        self.cfg = app.cfg

        if self.log is None:
            self.log = self.cfg.logger_class(app.cfg)

        # reopen files
        if 'GUNICORN_FD' in os.environ:
            self.log.reopen_files()

        self.worker_class = self.cfg.worker_class
        self.address = self.cfg.address
        self.num_workers = self.cfg.workers
        self.timeout = self.cfg.timeout
        self.proc_name = self.cfg.proc_name

        # set enviroment' variables
        if self.cfg.env:
            for k, v in self.cfg.env.items():
                os.environ[k] = v

        if self.cfg.preload_app:
            self.app.wsgi()

    def start(self):
        if 'GUNICORN_PID' in os.environ:
            self.master_pid = int(os.environ.get('GUNICORN_PID'))
            self.proc_name = self.proc_name + ".2"
            self.master_name = "Master.2"

        self.pid = os.getpid()
        if self.cfg.pidfile is not None:
            pidname = self.cfg.pidfile
            if self.master_pid != 0:
                pidname += ".2"
            self.pidfile = Pidfile(pidname)
            self.pidfile.create(self.pid)
        self.cfg.on_starting(self)

        # store root process PID
        self.app.websrv.app.config['ROOT_PID'] = self.pid

        self.init_signals()

        if not self.LISTENERS:
            fds = None
            listen_fds = systemd.listen_fds()
            if listen_fds:
                self.systemd = True
                fds = range(systemd.SD_LISTEN_FDS_START,
                            systemd.SD_LISTEN_FDS_START + listen_fds)

            elif self.master_pid:
                fds = []
                for fd in os.environ.pop('GUNICORN_FD').split(','):
                    fds.append(int(fd))

            self.LISTENERS = sock.create_sockets(self.cfg, self.log, fds)

        listeners_str = ",".join([str(l) for l in self.LISTENERS])
        self.log.info("Running on: %s", listeners_str)
        self.log.info("Using worker: %s", self.cfg.worker_class_str)

        # check worker class requirements
        if hasattr(self.worker_class, "check_config"):
            self.worker_class.check_config(self.cfg, self.log)

        self.cfg.when_ready(self)


# to run WebArbiter from thread
class ThreadWebArbiter(WebArbiter):

    def init_signals(self):
        pass

    def run(self):
        self.start()
        self.manage_workers()

    def monitor_workers(self):
        self.reap_workers()
        self.manage_workers()
