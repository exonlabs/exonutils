# -*- coding: utf-8 -*-
from exonutils.db.common import sql_identifier
from exonutils.db.query import BaseQuery

__all__ = []


class Query(BaseQuery):

    # columns usage:
    # [(colname, definition [, constraint]), ...]
    # ex:
    # [('name1', 'TEXT NOT NULL', 'INDEX UNIQUE'), ...]

    # constraints:
    # ['CHECK (field1 IN (0, 1))',
    #  'FOREIGN KEY (tbl1_id) REFERENCES tbl1 (tbl1_id)', ...]

    def create_table(self):
        columns, constraints, indexes = [], [], []

        for c in self.model.tbl_columns():
            columns.append('"%s" %s' % (sql_identifier(c[0]), c[1]))

            if 'BOOLEAN' in c[1]:
                constraints.append('CHECK ("%s" IN (0,1))' % c[0])

            if len(c) <= 2:
                continue

            if 'PRIMARY' in c[2]:
                constraints.append('PRIMARY KEY ("%s")' % c[0])
            elif 'UNIQUE' in c[2] and 'INDEX' not in c[2]:
                constraints.append('UNIQUE ("%s")' % c[0])

            if 'PRIMARY' in c[2] or 'INDEX' in c[2]:
                u = 'UNIQUE ' if 'PRIMARY' in c[2] or 'UNIQUE' in c[2] else ''
                indexes.append(
                    'CREATE %sINDEX IF NOT EXISTS ' % u +
                    '"ix_%s_%s" ' % (self.tbl_name, c[0]) +
                    'ON "%s" ("%s");' % (self.tbl_name, c[0]))

        defs = columns
        defs.extend(constraints)
        defs.extend(self.model.tbl_constraints())

        sql = 'CREATE TABLE IF NOT EXISTS "%s" (\n' % self.tbl_name
        sql += ',\n'.join(defs)
        if self.model.tbl_args().get('without_rowid', False):
            sql += '\n) WITHOUT ROWID;\n'
        else:
            sql += '\n);\n'
        self.dbs.execute(sql)

        # create indexes
        for sql in indexes:
            self.dbs.execute(sql)

        self.dbs.commit()
