"""Small, deterministic models of library values; never invoke application code."""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from .state import U


def known(value):
    if value is U:
        return False
    if isinstance(value, dict):
        if '__symbol__' in value:
            return False
        return all(known(v) for k, v in value.items() if not k.startswith('__'))
    if isinstance(value, (list, tuple)):
        return all(known(v) for v in value)
    return True


def key_equal(a, b):
    if a is U or b is U: return U
    symbolic_a = isinstance(a, dict) and '__symbol__' in a
    symbolic_b = isinstance(b, dict) and '__symbol__' in b
    if symbolic_a or symbolic_b:
        if symbolic_a and symbolic_b and a['__symbol__'] == b['__symbol__'] and a.get('__type__') == b.get('__type__'):
            return True
        if a is None or b is None:
            symbol = a if symbolic_a else b
            return False if 'non_null' in symbol.get('__constraints__', []) else U
        for symbol, other in ((a, b), (b, a)):
            if isinstance(symbol, dict) and '__symbol__' in symbol:
                if isinstance(other, dict) and other.get('__symbol__') in symbol.get('__distinct_symbols__', []):
                    return False
                if isinstance(other, (str, int, float, bool)) and any(type(other) is type(value) and other == value for value in symbol.get('__distinct_from__', [])):
                    return False
        return U
    if isinstance(a, dict) and isinstance(b, dict):
        if '__enum__' in a and '__enum__' in b:
            return a['__enum__'] == b['__enum__']
        results = [key_equal(a.get(k, U), v) for k, v in b.items() if not k.startswith('__')]
        return False if False in results else U if U in results else True
    return a == b


def http_entity(value):
    if not isinstance(value, dict):
        return False
    if '__http_entity__' in value:
        return value['__http_entity__'] is True
    typ = value.get('__type__', '').split('<')[0]
    return typ in {'HttpEntity', 'ResponseEntity', 'RequestEntity',
                   'org.springframework.http.HttpEntity', 'org.springframework.http.ResponseEntity',
                   'org.springframework.http.RequestEntity'}


def optional_value(value):
    return isinstance(value, dict) and value.get('__optional__') is True


def unwrap(value):
    return value.get('body', U) if http_entity(value) else value


def wire(value):
    if isinstance(value, dict):
        if optional_value(value): return wire(value['optional'])
        return {k: wire(v) for k, v in value.items()}
    if isinstance(value, list): return [wire(v) for v in value]
    return value


def date_value(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value[:19])
        except ValueError:
            pass
    return U


def construct(typ, args, now):
    base = typ.split('<')[0].split('.')[-1]
    if base in ('ResponseEntity', 'HttpEntity'):
        return True, {'__type__': base, '__http_entity__': True, 'body': args[0] if args else None}
    if base == 'BigDecimal':
        try:
            return True, Decimal(str(args[0])) if args and known(args[0]) else U
        except InvalidOperation:
            return True, U
    if base == 'Date':
        if not args:
            return True, now
        if len(args) == 1 and isinstance(args[0], (int, float)):
            return True, datetime(1970, 1, 1) + timedelta(milliseconds=args[0])
        if len(args) == 6 and all(isinstance(a, int) for a in args):
            try:
                return True, datetime(args[0] + 1900, args[1] + 1, *args[2:])
            except ValueError:
                pass
        return True, U
    if base in ('SimpleDateFormat', 'DecimalFormat'):
        return True, {'__type__': base, 'pattern': args[0] if args else U}
    if base in ('HashMap', 'LinkedHashMap', 'Map'):
        return True, {'__map__': {}}
    return False, U


