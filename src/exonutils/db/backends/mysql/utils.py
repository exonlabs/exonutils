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
        default=defaults.get('port', 3306),
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
        from MySQLdb import connect
    except ImportError:
        raise RuntimeError("[mysqlclient] backend package not installed")

    host = options.get('host') or 'localhost'
    port = int(options.get('port') or 3306)

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
        "Enter DB admin user", default='root')
    adm_pass = ch.get_password(
        "Enter DB admin password", default='')

    # create connection
    conn = connect(
        host=host, port=port, user=adm_user, password=adm_pass,
        charset='utf8mb4', connect_timeout=10)

    # create database
    cur = conn.cursor()
    cur.execute("SHOW DATABASES LIKE '%s';" % database)
    if not cur.fetchall():
        cur.execute(
            "CREATE DATABASE %s" % database +
            " CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    cur.close()

    # create user and grant privileges
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM mysql.user " +
        "WHERE user='%s' AND host='%%';" % username)
    if not cur.fetchall():
        cur.execute(
            "CREATE USER '%s'@'%%' IDENTIFIED BY '%s';"
            % (username, password))
    else:
        cur.execute(
            "ALTER USER '%s'@'%%' IDENTIFIED BY '%s';"
            % (username, password))
    cur.execute(
        "GRANT ALL ON %s.* TO %s@'%%';"
        % (database, username))
    cur.execute("FLUSH PRIVILEGES;")
    cur.close()

    conn.close()
    return True
