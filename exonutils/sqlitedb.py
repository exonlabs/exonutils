# -*- coding: utf-8 -*-
"""
    :copyright: 2021, ExonLabs. All rights reserved.
    :license: BSD, see LICENSE for more details.
"""
import re
import uuid
import logging
import sqlite3

__all__ = []

_logger = logging.getLogger('sqlitedb')


class BaseModel(object):
    __tablename__ = ''
    __table_args__ = {}
    __table_columns__ = [
        # Usage:
        # (colname, definition [, constraint]),
        # ex:
        # ('name1', 'VARCHAR(32) NOT NULL', 'INDEX UNIQUE'),
    ]
    __table_constraints__ = [
        # ex:
        # 'CHECK (field1 IN (0, 1))',
        # 'FOREIGN KEY (tbl1_id) REFERENCES tbl1 (tbl1_id)',
    ]

    def __init__(self, data):
        for k in self._columns():
            setattr(self, k[0], data[k[0]])

    def __repr__(self):
        attrs = [k[0] for k in self._columns()][1:]
        return "%s(%s)" % (
            self.__class__.__name__,
            ', '.join(['%s=%s' % (a, getattr(self, a)) for a in attrs]))

    @classmethod
    def _columns(cls):
        cols = [('guid', 'VARCHAR(32) NOT NULL', 'PRIMARY')]
        cols.extend(cls.__table_columns__)
        return cols

    @classmethod
    def _constraints(cls):
        return cls.__table_constraints__

    @classmethod
    def _orders(cls):
        # return string 'col1 ASC, col2 DESC ...'
        cols = [k[0] for k in cls._columns()][1:]
        if cols:
            return '%s ASC' % cols[0]
        return None

    def modify(self, dbs, data, commit=True):
        if 'guid' in data.keys():
            del(data['guid'])
        q = dbs.query(self.__class__)
        q.filter_by(guid=self.guid).update(data)
        if commit:
            dbs.commit()
        return True

    def remove(self, dbs, commit=True):
        q = dbs.query(self.__class__)
        q.filter_by(guid=self.guid).delete()
        if commit:
            dbs.commit()
        return True

    @classmethod
    def get(cls, dbs, guid):
        return dbs.query(cls).filter_by(guid=guid).one_or_none()

    @classmethod
    def select(cls, dbs, filters=None, orders=None, limit=100, offset=0):
        q = dbs.query(cls)
        if filters:
            q = q.filter(filters)
        orders = orders or cls._orders()
        if orders:
            q = q.order_by(orders)
        return q.limit(limit).offset(offset).all() or []

    @classmethod
    def find_all(cls, dbs, filters, orders=None):
        q = dbs.query(cls)
        if filters:
            q = q.filter(filters)
        orders = orders or cls._orders()
        if orders:
            q = q.order_by(orders)
        return q.all() or []

    @classmethod
    def find_one(cls, dbs, filters):
        q = dbs.query(cls)
        if filters:
            q = q.filter(filters)
        return q.one_or_none()

    @classmethod
    def count(cls, dbs, filters):
        q = dbs.query(cls)
        if filters:
            q = q.filter(filters)
        return q.count()

    @classmethod
    def create(cls, dbs, data, commit=True):
        data['guid'] = uuid.uuid5(uuid.uuid1(), uuid.uuid4().hex).hex
        obj = cls(data)
        dbs.query(cls).insert(data)
        if commit:
            dbs.commit()
        return obj

    @classmethod
    def update(cls, dbs, filters, data, commit=True):
        if 'guid' in data.keys():
            del(data['guid'])
        q = dbs.query(cls)
        if filters:
            q = q.filter(filters)
        res = q.update(data)
        if commit:
            dbs.commit()
        return res

    @classmethod
    def delete(cls, dbs, filters, commit=True):
        q = dbs.query(cls)
        if filters:
            q = q.filter(filters)
        res = q.delete()
        if commit:
            dbs.commit()
        return res

    @classmethod
    def initial_data(cls, dbs):
        # Usage:
        # cls.create(dbs, ...)
        pass

    @classmethod
    def table_migrate(cls, dbs):
        # Usage:
        # dbs.executescript(...)
        pass


