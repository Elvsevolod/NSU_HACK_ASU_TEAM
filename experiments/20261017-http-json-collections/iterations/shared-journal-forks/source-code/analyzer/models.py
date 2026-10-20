"""Small, deterministic models of library values; never invoke application code."""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import re
import hashlib
from copy import deepcopy
from .state import U
from .java_exceptions import JavaThrow
from .java_collections import JavaMap


def http_headers_type(typ):
    return typ.lstrip('?') in ('HttpHeaders','org.springframework.http.HttpHeaders')


def uuid_value(value):
    if value is None:raise JavaThrow({'__type__':'NullPointerException'})
    if isinstance(value,dict):
        if value.get('__type__','').split('.')[-1]=='UUID':return value
        if value.get('__uuid_text__') is True and '__symbol__' in value:
            return {'__type__':'UUID','__symbol__':value.get('__uuid_origin__',value['__symbol__']+':UUID'),
                    '__uuid_string__':deepcopy(value),'__constraints__':['non_null']}
        return U
    if isinstance(value,str):
        if re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',value):
            return {'__type__':'UUID','__uuid_literal__':value.lower()}
        if value.isascii() and (value.count('-')!=4 or re.search('[^0-9a-fA-F-]',value)):
            raise JavaThrow({'__type__':'IllegalArgumentException'})
    return U


def status_code(value):
    if type(value) is int and 100 <= value <= 599:return value
    return {'OK':200,'CREATED':201,'ACCEPTED':202,'NO_CONTENT':204,
            'MOVED_PERMANENTLY':301,'FOUND':302,'BAD_REQUEST':400,'UNAUTHORIZED':401,
            'FORBIDDEN':403,'NOT_FOUND':404,'METHOD_NOT_ALLOWED':405,'CONFLICT':409,
            'UNPROCESSABLE_ENTITY':422,'TOO_MANY_REQUESTS':429,'INTERNAL_SERVER_ERROR':500,
            'NOT_IMPLEMENTED':501,'BAD_GATEWAY':502,'SERVICE_UNAVAILABLE':503}.get(value,U) if isinstance(value,str) else U


def known(value, active=None):
    if value is U:
        return False
    if not isinstance(value,(dict,list,tuple)):
        return True
    active=set() if active is None else active
    if id(value) in active:return False
    active.add(id(value))
    try:
        if isinstance(value,JavaMap):
            return isinstance(value.mapping,dict) and all(known(v,active) for v in value.mapping.values())
        if isinstance(value,dict):
            if '__symbol__' in value:return False
            return all(known(v,active) for k,v in value.items() if not k.startswith('__'))
        return all(known(v,active) for v in value)
    finally:
        active.remove(id(value))


def map_equal(left,right):
    if not isinstance(right,JavaMap):
        return False if right is None or type(right) in (str,bool,int,float) else U
    if left is right:return True
    if not isinstance(left.mapping,dict) or not isinstance(right.mapping,dict):return U
    if left.mapping.keys()!=right.mapping.keys():return False
    results=[]
    for key,a in left.mapping.items():
        b=right.mapping[key]
        if a is U or b is U:results.append(U)
        elif a is None or b is None:results.append(a is None and b is None)
        elif type(a) in (str,bool) and type(b) in (str,bool):results.append(type(a) is type(b) and a==b)
        elif type(a) in (str,bool,int,float) and type(b) in (str,bool,int,float):
            if any(type(item) is float and (item!=item or item in (float('inf'),float('-inf'))) for item in (a,b)):
                results.append(U)
            else:
                results.append(False if type(a)!=type(b) and (type(a) in (str,bool) or type(b) in (str,bool)) or a!=b else U)
        elif isinstance(a,(JavaMap,list)) and a is b:results.append(True)
        else:results.append(U) # Project-defined equals requires execution, not structural Python equality.
    return False if False in results else U if U in results else True


def key_equal(a, b):
    if a is U or b is U: return U
    if isinstance(a,JavaMap):return map_equal(a,b)
    if isinstance(b,JavaMap):return map_equal(b,a)
    uuid_a=isinstance(a,dict) and a.get('__type__','').split('.')[-1]=='UUID'
    uuid_b=isinstance(b,dict) and b.get('__type__','').split('.')[-1]=='UUID'
    if uuid_a or uuid_b:
        if not uuid_a or not uuid_b:return False
        if '__uuid_literal__' in a and '__uuid_literal__' in b:return a['__uuid_literal__']==b['__uuid_literal__']
        if a.get('__symbol__') and a.get('__symbol__')==b.get('__symbol__'):return True
        return U
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


