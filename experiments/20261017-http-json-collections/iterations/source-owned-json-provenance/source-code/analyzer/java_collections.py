"""Constructor-owned values: JSON dictionaries cannot forge a Java Map type."""
from .state import U


class JavaIdentity:
    """An opaque allocation token shared by copies of abstract state."""
    def __deepcopy__(self,memo):return self


class JavaRecord(dict):
    """Source-declared DTO fields, without a claim about exact runtime class."""
    def __init__(self,declared_type,fields,wire_fields=None):
        super().__init__(fields)
        self.declared_type=declared_type
        self.wire_fields=frozenset(set(fields)-{'__type__','__http_entity__'} if wire_fields is None else wire_fields)


class JsonObject(dict):
    """Actual JSON properties; an optional source-schema hint is not a property."""
    def __init__(self,values=(),origin_type=None):
        super().__init__(values)
        self.origin_type=origin_type


class JsonText(dict):
    """An abstract serialized JSON string, created only by JSON adapters."""
    def __init__(self,payload):super().__init__(__json__=payload)
    @property
    def payload(self):return self['__json__']


class JavaObject(JavaRecord):
    """An object whose concrete class was observed at a source constructor."""
    def __init__(self, java_type, fields, identity=...,wire_fields=None):
        super().__init__(java_type,fields,wire_fields)
        self.java_type = java_type
        self.java_identity = JavaIdentity() if identity is ... else identity


class JavaMap(dict):
    def __init__(self, values=None, identity=..., typed_entries=None,origin_type=None):
        # Keep the report representation stable, while retaining runtime identity.
        super().__init__(__map__={} if values is None else values)
        self['__typed_entries__']=[] if typed_entries is None else typed_entries
        self.java_identity = JavaIdentity() if identity is ... else identity
        self.last_issue=None
        self.origin_type=origin_type

    @property
    def mapping(self):
        return self['__map__']

    def invalidate(self):
        self['__map__'] = U
        self['__typed_entries__']=[]
        if self.last_issue is None:self.last_issue='unknown_map_state'

    @property
    def typed_entries(self):return self['__typed_entries__']

    def entries(self):
        return [{'kind':'String','key':key,'value':value} for key,value in self.mapping.items()]+self.typed_entries


def reference_equal(left,right):
    if left is U or right is U:return U
    if left is right:return True
    if isinstance(left,(JavaObject,JavaMap)) and isinstance(right,(JavaObject,JavaMap)):
        return left.java_identity is right.java_identity if left.java_identity is not None and right.java_identity is not None else U
    if left is None or right is None or type(left) in (str,int,float,bool) or type(right) in (str,int,float,bool):return False
    return U


def schema_type(value):
    """A source schema hint for binding; never proof of a Java runtime class."""
    if isinstance(value,JavaRecord):return value.declared_type
    if isinstance(value,(JavaMap,JsonObject)):return value.origin_type
    typ=value.get('__type__') if isinstance(value,dict) and '__symbol__' not in value else None
    return typ if isinstance(typ,str) else None


def is_symbolic(value):
    return type(value) is dict and '__symbol__' in value


def semantic_view(value):
    """Expose source-proven JSON object fields to the language-binding layer."""
    if isinstance(value,JavaMap) and value.origin_type and isinstance(value.mapping,dict):
        fields=dict(value.mapping)
        fields.setdefault('__type__',value.origin_type)
        return JavaRecord(value.origin_type,fields,value.mapping)
    return value


def raw_json_map(value,unresolved=None):
    """Default untyped JSON binding, never inferred from a business key shape."""
    if isinstance(value,dict):
        # A typed abstract DTO still carries metadata that a JSON codec must
        # resolve from source; do not expose it as a fabricated user map entry.
        if '__type__' in value and not isinstance(value,JsonObject) or any(type(key) is not str for key in value):
            if unresolved:unresolved('untyped HTTP JSON contains ambiguous abstract DTO metadata or non-string keys')
            return U
        return JavaMap({key:raw_json_map(item,unresolved) for key,item in value.items()},origin_type=getattr(value,'origin_type',None))
    if isinstance(value,list):
        return [raw_json_map(item,unresolved) for item in value]
    return value
