# -*- coding: utf-8 -*-
import copy
from importlib import import_module

__all__ = []


class DBHandler(object):

    def __init__(self, options={}):
        self.options = copy.deepcopy(options)
        self.logger = None

        backend = self.options.get('backend')
        try:
            mod = import_module(
                '.%s.session' % backend, package='exonutils.db.backends')
        except ImportError:
            raise ValueError("invalid DB backend: %s" % backend)

        self.backend = backend
        self.session_factory = mod.Session

    # return session handler object
    def create_session(self):
        session = self.session_factory(options=self.options)
        session.logger = self.logger
        return session

    # create database tables and initialize data
    def init_database(self, models):
        # create database structure
        with self.create_session() as dbs:
            for model in models:
                dbs.query(model).create_table()

        # execute migrations
        with self.create_session() as dbs:
            for model in models:
                model.migrate_table(dbs)

        # load initial models data
        with self.create_session() as dbs:
            for model in models:
                model.initialize_data(dbs)

        return True
