"""Constructor-owned values: JSON dictionaries cannot forge a Java Map type."""
from .state import U
from copy import deepcopy
from .boxed_values import value_kind,json_value_kind
from .map_keys import same_key


class JavaIdentity:
    """An opaque allocation token shared by copies of abstract state."""
    def __deepcopy__(self,memo):return self


class JavaTypeToken(dict):
    """A source-proven Class/JSON type descriptor, never inferred from data."""
    def __init__(self,written,context,kind):
        super().__init__(__java_type__=written)
        self.written,self.kind=written,kind
        self.context={key:context[key] for key in ('module','file')}


class JavaTypeFactory(dict):
    def __init__(self):super().__init__(__type_factory__=True)


class JacksonFeature(dict):
    def __init__(self,name):
        super().__init__(__jackson_feature__=name)
        self.name=name


class JavaJsonMapper(dict):
    """Exact native constructor, with separately observed codec settings."""
    defaults={'FAIL_ON_UNKNOWN_PROPERTIES':True,'FAIL_ON_NULL_FOR_PRIMITIVES':False}
    def __init__(self,flags=None,identity=...):
        super().__init__(__json_mapper__=True)
        self.flags=dict(self.defaults if flags is None else flags)
        self.used,self.opaque=False,False
        self.java_identity=JavaIdentity() if identity is ... else identity

    def invalidate(self):
        self.opaque=True
        self.flags={key:U for key in self.defaults}


class JavaEnumValue(dict):
    """A source-declared enum constant; identity is separate from business fields."""
    def __init__(self,key,owner,fields,json_default=True):
        super().__init__(fields)
        self.enum_key,self.enum_owner=key,owner
        self.enum_name=key.rsplit('.',1)[-1]
        self.json_default=json_default


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
    def __init__(self,payload,exact=False):
        super().__init__(__json__=payload)
        self.exact=exact
    @property
    def payload(self):return self['__json__']


class JavaObject(JavaRecord):
    """An object whose concrete class was observed at a source constructor."""
    def __init__(self, java_type, fields, identity=...,wire_fields=None):
        super().__init__(java_type,fields,wire_fields)
        self.java_type = java_type
        self.java_identity = JavaIdentity() if identity is ... else identity


class JavaMap(dict):
    def __init__(self, values=None, identity=..., typed_entries=None,origin_type=None,value_types=None,flavor=None,order=None):
        # Keep the report representation stable, while retaining runtime identity.
        super().__init__(__map__={} if values is None else values)
        self['__typed_entries__']=[] if typed_entries is None else typed_entries
        self.java_identity = JavaIdentity() if identity is ... else identity
        self.last_issue=None
        self.origin_type=origin_type
        self.value_types={key:value_kind(value) for key,value in self.mapping.items()} if value_types is None and isinstance(self.mapping,dict) else dict(value_types or {})
        self.flavor=flavor
        self.order=[] if flavor=='LinkedHashMap' and values is None and order is None else U if order is None else order
        self.structural_version,self.mutation_version=0,0
        self.uncertain_versions=set()

    def touch(self,structural=False,uncertain=False):
        uncertain=uncertain or structural and self.flavor not in ('HashMap','LinkedHashMap')
        self.mutation_version+=1
        if structural or uncertain:self.structural_version+=1
        if uncertain:self.uncertain_versions.add(self.structural_version)

    @property
    def mapping(self):
        return self['__map__']

    def invalidate(self):
        self.touch(uncertain=True)
        self['__map__'] = U
        self['__typed_entries__']=[]
        self.value_types.clear()
        self.order=U
        if self.last_issue is None:self.last_issue='unknown_map_state'

    @property
    def typed_entries(self):return self['__typed_entries__']

    def raw_entries(self):
        return [{'kind':'String','key':key,'value':value,'value_kind':self.value_types.get(key)} for key,value in self.mapping.items()]+self.typed_entries

    def slot(self,key):
        if not isinstance(self.mapping,dict):return U
        if key['kind']=='String' and isinstance(key['key'],str) and key['key'] in self.mapping:
            return {'kind':'String','key':key['key'],'value':self.mapping[key['key']],'value_kind':self.value_types.get(key['key'])}
        entries=self.typed_entries if key['kind']!='String' or isinstance(key['key'],str) else self.raw_entries()
        unknown=False
        for entry in entries:
            equal=same_key(entry,key)
            if equal is True:return entry
            if equal is U:unknown=True
        return U if unknown else None

    def entries(self):
        if isinstance(self.order,list):return [self.slot(key) for key in self.order]
        return self.raw_entries()

    def put(self,key,value,kind):
        found=self.slot(key)
        if found is U:self.invalidate();self.last_issue='unknown_map_key_equality';return U
        old=found['value'] if found is not None else None
        if key['kind']=='String' and isinstance(key['key'],str):
            self.mapping[key['key']]=value;self.value_types[key['key']]=kind
        elif found is not None:found.update(value=value,value_kind=kind)
        else:self.typed_entries.append({**key,'value':value,'value_kind':kind})
        if found is None and isinstance(self.order,list):self.order.append(dict(key))
        self.touch(structural=found is None)
        return old

    def remove(self,key):
        found=self.slot(key)
        if found is U:self.invalidate();self.last_issue='unknown_map_key_equality';return U
        if found is None:return None
        if key['kind']=='String' and isinstance(key['key'],str):
            del self.mapping[key['key']];self.value_types.pop(key['key'],None)
        else:self.typed_entries.remove(found)
        if isinstance(self.order,list):self.order[:]=[item for item in self.order if same_key(item,key) is not True]
        self.touch(structural=True)
        return found['value']

    def clear_mappings(self):
        self['__map__']={};self.typed_entries.clear();self.value_types.clear()
        self.order=[] if self.flavor=='LinkedHashMap' else U
        self.touch(structural=True,uncertain=self.flavor not in ('HashMap','LinkedHashMap'))

    def merge_metadata(self,left,right):
        self.flavor=left.flavor if left.flavor==right.flavor else None
        self.order=deepcopy(left.order) if isinstance(self.mapping,dict) and isinstance(left.order,list) and isinstance(right.order,list) and len(left.order)==len(right.order) and all(same_key(a,b) is True for a,b in zip(left.order,right.order)) else U
        self.structural_version=max(left.structural_version,right.structural_version)
        self.uncertain_versions=left.uncertain_versions|right.uncertain_versions
        if left.structural_version!=right.structural_version:
            self.structural_version+=1;self.uncertain_versions.add(self.structural_version)
        self.mutation_version=max(left.mutation_version,right.mutation_version)+(left.mutation_version!=right.mutation_version)
        return self


