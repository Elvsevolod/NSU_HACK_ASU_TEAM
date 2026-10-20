"""Small, deterministic models of library values; never invoke application code."""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN,getcontext
import re
import hashlib
from copy import deepcopy
from .state import U
from .java_exceptions import JavaThrow
from .java_collections import JavaMap,JavaObject,JavaRecord,JavaEnumValue,JavaTypeToken,JavaTypeFactory,JsonObject,JsonText,JavaMapView,JavaMapEntry,JavaMapIterator,JavaJsonMapper,JacksonFeature
from .map_keys import key_spec,same_key,json_key
from .boxed_values import value_kind,boxed_equal
from .map_views import view_library
from .java_numbers import int_value


def http_headers_type(typ):
    return typ.lstrip('?') in ('HttpHeaders','org.springframework.http.HttpHeaders')


def uuid_value(value):
    if value is None:raise JavaThrow({'__type__':'NullPointerException'})
    if type(value) is dict:
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
        if isinstance(value,(JavaMapView,JavaMapEntry,JavaMapIterator,JavaJsonMapper,JacksonFeature)):return False
        if isinstance(value,JsonText):return False
        if isinstance(value,JavaRecord):return all(key in value and known(value[key],active) for key in value.wire_fields)
        if isinstance(value,JavaEnumValue):return all(known(child,active) for child in value.values())
        if isinstance(value,JsonObject):return all(known(child,active) for child in value.values())
        if isinstance(value,JavaMap):
            return isinstance(value.mapping,dict) and all(known(e['key'],active) and known(e['value'],active) for e in value.entries())
        if isinstance(value,dict):
            if '__symbol__' in value:return False
            return all(known(v,active) for k,v in value.items() if not k.startswith('__'))
        return all(known(v,active) for v in value)
    finally:
        active.remove(id(value))


def map_equal(left,right):
    if not isinstance(right,JavaMap):
        return False if right is None or type(right) in (str,bool,int,float) else U
    if left is right or left.java_identity is not None and left.java_identity is right.java_identity:return True
    if not isinstance(left.mapping,dict) or not isinstance(right.mapping,dict):return U
    if len(left.entries())!=len(right.entries()):return False
    results=[]
    for entry in left.entries():
        found=map_slot(right,entry)
        if found is U:results.append(U);continue
        if found is None:return False
        a,b=entry['value'],found['value']
        if a is U or b is U:results.append(U)
        elif a is None or b is None:results.append(a is None and b is None)
        elif entry.get('value_kind') is not None and found.get('value_kind') is not None:
            results.append(boxed_equal(a,b,entry['value_kind'],found['value_kind'],key_equal))
        elif type(a) in (str,bool,int,float) and type(b) in (str,bool,int,float):
            if any(type(item) is float and (item!=item or item in (float('inf'),float('-inf'))) for item in (a,b)):
                results.append(U)
            else:
                results.append(False if type(a)!=type(b) and (type(a) in (str,bool) or type(b) in (str,bool)) or a!=b else U)
        elif isinstance(a,(JavaMap,list)) and a is b:results.append(True)
        else:results.append(U) # Project-defined equals requires execution, not structural Python equality.
    return False if False in results else U if U in results else True


def map_slot(mapping,key):
    return mapping.slot(key)


def key_equal(a, b):
    if a is U or b is U: return U
    if isinstance(a,JavaMap):return map_equal(a,b)
    if isinstance(b,JavaMap):return map_equal(b,a)
    uuid_a=type(a) is dict and isinstance(a.get('__type__'),str) and a['__type__'].split('.')[-1]=='UUID'
    uuid_b=type(b) is dict and isinstance(b.get('__type__'),str) and b['__type__'].split('.')[-1]=='UUID'
    if uuid_a or uuid_b:
        if not uuid_a or not uuid_b:return False
        if '__uuid_literal__' in a and '__uuid_literal__' in b:return a['__uuid_literal__']==b['__uuid_literal__']
        if a.get('__symbol__') and a.get('__symbol__')==b.get('__symbol__'):return True
        return U
    symbolic_a = type(a) is dict and '__symbol__' in a
    symbolic_b = type(b) is dict and '__symbol__' in b
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
        if isinstance(a,JavaEnumValue) and isinstance(b,JavaEnumValue):
            return a.enum_key == b.enum_key
        if isinstance(a,JavaEnumValue) or isinstance(b,JavaEnumValue):return False
        keys=b.keys() if isinstance(b,JsonObject) else b.wire_fields if isinstance(b,JavaRecord) else [k for k in b if not k.startswith('__')]
        results = [key_equal(a.get(k,U),b.get(k,U)) for k in keys]
        return False if False in results else U if U in results else True
    return a == b