def header_values(value):
    if value is U:return U
    if isinstance(value,dict) and value.get('__http_headers__'):
        return value.get('headers',U)
    return value if isinstance(value,dict) and not value.get('__type__') else U


def optional_value(value):
    return isinstance(value, dict) and value.get('__optional__') is True


def unwrap(value):
    return value.get('body', U) if http_entity(value) else value


def wire(value):
    active=set()
    def convert(item):
        if not isinstance(item,(dict,list)):
            return item
        if id(item) in active:
            raise JavaThrow({'__type__':'JsonMappingException','__serialization_failure__':True})
        active.add(id(item))
        try:
            if isinstance(item,JavaMap):
                return {key:convert(child) for key,child in item.mapping.items()} if isinstance(item.mapping,dict) else U
            if isinstance(item,dict):
                if optional_value(item):return convert(item['optional'])
                return {key:convert(child) for key,child in item.items()}
            return [convert(child) for child in item]
        finally:
            active.remove(id(item))
    return convert(value)


def date_value(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value[:19])
        except ValueError:
            pass
    return U


def java_date_text(value):
    """Date.toString shape; timezone text and concrete text are not invented."""
    if not isinstance(value,datetime):return U
    return {'__symbol__':'date-text-'+hashlib.sha256(value.isoformat().encode()).hexdigest()[:16],
            '__type__':'String','__java_date_text__':True,'__min_length__':25,
            '__constraints__':['non_null'],'__generation__':'java.util.Date.toString'}


def date_pattern(pattern):
    if not isinstance(pattern,str):return None
    tokens=re.findall(r"''|'[^']*'|[A-Za-z]+|[^A-Za-z']+",pattern)
    if ''.join(tokens)!=pattern:return None
    supported={'yyyy':'%Y','MM':'%m','dd':'%d','HH':'%H','mm':'%M','ss':'%S'}
    output=[]
    for token in tokens:
        if token=="''":output.append("'")
        elif token.startswith("'"):output.append(token[1:-1].replace('%','%%'))
        elif token[0].isalpha():
            if token not in supported:return None
            output.append(supported[token])
        else:output.append(token.replace('%','%%'))
    return ''.join(output)


def construct(typ, args, now):
    base = typ.split('<')[0].split('.')[-1]
    if base=='HttpHeaders':return True,{'__type__':'HttpHeaders','__http_headers__':True,'headers':{}}
    if base in ('ResponseEntity', 'HttpEntity'):
        header_only=bool(len(args)==(1 if base=='HttpEntity' else 2) and isinstance(args[0],dict) and args[0].get('__http_headers__'))
        body=args[0] if args and not header_only and (base=='HttpEntity' or len(args)>1) else None
        value = {'__type__': base, '__http_entity__': True, 'body':body,
                 'headers':args[0] if header_only else args[1] if len(args)>1 and base=='HttpEntity' or len(args)>2 else {}}
        if base=='ResponseEntity':value['status'] = status_code(args[-1]) if args else U
        return True, value
    if base == 'BigDecimal':
        try:
            value=Decimal(str(args[0])) if args and known(args[0]) else U
            return True,abs(value) if isinstance(value,Decimal) and value.is_zero() else value
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
        return True, {'__type__': base, 'pattern': args[0] if args else U,'options':args[1:]}
    if base in ('HashMap', 'LinkedHashMap', 'Map'):
        if not args:
            return True,JavaMap()
        if len(args)==1 and args[0] is None:
            raise JavaThrow({'__type__':'NullPointerException'})
        if len(args)==1 and isinstance(args[0],JavaMap):
            return True,JavaMap(dict(args[0].mapping) if isinstance(args[0].mapping,dict) else U)
        if len(args)==1 and type(args[0]) is int:
            if args[0]<0:raise JavaThrow({'__type__':'IllegalArgumentException'})
            return True,JavaMap()
        return True,U
    return False, U