class _Query(object):

    def __init__(self, dbs, model):
        self.dbs = dbs
        self.Model = model

        self._filters = None
        self._filterparams = None
        self._groupby = None
        self._orderby = None
        self._limit = None
        self._offset = None

    def filter(self, filters):
        if type(filters) is str:
            self._filters = filters
        elif type(filters) is list:
            self._filters = filters[0]
            self._filterparams = filters[1]
        else:
            raise RuntimeError("unsupported filters type")
        return self

    def filter_by(self, **kwargs):
        self._filters = ' AND '.join([
            '%s=:%s' % (k, k) for k in kwargs.keys()])
        self._filterparams = kwargs
        return self

    def group_by(self, groupby):
        self._groupby = groupby
        return self

    def order_by(self, orderby):
        self._orderby = orderby
        return self

    def limit(self, limit):
        self._limit = limit
        return self

    def offset(self, offset):
        self._offset = offset
        return self

    def all(self):
        q = 'SELECT * FROM "%s"' % self.Model.__tablename__
        if self._filters:
            q += '\nWHERE %s' % self._filters
        if self._groupby:
            q += '\nGROUP BY %s' % self._groupby
        if self._orderby:
            q += '\nORDER BY %s' % self._orderby
        if self._limit:
            q += '\nLIMIT %s' % self._limit
        if self._offset:
            q += '\nOFFSET %s' % self._offset
        q += ';'

        self.dbs.execute(q, params=self._filterparams)
        res = self.dbs.fetchall()
        if res:
            return [self.Model(d) for d in res]

        return None

    def first(self):
        q = 'SELECT * FROM "%s"' % self.Model.__tablename__
        if self._filters:
            q += '\nWHERE %s' % self._filters
        if self._groupby:
            q += '\nGROUP BY %s' % self._groupby
        if self._orderby:
            q += '\nORDER BY %s' % self._orderby
        q += '\nLIMIT 1;'

        self.dbs.execute(q, params=self._filterparams)
        res = self.dbs.fetchall()
        if res:
            return self.Model(res[0])

        return None

    def one(self):
        res = self.one_or_none()
        if res:
            return res

        raise RuntimeError("no results found")

    def one_or_none(self):
        q = 'SELECT * FROM "%s"' % self.Model.__tablename__
        if self._filters:
            q += '\nWHERE %s' % self._filters
        if self._groupby:
            q += '\nGROUP BY %s' % self._groupby
        if self._orderby:
            q += '\nORDER BY %s' % self._orderby
        q += '\nLIMIT 2;'

        self.dbs.execute(q, params=self._filterparams)
        res = self.dbs.fetchall()
        if res:
            if len(res) > 1:
                raise RuntimeError("multiple entries found")
            return self.Model(res[0])

        return None

    def count(self):
        q = 'SELECT count(*) as count FROM "%s"' % self.Model.__tablename__
        if self._filters:
            q += '\nWHERE %s' % self._filters
        if self._groupby:
            q += '\nGROUP BY %s' % self._groupby
        q += ';'

        self.dbs.execute(q, params=self._filterparams)
        res = self.dbs.fetchall()
        if res:
            return res[0]['count']

        return 0

    def insert(self, data):
        if type(data) is not dict:
            raise RuntimeError("invalid data type, dict required")

        attrs = list(data.keys())

        q = 'INSERT INTO "%s"' % self.Model.__tablename__
        q += '\n("%s")' % '", "'.join([k for k in attrs])
        q += '\nVALUES'
        q += '\n(%s)' % ', '.join([':%s' % k for k in attrs])
        q += ';'

        return self.dbs.execute(q, params=data)

    def update(self, data):
        if type(data) is not dict:
            raise RuntimeError("invalid data type, dict required")

        params = {'%s_1' % k: v for k, v in data.items()}

        q = 'UPDATE "%s"' % self.Model.__tablename__
        q += '\nSET %s' % ', '.join([
            '"%s"=:%s_1' % (k, k) for k in data.keys()])
        if self._filters:
            q += '\nWHERE %s' % self._filters
            if self._filterparams:
                if type(self._filterparams) is not dict:
                    raise RuntimeError(
                        "invalid filter params data type, dict required")
                params.update(self._filterparams)
        q += ';'

        self.dbs.execute(q, params=params)
        return self.dbs.rowcount()

    def delete(self):
        q = 'DELETE FROM "%s"' % self.Model.__tablename__
        if self._filters:
            q += '\nWHERE %s' % self._filters
        q += ';'

        self.dbs.execute(q, params=self._filterparams)
        return self.dbs.rowcount()