class JavaMapView(dict):
    def __init__(self,mapping,kind):
        super().__init__(__map_view__=kind)
        self.backing,self.kind,self.java_identity,self.last_issue=mapping,kind,None,None


class JavaMapEntry(dict):
    def __init__(self,mapping,key):
        super().__init__(__map_entry__=True)
        self.backing,self.key,self.version=mapping,dict(key),mapping.mutation_version
        self.java_identity,self.last_issue=None,None


class JavaMapIterator(dict):
    def __init__(self,view):
        super().__init__(__map_iterator__=True)
        self.view=view
        self.remaining=[{'kind':entry['kind'],'key':entry['key']} for entry in view.backing.entries()] if isinstance(view.backing.mapping,dict) else U
        self.expected=view.backing.structural_version
        self.last,self.java_identity,self.last_issue=None,None,None


def reference_equal(left,right):
    from .native_storage import JavaList,JavaListIterator
    if left is U or right is U:return U
    if left is right:return True
    if isinstance(left,JavaEnumValue) and isinstance(right,JavaEnumValue):return left.enum_key==right.enum_key
    if isinstance(left,JacksonFeature) and isinstance(right,JacksonFeature):return left.name==right.name
    if isinstance(left,(JavaObject,JavaMap,JavaMapView,JavaMapEntry,JavaMapIterator,JavaJsonMapper,JavaList,JavaListIterator)) and isinstance(right,(JavaObject,JavaMap,JavaMapView,JavaMapEntry,JavaMapIterator,JavaJsonMapper,JavaList,JavaListIterator)):
        return left.java_identity is right.java_identity if left.java_identity is not None and right.java_identity is not None else U
    if left is None or right is None or type(left) in (str,int,float,bool) or type(right) in (str,int,float,bool):return False
    return U


def schema_type(value):
    """A source schema hint for binding; never proof of a Java runtime class."""
    if isinstance(value,JavaRecord):return value.declared_type
    if isinstance(value,(JavaMap,JsonObject)):return value.origin_type
    if isinstance(value,JavaEnumValue):return None
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
    if isinstance(value,JsonText):return deepcopy(value)
    if isinstance(value,dict):
        if is_symbolic(value) and value.get('__type__') in ('String','java.lang.String','int','long','boolean','double','float'):
            return deepcopy(value)
        # A typed abstract DTO still carries metadata that a JSON codec must
        # resolve from source; do not expose it as a fabricated user map entry.
        if '__type__' in value and not isinstance(value,JsonObject) or any(type(key) is not str for key in value):
            if unresolved:unresolved('untyped HTTP JSON contains ambiguous abstract DTO metadata or non-string keys')
            return U
        return JavaMap({key:raw_json_map(item,unresolved) for key,item in value.items()},origin_type=getattr(value,'origin_type',None),
                       value_types={key:json_value_kind(item) for key,item in value.items()})
    if isinstance(value,list):
        from .native_storage import JavaList
        return JavaList([raw_json_map(item,unresolved) for item in value],[json_value_kind(item) for item in value])
    return value