def library(name, obj, args, receiver, now):
    """Return (handled, value). Unsupported operations retain Unknown."""
    typ = obj.get('__type__', '') if isinstance(obj, dict) else ''
    if typ.split('.')[-1]=='UUID':
        if name=='toString' and '__uuid_string__' in obj:return True,deepcopy(obj['__uuid_string__'])
        if name=='toString' and '__uuid_literal__' in obj:return True,obj['__uuid_literal__']
        if name=='equals' and args:return True,key_equal(obj,args[0])
    if typ.split('.')[-1]=='BindingResult' and isinstance(obj.get('__binding_errors__'),list):
        if name=='hasErrors':return True,bool(obj['__binding_errors__'])
        if name=='getFieldErrors':return True,obj['__binding_errors__']
    if isinstance(obj,dict) and obj.get('__http_headers__'):
        if name in ('set','add') and len(args)==2 and isinstance(args[0],str):
            if obj['headers'] is U:obj['headers']={'__rest_unknown__':True}
            key=args[0].lower()
            obj['headers'][key]=[args[1]] if name=='set' else obj['headers'].get(key,[])+[args[1]]
            return True,None
        if name=='getFirst' and args and isinstance(args[0],str):
            headers=header_values(obj)
            if headers is U:return True,U
            values=headers.get(args[0].lower(),U if headers.get('__rest_unknown__') else [])
            return True,values[0] if isinstance(values,list) and values else None if values==[] else U
        if name=='setContentType' and args:
            if obj['headers'] is U:obj['headers']={'__rest_unknown__':True}
            obj['headers']['content-type']=[args[0]]
            return True,None
    if isinstance(obj,dict) and '__symbol__' in obj:
        if typ.split('.')[-1]=='UUID' and name=='toString':
            return True, {**obj,'__symbol__':obj['__symbol__']+':text','__type__':'String','__length__':36,
                          '__uuid_text__':True,'__uuid_origin__':obj['__symbol__']}
        if typ.split('.')[-1]=='String':
            if name=='toString':return True,obj
            if name=='length':
                if '__length__' in obj:return True,obj['__length__']
                if '__min_length__' in obj:
                    return True,{'__symbol__':obj['__symbol__']+':length','__type__':'int',
                                 '__interval__':{'low':obj['__min_length__'],'low_closed':True,'high':None}}
                return True,U
            if name in ('isEmpty','isBlank'):
                return True,False if obj.get('__uuid_text__') else U
        if name=='equals' and args:return True,key_equal(obj,args[0])
    if name == 'status' and receiver.endswith('ResponseEntity') and args:
        return True, {'__response_builder__': args[0]}
    if name == 'body' and isinstance(obj, dict) and '__response_builder__' in obj:
        return True, {'__type__': 'ResponseEntity', '__http_entity__': True, 'body': args[0] if args else None,
                      'status':status_code(obj['__response_builder__'])}
    if name == 'build' and isinstance(obj,dict) and '__response_builder__' in obj:
        return True, {'__type__':'ResponseEntity','__http_entity__':True,'body':None,'status':status_code(obj['__response_builder__'])}
    if receiver.endswith('ResponseEntity') and name in ('notFound','badRequest','noContent'):
        return True, {'__response_builder__':{'notFound':404,'badRequest':400,'noContent':204}[name]}
    if receiver in ('Optional','java.util.Optional') and name in ('empty','of','ofNullable'):
        value = args[0] if args else None
        if name=='of' and value is None:raise JavaThrow({'__type__':'NullPointerException'})
        return True, {'__optional__':True,'optional':value}
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
        return True, {'__type__': 'ResponseEntity', '__http_entity__': True, 'body': args[0] if args else None,'status':200}
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
            return True, len(obj.encode('utf-16-le',errors='surrogatepass'))//2
        if name == 'replace' and len(args) == 2 and all(isinstance(a, str) for a in args):
            return True, obj.replace(*args)
        if name == 'split' and args and isinstance(args[0], str):
            return True, obj.split(args[0])
        if name in ('substring', 'charAt') and args and all(isinstance(a, int) for a in args):
            length=len(obj.encode('utf-16-le',errors='surrogatepass'))//2
            if args[0]<0 or args[0]>length or name=='charAt' and args[0]==length or len(args)>1 and (args[1]<args[0] or args[1]>length):
                raise JavaThrow({'__type__':'StringIndexOutOfBoundsException'})
            if any(ord(char)>0xFFFF for char in obj):return False,U
            if name == 'charAt':
                return True, obj[args[0]] if 0 <= args[0] < len(obj) else U
            return True, obj[args[0]:args[1] if len(args) > 1 else None]
    if name == 'toString' and isinstance(obj,datetime):return True,java_date_text(obj)
    if name == 'toString' and isinstance(obj,Decimal):return True,str(obj)
    if receiver in ('System','java.lang.System') and name=='currentTimeMillis' and not args:
        return True,int((now-datetime(1970,1,1)).total_seconds()*1000) if isinstance(now,datetime) else U
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
            units = {'MINUTE': 'minutes', 'HOUR': 'hours', 'HOUR_OF_DAY':'hours','DAY_OF_MONTH': 'days'}
            if args[0] in units: obj['time'] = dt + timedelta(**{units[args[0]]: args[1]})
            else:return False,U
            return True, None
        if name == 'getTime':
            return True, dt
        if name == 'get' and args and isinstance(dt, datetime):
            values = {'YEAR': dt.year, 'MONTH': dt.month-1, 'DAY_OF_MONTH': dt.day,
                      'HOUR': dt.hour % 12, 'HOUR_OF_DAY': dt.hour, 'MINUTE': dt.minute, 'SECOND': dt.second}
            return True, values.get(args[0], U)
    if typ == 'SimpleDateFormat' and args:
        pattern=date_pattern(obj['pattern'])
        if pattern is None or obj.get('options'):return False,U
        if name=='parse' and pattern.startswith(('%Y','%m','%d','%H','%M','%S')):
            source=args[0]
            if source is None:raise JavaThrow({'__type__':'NullPointerException'})
            if isinstance(source,dict) and source.get('__java_date_text__') or isinstance(source,str) and re.match(r'^\s*[A-Za-z]',source):
                raise JavaThrow({'__type__':'ParseException'})
        if name == 'parse' and isinstance(args[0],str):
            if not all(token in pattern for token in ('%Y','%m','%d')):return False,U
            try:return True,datetime.strptime(args[0],pattern)
            except ValueError:return False,U
        if name == 'format' and isinstance(args[0], datetime):return True,args[0].strftime(pattern)
    if typ == 'DecimalFormat' and name == 'format' and args and isinstance(args[0], (int, float, Decimal)):
        pattern=re.fullmatch(r'#*(0+)(?:\.(0+))?',obj['pattern']) if isinstance(obj.get('pattern'),str) else None
        if pattern is None or obj.get('options'):return False,U
        digits=len(pattern[2] or '')
        value=Decimal.from_float(args[0]) if type(args[0]) is float else Decimal(args[0])
        try:
            if not value.is_finite():return False,U
            rounded=value.quantize(Decimal(1).scaleb(-digits),rounding=ROUND_HALF_EVEN)
            rendered=format(rounded,'.'+str(digits)+'f')
            return True,rendered.zfill(len(pattern[1])+(digits+1 if digits else 0)+(1 if rounded.is_signed() else 0))
        except InvalidOperation:return False,U
    if isinstance(obj, list):
        if name in ('contains', 'indexOf') and args:
            # Project equals callbacks require the engine's source context.
            return False,U
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
            if i>=len(items):raise JavaThrow({'__type__':'NoSuchElementException'})
            obj['index'] += 1
            return True, items[i] if i < len(items) else U
    if isinstance(obj,JavaMap):
        mapping = obj.mapping
        if name == 'equals' and len(args)==1:return True,map_equal(obj,args[0])
        if not isinstance(mapping,dict):
            return True,U
        if name in ('put','get','containsKey') and args and type(args[0]) is not str:
            if name == 'put':obj.invalidate()
            return True,U
        if name == 'put' and len(args) == 2:
            old = mapping.get(args[0]); mapping[args[0]] = args[1]; return True, old
        if name == 'get' and args:
            return True, mapping.get(args[0])
        if name == 'containsKey' and args:
            return True,args[0] in mapping
        if name == 'size' and not args:return True,len(mapping)
        if name == 'isEmpty' and not args:return True,not mapping
        if name in ('entrySet','keySet','values','containsValue','getOrDefault','hashCode','toString'):
            # These are backed views or require additional Java value rules.
            # Python list/dict order and snapshots are not Java Map semantics.
            return True,U
        # An unsupported callback/mutation must not leave earlier values known.
        obj.invalidate()
        return True,U
    return False, U
