"""Read a MySQL dump as text, retaining independent state for each scenario."""
from copy import deepcopy
from enum import Enum
import gzip
import re


class Unknown(Enum):
    VALUE = 'unknown'


U = Unknown.VALUE


class JavaScriptValue(Enum):
    UNDEFINED = 'javascript undefined'


JS_UNDEFINED = JavaScriptValue.UNDEFINED


def camel(name):
    return re.sub(r'_([a-z])', lambda m: m[1].upper(), name)


def sql_rows(source):
    """Tokenize the dump's VALUES tuples, including escaped quotes and commas."""
    token, row, quoted, escaped, quoted_value = '', [], False, False, False
    position = 0
    while position < len(source):
        char = source[position]
        position += 1
        if escaped:
            token += {'n': '\n', 'r': '\r', 't': '\t', '0': '\0', 'b':'\b', 'Z':'\x1a'}.get(char, char)
            escaped = False
        elif quoted:
            if char == '\\':
                escaped = True
            elif char == "'":
                if position < len(source) and source[position] == "'":
                    token += "'"
                    position += 1
                else:
                    quoted = False
            else:
                token += char
        elif char == "'":
            quoted = quoted_value = True
        elif char in ',)':
            if token.strip() or quoted_value:
                value = token if quoted_value else token.strip()
                if not quoted_value:
                    if value.upper() == 'NULL':
                        value = None
                    elif re.fullmatch(r'-?\d+', value):
                        value = int(value)
                    elif re.fullmatch(r'-?\d+\.\d+', value):
                        value = float(value)
                    else:
                        value = U
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
        self.schemas = {}
        self.unknown_tables = set()
        self.warnings = []
        db = None
        opener = gzip.open if str(path).endswith('.gz') else open
        with opener(path, 'rt', encoding='utf-8', errors='surrogateescape') as stream:
            content = stream.read()
        columns = {}
        inserted = set()
        for statement in re.finditer(r'USE `([^`]+)`;|CREATE TABLE `([^`]+)` \((.*?)\) ENGINE|INSERT INTO `([^`]+)`\s*(\([^()]*\))?\s+VALUES (.*?);\s*(?:\n|$)', content, re.S|re.I):
            use, create, fields, insert, names_clause, values = statement.groups()
            if use:
                db = use
            elif create:
                columns[(db, create)] = re.findall(r'^\s*`([^`]+)`', fields, re.M)
                self.tables[(db, create)] = []
            elif insert:
                inserted.add(statement.start())
                names = columns[(db, insert)] if names_clause is None else [a or b for a,b in re.findall(r'`([^`]+)`|\b([A-Za-z_]\w*)\b',names_clause)]
                if any(name not in columns[(db,insert)] for name in names) or len(names)!=len(set(names)):
                    raise ValueError('Invalid INSERT column list: '+insert)
                for row in sql_rows(values):
                    if len(row) != len(names):
                        raise ValueError(f'Dump row length mismatch: {db}.{insert}')
                    self.tables[(db, insert)].append({camel(k): v for k, v in zip(names, row)})
                    if U in row:
                        self.warnings.append('Unsupported SQL literal retained as unknown in '+insert)
        for statement in re.finditer(r'^\s*(?:INSERT|REPLACE)\b',content,re.I|re.M):
            start = statement.start()+len(statement[0])-len(statement[0].lstrip())
            if start not in inserted:
                self.warnings.append('Unsupported dump insertion at offset '+str(start)+'; table contents widened')
                self.unknown_tables.update(self.tables)

    def materialize(self, resource, row, aliases=None, collections=None, primary_field=None):
        record = deepcopy(row)
        for column, field in (aliases or {}).items():
            if column in record and field not in record:
                record[field] = record[column]
        db = self.schemas.get(resource.get('schema', ''), resource.get('schema', ''))
        if (db, resource['name']) not in self.tables:
            candidates = [schema for schema, table in self.tables if table == resource['name']]
            if len(candidates) == 1:
                db = candidates[0]
        for prop, table, foreign, *columns in collections or []:
            if prop not in record:
                norm = lambda value: re.sub(r'[^a-z0-9]', '', value.lower())
                def get(row, column):
                    return next((value for key, value in row.items() if norm(key) == norm(column)), U)
                rows = self.tables.get((db, table))
                if rows is None or (db, table) in self.unknown_tables:
                    record[prop] = U
                    continue
                if not primary_field or record.get(primary_field, U) in (U, None) or any(get(r, foreign) is U for r in rows):
                    record[prop] = U
                    continue
                selected = [r for r in rows if primary_field and get(r, foreign) == record.get(primary_field)]
                if columns:
                    value_column, order_column = columns
                    if order_column:
                        positions = [get(r, order_column) for r in selected]
                        if (any(not isinstance(index, int) or isinstance(index, bool) for index in positions)
                                or sorted(positions) != list(range(len(positions)))):
                            record[prop] = U
                            continue
                        selected = sorted(selected, key=lambda r: get(r, order_column))
                    record[prop] = [get(r, value_column) for r in selected]
                else:
                    record[prop] = [{k: v for k, v in r.items() if k != foreign} for r in selected]
        return record

    def copy(self):
        return deepcopy(self)

    def invalidate(self, rows):
        for key, existing in self.tables.items():
            if existing is rows:
                self.unknown_tables.add(key)

    def rows(self, resource):
        schema = resource.get('schema', '')
        db = self.schemas.get(schema, schema)
        key = (db, resource['name'])
        if key in self.unknown_tables:
            return None
        if key in self.tables:
            return self.tables[key]
        matches = [(key, rows) for key, rows in self.tables.items() if key[1] == resource['name']]
        return matches[0][1] if len(matches) == 1 and matches[0][0] not in self.unknown_tables else None

    def summary(self):
        return {db + '.' + table: len(rows) for (db, table), rows in sorted(self.tables.items())}


