# -*- coding: utf-8 -*-
import time
import sqlite3

from exonutils.db.session import BaseSession
from .query import Query

__all__ = []


class Session(BaseSession):

    def __init__(self, options={}):
        super(Session, self).__init__(options=options)

        self._connection = None
        self._cursor = None

    def query(self, model, **kwargs):
        return Query(self, model, **kwargs)

    def is_connected(self):
        return bool(self._connection)

    def connect(self):
        if not self._connection:
            if not self.options.get('database'):
                raise ValueError("invalid database configuration")

            self.logger.debug(
                "(%s) - connect" % self.options['database'])

            self._connection = sqlite3.connect(
                self.options['database'],
                timeout=self.options.get('connect_timeout', 10),
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

            self._connection.isolation_level = \
                self.options.get('isolation_level', None)
            self._connection.row_factory = lambda cur, row: {
                col[0]: row[idx] for idx, col in enumerate(cur.description)}

        if not self._cursor:
            self._cursor = self._connection.cursor()
            if self.options.get('foreign_keys_constraints', True):
                self._cursor.execute('PRAGMA foreign_keys=ON')

    def close(self):
        if self._connection:
            self.logger.debug(
                "(%s) - close" % self.options['database'])
            self._connection.close()

        self._connection = None
        self._cursor = None

    def execute(self, sql, params=None):
        self.connect()
        self._log_sql(sql, params=params)

        retries = self.options.get('retries') or 10
        retry_delay = self.options.get('retry_delay') or 0.3

        err = ""
        for i in range(retries):
            try:
                if params:
                    self._cursor.execute(sql, params)
                else:
                    self._cursor.execute(sql)
                return
            except ValueError:
                raise
            except (sqlite3.NotSupportedError, sqlite3.IntegrityError,
                    sqlite3.ProgrammingError) as e:
                err = str(e)
                break
            except Exception as e:
                err = str(e)

            time.sleep(retry_delay)

        raise RuntimeError(err)

    def executescript(self, sql_script):
        self.connect()
        self._log_sql(sql_script)

        retries = self.options.get('retries') or 10
        retry_delay = self.options.get('retry_delay') or 0.3

        err = ""
        for i in range(retries):
            try:
                self._cursor.executescript(sql_script)
                return
            except ValueError:
                raise
            except (sqlite3.NotSupportedError, sqlite3.IntegrityError,
                    sqlite3.ProgrammingError) as e:
                err = str(e)
                break
            except Exception as e:
                err = str(e)

            time.sleep(retry_delay)

        raise RuntimeError(err)

    def fetchone(self):
        if not self._connection:
            raise RuntimeError("not connected")

        return self._cursor.fetchone()

    def fetchmany(self, size=10):
        if not self._connection:
            raise RuntimeError("not connected")

        return self._cursor.fetchmany(size=size)

    def fetchall(self):
        if not self._connection:
            raise RuntimeError("not connected")

        return self._cursor.fetchall()

    def rowcount(self):
        if not self._connection:
            raise RuntimeError("not connected")

        return self._cursor.rowcount

    def lastrowid(self):
        if not self._connection:
            raise RuntimeError("not connected")

        return self._cursor.lastrowid

    def commit(self):
        if not self._connection:
            raise RuntimeError("not connected")

        self.logger.debug("(%s) - commit" % self.options['database'])
        self._connection.commit()

    def rollback(self):
        if not self._connection:
            raise RuntimeError("not connected")

        self.logger.debug("(%s) - rollback" % self.options['database'])
        self._connection.rollback()
