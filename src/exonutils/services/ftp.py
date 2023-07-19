# -*- coding: utf-8 -*-
import os
import time
import ssl
import ftplib
import threading
import logging

"""
FTP client supporting TLS v1.2/1.3

FTP Options
{
    'host': 'x.x.x.x',           # FTP server IP address
    'port': 21,                  # FTP server port
    'username': 'username',      # access username
    'password': 'password',      # access password
    'dir_path': '/',             # upload path on FTP server

    'transfer_mode': 'Passive',  # transfer mode: Passive|Active
    'transfer_blksize': 1024,    # max block size for sending files

    'tls_enable': True,          # enable TLS connection
    'tls_protocol': 'Explicit'   # TLS operation mode: Explicit|Implicit
                                   (default explicit TLS over FTP port)
    'tls_version': 'Auto',       # TLS version: Auto|TLSv1_2|TLSv1_3
}
"""


# class _ReusedSslSocket(ssl.SSLSocket):

#     def unwrap(self):
#         pass


class _ExplicitFtpTls(ftplib.FTP_TLS):

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(
                conn, server_hostname=self.host,
                session=self.sock.session)
            # conn.__class__ = _ReusedSslSocket
        return conn, size

    # TMP FIX: till python ssl lib is compatible with TLS 1.3
    def storbinary(self, cmd, fp, blocksize=8192, callback=None, rest=None):
        self.voidcmd('TYPE I')
        with self.transfercmd(cmd, rest) as conn:
            while True:
                buf = fp.read(blocksize)
                if not buf:
                    break
                conn.sendall(buf)
                if callback:
                    callback(buf)
            # if isinstance(conn, ssl.SSLSocket):
            #     conn.unwrap()

            # delay to allow file save on server side
            time.sleep(1)

        # make dummy command to clear previous connection error
        try:
            self.abort()
            return self.voidresp()
        except Exception:
            pass

        return '200'


class _ImplicitFtpTls(_ExplicitFtpTls):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sock = None

    @property
    def sock(self):
        return self._sock

    @sock.setter
    def sock(self, value):
        if value is not None and not isinstance(value, ssl.SSLSocket):
            value = self.context.wrap_socket(value)
        self._sock = value


class FTPClient(object):

    def __init__(self, options, logger=None):
        self.options = options
        # ftp logger
        self.log = logger or logging.getLogger()
        # debug mode
        self.debug = bool(self.log.level == logging.DEBUG)

        # stop event
        self.term_event = threading.Event()

        self._ftphnd = None

    def _connect(self):
        host = self.options.get('host')
        port = int(self.options.get('port', 0))

        self.log.info(
            "(FTP) starting connection: %s:%s" % (host, port))

        tls_enable = bool(self.options.get('tls_enable'))
        tls_explicit = bool(
            self.options.get('tls_protocol') != 'Implicit')
        timeout = int(self.options.get('timeout') or 30)

        # create connection handler
        if tls_enable:
            ssl_ctx = ssl.create_default_context(
                purpose=ssl.Purpose.CLIENT_AUTH)

            tls_ver = self.options.get('tls_version') or 'Auto'
            if tls_ver == 'TLSv1_2':
                ssl_ctx.options |= ssl.OP_NO_TLSv1_3

            if tls_explicit:
                self._ftphnd = _ExplicitFtpTls(
                    context=ssl_ctx, timeout=timeout)
            else:
                self._ftphnd = _ImplicitFtpTls(
                    context=ssl_ctx, timeout=timeout)
        else:
            self._ftphnd = ftplib.FTP(timeout=timeout)

        # # for testing only
        # self._ftphnd.set_debuglevel(1)

        # set transfer mode
        trans_mode = self.options.get('transfer_mode') or 'Passive'
        self._ftphnd.set_pasv(trans_mode != 'Active')

        # open connection
        self._ftphnd.connect(host, port)

        # activate TLS mode
        if tls_enable:
            if tls_explicit:
                self._ftphnd.auth()
            self._ftphnd.prot_p()

        # set login
        self._ftphnd.login(
            self.options.get('username') or 'anonymous',
            self.options.get('password') or '')

    def _disconnect(self):
        try:
            if self._ftphnd:
                self._ftphnd.quit()
                self.log.info("(FTP) disconnected")
        except Exception:
            pass

        self._ftphnd = None

    def _file_operation(self, local_path, remote_path, is_dnload=True,
                        **kwargs):
        host = self.options.get('host')
        if not host:
            raise ValueError("INVALID_PARAMS - no ftp host defined")
        port = int(self.options.get('port', 0))
        if not port:
            raise ValueError("INVALID_PARAMS - no ftp port defined")

        if not self.options.get('tls_enable'):
            self.log.warning("(FTP) using non-secure connection")

        remote_dir_parts = ["/"]

        # download mode: local_path -> dir, remote_path -> file
        if is_dnload:
            if not remote_path:
                raise ValueError("INVALID_PARAMS - invalid remote_path")
            local_path = os.path.join(
                local_path, remote_path.split('/')[-1])
            remote_dir_parts.extend(remote_path.split('/')[:-1])
            cmd = 'RETR %s' % os.path.basename(local_path)
        # upload mode: local_path -> file, remote_path -> dir
        else:
            remote_dir_parts.extend(remote_path.split('/'))
            cmd = 'STOR %s' % os.path.basename(local_path)

        self.term_event.clear()

        retries = int(kwargs.get('retries') or 0)
        retry_delay = int(kwargs.get('retry_delay') or 5)
        block = int(self.options.get('transfer_blksize') or 1024)

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

                self._connect()

                # set remote path
                for n in remote_dir_parts:
                    if n:
                        self._ftphnd.cwd(n)

                if is_dnload:
                    with open(local_path, 'wb') as fh:
                        self._ftphnd.retrbinary(
                            cmd, fh.write, blocksize=block)
                else:
                    with open(local_path, 'rb') as fh:
                        self._ftphnd.storbinary(
                            cmd, fh, blocksize=block)

                self._disconnect()
                return True

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
        res = self._file_operation(
            local_dir, remote_file, is_dnload=True, **kwargs)

        if res:
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
        res = self._file_operation(
            local_file, remote_dir, is_dnload=False, **kwargs)

        if res:
            self.log.info("(FTP) upload done: %s" % local_file)
            return True
        else:
            self.log.error("(FTP) upload failed: %s" % local_file)
            return False

    # stop current operations
    def cancel(self):
        self.term_event.set()
