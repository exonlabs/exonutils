# -*- coding: utf-8 -*-
import re

__all__ = []


def sql_identifier(name):
    name = str(name)
    if not name:
        raise ValueError("invalid empty sql identifier")

    if not re.match("^[a-zA-Z0-9_]+$", name):
        raise ValueError("invalid sql identifier [%s]" % name)

    return name
