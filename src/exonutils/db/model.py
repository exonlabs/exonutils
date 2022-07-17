# -*- coding: utf-8 -*-
import uuid

__all__ = []


class BaseModel(object):
    __table_name__ = ''
    __table_args__ = {}
    __table_columns__ = [
        # Usage:
        # (colname, definition [, constraint]),
        # ex:
        # ('name1', 'TEXT NOT NULL', 'INDEX UNIQUE'),
    ]
    __table_constraints__ = [
        # ex:
        # 'CHECK (field1 IN (0, 1))',
        # 'FOREIGN KEY (tbl1_id) REFERENCES tbl1 (tbl1_id)',
    ]
    __table_adapters__ = {
        # Usage:
        # 'colname': adapter_callable,
    }
    __table_converters__ = {
        # Usage:
        # 'colname': converter_callable,
    }

    def __init__(self):
        raise RuntimeError("can't create instance from model type")

    @classmethod
    def tbl_name(cls):
        return cls.__table_name__

    @classmethod
    def tbl_args(cls):
        return cls.__table_args__

    @classmethod
    def tbl_columns(cls):
        res = []
        if cls.__table_columns__[0][0] != 'guid':
            res = [('guid', 'TEXT NOT NULL', 'PRIMARY')]
        res.extend(cls.__table_columns__)
        return res

    @classmethod
    def tbl_constraints(cls):
        return cls.__table_constraints__

    @classmethod
    def tbl_adapters(cls):
        return cls.__table_adapters__

    @classmethod
    def tbl_converters(cls):
        return cls.__table_converters__

    @classmethod
    def data_adapters(cls, data):
        for colname, fn in cls.tbl_adapters().items():
            if colname in data:
                data[colname] = fn(data[colname])
        return data

    @classmethod
    def data_converters(cls, data):
        for colname, fn in cls.tbl_converters().items():
            if colname in data:
                data[colname] = fn(data[colname])
        return data

    @classmethod
    def default_orders(cls):
        cols = [c[0] for c in cls.tbl_columns()]
        if cols:
            if cols[0] != 'guid':
                return ['%s ASC' % cols[0]]
            elif len(cols) >= 2:
                return ['%s ASC' % cols[1]]
        return []

    @classmethod
    def generate_guid(cls):
        return uuid.uuid5(uuid.uuid1(), uuid.uuid4().hex).hex

    @classmethod
    def get(cls, dbs, guid, columns=[], **kwargs):
        return dbs.query(cls, **kwargs).one(
            {'guid': guid}, columns=columns)

    @classmethod
    def select(cls, dbs, filters, columns=[], groups=[], orders=[],
               limit=100, offset=-1, **kwargs):
        return dbs.query(cls, **kwargs).select(
            filters, columns=columns, groups=groups,
            orders=orders or cls.default_orders(),
            limit=limit, offset=offset)

    @classmethod
    def findall(cls, dbs, filters, columns=[], groups=[], orders=[],
                **kwargs):
        return dbs.query(cls, **kwargs).select(
            filters, columns=columns, groups=groups,
            orders=orders or cls.default_orders())

    @classmethod
    def findone(cls, dbs, filters, columns=[], groups=[], **kwargs):
        return dbs.query(cls, **kwargs).one(
            filters, columns=columns, groups=groups)

    @classmethod
    def count(cls, dbs, filters, groups=[], **kwargs):
        return dbs.query(cls, **kwargs).count(
            filters, groups=groups)

    @classmethod
    def create(cls, dbs, data, commit=True, **kwargs):
        if 'guid' not in data.keys():
            data['guid'] = cls.generate_guid()
        dbs.query(cls, **kwargs).insert(cls.data_adapters(data))
        if commit:
            dbs.commit()
        return data['guid']

    @classmethod
    def update(cls, dbs, filters, data, commit=True, **kwargs):
        if 'guid' in data.keys():
            del(data['guid'])
        res = dbs.query(cls, **kwargs).update(
            filters, cls.data_adapters(data))
        if commit:
            dbs.commit()
        return res

    @classmethod
    def delete(cls, dbs, filters, commit=True, **kwargs):
        res = dbs.query(cls, **kwargs).delete(filters)
        if commit:
            dbs.commit()
        return res

    @classmethod
    def initialize_data(cls, dbs, **kwargs):
        # Usage:
        # cls.create(dbs, ...)
        pass

    @classmethod
    def migrate_table(cls, dbs, **kwargs):
        # Usage:
        # dbs.execute(...)
        pass
