"""Constructor-owned values: JSON dictionaries cannot forge a Java Map type."""
from .state import U


class JavaIdentity:
    """An opaque allocation token shared by copies of abstract state."""
    def __deepcopy__(self,memo):return self


class JavaObject(dict):
    """An object whose concrete class was observed at a source constructor."""
    def __init__(self, java_type, fields, identity=...):
        super().__init__(fields)
        self.java_type = java_type
        self.java_identity = JavaIdentity() if identity is ... else identity


class JavaMap(dict):
    def __init__(self, values=None, identity=..., typed_entries=None):
        # Keep the report representation stable, while retaining runtime identity.
        super().__init__(__map__={} if values is None else values)
        self['__typed_entries__']=[] if typed_entries is None else typed_entries
        self.java_identity = JavaIdentity() if identity is ... else identity
        self.last_issue=None

    @property
    def mapping(self):
        return self['__map__']

    def invalidate(self):
        self['__map__'] = U
        self['__typed_entries__']=[]

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


def raw_json_map(value,unresolved=None):
    """Default untyped JSON binding, never inferred from a business key shape."""
    if isinstance(value,dict):
        # A typed abstract DTO still carries metadata that a JSON codec must
        # resolve from source; do not expose it as a fabricated user map entry.
        if '__type__' in value or any(type(key) is not str for key in value):
            if unresolved:unresolved('untyped HTTP JSON contains ambiguous abstract DTO metadata or non-string keys')
            return U
        return JavaMap({key:raw_json_map(item,unresolved) for key,item in value.items()})
    if isinstance(value,list):
        return [raw_json_map(item,unresolved) for item in value]
    return value
