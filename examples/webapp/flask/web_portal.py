# -*- coding: utf-8 -*-
import sys
import logging
from argparse import ArgumentParser

from exonutils.webapp.flask.server import SimpleWebServer
from exonutils.webapp.flask.view import BaseWebView
from exonutils.webapp.gunicorn.extserver import ExtWebServer, WebArbiter

logging.basicConfig(
    level=logging.INFO, stream=sys.stdout,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s')
logging.addLevelName(logging.WARNING, "WARN")
logging.addLevelName(logging.CRITICAL, "FATAL")


HOST = "0.0.0.0"
PORT = 8000

APP_OPTIONS = {
    'secret_key': "0123456789ABCDEF",
    'max_content_length': 10485760,  # 10MiB
    'templates_auto_reload': False,
}

EXT_OPTIONS = {
    'bind': '%s:%s' % (HOST, PORT),
    'workers': 2,
    'threads': 1,
    'max_requests': 0,
    'timeout': 0,
}


class IndexView(BaseWebView):
    routes = [('/', 'index')]

    def get(self, **kwargs):
        self.log.debug(self.__class__.__name__)
        return self.__class__.__name__


class HomeView(BaseWebView):
    routes = [('/home', 'home')]

    def get(self, **kwargs):
        self.log.debug(self.__class__.__name__)
        return self.__class__.__name__


class ExitView(BaseWebView):
    routes = [('/exit', 'exit')]

    def get(self, **kwargs):
        self.parent.stop()
        return ''


def main():
    logger = logging.getLogger()
    logger.name = 'main'

    reqlog = logging.getLogger('%s.requests' % logger.name)
    reqlog.handlers = [logging.StreamHandler(sys.stdout)]

    try:
        pr = ArgumentParser(prog=None)
        pr.add_argument(
            '-x', dest='debug', action='count', default=0,
            help='set debug modes')
        pr.add_argument(
            '--ext-websrv', dest='ext_websrv', action='store_true',
            help="use extended gunicorn web server")
        args = pr.parse_args()

        if args.debug > 0:
            logger.setLevel(logging.DEBUG)
        if args.debug >= 3:
            APP_OPTIONS['templates_auto_reload'] = True

        websrv = SimpleWebServer(
            'WebPortal', options=APP_OPTIONS,
            logger=logger, reqlogger=reqlog, debug=args.debug)
        websrv.initialize()

        for view_cls in BaseWebView.__subclasses__():
            websrv.add_view(view_cls)

        if args.ext_websrv:
            ext_websrv = ExtWebServer(websrv, options=EXT_OPTIONS)
            WebArbiter(ext_websrv).run()
        else:
            websrv.start(
                HOST, PORT,
                debug=bool(args.debug >= 1),
                use_reloader=bool(args.debug >= 3))

    except Exception as e:
        logger.fatal(str(e), exc_info=args.debug)
        sys.exit(1)


if __name__ == '__main__':
    main()
