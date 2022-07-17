# -*- coding: utf-8 -*-
import copy
import sqlalchemy as sa

__all__ = []


class DBHandler(object):

    def __init__(self, options={}):
        self.options = copy.deepcopy(options)
        self.logger = None

        backend = self.options.get('backend')
        if backend == 'sqlite':
            driver = 'sqlite'
            query_opts = {}
        elif backend == 'pgsql':
            driver = 'postgresql+psycopg2'
            query_opts = {'client_encoding': 'utf8'}
        elif backend == 'mysql':
            driver = 'mysql+mysqldb'
            query_opts = {'charset': 'utf8mb4'}
        elif backend == 'mssql':
            driver = 'mssql+pymssql'
            query_opts = {'charset': 'utf8'}
        else:
            raise RuntimeError("invalid backend: %s" % backend)

        self.url = sa.engine.url.URL(
            driver,
            database=self.options.get('database'),
            host=self.options.get('host'),
            port=self.options.get('port'),
            username=self.options.get('username'),
            password=self.options.get('password'),
            query=query_opts,
        )

        self.engine = None
        self.backend = backend
        self.session_factory = None

    def init_engine(self, **kwargs):
        if not self.url:
            raise RuntimeError("invalid engine URL")

        backend = self.url.get_backend_name()
        if backend == 'sqlite':
            self.engine = sa.create_engine(
                self.url, poolclass=sa.pool.NullPool)
        else:
            pool = kwargs.get('pool')
            connect_timeout = kwargs.get('connect_timeout') or 0
            query_timeout = kwargs.get('query_timeout') or 0

            if backend == 'pgsql':
                connect_args = {
                    'connect_timeout': connect_timeout,
                    'options': "-c statement_timeout=%s" % query_timeout,
                }
            elif backend == 'mysql':
                connect_args = {
                    'connect_timeout': connect_timeout,
                    'read_timeout': query_timeout,
                    'write_timeout': query_timeout,
                }
            elif backend == 'mssql':
                connect_args = {
                    'login_timeout': connect_timeout,
                    'timeout': query_timeout,
                }
            else:
                connect_args = {}

            if pool and pool.get('size', 0) > 0:
                self.engine = sa.create_engine(
                    self.url,
                    pool_size=pool['size'],
                    max_overflow=pool.get('overflow', 8),
                    pool_timeout=pool.get('timeout', 10),
                    pool_recycle=pool.get('recycle', 1800),
                    connect_args=connect_args)
            else:
                self.engine = sa.create_engine(
                    self.url,
                    poolclass=sa.pool.NullPool,
                    connect_args=connect_args)

    def create_session(self):
        if not self.session_factory:
            if not self.engine:
                self.init_engine()
            self.session_factory = sa.orm.scoped_session(
                sa.orm.sessionmaker(bind=self.engine))

        return self.session_factory
