# -*- coding: utf-8 -*-
from .common import sql_identifier

__all__ = []


class BaseQuery(object):

    def __init__(self, dbs, model, **kwargs):
        self.dbs = dbs
        self.model = model

        # set runtime table name to use, this allows for mapping
        # same model to multiple tables
        self.tbl_name = sql_identifier(
            kwargs.get('tbl_name') or self.model.tbl_name())

    # columns (list): [col1, col2 ...]
    @classmethod
    def parse_columns(cls, columns):
        if columns:
            return ", ".join([sql_identifier(v) for v in columns])
        return "*"

    @classmethod
    def parse_filters(cls, filters):
        if type(filters) is str:
            return filters, None
        elif type(filters) in [list, tuple]:
            return filters[0], filters[1]
        elif type(filters) is dict:
            fltrs, params = [], []
            for k, v in filters.items():
                fltrs.append('%s=?' % sql_identifier(k))
                params.append(v)
            return ' AND '.join(fltrs), params

        raise ValueError("invalid filters type")

    # groups (list): [col1, col2 ...]
    @classmethod
    def parse_groups(cls, groups):
        return ", ".join([
            sql_identifier(v) for v in groups])

    # orders (list): [col1 ASC|DESC, col2 ASC|DESC ...]
    @classmethod
    def parse_orders(cls, orders):
        res = []
        for v in orders:
            a, b = v.rsplit(" ", 1)
            res.append("%s %s" % (
                sql_identifier(a),
                b.upper() if b.upper() in ['ASC', 'DESC'] else 'ASC'))
        return ", ".join(res)

    # return all elements matching select query
    def select(self, filters, columns=[], groups=[], orders=[],
               limit=-1, offset=-1):
        q = "SELECT %s FROM %s" % (
            self.parse_columns(columns), self.tbl_name)
        if filters:
            filters, execargs = self.parse_filters(filters)
            q += "\nWHERE %s" % filters
        else:
            execargs = []
        if groups:
            q += "\nGROUP BY %s" % self.parse_groups(groups)
        if orders:
            q += "\nORDER BY %s" % self.parse_orders(orders)
        if limit >= 0:
            q += "\nLIMIT %s" % int(limit)
        if offset >= 0:
            q += "\nOFFSET %s" % int(offset)
        q += ";"

        self.dbs.execute(q, params=execargs)
        return self.dbs.fetchall()

    # return first element matching select query or None
    def first(self, filters, columns=[], groups=[], orders=[]):
        res = self.select(
            filters, columns=columns, groups=groups, orders=orders,
            limit=1, offset=-1)
        if res:
            return res[0]

        return None

    # return one element matching select query or None
    # there must be only one element if exists
    def one(self, filters, columns=[], groups=[]):
        res = self.select(
            filters, columns=columns, groups=groups, limit=2)
        if res:
            if len(res) > 1:
                raise ValueError("multiple entries found")
            return res[0]

        return None

    def count(self, filters, groups=[]):
        q = "SELECT count(*) as count FROM %s" % self.tbl_name
        if filters:
            filters, execargs = self.parse_filters(filters)
            q += "\nWHERE %s" % filters
        else:
            execargs = []
        if groups:
            q += "\nGROUP BY %s" % self.parse_groups(groups)
        q += ";"

        self.dbs.execute(q, params=execargs)
        res = self.dbs.fetchone()
        return res['count']

    def insert(self, data):
        if type(data) is not dict:
            raise ValueError("invalid data type")

        columns, params = [], []
        for k, v in data.items():
            columns.append(sql_identifier(k))
            params.append(v)

        q = "INSERT INTO %s" % self.tbl_name
        q += "\n(%s)" % ", ".join(columns)
        q += "\nVALUES"
        q += "\n(%s)" % ", ".join(['?'] * len(columns))
        q += ";"

        self.dbs.execute(q, params=params)
        return self.dbs.rowcount()

    def update(self, filters, data):
        if type(data) is not dict:
            raise ValueError("invalid data type")

        columns, params = [], []
        for k, v in data.items():
            if type(v) is str and 'CASE' in v:
                columns.append('%s=%s' % (sql_identifier(k), v))
            else:
                columns.append('%s=?' % sql_identifier(k))
                params.append(v)

        q = "UPDATE %s" % self.tbl_name
        q += "\nSET %s" % ", ".join(columns)
        if filters:
            filters, execargs = self.parse_filters(filters)
            q += "\nWHERE %s" % filters
        else:
            execargs = []
        q += ";"

        params.extend(execargs)
        self.dbs.execute(q, params=params)
        return self.dbs.rowcount()

    def delete(self, filters):
        q = "DELETE FROM %s" % self.tbl_name
        if filters:
            filters, execargs = self.parse_filters(filters)
            q += "\nWHERE %s" % filters
        else:
            execargs = []
        q += ";"

        self.dbs.execute(q, params=execargs)
        return self.dbs.rowcount()

    def create_table(self):
        raise NotImplementedError()
