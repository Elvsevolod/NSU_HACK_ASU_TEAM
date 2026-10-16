"""Read a MySQL dump as text, retaining independent state for each scenario."""
from copy import deepcopy
from enum import Enum
from datetime import datetime
import gzip
import re


class Unknown(Enum):
    VALUE = 'unknown'


U = Unknown.VALUE


def camel(name):
    return re.sub(r'_([a-z])', lambda m: m[1].upper(), name)


def sql_rows(source):
    """Tokenize the dump's VALUES tuples, including escaped quotes and commas."""
    token, row, quoted, escaped, quoted_value = '', [], False, False, False
    for char in source:
        if escaped:
            token += {'n': '\n', 'r': '\r', 't': '\t', '0': '\0'}.get(char, char)
            escaped = False
        elif quoted:
            if char == '\\':
                escaped = True
            elif char == "'":
                quoted = False
            else:
                token += char
        elif char == "'":
            quoted = quoted_value = True
        elif char in ',)':
            if token.strip() or quoted_value:
                value = token if quoted_value else token.strip()
                if not quoted_value:
                    if value == 'NULL':
                        value = None
                    elif re.fullmatch(r'-?\d+', value):
                        value = int(value)
                    elif re.fullmatch(r'-?\d+\.\d+', value):
                        value = float(value)
                row.append(value)
                token, quoted_value = '', False
            if char == ')':
                yield row
                row = []
        elif char not in '(':
            token += char


class Database:
    def __init__(self, path):
        self.tables = {}
        db = None
        opener = gzip.open if str(path).endswith('.gz') else open
        with opener(path, 'rt', encoding='utf-8', errors='surrogateescape') as stream:
            content = stream.read()
        columns = {}
        for statement in re.finditer(r'USE `([^`]+)`;|CREATE TABLE `([^`]+)` \((.*?)\) ENGINE|INSERT INTO `([^`]+)` VALUES (.*?);\s*(?:\n|$)', content, re.S):
            use, create, fields, insert, values = statement.groups()
            if use:
                db = use
            elif create:
                columns[(db, create)] = re.findall(r'^\s*`([^`]+)`', fields, re.M)
                self.tables[(db, create)] = []
            elif insert:
                names = columns[(db, insert)]
                for row in sql_rows(values):
                    if len(row) != len(names):
                        raise ValueError(f'Dump row length mismatch: {db}.{insert}')
                    self.tables[(db, insert)].append({camel(k): v for k, v in zip(names, row)})

    def materialize(self, resource, row, aliases=None, collections=None):
        record = deepcopy(row)
        for column, field in (aliases or {}).items():
            if column in record and field not in record:
                record[field] = record[column]
        db = re.sub(r'-(service|mysql)$', '', resource.get('schema', '')).replace('-', '_')
        for prop, table, foreign in collections or []:
            if prop not in record:
                record[prop] = [{k: v for k, v in r.items() if k != foreign}
                                for r in self.tables.get((db, table), []) if r.get(foreign) == record.get('id')]
        if resource['name'] in ('trip', 'trip2') and 'type' in row and 'number' in row:
            # JPA @Embedded TripId is stored as two SQL columns.
            type_name = row['type'] if isinstance(row['type'], str) else ['G', 'D', 'Z', 'T', 'K'][row['type']]
            record['tripId'] = {'__type__': 'TripId', 'type': {'__enum__': 'Type.' + type_name, 'name': type_name}, 'number': row['number']}
        prefix = resource['name'] + '_'
        for (schema, table), rows in self.tables.items():
            if schema != db or not table.startswith(prefix): continue
            prop = camel(table[len(prefix):])
            if prop in record: continue
            foreign = camel(resource['name'] + '_id')
            items = [r for r in rows if r.get(foreign) == row.get('id')]
            if items or foreign in (rows[0] if rows else {}):
                record[prop] = [r.get(prop, U) for r in sorted(items, key=lambda r: r.get(prop + 'Order', 0))]
        return record

    def copy(self):
        return deepcopy(self)

    def rows(self, resource):
        schema = resource.get('schema', '')
        db = re.sub(r'-(service|mysql)$', '', schema).replace('-', '_')
        key = (db, resource['name'])
        if key in self.tables:
            return self.tables[key]
        matches = [rows for (_, table), rows in self.tables.items() if table == resource['name']]
        return matches[0] if len(matches) == 1 else None

    def summary(self):
        return {db + '.' + table: len(rows) for (db, table), rows in sorted(self.tables.items())}


class ScenarioState:
    def __init__(self, database):
        self.database = database.copy()
        self.role = 'passenger'
        self.regular = False
        self.user = 'fdse_microservice'
        users = database.tables.get(('ts_auth', 'auth_user'), [])
        user = next((u for u in users if u.get('userName') == self.user), {})
        self.account_id = user.get('userId', U)
        self.default_identity = (self.user, self.account_id)
        roles = database.tables.get(('ts_auth', 'user_roles'), [])
        admin_ids = {r.get('userId') for r in roles if 'ADMIN' in str(r.get('roles', ''))}
        admin = next((u for u in users if u.get('userId') in admin_ids), {})
        self.admin_identity = (admin.get('userName', U), admin.get('userId', U))
        self.new_account = False
        self.orders = []
        self.last_order = None
        self.last_trip = U
        self.last_contact = U
        self.symbol_sequence = 0
        self.now = datetime(2026, 9, 15, 12)
        self.route = {}
        self.search_results = []
        self.searches = {}
        self.created_route = U
        self.last_consign = {}
        self.last_food = {}

    def select_identity(self):
        if self.role == 'admin':
            self.user, self.account_id = self.admin_identity
        elif not self.new_account:
            self.user, self.account_id = self.default_identity

    def snapshot(self):
        return {'role': self.role, 'regular_train': self.regular, 'user': self.user,
                'account_id': self.account_id, 'orders': deepcopy(self.orders),
                'last_order': self.last_order, 'last_trip': self.last_trip,
                'last_contact': self.last_contact, 'route': deepcopy(self.route),
                'last_consign': deepcopy(self.last_consign)}
