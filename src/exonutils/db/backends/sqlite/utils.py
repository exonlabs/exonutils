# -*- coding: utf-8 -*-
import os
from exonutils.utils.console import Console

__all__ = []


# get database config options
def interactive_config(defaults={}):
    options = {
        'backend': 'sqlite',
    }

    ch = Console()
    options['database'] = ch.get_value(
        "Enter db path",
        default=defaults.get('database'),
        required=True)

    return options


# database backend setup
def interactive_setup(options):
    database = options.get('database')
    if not database:
        raise ValueError("invalid database configuration")

    # create db file
    if not os.path.exists(os.path.dirname(database)):
        os.makedirs(os.path.dirname(database))
    open(database, 'a').close()

    return True
