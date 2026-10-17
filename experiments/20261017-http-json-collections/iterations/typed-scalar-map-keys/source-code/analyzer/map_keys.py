"""A bounded key model: boxing identity matters before JSON serialization."""
from .state import U


def key_spec(value,hint=None):
    aliases={'int':'Integer','long':'Long','short':'Short','byte':'Byte','char':'Character','boolean':'Boolean',
             'java.lang.String':'String','java.lang.Integer':'Integer','java.lang.Long':'Long',
             'java.lang.Character':'Character','java.lang.Boolean':'Boolean','java.lang.Short':'Short','java.lang.Byte':'Byte'}
    kind=aliases.get(hint,hint)
    if isinstance(value,str) and kind in (None,'String','Character'):
        if kind=='Character' and len(value.encode('utf-16-le',errors='surrogatepass'))!=2:return None
        return {'kind':kind or 'String','key':value}
    if type(value) is bool and kind in (None,'Boolean'):return {'kind':'Boolean','key':value}
    if type(value) is int and kind in (None,'Integer','Long','Short','Byte'):
        kind=kind or 'Integer'
        bits={'Integer':32,'Long':64,'Short':16,'Byte':8}[kind]
        if -(1<<(bits-1))<=value<(1<<(bits-1)):return {'kind':kind,'key':value}
    if type(value) is dict and value.get('__type__') in ('String','java.lang.String') and '__symbol__' in value:
        return {'kind':'String','key':value}
    return None


def same_key(left,right):
    if left['kind']!=right['kind']:return False
    a,b=left['key'],right['key']
    if isinstance(a,dict) or isinstance(b,dict):
        if isinstance(a,dict) and isinstance(b,dict) and a.get('__symbol__')==b.get('__symbol__'):return True
        for symbol,other in ((a,b),(b,a)):
            if isinstance(symbol,dict) and isinstance(other,str):
                length=len(other.encode('utf-16-le',errors='surrogatepass'))//2
                if type(symbol.get('__length__')) is int and symbol['__length__']!=length:return False
                if other in symbol.get('__distinct_from__',[]):return False
            if isinstance(symbol,dict) and isinstance(other,dict) and other.get('__symbol__') in symbol.get('__distinct_symbols__',[]):return False
        return U
    return a==b


def json_key(entry):
    value=entry['key']
    if entry['kind']=='Boolean':return 'true' if value else 'false'
    if type(value) in (str,int):return str(value)
    return U
