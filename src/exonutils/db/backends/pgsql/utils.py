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
        default=defaults.get('port', 5432),
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
        from psycopg2 import connect
    except ImportError:
        raise RuntimeError("[psycopg2] backend package not installed")

    host = options.get('host') or 'localhost'
    port = int(options.get('port') or 5432)

    database = options.get('database', None)
    if not database:
        raise ValueError("invalid empty database name")
    username = options.get('username', None)
    if not username:
        raise ValueError("invalid empty database username")
    password = options.get('password', None)
    if not password:
        raise ValueError("invalid empty database password")

    # get superuser access for database setup
    ch = Console()
    adm_user = ch.get_value(
        "Enter DB admin user", default='postgres')
    adm_pass = ch.get_password(
        "Enter DB admin password", default='')

    # create connection
    conn = connect(
        host=host, port=port, user=adm_user, password=adm_pass,
        database='postgres', client_encoding='utf8')
    conn.set_session(autocommit=True)

    # create role
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM pg_roles WHERE rolname='%s';"
        % (username))
    if not cur.fetchall():
        cur.execute(
            "CREATE ROLE %s LOGIN PASSWORD '%s';"
            % (username, password))
    else:
        cur.execute(
            "ALTER ROLE %s WITH PASSWORD '%s';"
            % (username, password))
    cur.close()

    # create database
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM pg_database WHERE datname='%s';"
        % (database))
    if not cur.fetchall():
        cur.execute(
            "CREATE DATABASE %s OWNER %s ENCODING 'UTF8'"
            % (database, username) +
            " LC_COLLATE 'en_US.UTF-8' LC_CTYPE 'en_US.UTF-8';")
    cur.close()

    # grant privileges
    cur = conn.cursor()
    cur.execute(
        "GRANT ALL PRIVILEGES ON DATABASE %s TO %s;"
        % (database, username))
    cur.close()

    conn.close()
    return True