def library(name, obj, args, receiver, now):
    """Return (handled, value). Unsupported operations retain Unknown."""
    typ = obj.get('__type__', '') if isinstance(obj, dict) else ''
    if name == 'status' and receiver.endswith('ResponseEntity') and args:
        return True, {'__response_builder__': args[0]}
    if name == 'body' and isinstance(obj, dict) and '__response_builder__' in obj:
        return True, {'__type__': 'ResponseEntity', '__http_entity__': True, 'body': args[0] if args else None}
    if receiver == 'Math' and name in ('min', 'max') and args and all(isinstance(a, (int, float)) for a in args):
        return True, (min if name == 'min' else max)(args)
    if name == 'parseBoolean' and args and isinstance(args[0], str):
        return True, args[0].lower() == 'true'
    if name == 'asList' and receiver == 'Arrays':
        return True, args[0] if len(args) == 1 and isinstance(args[0], list) else list(args)
    if name == 'writeValueAsString' and args:
        return True, {'__json__': wire(args[0])}
    if name == 'readValue' and args and isinstance(args[0], dict) and '__json__' in args[0]:
        return True, args[0]['__json__']
    if name == 'ok' and (receiver.endswith('ResponseEntity') or not receiver):
        return True, {'__type__': 'ResponseEntity', '__http_entity__': True, 'body': args[0] if args else None}
    if name == 'orElse' and optional_value(obj):
        val = obj['optional']
        return True, args[0] if val is None else val
    if isinstance(obj, Decimal) and args and isinstance(args[0], (Decimal, int, float)):
        b = Decimal(str(args[0]))
        ops = {'compareTo': lambda: (obj > b) - (obj < b), 'add': lambda: obj + b,
               'subtract': lambda: obj - b, 'multiply': lambda: obj * b}
        if name in ops:
            return True, ops[name]()
    if name in ('doubleValue', 'intValue') and isinstance(obj, (Decimal, int, float)):
        return True, int(obj) if name == 'intValue' else float(obj)
    if isinstance(obj, str):
        if name in ('toLowerCase', 'toUpperCase', 'trim'):
            return True, {'toLowerCase': str.lower, 'toUpperCase': str.upper, 'trim': str.strip}[name](obj)
        if name in ('length',):
            return True, len(obj)
        if name == 'replace' and len(args) == 2 and all(isinstance(a, str) for a in args):
            return True, obj.replace(*args)
        if name == 'split' and args and isinstance(args[0], str):
            return True, obj.split(args[0])
        if name in ('substring', 'charAt') and args and all(isinstance(a, int) for a in args):
            if name == 'charAt':
                return True, obj[args[0]] if 0 <= args[0] < len(obj) else U
            return True, obj[args[0]:args[1] if len(args) > 1 else None]
    if name == 'toString' and isinstance(obj, (Decimal, datetime)):
        return True, str(obj)
    if name == 'getTime' and isinstance(obj, datetime):
        return True, int((obj - datetime(1970, 1, 1)).total_seconds() * 1000)
    if name in ('before', 'after') and isinstance(obj, datetime) and args:
        other = date_value(args[0])
        return True, (obj < other if name == 'before' else obj > other) if other is not U else U
    if name == 'getInstance' and receiver == 'Calendar':
        return True, {'__type__': 'Calendar', 'time': now}
    if typ == 'Calendar':
        if name == 'setTime':
            obj['time'] = date_value(args[0]); return True, None
        dt = obj.get('time', U)
        if name == 'add' and len(args) == 2 and isinstance(dt, datetime) and isinstance(args[1], (int, float)):
            units = {'MINUTE': 'minutes', 'HOUR': 'hours', 'DAY_OF_MONTH': 'days'}
            if args[0] in units: obj['time'] = dt + timedelta(**{units[args[0]]: args[1]})
            return True, None
        if name == 'getTime':
            return True, dt
        if name == 'get' and args and isinstance(dt, datetime):
            values = {'YEAR': dt.year, 'MONTH': dt.month-1, 'DAY_OF_MONTH': dt.day,
                      'HOUR': dt.hour % 12, 'HOUR_OF_DAY': dt.hour, 'MINUTE': dt.minute, 'SECOND': dt.second}
            return True, values.get(args[0], U)
    if typ == 'SimpleDateFormat' and args:
        if name == 'parse':
            return True, date_value(args[0])
        if name == 'format' and isinstance(args[0], datetime):
            return True, args[0].strftime('%Y-%m-%d %H:%M:%S' if 'HH' in str(obj['pattern']) else '%Y-%m-%d')
    if typ == 'DecimalFormat' and name == 'format' and args and isinstance(args[0], (int, float, Decimal)):
        return True, format(args[0], '.2f')
    if isinstance(obj, list):
        if name in ('contains', 'indexOf') and args:
            if isinstance(args[0], dict) and known(args[0].get('id', U)) and all(isinstance(item, dict) and known(item.get('id', U)) and item['id'] != args[0]['id'] for item in obj):
                return True, False if name == 'contains' else -1
            if not known(args[0]):
                return True, U
            return True, args[0] in obj if name == 'contains' else obj.index(args[0]) if args[0] in obj else -1
        if name == 'remove' and args and known(args[0]):
            if isinstance(args[0], int):
                return True, obj.pop(args[0]) if 0 <= args[0] < len(obj) else U
            if args[0] in obj: obj.remove(args[0]); return True, True
            return True, False
        if name in ('removeAll', 'retainAll') and args and isinstance(args[0], list):
            obj[:] = [v for v in obj if (v in args[0]) == (name == 'retainAll')]
            return True, True
        if name == 'iterator':
            return True, {'__iterator__': obj, 'index': 0}
    if isinstance(obj, dict) and '__iterator__' in obj:
        i, items = obj['index'], obj['__iterator__']
        if name == 'hasNext':
            return True, i < len(items)
        if name == 'next':
            obj['index'] += 1
            return True, items[i] if i < len(items) else U
    if isinstance(obj, dict) and '__map__' in obj:
        mapping = obj['__map__']
        if name == 'put' and len(args) == 2 and known(args[0]):
            old = mapping.get(str(args[0])); mapping[str(args[0])] = args[1]; return True, old
        if name == 'get' and args:
            return True, mapping.get(str(args[0])) if known(args[0]) else U
        if name == 'entrySet':
            return True, [{'key': k, 'value': v} for k, v in mapping.items()]
        if name in ('keySet', 'values'):
            return True, list(mapping.keys() if name == 'keySet' else mapping.values())
        if name == 'containsKey' and args:
            return True, str(args[0]) in mapping if known(args[0]) else U
    return False, U