def http_entity(value):
    if not isinstance(value, dict) or isinstance(value,(JavaRecord,JavaEnumValue,JsonObject,JsonText)):
        return False
    if '__http_entity__' in value:
        return value['__http_entity__'] is True
    typ = value.get('__type__', '').split('<')[0]
    return typ in {'HttpEntity', 'ResponseEntity', 'RequestEntity',
                   'org.springframework.http.HttpEntity', 'org.springframework.http.ResponseEntity',
                   'org.springframework.http.RequestEntity'}


def header_values(value):
    if value is U:return U
    if type(value) is dict and value.get('__http_headers__'):
        return value.get('headers',U)
    return value if isinstance(value,dict) and not value.get('__type__') else U


def optional_value(value):
    return isinstance(value, dict) and not isinstance(value,(JavaRecord,JavaEnumValue,JsonObject,JsonText)) and value.get('__optional__') is True


def unwrap(value):
    return value.get('body', U) if http_entity(value) else value


def wire(value,unresolved=None,schema_limits=None,bean_reader=None):
    active=set()
    def convert(item):
        if isinstance(item,(JavaMapEntry,JavaMapIterator)):
            if unresolved:unresolved('JSON Map.Entry/iterator representation requires a supported codec and version')
            return U
        if not isinstance(item,(dict,list)):
            return item
        if id(item) in active:
            raise JavaThrow({'__type__':'JsonMappingException','__serialization_failure__':True})
        if bean_reader is not None and isinstance(item,JavaRecord) and len(active)>=64:
            if unresolved:unresolved('JSON bean recursion exceeds the supported depth')
            return U
        active.add(id(item))
        try:
            if isinstance(item,JavaMapView):
                if not isinstance(item.backing.mapping,dict):
                    if unresolved:unresolved('JSON Map view contents are unknown')
                    return U
                entries=item.backing.entries()
                if len(entries)>1 and not isinstance(item.backing.order,list):
                    if unresolved:unresolved('JSON Map view element order is unknown')
                    return U
                return [convert(entry['key'] if item.kind=='keys' else entry['value'] if item.kind=='values' else JavaMapEntry(item.backing,entry)) for entry in entries]
            if isinstance(item,JsonText):return JsonText(convert(item.payload),item.exact)
            if isinstance(item,(JavaTypeToken,JavaTypeFactory,JavaJsonMapper,JacksonFeature)):
                if unresolved:unresolved('JSON encoding of a Java codec or type descriptor is not modeled')
                return U
            if isinstance(item,JavaEnumValue):
                if item.json_default:return item.enum_name
                if unresolved:unresolved('custom enum JSON representation is not modeled')
                return U
            if isinstance(item,JavaRecord):
                if bean_reader is not None:
                    read=bean_reader(item,unresolved)
                    if read is U:return U
                    pairs,ordered=read
                    converted=[(key,convert(child)) for key,child in pairs]
                    return JsonObject(converted if ordered else dict(converted),item.declared_type)
                if unresolved and schema_limits:
                    for message in schema_limits(item.declared_type):unresolved(message)
                return JsonObject({key:convert(item.get(key,U)) for key in sorted(item.wire_fields)},item.declared_type)
            if isinstance(item,JsonObject):
                values=({key:convert(child) for key,child in item.items()} if item.source_pairs is None else
                        [(key,convert(child)) for key,child in item.source_pairs])
                return JsonObject(values,item.origin_type)
            if isinstance(item,JavaMap):
                if not isinstance(item.mapping,dict):
                    if unresolved:unresolved('Java Map contents are unknown at the JSON boundary')
                    return U
                result={}
                for entry in item.entries():
                    key=json_key(entry)
                    if key is U or key in result:
                        if unresolved:unresolved('Java Map JSON key encoding or duplicate-field order is unresolved')
                        return U
                    result[key]=convert(entry['value'])
                return JsonObject(list(result.items()) if isinstance(item.order,list) else result,item.origin_type)
            if isinstance(item,dict):
                if type(item) is dict and item.get('__type__') in ('UUID','java.util.UUID'):
                    handled,result=library('toString',item,[],'',U)
                    if handled:return result
                    if unresolved:unresolved('UUID JSON text is not known')
                    return U
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
        if len(args)!=1 or not known(args[0]):return True,U
        try:
            value=Decimal(args[0]) if type(args[0]) in (int,float) else Decimal(str(args[0]))
            if not value.is_finite():raise JavaThrow({'__type__':'NumberFormatException'})
            return True,value.copy_abs() if value.is_zero() else value
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
            return True,JavaMap(flavor=base)
        if len(args)==1 and args[0] is None:
            raise JavaThrow({'__type__':'NullPointerException'})
        if len(args)==1 and isinstance(args[0],JavaMap):
            return True,JavaMap(dict(args[0].mapping) if isinstance(args[0].mapping,dict) else U,
                                typed_entries=[dict(entry) for entry in args[0].typed_entries],value_types=args[0].value_types,flavor=base,
                                order=deepcopy(args[0].order) if base=='LinkedHashMap' else U)
        if len(args)==1 and type(args[0]) is int:
            if args[0]<0:raise JavaThrow({'__type__':'IllegalArgumentException'})
            return True,JavaMap(flavor=base)
        return True,U
    return False, U


