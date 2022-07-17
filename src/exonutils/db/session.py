# -*- coding: utf-8 -*-
import re
import copy
import logging

__all__ = []


class BaseSession(object):

    def __init__(self, options={}):
        self.options = copy.deepcopy(options)
        self.logger = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _log_sql(self, sql, params=None):
        if self.logger and self.logger.level == logging.DEBUG:
            # clean extra newlines with spaces
            sql = re.sub('\n\\s+', '\n', sql).strip()
            self.logger.debug(
                "SQL:\n---\n%s\nParams: %s\n---" % (sql, params))

    def query(self, model, **kwargs):
        raise NotImplementedError()

    def is_connected(self):
        raise NotImplementedError()

    def connect(self):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()

    def execute(self, sql, params=None):
        raise NotImplementedError()

    def fetchone(self):
        raise NotImplementedError()

    def fetchall(self):
        raise NotImplementedError()

    def rowcount(self):
        raise NotImplementedError()

    def lastrowid(self):
        raise NotImplementedError()

    def commit(self):
        raise NotImplementedError()

    def rollback(self):
        raise NotImplementedError()
