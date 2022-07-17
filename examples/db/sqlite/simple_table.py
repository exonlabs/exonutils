# -*- coding: utf-8 -*-
import sys
import logging
from pprint import pprint
from argparse import ArgumentParser

from exonutils.db.model import BaseModel
from exonutils.db.handlers import DBHandler

from exonutils.db.backends.sqlite.utils import \
    interactive_config, interactive_setup

logging.basicConfig(
    level=logging.INFO, stream=sys.stdout,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s')
logging.addLevelName(logging.WARNING, "WARN")
logging.addLevelName(logging.CRITICAL, "FATAL")

DB_OPTIONS = {
    "database": "/tmp/test.db",

    # -- Optional args --
    # "connect_timeout": 30,
    # "retries": 10,
    # "retry_delay": 0.5,
    # "isolation_level": None,
    # "foreign_keys_constraints": True,
}


class Foobar(BaseModel):
    __table_name__ = 'foobar'
    __table_columns__ = [
        ("col1", "TEXT NOT NULL", "UNIQUE INDEX"),
        ("col2", "TEXT"),
        ("col3", "INTEGER"),
        ("col4", "BOOLEAN NOT NULL DEFAULT 0"),
    ]

    @classmethod
    def initialize_data(cls, dbs, **kwargs):
        for i in range(5):
            data = cls.findone(
                dbs, "col1='foo_%s'" % i, **kwargs)
            if not data:
                cls.create(dbs, {
                    'col1': 'foo_%s' % i,
                    'col2': 'description %s' % i,
                    'col3': i,
                }, **kwargs)


def main():
    logger = logging.getLogger()
    logger.name = 'main'

    try:
        pr = ArgumentParser(prog=None)
        pr.add_argument(
            '-x', dest='debug', action='count', default=0,
            help='set debug modes')
        args = pr.parse_args()

        if args.debug > 0:
            logger.setLevel(logging.DEBUG)

        print("\nDB Options:")
        cfg = interactive_config(defaults=DB_OPTIONS)
        pprint(cfg)
        print()

        interactive_setup(cfg)
        print("DB setup: Done")

        dbh = DBHandler(cfg)
        dbh.logger = logger

        dbh.init_database([Foobar])
        print("DB initialize: Done")

        # checking DB
        print("\nAll entries:")
        with dbh.create_session() as dbs:
            for item in Foobar.findall(dbs, None):
                pprint(item)

            print("\nTotal Items: %s" % Foobar.count(dbs, None))

        print()

    except Exception as e:
        logger.fatal(str(e), exc_info=args.debug)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n-- terminated --")


if __name__ == '__main__':
    main()
