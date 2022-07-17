# -*- coding: utf-8 -*-
from importlib import import_module

__all__ = []


# get database config options
def interactive_config(backend, defaults={}):
    try:
        mod = import_module(
            '.%s.utils' % backend, package='exonutils.db.backends')
    except ImportError:
        raise ValueError("invalid DB backend: %s" % backend)

    options = {
        'backend': backend,
    }
    options.update(mod.interactive_config(defaults=defaults))

    return options


# database backend setup
def interactive_setup(backend, options):
    try:
        mod = import_module(
            '.%s.utils' % backend, package='exonutils.db.backends')
    except ImportError:
        raise ValueError("invalid DB backend: %s" % backend)

    return mod.interactive_setup(options)
