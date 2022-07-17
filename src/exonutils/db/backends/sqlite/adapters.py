# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime, date, time

__all__ = []


def register_default_adapters():

    # BOOLEAN

    def bool_adapter(value):
        return 1 if bool(value) else 0

    def bool_converter(value):
        return bool(int(value))

    sqlite3.register_adapter(bool, bool_adapter)
    sqlite3.register_converter("BOOLEAN", bool_converter)

    # DATETIME, DATE, TIME

    def _parse_datetime(value):
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d", "%H:%M:%S.%f", "%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except:
                pass
        raise ValueError("unconverted datetime format")

    def datetime_adapter(value):
        if value:
            return value.strftime("%Y-%m-%d %H:%M:%S.%f")
        return None

    def datetime_converter(value):
        if value:
            return _parse_datetime(value.decode())
        return None

    def date_adapter(value):
        if value:
            return value.strftime("%Y-%m-%d")
        return None

    def date_converter(value):
        if value:
            return _parse_datetime(value.decode()).date()
        return None

    def time_adapter(value):
        if value:
            return value.strftime("%H:%M:%S.%f")
        return None

    def time_converter(value):
        if value:
            return _parse_datetime(value.decode()).time()
        return None

    sqlite3.register_adapter(datetime, datetime_adapter)
    sqlite3.register_converter("DATETIME", datetime_converter)
    sqlite3.register_adapter(date, date_adapter)
    sqlite3.register_converter("DATE", date_converter)
    sqlite3.register_adapter(time, time_adapter)
    sqlite3.register_converter("TIME", time_converter)
