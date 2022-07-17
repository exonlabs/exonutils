# -*- coding: utf-8 -*-
from exonutils.utils.console import Console

__all__ = []


# get database config options
def interactive_config(defaults={}):
    options = {}

    ch = Console()
    options['database'] = ch.get_value(
        "Enter db name", required=True)
    options['host'] = ch.get_value(
        "Enter db host",
        default=defaults.get('host', 'localhost'),
        required=True)
    options['port'] = ch.get_number(
        "Enter db port",
        default=defaults.get('port', 1433),
        required=True)
    options['username'] = ch.get_value(
        "Enter db username",
        default=defaults.get('username'),
        required=True)
    options['password'] = ch.get_password(
        "Enter db password",
        default=defaults.get('password'),
        required=True)
    ch.confirm_password(
        "Confirm db password", options['password'])

    return options


# database backend setup
def interactive_setup(options):
    try:
        from pymssql import connect
    except ImportError:
        raise RuntimeError("[pymssql] backend package not installed")

    host = options.get('host') or 'localhost'
    port = int(options.get('port') or 1433)

    database = options.get('database', None)
    if not database:
        raise ValueError("invalid empty database name")
    username = options.get('username', None)
    if not username:
        raise ValueError("invalid empty database username")
    password = options.get('password', None)
    if not password:
        raise ValueError("invalid empty database password")

    # create connection
    conn = connect(
        host=host, port=port, user=username, password=password,
        charset='utf8', login_timeout=10)

    # create database
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sys.databases WHERE name='%s'" % database)
    if not cur.fetchall():
        raise RuntimeError("database doesn't exist on server")
    cur.close()

    conn.close()
    return True