class _Session(object):

    connect_timeout = 30

    def __init__(self, database, debug=0):
        self.debug = debug
        self.database = database
        self.connection = None
        self.cursor = None

    def connect(self):
        if self.debug >= 4:
            global _logger
            _logger.debug("(%s) open connection" % self.database)
        self.connection = sqlite3.connect(
            self.database,
            timeout=self.connect_timeout,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.connection.isolation_level = None
        self.connection.row_factory = sqlite3.Row

    def close(self):
        if self.connection:
            if self.debug >= 4:
                global _logger
                _logger.debug("(%s) close connection" % self.database)
            self.connection.close()
        self.connection = None

    def query(self, model):
        return _Query(self, model)

    def _sql_log(self, sql, params=None):
        global _logger
        # clean extra newlines with spaces
        sql = re.sub('\n\\s+', '\n', sql).strip()
        _logger.info("SQL:\n---\n%s\n---" % sql)
        if params:
            _logger.info("PARAMS: %s" % params)

    def execute(self, sql, params=None):
        if not self.connection:
            self.connect()
        if self.debug >= 4:
            self._sql_log(sql, params=params)
        if not self.cursor:
            self.cursor = self.connection.cursor()
        if params:
            self.cursor.execute(sql, params)
        else:
            self.cursor.execute(sql)
        return True

    def executescript(self, sql_script):
        if not self.connection:
            self.connect()
        if self.debug >= 4:
            self._sql_log(sql_script)
        if not self.cursor:
            self.cursor = self.connection.cursor()
        self.cursor.executescript(sql_script)
        return True

    def fetchone(self):
        if self.cursor:
            return self.cursor.fetchone()
        return None

    def fetchall(self):
        if self.cursor:
            return self.cursor.fetchall()
        return None

    def rowcount(self):
        if self.cursor:
            return self.cursor.rowcount
        return None

    def lastrowid(self):
        if self.cursor:
            return self.cursor.lastrowid
        return None

    def commit(self):
        if self.debug >= 4:
            global _logger
            _logger.debug("(%s) commit" % self.database)
        if self.connection:
            self.connection.commit()
            return True
        return False

    def rollback(self):
        if self.debug >= 4:
            global _logger
            _logger.debug("(%s) rollback" % self.database)
        if self.connection:
            self.connection.rollback()
            return True
        return False


class SessionHandler(object):

    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._session.close()


class DatabaseHandler(object):

    def __init__(self, database, debug=0):
        self.debug = debug
        self.database = database

    def session_factory(self):
        return _Session(self.database, debug=self.debug)

    def session_handler(self):
        return SessionHandler(self.session_factory())


# adjust logging for sqlite
def init_logging(debug=0):
    global _logger
    if debug >= 5:
        _logger.setLevel(logging.DEBUG)
    elif debug >= 4:
        _logger.setLevel(logging.INFO)
    else:
        _logger.setLevel(logging.ERROR)


# create database tables and initial data
def init_database(dbh, models):
    # create database structure
    with dbh.session_handler() as dbs:
        for Model in models:
            dbs.executescript(_sql_create_table(Model))
            dbs.commit()

    # execute migrations
    with dbh.session_handler() as dbs:
        for Model in models:
            Model.table_migrate(dbs)

    # load initial models data
    with dbh.session_handler() as dbs:
        for Model in models:
            Model.initial_data(dbs)

    return True


def _sql_create_table(model):
    if not model.__table_columns__:
        return ''

    columns, constraints, indexes = [], [], []
    for k in model._columns():
        columns.append('"%s" %s' % (k[0], k[1]))
        if len(k) <= 2:
            continue

        if 'PRIMARY' in k[2]:
            constraints.append('PRIMARY KEY ("%s")' % k[0])
        elif 'UNIQUE' in k[2] and 'INDEX' not in k[2]:
            constraints.append('UNIQUE ("%s")' % k[0])

        if 'PRIMARY' in k[2] or 'INDEX' in k[2]:
            u = 'UNIQUE ' if 'PRIMARY' in k[2] or 'UNIQUE' in k[2] else ''
            indexes.append(
                'CREATE %sINDEX IF NOT EXISTS ' % u +
                '"ix_%s_%s" ' % (model.__tablename__, k[0]) +
                'ON "%s" ("%s");' % (model.__tablename__, k[0]))

    defs = columns
    defs.extend(constraints)
    defs.extend(model._constraints())

    sql = 'CREATE TABLE IF NOT EXISTS "%s" (\n' % model.__tablename__
    sql += ',\n'.join(defs)
    if model.__table_args__.get('without_rowid', False):
        sql += '\n) WITHOUT ROWID;\n'
    else:
        sql += '\n);\n'
    sql += '\n'.join(indexes)

    return sql