class ScenarioState:
    """Generic path-local database, browser state and response journal."""
    def __init__(self, database, context=None):
        self.database = database.copy()
        self.context = deepcopy(context or {})
        self.now = self.context.get('clock', U)
        self.browser = {'storage': {}, 'form': {}, 'dom': {}, 'url': {}, 'options': {}, 'script': {}}
        self.history = []
        self.symbol_sequence = 0
        self.input_sequence = 0
        self.limitations = []
        self.analysis_assumptions = []

    def fresh_input(self, label, typ='String'):
        existing = {str(v) for rows in self.database.tables.values() for row in rows for v in row.values()}
        normalized = lambda name: re.sub('[^a-z0-9]', '', name.lower())
        related = [value for rows in self.database.tables.values() for row in rows for name, value in row.items()
                   if normalized(name) == normalized(label)]
        excluded = list(dict.fromkeys(value for value in related if isinstance(value, (str, int, float, bool))))
        symbols = [value['__symbol__'] for value in related if isinstance(value, dict) and '__symbol__' in value]
        while True:
            self.input_sequence += 1
            value = 'symbolic-input-' + label + '-' + str(self.input_sequence)
            if value not in existing:
                return {'__symbol__': value, '__type__': typ, '__constraints__': ['non_null', 'fresh_unique'],
                        '__distinct_from__': excluded, '__distinct_symbols__': symbols}

    def generated_value(self,typ,kind,existing=()):
        self.symbol_sequence += 1
        return {'__symbol__':'generated-'+str(self.symbol_sequence),'__type__':typ,
                '__constraints__':['non_null'],'__generation__':kind,
                '__distinct_from__':[v for v in existing if isinstance(v,(str,int,float,bool))],
                '__distinct_symbols__':[v['__symbol__'] for v in existing if isinstance(v,dict) and '__symbol__' in v]}

    def snapshot(self):
        return {'browser': deepcopy(self.browser),
                'history': [{k: item.get(k) for k in ('step', 'entry', 'action')} for item in self.history],
                'clock': self.now, 'database_rows': self.database.summary(),
                'unknown_tables':[schema+'.'+table for schema,table in sorted(self.database.unknown_tables)],
                'analysis_assumptions':list(self.analysis_assumptions),
                'limitations': list(self.limitations)}
