# -*- coding: utf-8 -*-
import os
import threading
import logging

from exonutils.utils.shell import Shell

"""
FTP client supporting TLS v1.2/1.3

FTP Options
{
    'host': 'x.x.x.x',           # FTP server IP address
    'port': 21,                  # FTP server port
    'username': 'username',      # access username
    'password': 'password',      # access password

    'transfer_mode': 'Passive',  # transfer mode: Passive|Active

    'tls_enable': True,          # enable TLS connection
    'tls_protocol': 'Explicit'   # TLS operation mode: Explicit|Implicit
                                   (default explicit TLS over FTP port)
    'tls_version': 'Auto',       # TLS version: Auto|TLSv1_2|TLSv1_3
}
"""


class FTPClient(object):

    def __init__(self, options, logger=None):
        self.options = options
        # ftp logger
        self.log = logger or logging.getLogger()
        # debug mode
        self.debug = bool(self.log.level == logging.DEBUG)

        # ftp terminate event
        self.term_event = threading.Event()

    # return file operation command for download or upload
    def _file_operation(self, local_path, remote_path, is_dnload=True,
                        **kwargs):
        if not os.path.exists(local_path):
            raise ValueError(
                "INVALID_PARAMS - invalid path %s" % local_path)

        host = self.options.get('host')
        if not host:
            raise ValueError("INVALID_PARAMS - no ftp host defined")
        port = int(self.options.get('port', 0))
        if not port:
            raise ValueError("INVALID_PARAMS - no ftp port defined")

        # download mode: local_path -> dir, remote_path -> file
        if is_dnload:
            if not remote_path:
                raise ValueError("INVALID_PARAMS - invalid remote_path")
            local_path = os.path.join(
                local_path, remote_path.split('/')[-1])
        # upload mode: local_path -> file, remote_path -> dir
        else:
            if remote_path:
                remote_path += '/'

        cmd = 'curl -s -S'
        proto = 'ftp'

        # set TLS
        if self.options.get('tls_enable'):
            cmd += ' --ssl-reqd --insecure'

            tls_ver = self.options.get('tls_version')
            if tls_ver == 'TLSv1_3':
                cmd += ' --tlsv1.3'
            elif tls_ver == 'TLSv1_2':
                cmd += ' --tlsv1.2 --tls-max 1.2'
            else:
                cmd += ' --tlsv1.2'

            if self.options.get('tls_protocol') == 'Implicit':
                proto = 'ftps'

        # set transfer mode
        if self.options.get('transfer_mode') == 'Active':
            cmd += ' -P -'
        else:
            cmd += ' --ftp-pasv --ftp-skip-pasv-ip'

        # set login
        user = self.options.get('username') or ''
        if user:
            passwd = self.options.get('password') or ''
            if passwd:
                cmd += ' -u "%s:%s"' % (user, passwd)
            else:
                cmd += ' -u "%s"' % (user)

        # set remote url
        cmd += ' %s://%s:%s/%s' % (proto, host, port, remote_path)

        # set local path
        if is_dnload:
            cmd += ' -o %s' % local_path
        else:
            cmd += ' -T %s' % local_path

        return cmd

    # execute operation command with retries and timeouts
    def _run_command(self, cmd, **kwargs):
        host = self.options.get('host')
        if not host:
            raise ValueError("INVALID_PARAMS - no ftp host defined")
        port = int(self.options.get('port', 0))
        if not port:
            raise ValueError("INVALID_PARAMS - no ftp port defined")

        if not self.options.get('tls_enable'):
            self.log.warning("(FTP) using non-secure connection")

        self.term_event.clear()

        retries = int(kwargs.get('retries') or 0)
        retry_delay = int(kwargs.get('retry_delay') or 5)
        timeout = int(kwargs.get('timeout') or 300)

        # # for testing only (NOTE: password is logged in cleartext)
        # self.log.debug("(FTP) operation command: %s" % cmd)

        err = ""
        for i in range(retries + 1):
            try:
                if i > 0:
                    if err:
                        self.log.error(
                            "(FTP) operation failed: %s -- retry in %s sec"
                            % (err or "unknown error", retry_delay))
                    if self.term_event.wait(timeout=retry_delay):
                        self.log.info("(FTP) operation cancelled")
                        return False
                    self.log.info("(FTP) retrying (%s/%s)" % (i, retries))

                self.log.info(
                    "(FTP) starting connection: %s:%s" % (host, port))

                # run command
                retcode, out, err = Shell.run(cmd, timeout=timeout)
                self.log.info("(FTP) disconnected")
                if int(retcode) == 0:
                    return True

                err = err.split('(%s)' % retcode, 1)[-1].strip()

            except Exception as e:
                err = str(e)

        self.log.error(
            "(FTP) operation failed: %s" % (err or "unknown error"))
        return False

    def download(self, remote_file, local_dir, **kwargs):
        remote_file = remote_file.strip(' /')
        remote_file = '/' + remote_file

        self.log.info("(FTP) start downloading: %s" % remote_file)

        # generate operation
        cmd = self._file_operation(
            local_dir, remote_file, is_dnload=True, **kwargs)

        if self._run_command(cmd, **kwargs):
            self.log.info("(FTP) download done: %s" % remote_file)
            return True
        else:
            self.log.error("(FTP) download failed: %s" % remote_file)
            return False

    def upload(self, local_file, remote_dir, **kwargs):
        remote_dir = remote_dir.strip(' /')
        remote_dir = '/' + remote_dir

        self.log.info("(FTP) start uploading: %s" % local_file)

        # generate operation
        cmd = self._file_operation(
            local_file, remote_dir, is_dnload=False, **kwargs)

        if self._run_command(cmd, **kwargs):
            self.log.info("(FTP) upload done: %s" % local_file)
            return True
        else:
            self.log.error("(FTP) upload failed: %s" % local_file)
            return False

    # stop current operations
    def cancel(self):
        self.term_event.set()