def library(name, obj, args, receiver, now, key_type=None,json_issue=None,value_type=None,choose=None):
    """Return (handled, value). Unsupported operations retain Unknown."""
    if isinstance(obj,(JavaMapView,JavaMapEntry,JavaMapIterator)):
        return view_library(name,obj,args,key_type,value_type,key_equal,choose)
    if isinstance(obj,(JavaRecord,JavaEnumValue,JavaTypeToken,JavaTypeFactory,JsonObject,JsonText,JavaJsonMapper,JacksonFeature)):return False,U
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
        return True, JsonText(wire(args[0],json_issue))
    if name == 'readValue' and args and isinstance(args[0],JsonText):
        return False,U # The engine needs the explicit target class and source type.
    if name == 'ok' and (receiver.endswith('ResponseEntity') or not receiver):
        return True, {'__type__': 'ResponseEntity', '__http_entity__': True, 'body': args[0] if args else None,'status':200}
    if name == 'orElse' and optional_value(obj):
        val = obj['optional']
        return True, args[0] if val is None else val
    if isinstance(obj,Decimal) and name=='equals' and len(args)==1:
        if isinstance(args[0],Decimal):
            return True,(obj.copy_abs() if obj.is_zero() else obj).as_tuple()==(args[0].copy_abs() if args[0].is_zero() else args[0]).as_tuple()
        return True,False if args[0] is None or type(args[0]) in (str,bool,int,float) else U
    if isinstance(obj, Decimal) and args and isinstance(args[0], (Decimal, int, float)):
        b = Decimal(str(args[0]))
        ops = {'compareTo': lambda: (obj > b) - (obj < b), 'add': lambda: obj + b,
               'subtract': lambda: obj - b, 'multiply': lambda: obj * b}
        if name in ops:
            if name!='compareTo':
                needed=(len(obj.as_tuple().digits)+len(b.as_tuple().digits) if name=='multiply' else
                        max(obj.adjusted(),b.adjusted())-min(obj.as_tuple().exponent,b.as_tuple().exponent)+2)
                if needed>getcontext().prec:return True,U
            return True, ops[name]()
    if name in ('doubleValue', 'intValue') and isinstance(obj, (Decimal, int, float)):
        return True, int_value(obj) if name == 'intValue' else float(obj)
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
        obj.last_issue=None
        mapping = obj.mapping
        if name in ('keySet','values','entrySet') and not args:
            return True,JavaMapView(obj,{'keySet':'keys','values':'values','entrySet':'entries'}[name])
        if name == 'equals' and len(args)==1:return True,map_equal(obj,args[0])
        if name=='clear' and not args:
            obj.clear_mappings();return True,None
        if not isinstance(mapping,dict):
            obj.last_issue='unknown_map_state'
            return True,U
        if name in ('put','get','containsKey','remove','getOrDefault') and args:
            key=key_spec(args[0],key_type)
            found=map_slot(obj,key) if key is not None else U
            if found is U:
                obj.last_issue='unsupported_map_key' if key is None else 'unknown_map_key_equality'
                if name in ('put','remove'):obj.invalidate()
                return True,U
            if name=='containsKey':return True,found is not None
            old=found['value'] if found is not None else None
            if name=='get':return True,old
            if name=='getOrDefault' and len(args)==2:return True,old if found is not None else args[1]
            if name=='put' and len(args)==2:return True,obj.put(key,args[1],value_kind(args[1],value_type))
            if name=='remove' and len(args)==1:return True,obj.remove(key)
        if name=='putAll' and len(args)==1:
            if args[0] is None:raise JavaThrow({'__type__':'NullPointerException'})
            if isinstance(args[0],JavaMap) and isinstance(args[0].mapping,dict):
                if isinstance(obj.order,list) and not isinstance(args[0].order,list):obj.order=U
                for entry in args[0].entries():
                    library('put',obj,[entry['key'],entry['value']],receiver,now,key_type=entry['kind'],value_type=entry.get('value_kind') or 'unresolved')
                    if obj.mapping is U:return True,U
                return True,None
            obj.invalidate();return True,U
        if name == 'size' and not args:return True,len(mapping)+len(obj.typed_entries)
        if name == 'isEmpty' and not args:return True,not mapping and not obj.typed_entries
        if name in ('entrySet','keySet','values','containsValue','hashCode','toString','getClass'):
            # These are backed views or require additional Java value rules.
            # Python list/dict order and snapshots are not Java Map semantics.
            obj.last_issue='unsupported_map_view' if name in ('entrySet','keySet','values') else 'unsupported_map_operation'
            return True,U
        # An unsupported callback/mutation must not leave earlier values known.
        obj.invalidate()
        obj.last_issue='unsupported_map_mutation'
        return True,U
    return False, U
