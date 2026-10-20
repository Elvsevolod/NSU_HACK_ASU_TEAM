"""Bounded abstract interpretation of Java source, with explicit unknown values.

Only source text is interpreted. This module never loads JVM classes or contacts
the application's services. Unresolved branches retain both possible paths.
"""
from collections import defaultdict,Counter
from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
import json
import operator
import math
import re

from .project import text,walk,declaration_matches,keywords
from .state import U
from .models import construct, library, known, unwrap, wire, key_equal, http_entity, optional_value, status_code, header_values
from .constraints import assume, compare
from .java_exceptions import JavaThrow, assignable, native_type, NATIVE_TYPES
from .symbolic_text import concat_text
from .request_url import request_address, client_template
from .http_binding import bind_named, BindingFailure
from .request import Request, MISSING, thaw
from .models import java_date_text, uuid_value, http_headers_type
from .java_collections import JavaObject, JavaRecord, JavaMap, JavaMapView, JavaMapEntry, JavaMapIterator, JavaEnumValue, JavaTypeToken, JavaTypeFactory, JsonObject, JsonText, JavaJsonMapper, JacksonFeature, reference_equal, is_symbolic
from .bean_properties import default_bean_plan,generated_accessor
from .json_codec import operation as codec_operation, conversion as codec_conversion
from .java_numbers import parse_integer
from .source_generics import render as render_source_type,environment as source_environment,member_type,member_scope,call_context
from .source_conversions import compiled_type,declaration_erasure,consumer_type,storage_type,PRIMITIVES
from .boxed_values import NO_KIND,boxed_equal
from .native_storage import JavaFrame,JavaList,JavaListIterator,ReadOnlyList
from .native_arrays import JavaArray,ArrayListView
from .java_lists import call as native_list_call,iteration as native_list_iteration
from .reference_scalars import equal as scalar_reference_equal
from .context_key import fingerprint
from .http_json import decode_response,type_parts
from .map_keys import same_key,key_spec
from .heap_join import join_environment,clone_environment,clone_execution,adopt_execution,owned_objects,widen,source_nodes
from .map_views import iterator_next
from .bean_lifecycle import BeanLifecycle
from .native_contracts import resolve as resolve_native_call,string_call,unknown_observer


def member(obj, key):
    if not isinstance(obj, dict):
        return U
    if key in obj:
        return obj[key]
    if isinstance(obj,(JavaRecord,JsonObject,JavaEnumValue)):return U
    normalized = re.sub(r'[^a-z0-9]', '', key.lower())
    return next((v for k, v in obj.items() if re.sub(r'[^a-z0-9]', '', k.lower()) == normalized), U)


def merge_record_metadata(result,left,right):
    for name in ('_native_field_kinds','_field_reference_types'):
        a,b=getattr(left,name,{}),getattr(right,name,{})
        setattr(result,name,{key:a.get(key) if a.get(key)==b.get(key) else None for key in a.keys()|b.keys()})
    result._unchecked_generic_fields=set(getattr(left,'_unchecked_generic_fields',()))|set(getattr(right,'_unchecked_generic_fields',()))
    for name in ('source_owner','_json_receiver_type','_json_receiver_context'):
        value=getattr(left,name,None)
        if value is not None and value==getattr(right,name,None):setattr(result,name,deepcopy(value))
    return result


def exception_type(value):
    return value.java_type if isinstance(value,JavaObject) else native_type(value.get('__type__',U)) if type(value) is dict else U


def merge(a, b, active=None, memo=None):
    active=set() if active is None else active
    memo={} if memo is None else memo
    pair=(id(a),id(b))
    if pair in active:return U
    if pair not in memo:memo[pair]=merge_values(a,b,active,memo)
    return memo[pair]


def merge_values(a, b, active, memo):
    if a is b:return a
    if isinstance(a,JacksonFeature) or isinstance(b,JacksonFeature):
        return a if isinstance(a,JacksonFeature) and isinstance(b,JacksonFeature) and a.name==b.name else U
    if isinstance(a,JavaJsonMapper) or isinstance(b,JavaJsonMapper):
        if not isinstance(a,JavaJsonMapper) or not isinstance(b,JavaJsonMapper):return U
        identity=a.java_identity if a.java_identity is b.java_identity else None
        result=JavaJsonMapper({key:merge(a.flags[key],b.flags[key],active,memo) for key in a.defaults},identity)
        result.used,result.opaque=a.used or b.used,a.opaque or b.opaque
        return result
    if isinstance(a,JavaTypeToken) or isinstance(b,JavaTypeToken):
        return a if isinstance(a,JavaTypeToken) and isinstance(b,JavaTypeToken) and (a.written,a.kind,a.context)==(b.written,b.kind,b.context) else U
    if isinstance(a,JavaEnumValue) or isinstance(b,JavaEnumValue):
        return a if isinstance(a,JavaEnumValue) and isinstance(b,JavaEnumValue) and a.enum_key==b.enum_key and a==b else U
    if isinstance(a,JavaRecord) or isinstance(b,JavaRecord):
        if not isinstance(a,JavaRecord) or not isinstance(b,JavaRecord) or a.declared_type!=b.declared_type:return U
    active=set() if active is None else active
    pair=(id(a),id(b))
    if pair in active:return U
    active.add(pair)
    try:
        if isinstance(a,JavaRecord):
            from .persistence import LazyRecord
            if isinstance(a,LazyRecord) or isinstance(b,LazyRecord):
                if not isinstance(a,LazyRecord) or not isinstance(b,LazyRecord) or (a.resource,a.id_fields,a.loaded)!=(b.resource,b.id_fields,b.loaded):return U
                result=LazyRecord(a.declared_type,{key:merge(a.get(key,U),b.get(key,U),active,memo) for key in a.keys()|b.keys()},a.wire_fields|b.wire_fields,a.resource,a.id_fields)
                result.loaded=a.loaded
                return merge_record_metadata(result,a,b)
            fields={key:merge(a.get(key,U),b.get(key,U),active,memo) for key in sorted(a.keys()|b.keys())}
            wire_fields=a.wire_fields|b.wire_fields
            if isinstance(a,JavaObject) and isinstance(b,JavaObject):
                identity=a.java_identity if a.java_identity is b.java_identity else None
                return merge_record_metadata(JavaObject(a.java_type,fields,identity,wire_fields),a,b)
            return merge_record_metadata(JavaRecord(a.declared_type,fields,wire_fields),a,b)
        if isinstance(a,JavaMap) or isinstance(b,JavaMap):
            if not isinstance(a,JavaMap) or not isinstance(b,JavaMap):return U
            identity=a.java_identity if a.java_identity is b.java_identity else None
            if (not isinstance(a.mapping,dict) or not isinstance(b.mapping,dict) or a.mapping.keys()!=b.mapping.keys()
                    or len(a.typed_entries)!=len(b.typed_entries)
                    or any(same_key(left,right) is not True for left,right in zip(a.typed_entries,b.typed_entries))):
                return JavaMap(U,identity).merge_metadata(a,b)
            typed=[{**left,'value':merge(left['value'],right['value'],active,memo),
                    'value_kind':left.get('value_kind') if left.get('value_kind')==right.get('value_kind') else None} for left,right in zip(a.typed_entries,b.typed_entries)]
            origin=a.origin_type if a.origin_type==b.origin_type else None
            kinds={key:a.value_types.get(key) if a.value_types.get(key)==b.value_types.get(key) else None for key in a.mapping}
            return JavaMap({key:merge(value,b.mapping[key],active,memo) for key,value in a.mapping.items()},identity,typed,origin,kinds).merge_metadata(a,b)
        if isinstance(a,JavaMapView) or isinstance(b,JavaMapView):
            if not isinstance(a,JavaMapView) or not isinstance(b,JavaMapView) or a.kind!=b.kind:return U
            backing=merge(a.backing,b.backing,active,memo)
            return JavaMapView(backing,a.kind) if isinstance(backing,JavaMap) else U
        if isinstance(a,JavaMapEntry) or isinstance(b,JavaMapEntry):
            if not isinstance(a,JavaMapEntry) or not isinstance(b,JavaMapEntry) or same_key(a.key,b.key) is not True:return U
            backing=merge(a.backing,b.backing,active,memo)
            if not isinstance(backing,JavaMap):return U
            result=JavaMapEntry(backing,a.key);result.version=a.version if a.version==b.version else None
            return result
        if isinstance(a,JavaMapIterator) or isinstance(b,JavaMapIterator):
            if not isinstance(a,JavaMapIterator) or not isinstance(b,JavaMapIterator):return U
            view=merge(a.view,b.view,active,memo)
            if not isinstance(view,JavaMapView):return U
            result=JavaMapIterator(view)
            result.remaining=merge(a.remaining,b.remaining,active,memo)
            result.expected=a.expected if a.expected==b.expected else None
            result.last=merge(a.last,b.last,active,memo)
            return result
        if isinstance(a,JsonText) or isinstance(b,JsonText):
            return JsonText(merge(a.payload,b.payload,active,memo),a.exact and b.exact) if isinstance(a,JsonText) and isinstance(b,JsonText) else U
        if isinstance(a,JsonObject) or isinstance(b,JsonObject):
            if not isinstance(a,JsonObject) or not isinstance(b,JsonObject):return U
            fields={key:merge(a.get(key,U),b.get(key,U),active,memo) for key in a.keys()|b.keys()}
            result=JsonObject(fields,a.origin_type if a.origin_type==b.origin_type else None)
            if a.source_pairs is not None and b.source_pairs is not None and tuple(k for k,_ in a.source_pairs)==tuple(k for k,_ in b.source_pairs):
                result.source_pairs=tuple((key,merge(left,right,active,memo)) for (key,left),(_,right) in zip(a.source_pairs,b.source_pairs))
            return result
        if isinstance(a,JavaFrame) or isinstance(b,JavaFrame):
            if not isinstance(a,JavaFrame) or not isinstance(b,JavaFrame):return U
            values={key:merge(a.get(key,U),b.get(key,U),active,memo) for key in a.keys()|b.keys()}
            kinds={key:a.kinds.get(key) if a.kinds.get(key)==b.kinds.get(key) else None for key in values}
            return JavaFrame(values,kinds)
        if isinstance(a,JavaList) or isinstance(b,JavaList):
            if isinstance(a,ReadOnlyList) or isinstance(b,ReadOnlyList):
                if type(a) is not type(b):return U
                backing=merge(a.backing,b.backing,active,memo)
                if not isinstance(backing,JavaList):return U
                result=type(a)(backing)
                result.java_identity=a.java_identity if a.java_identity is b.java_identity else None
                return result
            from .persistence import LazyCollection
            lazy=isinstance(a,LazyCollection) or isinstance(b,LazyCollection)
            if lazy:
                attributes=('resource','foreign','key','value_column','order_column','origin','reason','loaded')
                if not isinstance(a,LazyCollection) or not isinstance(b,LazyCollection) or any(getattr(a,key)!=getattr(b,key) for key in attributes):return U
            if not isinstance(a,JavaList) or not isinstance(b,JavaList) or len(a)!=len(b):return U
            values=[merge(left,right,active,memo) for left,right in zip(a,b)]
            kinds=[left if left==right else None for left,right in zip(a.kinds,b.kinds)]
            identity=a.java_identity if a.java_identity is b.java_identity else None
            if isinstance(a,JavaArray) or isinstance(b,JavaArray):
                return JavaArray(values,a.component,kinds,identity) if isinstance(a,JavaArray) and isinstance(b,JavaArray) and a.component==b.component else U
            result=JavaList(values,kinds,identity)
            if lazy:
                result=LazyCollection(a.resource,a.foreign,a.key,a.value_column,a.order_column,a.origin,a.reason)
                result.loaded=a.loaded;result.extend(values,kinds);result.java_identity=identity
            result.structural_version=a.structural_version if a.structural_version==b.structural_version else None
            result.opaque=a.opaque or b.opaque
            result.fixed_size=a.fixed_size if a.fixed_size==b.fixed_size else None
            result.flavor=a.flavor if a.flavor==b.flavor else None
            result.order_known=a.order_known and b.order_known
            return result
        if isinstance(a,JavaListIterator) or isinstance(b,JavaListIterator):
            if not isinstance(a,JavaListIterator) or not isinstance(b,JavaListIterator):return U
            backing=merge(a['backing'],b['backing'],active,memo)
            if not isinstance(backing,JavaList):return U
            result=JavaListIterator(backing)
            result.java_identity=a.java_identity if a.java_identity is b.java_identity else None
            result.update((name,merge(a[name],b[name],active,memo)) for name in ('index','last'))
            result['expected']=a['expected'] if a['expected']==b['expected'] else None
            return result
        if isinstance(a, dict) and isinstance(b, dict):
            return {key: merge(a.get(key, U), b.get(key, U),active,memo) for key in sorted(a.keys() | b.keys(), key=lambda k: (type(k).__name__, str(k)))}
        if isinstance(a,list) and isinstance(b,list):
            if len(a)!=len(b):return U
            joined=[merge(left,right,active,memo) for left,right in zip(a,b)]
            return joined if joined==a and joined==b else U
        if isinstance(a,tuple) and isinstance(b,tuple) and len(a)==len(b) and len(a) in (5,7) and a[0]==b[0]=='lambda':
            if a[1]!=b[1] or a[3:]!=b[3:]:return U
            return ('lambda',a[1],merge(a[2],b[2],active,memo),*a[3:])
        if type(a) is type(b) and a == b:return a
        return U
    finally:
        active.remove(pair)


class AlternativeRequired(Exception):
    def __init__(self, key, choices):
        self.key, self.choices = key, choices


class CompletionRequired(AlternativeRequired):
    """Completion modes cannot share a continuation or a catch clause."""


class AnalysisBoundary(Exception):
    def __init__(self,message,category='completion_budget'):
        super().__init__(message)
        self.category=category


class Engine:
    def __init__(self, project, state, decisions=None, conservative=False, constraints=True):
        self.p, self.state = project, state
        self.edges = set()
        self.evidence = defaultdict(set)
        self.conditions, self.warnings = [], set()
        self.data_operations = []
        self.created_objects = []
        self.active = set()
        self.calls = 0
        self.method = None
        self.invocation_projection = None
        self.params = {}
        self.uncertain = 0
        self.decisions = decisions or {}
        self.conservative = conservative
        self.branch_index = 0
        self.approximate = False
        self.outcome = 'returned' 
        self.use_constraints = constraints
        self.variable_types = {}
        self.source_bindings={}
        self.receiver_type=''
        self.value_frames=[]
        self.last_reference_kind=NO_KIND
        self.current_return_kind=NO_KIND
        self.last_invoke_kind=NO_KIND
        self.last_callback_kind=NO_KIND
        self.last_invoke_started=False
        self.return_type_override=None
        self.entry_list_bindings={}
        self.constraint_sequence = 0
        self.filter_frames = []
        self.operation_issues=Counter()
        self.events, self.request_events = [], []
        self.semantic_callbacks, self.reflection_edges = [], set()
        self.http_responses = []
        self.candidate_edges = set()
        self.guard_stack, self.execution_assumptions = [], []
        self.event_keys = set()
        self.assumption_registry = {}
        self.event_contexts, self.event_context_ids = {}, {}
        self.input_assumptions = []
        self.effect_events, self.opaque_heap = [], []
        self.path_replay = False
        self.allow_completion_splits=True
        self.persistence_events = []
        self.implicit_initializer = 0
        self.initializer_context = None

    def source_call_visible(self):
        return not self.initializer_context or self.method != self.initializer_context[1] or not self.initializer_context[2]

    def opaque(self, value):
        return any(value is reference for reference in self.opaque_heap)

    def constraint_symbol(self):
        self.constraint_sequence += 1
        return 'path-scalar-' + str(self.constraint_sequence)

    def choose(self, label, choices):
        self.branch_index += 1
        key = str(self.branch_index) + ':' + label
        if key in self.decisions:
            return self.decisions[key]
        if not self.conservative:
            raise AlternativeRequired(key, choices)
        self.approximate = True
        self.warnings.add('path budget: alternatives conservatively retained at ' + label)
        return None

    def add(self, source, relation, target, reason, values=None):
        if relation=='calls' and self.invocation_projection==(source,False):
            self.reflection_edges.add((source,relation,target))
            return
        self.edges.add((source, relation, target))
        self.evidence[(source, relation, target)].add(reason)
        request_id = self.filter_frames[-1].get('request_id') if self.filter_frames else None
        guards = tuple(tuple(sorted(item.items())) for item in self.guard_stack)
        self.execution_assumptions=list(dict.fromkeys(self.execution_assumptions))
        assumptions=[]
        for assumption in self.execution_assumptions:
            if assumption not in self.assumption_registry:self.assumption_registry[assumption]='A'+str(len(self.assumption_registry)+1)
            assumptions.append(self.assumption_registry[assumption])
        key = (source, relation, target, reason, request_id, guards, tuple(assumptions))
        if key not in self.event_keys:
            self.event_keys.add(key)
            context_key=(guards,tuple(assumptions))
            if context_key not in self.event_context_ids:
                context_id='C'+str(len(self.event_context_ids)+1)
                self.event_context_ids[context_key]=context_id
                self.event_contexts[context_id]={'guards':deepcopy(self.guard_stack),'assumptions':assumptions}
            context_id=self.event_context_ids[context_key]
            site = self.p.nodes.get(reason, {})
            self.events.append({'edge': (source, relation, target), 'request': request_id,
                'callsite': reason, 'method': self.method,
                'line': site.get('line'), 'context': context_id,
                'values':values if values is not None else {'request_provenance':request_id},
                'cause': ('datastore' if self.p.nodes[target].get('resource_kind')=='collection' else 'sql') if relation == 'data' else 'http' if relation == 'remote' else
                         'direct_call' if relation == 'calls' else
                         'framework_dispatch' if 'callback' in reason or 'filter' in reason else 'source_execution'})

    @property
    def confirmed_edges(self):
        return {tuple(event['edge']) for event in self.events
                if not self.event_contexts[event['context']]['assumptions']
                and all(not guard.get('assumed') for guard in self.event_contexts[event['context']]['guards'])}

    @contextmanager
    def event_guard(self, condition, value, assumed=False):
        self.guard_stack.append({'condition': condition, 'value': str(value), 'assumed': assumed})
        try:yield
        finally:self.guard_stack.pop()

    def assume(self, reason):
        if reason not in self.execution_assumptions:self.execution_assumptions.append(reason)

    def executed(self, mid, reason, values=None):
        if self.invocation_projection==(mid,False):
            self.reflection_edges.add(('', 'executes', mid))
            return
        self.add('', 'executes', mid, reason,values)

    def json_issue(self,message,reason):
        self.approximate=True
        self.assume('JSON model boundary: '+message+': '+reason)
        self.warnings.add(message+': '+reason)
        self.operation_issues[('http_json_binding',message)]+=1

    def json_wire(self,value,reason):
        return wire(value,lambda message:self.json_issue(message,reason),self.p.json_model_limits,BeanLifecycle(self,reason).read)

    def run(self, entry, params):
        self.params = params
        self.entry = entry
        request = params if isinstance(params, Request) else getattr(params, 'request', None)
        if request:
            provenance = thaw(request.provenance)
            self.input_assumptions = list(provenance.get('__assumptions__', [])) if isinstance(provenance, dict) else []
        try:
            args = (lambda: self.bind_request(entry, request, 'scenario request')) if request else lambda: [self.input_value(name, typ, params,entry) for name, typ in self.p.parameters(entry)]
            result,_ = self.http_invoke(entry, args, 'scenario request', request)
            response=unwrap(result)
            if any(entry==handler for handler,_,_ in self.p.ix.handlers):
                try:response=self.json_wire(response,entry)
                except JavaThrow as failure:
                    if isinstance(failure.value,dict) and failure.value.get('__serialization_failure__'):
                        self.outcome='HTTP serialization failure'
                        self.warnings.add('default HTTP JSON serialization failed: '+entry)
                        return U
                    raise
            if self.outcome == 'returned' and http_entity(result) and type(result.get('status')) is int and result['status']>=400:
                self.outcome='HTTP error response'
        except AnalysisBoundary as boundary:
            self.outcome='analysis completion budget exhausted' if boundary.category=='completion_budget' else boundary.category+' boundary'
            self.operation_issues[(boundary.category,'stop')]+=1
            self.warnings.add(str(boundary))
            self.fallback(entry)
            message='unobserved continuation after completion budget: '+entry
            from .resource_effects import possible_writes
            closure=self.p.ix.closure({entry})
            writable=possible_writes(self.p,closure[0],closure[3],bool(self.state.transactions))
            for _,relation,rid in self.candidate_edges:
                if relation!='data' or rid not in writable:continue
                rows=self.state.database.rows(self.p.nodes[rid])
                if rows is not None:self.state.database.invalidate(rows)
                self.state.resource_assumptions.setdefault(rid,[]).append(message)
            return U
        except JavaThrow as exc:
            self.outcome = 'uncaught application exception'
            self.warnings.add('uncaught Java exception: '+str(exception_type(exc.value)))
            return U
        return response

    def http_invoke(self,entry,args,reason,request=None,on_entry=None):
        if not self.p.enabled_type(self.p.methods[entry]['owner']):
            self.outcome='inactive request handler'
            self.warnings.add('request handler disabled by Spring profile: '+entry)
            return U,False
        meta=self.p.methods[entry]
        type_names=[*re.findall(r'[\w.]+',meta.get('return_raw','')),
                    *(typ for _,typ in self.p.parameters(entry))]
        for name in type_names:
            tid=self.p.resolve_type(name,meta['module'],meta['file'])
            for annotation in self.p.nodes.get(tid,{}).get('annotations',[]):
                if annotation['name'].split('.')[-1] in ('JsonSerialize','JsonDeserialize'):
                    self.approximate=True
                    self.warnings.add('custom HTTP codec is not executed: '+annotation['name']+' on '+name)
        filters = [mid for mid in self.p.by_name.get('doFilterInternal',[])
                   if self.p.ix.unit_of(mid)==self.p.ix.unit_of(entry)
                   and self.p.enabled_type(self.p.methods[mid]['owner'])
                   and 'OncePerRequestFilter' in (self.p.root/self.p.methods[mid]['file']).read_text()]
        def order(mid):
            annotations = [*self.p.methods[mid].get('annotations',[]),*self.p.nodes[self.p.methods[mid]['owner']].get('annotations',[])]
            values = [re.fullmatch(r'\(\s*(-?\d+)\s*\)',a.get('args','')) for a in annotations if a['name'].split('.')[-1]=='Order']
            return int(values[0][1]) if len(values)==1 and values[0] is not None else None
        orders = [order(mid) for mid in filters]
        if filters:
            self.approximate=True
            self.warnings.add('request filter registration is assumed from source classes; full bean registration is not modeled')
        if len(filters)>1 and (None in orders or len(set(orders))!=len(orders)):
            self.warnings.add('unknown request filter order; possible execution retained: '+entry)
            self.fallback(entry)
            for mid in filters:self.fallback(mid)
        filters.sort(key=lambda mid:(order(mid) is None,order(mid) or 0,mid))
        response = {'__type__':'HttpServletResponse','status':200,'body':U}
        frame = {'entry':entry,'args':args,'filters':filters,'reason':reason,'entered':False,'result':U,'on_entry':on_entry,'immutable_request':request,
                 'response':response,'request':{'__type__':'HttpServletRequest',
                    'headers':request.headers if request else U,
                    'method':request.method if request else U,
                    'uri':request.url if request else U,
                    'actor':thaw(request.actor) if request else U,
                    'session':thaw(request.session) if request else U}}
        frame['request_id'] = len(self.request_events) + 1
        self.request_events.append({'id': frame['request_id'], 'entry': entry, 'reason': reason,
                                    'request': request.record() if request else None})
        self.filter_frames.append(frame)
        try:
            self.continue_filter(len(self.filter_frames)-1,0)
            if frame['entered']:
                from .http_contracts import response_status
                result=None if meta.get('return_raw')=='void' else frame['result']
                status=result.get('status',U) if http_entity(result) else response_status(meta.get('annotations',[]))
                if status is None:status=response_status(self.p.nodes[meta['owner']].get('annotations',[]))
                if status is None:status=200
                self.http_responses.append({'request':frame['request_id'],'status':status,'entered':True,
                    'body_presence':'empty' if meta.get('return_raw')=='void' or status==204 else 'json'})
                if not http_entity(result):result={'__type__':'ResponseEntity','__http_entity__':True,'body':result,'status':status}
                return result,True
            if len(self.filter_frames)==1:self.outcome='HTTP binding failure' if frame.get('binding_failed') else 'request stopped by filter'
            self.http_responses.append({'request':frame['request_id'],'status':response['status'],'entered':False})
            return {'__type__':'ResponseEntity','__http_entity__':True,'body':response['body'],'status':response['status']},False
        except JavaThrow as failure:
            failure.http_entered=frame['entered']
            from .http_contracts import exception_handler,response_status
            handler=exception_handler(self,entry,failure)
            if handler:
                pars=self.p.parameters(handler)
                body=self.invoke(handler,[failure.value for _ in pars],reason='Spring ExceptionHandler callback')
                status=response_status(self.p.methods[handler].get('annotations',[]))
                if status is None:status=200
                if self.p.methods[handler].get('return_raw')=='void':body=None
                result=body if http_entity(body) else {'__type__':'ResponseEntity','__http_entity__':True,'body':body,'status':status}
                self.http_responses.append({'request':frame['request_id'],'status':result.get('status',U),'entered':frame['entered'],'exception_handler':handler,
                    'body_presence':'empty' if self.p.methods[handler].get('return_raw')=='void' else 'json'})
                return result,frame['entered']
            self.http_responses.append({'request':frame['request_id'],'status':self.server_error_status(entry,failure),'entered':frame['entered']})
            raise
        finally:
            self.filter_frames.pop()

    def server_error_status(self,target,failure):
        if getattr(failure,'mapping_unresolved',False):return U
        unit=self.p.ix.unit_of(target)
        cache=self.p.__dict__.setdefault('_server_error_mapping_cache',{})
        if unit not in cache:
            cache[unit]=any(any(parent.split('.')[-1] in ('HandlerExceptionResolver','ErrorController') for parent in parents)
                             for owner,parents in self.p.framework_types.items() if unit in self.p.ix.units.get(self.p.nodes[owner].get('module'),()))
        thrown=exception_type(failure.value)
        meta=self.p.methods[target]
        pending=[self.p.resolve_type(thrown,meta['module'],meta['file'])] if isinstance(thrown,str) else []
        seen=set();custom=cache[unit]
        while pending:
            owner=pending.pop()
            if owner is None or owner in seen:continue
            seen.add(owner)
            from .http_contracts import response_status
            status=response_status(self.p.nodes[owner].get('annotations',[]))
            if status is not None and not custom:return status
            pending.extend(self.p.type_parents.get(owner,()))
        if not custom and isinstance(failure.value,dict) and '__http_binding_status__' in failure.value:
            return failure.value['__http_binding_status__']
        if not custom and (assignable(thrown,'java.lang.Exception',self.p) is True or assignable(thrown,'java.lang.Error',self.p) is True):return 500
        self.json_issue('server exception status or custom exception resolver is not modeled',target)
        return U

    def continue_filter(self,frame_index,position):
        frame = self.filter_frames[frame_index]
        if position==len(frame['filters']):
            try:
                args=frame['args']() if callable(frame['args']) else frame['args']
                node_memo={id(node):node for node in source_nodes(args)}
                request_event=next(event for event in self.request_events if event['id']==frame['request_id'])
                request_event['binding_candidate_arguments']=[{'name':name,'declared_type':render_source_type(self.p,typ,self.p.methods[frame['entry']],{},self.standard_type) or typ,
                    'value':deepcopy(value,node_memo)} for (name,typ),value in zip(self.p.parameters(frame['entry']),args)]
                from .java_sets import shapes
                for argument,value in zip(request_event['binding_candidate_arguments'],args):
                    shape=shapes(value,'value')
                    if shape:argument['collection_shapes']=shape
                from .http_validation import validate
                validate(self,frame['entry'],args)
            except BindingFailure as failure:
                frame['binding_failed']=True
                self.warnings.add('HTTP binding rejected request: '+str(failure))
                frame['response']['status']=self.server_error_status(frame['entry'],JavaThrow(
                    {'__http_binding_status__':failure.status,'__type__':'ServletRequestBindingException'}))
                return
            frame['entered']=True
            from .security import authorize_request
            allowed=authorize_request(self,frame['entry'],args,frame.get('immutable_request'))
            if allowed is False:
                frame['entered']=False;frame['response']['status']=403
                return
            request_event['authorization_checked']=allowed is not None
            request_event['bound_arguments']=request_event.pop('binding_candidate_arguments')
            if frame['on_entry']:frame['on_entry'](frame['request_id'])
            frame['result']=self.invoke(frame['entry'],args,reason=frame['reason'])
            return
        mid = frame['filters'][position]
        skips=self.p.methods_of(self.p.methods[mid]['owner'],'shouldNotFilter')
        if len(skips)==1:
            skip=self.invoke(skips[0],[frame['request']],reason='OncePerRequestFilter shouldNotFilter callback')
            if type(skip) is not bool:
                self.approximate=True
                self.warnings.add('unknown shouldNotFilter result: '+mid)
                skip=self.choose(mid+':should-not-filter',[True,False])
                if skip is None:self.fallback(frame['entry'])
            if skip is True:
                self.continue_filter(frame_index,position+1)
                return
        values = [{'__filter_chain__':(frame_index,position+1)} if typ.endswith('FilterChain') else
                  frame['response'] if typ.endswith('HttpServletResponse') else frame['request']
                  for _,typ in self.p.parameters(mid)]
        self.invoke(mid,values,reason='project request filter')

    def input_value(self, name, typ, params,target=None):
        if typ.split('.')[-1].lstrip('?')=='HttpHeaders':
            return {'__type__': 'HttpHeaders','__http_headers__':True,'headers':U}
        target=target or self.method or getattr(self,'entry','')
        contract=self.p.http_parameters(target)
        flat=name in getattr(params,'flat_bodies',())
        if (name not in params or flat) and any(p['name']==name and p['kind']=='RequestBody' for p in contract):
            meta=self.p.methods[target]
            if self.p.resolve_type(typ,meta['module'],meta['file']) not in self.p.type_fields:
                self.json_issue('flat request body has no declared DTO property layout','scenario request')
                return U
            other={p['name'] for p in contract if p['kind']!='RequestBody'}
            absent=getattr(params,'body_omissions',{}).get(name,())
            return self.bind_http_body({key:value for key,value in params.items() if key not in other and key not in absent},typ,target,'scenario request',
                                       getattr(params,'body_unknowns',{}).get(name,{}))
        if name in params:
            if any(p['name']==name and p['kind']=='RequestBody' for p in self.p.http_parameters(target)):
                if self.standard_type(typ,'java.lang.String',self.p.methods[target]):
                    return deepcopy(params[name]) if isinstance(params[name],JsonText) else self.coerce(params[name],typ)
                return self.bind_http_body(params[name],typ,target,'scenario request')
            value=self.coerce(params[name],typ)
            base,elements=type_parts(typ)
            if type(value) is list and elements is not None and len(elements)<=1 and any(self.standard_type(base,'java.util.'+t,self.p.methods[target]) for t in ('List','ArrayList','LinkedList','Collection')):
                hint=next((kind for kind in ('String','Integer','Long','Short','Byte','Character','Boolean','Float','Double')
                           if elements and self.standard_type(elements[0],'java.lang.'+kind,self.p.methods[target])),None)
                key=id(value)
                if key not in self.entry_list_bindings:self.entry_list_bindings[key]=(value,JavaList(value,[hint]*len(value)),hint)
                original,bound,previous_hint=self.entry_list_bindings[key]
                if hint and previous_hint and hint!=previous_hint and bound:
                    bound.kinds[:]=[None]*len(bound)
                    self.approximate=True
                    self.warnings.add('shared entry list has conflicting declared native element classes')
                elif hint and not previous_hint:
                    bound.kinds[:]=[hint]*len(bound);self.entry_list_bindings[key]=(original,bound,hint)
                value=bound
            return value
        if typ.split('.')[-1] in ('String', 'UUID', 'int', 'double', 'boolean', 'Date', 'Long'):
            return U
        value = {'__type__': typ, **deepcopy(params)}
        method = target
        meta = self.p.methods.get(method, {})
        tid = self.p.resolve_type(typ, meta.get('module'), meta.get('file'))
        if tid in self.p.type_fields and not typ.startswith('org.springframework.http.'):
            if '__http_entity__' not in self.p.type_fields[tid]:value['__http_entity__'] = False
            value=JavaRecord(self.p.nodes[tid]['fqn'],value,self.p.type_fields[tid])
            value.source_owner=tid
        return value

    def bind_http_body(self,value,typ,target,reason,unknown_properties=None):
        """Own the HTTP value independently and rebind by the receiver's schema."""
        meta=self.p.methods[target]
        payload=self.json_wire(value,reason)
        if self.standard_type(typ,'java.lang.String',meta):
            if isinstance(payload,(JsonText,str)) or is_symbolic(payload) and payload.get('__type__') in ('String','java.lang.String'):return deepcopy(payload)
            if type(payload) in (int,bool):return str(payload).lower()
            if isinstance(payload,(dict,list)):return JsonText(payload)
            if payload is U or payload is None:return payload
            self.json_issue('HTTP request text representation is not modeled',reason)
            return U
        if isinstance(payload,JsonText):payload=payload.payload
        cache=self.p.__dict__.setdefault('_http_boot_codec',{})
        unit=self.p.ix.unit_of(target)
        if unit not in cache:
            owners=[owner for owner,info in self.p.nodes.items() if info['kind']=='type' and unit in self.p.ix.units.get(info.get('module'),())]
            boot=any(any(a['name'].rsplit('.',1)[-1]=='SpringBootApplication' for a in self.p.nodes[owner].get('annotations',[])) for owner in owners)
            custom=any(method['name'] in ('configureMessageConverters','extendMessageConverters') or
                       any(a['name'].rsplit('.',1)[-1]=='Bean' for a in method.get('annotations',[])) and
                       any(word in method.get('return_raw','') for word in ('ObjectMapper','Jackson2ObjectMapperBuilder','MappingJackson2HttpMessageConverter'))
                       for mid,method in self.p.methods.items() if self.p.ix.unit_of(mid)==unit)
            cache[unit]=boot and not custom
        codec=({'FAIL_ON_UNKNOWN_PROPERTIES':False,'FAIL_ON_NULL_FOR_PRIMITIVES':False,'FAIL_ON_IGNORED_PROPERTIES':False} if cache[unit] else None)
        try:
            return decode_response(self.p,payload,typ,meta,self.standard_type,lambda message:self.json_issue(message,reason),
                                   codec=codec,lifecycle=BeanLifecycle(self,reason,defaults_certain=codec is not None,request_unknowns=(payload,unknown_properties or {})))
        except JavaThrow as failure:
            if assignable(exception_type(failure.value),'com.fasterxml.jackson.core.JsonProcessingException',self.p) is True:
                raise BindingFailure('JSON body construction or property conversion failed') from None
            raise

    @staticmethod
    def coerce(value, typ):
        if typ in ('UUID','java.util.UUID') and value is not None and value is not U:
            try:return uuid_value(value)
            except JavaThrow:return U
        typ = typ.split('.')[-1]
        if value is U or value is None:
            return value
        if is_symbolic(value):
            aliases = {'Integer': 'int', 'Long': 'long', 'Boolean': 'boolean', 'Double': 'double', 'Float': 'float'}
            source_type = value['__type__'].split('.')[-1]
            return value if aliases.get(source_type, source_type) == aliases.get(typ, typ) else U
        if typ in ('boolean', 'Boolean'):
            return value if isinstance(value, bool) else value.lower() == 'true' if isinstance(value, str) and value.lower() in ('true', 'false') else U
        if typ in ('int', 'Integer', 'long', 'Long', 'short', 'Short', 'byte', 'Byte'):
            if isinstance(value, bool):
                return U
            try:
                return int(value) if isinstance(value, (str, int)) else U
            except ValueError:
                return U
        if typ in ('double', 'Double', 'float', 'Float'):
            try:
                return float(value) if not isinstance(value, bool) else U
            except (TypeError, ValueError):
                return U
        if typ == 'Date':
            from .models import date_value
            return date_value(value)
        if typ == 'String':
            return value if isinstance(value, str) else U
        if isinstance(value, str):
            try:
                if typ in ('int', 'Integer', 'long', 'Long'): return int(value)
                if typ in ('double', 'Double', 'float', 'Float'): return float(value)
                if typ in ('boolean', 'Boolean'): return value.lower() == 'true'
            except ValueError:
                return U
        return value

    @contextmanager
    def project_invocation(self,mid,export_method):
        # Library reflection can require semantic execution while its root
        # method is excluded by the output contract. Nested source calls own
        # a separate projection; data effects are never skipped here.
        previous=self.invocation_projection
        self.invocation_projection=(mid,export_method)
        try:yield
        finally:self.invocation_projection=previous

    def invoke(self, mid, args, receiver=None, reason='source call',type_context=None,argument_kinds=None,export_method=True):
        with self.project_invocation(mid,export_method):
            return self._invoke(mid,args,receiver,reason,type_context,argument_kinds)

    def _invoke(self, mid, args, receiver=None, reason='source call',type_context=None,argument_kinds=None):
        self.last_invoke_kind=NO_KIND
        self.last_invoke_started=False
        meta = self.p.methods[mid]
        if (receiver is None or receiver is U) and 'static' not in self.method_modifiers(mid):
            from .bean_initialization import initialized_receiver
            initialized=initialized_receiver(self,mid)
            if initialized is not U:receiver=initialized
        if self.p.profile_status(meta['owner']) is U:
            self.approximate=True
            self.warnings.add('unsupported Spring profile expression; candidate retained as possible: '+mid)
        for annotation in [*meta.get('annotations',[]),*self.p.nodes[meta['owner']].get('annotations',[])]:
            if annotation['name'].split('.')[-1] in ('PreAuthorize','PostAuthorize','Secured','RolesAllowed','Cacheable','CachePut','CacheEvict','Async') or annotation['name'].split('.')[-1].startswith('Conditional'):
                self.approximate=True
                self.warnings.add('framework method interception is not fully modeled: '+annotation['name']+' at '+mid)
        node=self.p.ast.get(mid)
        if node is not None and re.search(r'@(?:Valid|Validated)\b',text(node.child_by_field_name('parameters'))):
            self.approximate=True
            self.warnings.add('request bean validation is not fully modeled: '+mid)
        transactional = any(a['name'].split('.')[-1] == 'Transactional' for a in
                            [*meta.get('annotations', []), *self.p.nodes[meta['owner']].get('annotations', [])])
        type_context=type_context or call_context(self.p,mid,self.p.nodes[meta['owner']]['fqn'],meta,[],None,
                                                self.standard_type,'static' in self.method_modifiers(mid))[:2]
        # Mutable Java references are contexts by identity, not their rendered
        # fields. Rendering also fails for cyclic arguments and conflates nodes.
        def context_value(value):
            if isinstance(value, (dict, list, tuple)):
                return ('reference', id(getattr(value, 'java_identity', value)))
            return (type(value).__name__, value)
        signature = (mid, context_value(receiver), tuple(context_value(value) for value in args),fingerprint(args),type_context[1],tuple(sorted(type_context[0].items())),tuple(argument_kinds) if argument_kinds is not None else None)
        if signature in self.active or self.calls >= 12000 or len(self.active) >= 64:
            self.last_invoke_started=True
            self.executed(mid,reason)
            self.warnings.add('recursion or context budget: conservative closure used')
            self.fallback(mid)
            return U
        node = self.p.ast.get(mid)
        if node is None:
            self.last_invoke_started=True
            self.executed(mid,reason)
            self.warnings.add('no source body: ' + mid)
            self.fallback(mid)
            return U
        self.calls += 1
        self.active.add(signature)
        previous = self.method
        previous_types = self.variable_types
        previous_bindings,previous_receiver=self.source_bindings,self.receiver_type
        previous_return_kind=self.current_return_kind
        previous_return_type=self.return_type_override
        self.current_return_kind=NO_KIND
        self.return_type_override=None
        self.method = mid
        self.source_bindings,self.receiver_type=type_context
        self.variable_types = dict(self.p.parameters(mid))
        env=JavaFrame()
        env['this'] = receiver if isinstance(receiver, dict) else {}
        body = node.child_by_field_name('body')
        from . import persistence
        proxy_boundary = previous is None or self.p.methods[previous]['owner'] != meta['owner']
        annotations = [*meta.get('annotations', []), *self.p.nodes[meta['owner']].get('annotations', [])]
        started_transaction = persistence.begin(self,mid,annotations) if transactional and proxy_boundary else False
        data_start, failed = len(self.data_operations), True
        failure_value = U
        return_kind=NO_KIND
        started=False
        try:
            try:
                for index,(name,written) in enumerate(self.p.parameters(mid)):
                    value=args[index] if index<len(args) else U
                    # Missing caller metadata denotes a typed entry binding;
                    # an explicit unknown must not be replaced by a guess.
                    kind=(self.declared_kind(declaration_erasure(self,written)) if argument_kinds is None else
                          argument_kinds[index] if index<len(argument_kinds) else None)
                    value,kind=self.assignment_value(value,kind,written,None)
                    env.set_value(name,value,kind)
                from .event_values import witness
                self.executed(mid,reason,witness([env.get(name,U) for name,_ in self.p.parameters(mid)]));started=True
                pending_initializer=getattr(receiver,'_pending_initializer',None)
                if meta['name']=='<init>' and pending_initializer:
                    receiver._pending_initializer=None
                    self.initialize_instance(pending_initializer,receiver,reason)
                result, control = self.execute(body, env)
            except (TypeError, ValueError, IndexError, KeyError, AttributeError, ZeroDivisionError) as exc:
                self.approximate = True
                self.warnings.add('unsupported value operation in ' + mid + ': ' + type(exc).__name__)
                self.fallback(mid)
                result, control = U, None
            failed = control == 'throw'
            return_kind=self.current_return_kind if control=='return' else None
            failure_value = result if failed else None
        except JavaThrow as failure:
            failure_value = failure.value
            raise
        finally:
            try:
                if started_transaction:persistence.end(self,mid,failure_value if failed else None)
                elif transactional and proxy_boundary:persistence.nested_failure(self,mid,failure_value if failed else None)
            finally:
                self.method = previous
                self.variable_types = previous_types
                self.source_bindings,self.receiver_type=previous_bindings,previous_receiver
                self.current_return_kind=previous_return_kind
                self.return_type_override=previous_return_type
                self.last_invoke_kind=return_kind
                self.last_invoke_started=started
                self.active.remove(signature)
        if control == 'throw':
            raise JavaThrow(result)
        return result

    def fallback(self, mid):
        self.approximate = True
        self.assume('unsupported execution at ' + mid)
        cache=self.p.__dict__.setdefault('_fallback_closure_cache',{})
        if mid not in cache:cache[mid]=self.p.ix.closure({mid})
        methods, calls, remote, data = cache[mid]
        from .resource_effects import possible_writes
        writable=possible_writes(self.p,methods,data,bool(self.state.transactions))
        for method in methods:
            self.candidate_edges.add(('', 'executes', method))
        for relation, pairs in [('calls', calls), ('remote', remote), ('data', data)]:
            for source, target in pairs:
                self.candidate_edges.add((source, relation, target))
                if relation == 'data' and target in writable:
                    rows = self.state.database.rows(self.p.nodes[target])
                    if rows is not None:
                        self.state.database.invalidate(rows)

    def execution_fork(self,state):
        # Method execution never mutates completed request observations. Share
        # their payloads, but own the journal list and all mutable execution data.
        return deepcopy(state,{id(state.history):list(state.history)})

    def fork_join(self, choices, env, values, operation):
        """Fork all reachable inputs jointly, then join mutually exclusive effects."""
        from .paths import join_states
        before, uncertainty = self.state, self.uncertain
        assumptions = list(self.execution_assumptions)
        branch_assumptions = []
        before_return_kind,before_reference_kind=self.current_return_kind,self.last_reference_kind
        return_kinds,reference_kinds=[],[]
        original = {'env': env, 'values': values, 'browser': before.browser,
                    'actor_browsers':before.actor_browsers,'beans':before.bean_instances,
                    'history': before.history, 'params': self.params, 'opaque_heap': self.opaque_heap,
                    'managed': {unit: frame['managed'] for unit, frame in before.transactions.items()}}
        alternatives, states, results, controls = [], [], [], []
        diagnostic_names=('events','request_events','http_responses','effect_events','persistence_events','data_operations','semantic_callbacks')
        prefix={name:len(getattr(self,name)) for name in diagnostic_names}
        segments=[]
        try:
            for choice in choices:
                start={name:len(getattr(self,name)) for name in diagnostic_names}
                inputs = {key: value for key, value in original.items() if key != 'history'}
                (state, owned), copies = clone_execution(before,inputs)
                owned['history'] = state.history
                self.state = state
                self.state.browser, self.state.history = owned['browser'], owned['history']
                self.params = owned['params']
                self.opaque_heap = owned['opaque_heap']
                self.uncertain = uncertainty
                self.execution_assumptions = list(assumptions)
                self.current_return_kind,self.last_reference_kind=before_return_kind,before_reference_kind
                try:
                    with self.event_guard(self.method + ':alternative', choice, True):
                        value, control = operation(choice, owned['env'], owned['values'])
                except JavaThrow as failure:
                    value, control = failure.value, 'throw'
                branch_assumptions.extend(self.execution_assumptions)
                return_kinds.append(self.current_return_kind)
                reference_kinds.append(self.last_reference_kind)
                alternatives.append((owned, copies))
                states.append(self.state)
                results.append(value)
                controls.append(control)
                segments.append({name:getattr(self,name)[start[name]:] for name in diagnostic_names})
        finally:
            self.state = before
            self.params = original['params']
            self.opaque_heap = original['opaque_heap']
            self.uncertain = uncertainty
            self.execution_assumptions = list(dict.fromkeys(branch_assumptions or assumptions))
        if len(set(controls))>1:
            self.branch_index+=1
            key=str(self.branch_index)+':'+self.method+':completion'
            if key not in self.decisions:
                if self.path_replay:
                    if not self.allow_completion_splits:raise AnalysisBoundary('mixed completion requires another isolated continuation: '+self.method)
                    raise CompletionRequired(key,list(dict.fromkeys(controls)))
                self.assume('mixed completion modes require path replay: '+self.method)
            else:
                selected=[i for i,control in enumerate(controls) if control==self.decisions[key]]
                alternatives=[alternatives[i] for i in selected]
                states=[states[i] for i in selected]
                results=[results[i] for i in selected]
                controls=[controls[i] for i in selected]
                return_kinds=[return_kinds[i] for i in selected]
                reference_kinds=[reference_kinds[i] for i in selected]
                for name in diagnostic_names:
                    getattr(self,name)[prefix[name]:]=[event for i in selected for event in segments[i][name]]
                self.edges={tuple(event['edge']) for event in self.events}
                self.evidence=defaultdict(set)
                for event in self.events:self.evidence[tuple(event['edge'])].add(event['callsite'])
        left, left_copies = alternatives[0]
        if len(alternatives)==1:
            self.state,results[0]=adopt_execution(states[0],original,left,left_copies,results[0])
        else:
            for right, right_copies in alternatives[1:]:
                join_environment(original, left, right, left_copies, right_copies, merge)
                left, left_copies = clone_environment(original)
            self.state = join_states(states)
        self.state.browser, self.state.history = original['browser'], original['history']
        self.state.actor_browsers,self.state.bean_instances=original['actor_browsers'],original['beans']
        for unit, managed in original['managed'].items():
            if unit in self.state.transactions:self.state.transactions[unit]['managed'] = managed
        self.params = original['params']
        self.opaque_heap = original['opaque_heap']
        joined_env = original['env']
        env.clear()
        if isinstance(env,JavaFrame) and isinstance(joined_env,JavaFrame):
            for name,value in joined_env.items():env.set_value(name,value,joined_env.kinds.get(name))
        else:env.update(joined_env)
        self.current_return_kind=return_kinds[0] if all(kind==return_kinds[0] for kind in return_kinds) else None
        self.last_reference_kind=reference_kinds[0] if all(kind==reference_kinds[0] for kind in reference_kinds) else None
        value = results[0]
        for result in results[1:]:value = merge(value, result)
        if all(control == controls[0] for control in controls):
            return value, controls[0]
        self.approximate = True
        self.warnings.add('alternative completion modes retained: ' + repr(controls))
        return U, None

    @contextmanager
    def binding_scope(self,env,names):
        saved={name:(name in env,env.get(name),self.variable_types.get(name),getattr(env,'kinds',{}).get(name)) for name in names}
        try:yield
        finally:
            for name,(present,value,typ,kind) in saved.items():
                if present:
                    if isinstance(env,JavaFrame):env.set_value(name,value,kind)
                    else:env[name]=value
                else:env.pop(name,None)
                if typ is None:self.variable_types.pop(name,None)
                else:self.variable_types[name]=typ

    def unbox(self,value,node):
        if value is None and any(self.standard_type(self.source_type(node),'java.lang.'+name)
                                 for name in ('Integer','Long','Short','Byte','Float','Double','Character','Boolean')):
            raise JavaThrow({'__type__':'NullPointerException'})
        if value is None:
            self.approximate=True
            self.warnings.add('null scalar conversion requires an unresolved source type: '+self.method)
        return value

    def primitive_value(self,value,typ):
        if value is None and typ in ('int','long','short','byte','float','double','char','boolean'):
            raise JavaThrow({'__type__':'NullPointerException'})
        return value

    def remember_reference_kind(self,kind):
        if self.value_frames:self.value_frames[-1]['kind']=kind

    def source_reference_kind(self,node,observed=NO_KIND):
        written=compiled_type(self,node)
        if written in PRIMITIVES:return self.declared_kind(written)
        if observed is not NO_KIND:return observed
        kind=self.native_scalar_type(written)
        return {'boolean':'Boolean','byte':'Byte','short':'Short','char':'Character','int':'Integer',
                'long':'Long','float':'Float','double':'Double'}.get(kind,kind if kind in
                ('String','Boolean','Byte','Short','Character','Integer','Long','Float','Double') else None)

    def declared_kind(self,written,meta=None):
        native=(written if written in PRIMITIVES else next((name for name in ('String','Boolean','Byte','Short','Character','Integer','Long','Float','Double')
                if self.standard_type(written,'java.lang.'+name,meta)),''))
        return {'boolean':'Boolean','byte':'Byte','short':'Short','char':'Character','int':'Integer',
                'long':'Long','float':'Float','double':'Double'}.get(native,native or None)

    def reference_check(self,value,actual,wanted,reason,issue='unresolved_native_cast',operation='cast'):
        if value is None:return value
        wanted=declaration_erasure(self,wanted)
        if self.standard_type(wanted,'java.lang.Object'):return value
        from .reference_types import collection_compatibility
        compatibility=collection_compatibility(self,value,wanted)
        if compatibility is True:return value
        if compatibility is False:raise JavaThrow({'__type__':'ClassCastException'})
        if isinstance(value,JavaArray):
            if wanted==value.component+'[]':return value
            if wanted.endswith('[]'):
                target=wanted[:-2];component=value.component
                if component not in PRIMITIVES and self.standard_type(target,'java.lang.Object'):return value
                if component not in PRIMITIVES and self.standard_type(target,'java.lang.Number') and self.declared_kind(component) in ('Byte','Short','Integer','Long','Float','Double'):return value
                meta=self.p.methods[self.method]
                if component in PRIMITIVES or target in PRIMITIVES or self.native_scalar_type(component) and self.native_scalar_type(target):
                    raise JavaThrow({'__type__':'ClassCastException'})
                if self.p.resolve_type(component,meta['module'],meta['file']) and self.p.resolve_type(target,meta['module'],meta['file']):
                    if self.record_proves_type(JavaRecord(component,{},()),target):return value
                    raise JavaThrow({'__type__':'ClassCastException'})
            if any(self.standard_type(wanted,t) for t in ('java.lang.Cloneable','java.io.Serializable')):return value
            if any(self.standard_type(wanted,'java.util.'+name) for name in ('List','Collection','Map')):
                raise JavaThrow({'__type__':'ClassCastException'})
        elif wanted.endswith('[]') and isinstance(value,(JavaList,JavaMap,JavaObject)):
            raise JavaThrow({'__type__':'ClassCastException'})
        scalar=self.native_scalar_type(wanted)
        natives=('String','Boolean','Byte','Short','Character','Integer','Long','Float','Double')
        meta=self.p.methods[self.method]
        target_owner=self.p.resolve_type(wanted,meta['module'],meta['file'])
        if isinstance(value,JavaEnumValue):
            if target_owner==value.enum_owner:return value
            if target_owner:raise JavaThrow({'__type__':'ClassCastException'})
        if scalar in natives:
            if actual==scalar:return value
            if actual in natives and value is not U or isinstance(value,(JavaObject,JavaMap,JavaList,JavaMapView,JavaMapEntry,JavaMapIterator,JavaJsonMapper,JacksonFeature,JavaEnumValue)):
                raise JavaThrow({'__type__':'ClassCastException'})
        elif actual in natives and any(self.standard_type(wanted,name) for name in ('java.lang.Number','java.io.Serializable','java.lang.Comparable')):
            if not self.standard_type(wanted,'java.lang.Number') or actual in ('Byte','Short','Integer','Long','Float','Double'):return value
            if value is not U:raise JavaThrow({'__type__':'ClassCastException'})
        elif isinstance(value,JavaList) and value.flavor=='HashSet' and any(self.standard_type(wanted,'java.util.'+name) for name in ('Set','HashSet','Collection')):return value
        elif isinstance(value,JavaList) and value.flavor=='HashSet' and self.standard_type(wanted,'java.util.List'):raise JavaThrow({'__type__':'ClassCastException'})
        elif isinstance(value,JavaList) and not isinstance(value,JavaArray) and (any(self.standard_type(wanted,'java.util.'+name) for name in ('List','Collection')) or self.standard_type(wanted,'java.lang.Iterable')):
            return value
        elif isinstance(value,JavaMap) and self.standard_type(wanted,'java.util.Map'):return value
        elif isinstance(value,JavaMap) and value.flavor in ('HashMap','LinkedHashMap') and any(self.standard_type(wanted,'java.util.'+name) for name in ('HashMap','AbstractMap')):return value
        elif isinstance(value,JavaMap) and self.standard_type(wanted,'java.util.LinkedHashMap'):
            if value.flavor=='LinkedHashMap':return value
            if value.flavor=='HashMap':raise JavaThrow({'__type__':'ClassCastException'})
        elif isinstance(value,JavaList) and value.flavor in ('ArrayList','LinkedList') and self.standard_type(wanted,'java.util.'+value.flavor):return value
        elif isinstance(value,JavaMapEntry) and (self.standard_type(wanted,'java.util.Map.Entry') or wanted=='Map.Entry' and self.standard_type('Map','java.util.Map')):return value
        elif isinstance(value,JavaList) and self.standard_type(wanted,'java.io.Serializable'):return value
        elif isinstance(value,(JavaList,JavaMap)) and any(self.standard_type(wanted,name) for name in ('java.lang.Cloneable','java.io.Serializable')):
            if value.flavor in ('ArrayList','LinkedList','HashMap','LinkedHashMap'):return value
            if isinstance(value,JavaList) and value.flavor=='Arrays.ArrayList' and self.standard_type(wanted,'java.lang.Cloneable'):
                raise JavaThrow({'__type__':'ClassCastException'})
        elif self.record_proves_type(value,wanted):return value
        if isinstance(value,JavaList) and any(self.standard_type(wanted,'java.util.'+name) for name in ('Map','HashMap','LinkedHashMap')):
            raise JavaThrow({'__type__':'ClassCastException'})
        if isinstance(value,JavaMap) and any(self.standard_type(wanted,'java.util.'+name) for name in ('List','ArrayList','LinkedList')):
            raise JavaThrow({'__type__':'ClassCastException'})
        meta=self.p.methods[self.method]
        if actual in natives and value is not U and self.p.resolve_type(wanted,meta['module'],meta['file']):raise JavaThrow({'__type__':'ClassCastException'})
        if target_owner and isinstance(value,(JavaObject,JavaMap,JavaList,JavaMapView,JavaMapEntry,JavaMapIterator,JavaJsonMapper,JacksonFeature,JavaTypeToken,JavaTypeFactory,JavaListIterator)):
            raise JavaThrow({'__type__':'ClassCastException'})
        self.approximate=True
        self.warnings.add('implicit reference cast context or runtime kind is unresolved: '+reason+' -> '+(wanted or '<unresolved consumer>'))
        self.operation_issues[(issue,operation)]+=1
        return U

    def native_read_cast(self,value,actual,node,reason):
        self.remember_reference_kind(actual)
        if value is None:return value
        expected=consumer_type(self,node)
        if expected in PRIMITIVES:expected=compiled_type(self,node)
        return self.reference_check(value,actual,expected,reason,'unresolved_collection_cast','read')

    def assignment_value(self,value,kind,written,node,source_override=None):
        wanted=declaration_erasure(self,written)
        if value is U:return value,kind
        if wanted in PRIMITIVES:
            if value is None:raise JavaThrow({'__type__':'NullPointerException'})
            source=source_override if source_override is not None else compiled_type(self,node) if node is not None else wanted
            if not source and kind:source='java.lang.'+kind
            if source=='float' or self.native_scalar_type(source)=='Float' or wanted=='float':
                self.approximate=True
                self.warnings.add('float scalar promotion or rounding is not modeled: '+written)
                return U,None
            if source not in PRIMITIVES:
                scalar=self.native_scalar_type(source)
                if scalar:
                    value=self.reference_check(value,kind,source,text(node))
                    if value is U:return U,None
                else:
                    self.approximate=True
                    self.warnings.add('primitive binding has an unresolved unboxing source: '+written)
                    return U,None
            if is_symbolic(value) and value.get('__type__') in (wanted,self.declared_kind(wanted),'java.lang.'+self.declared_kind(wanted)):
                return value,self.declared_kind(wanted)
            if wanted=='boolean' and type(value) is bool:return value,'Boolean'
            if wanted=='char' and isinstance(value,str) and len(value)==1:return value,'Character'
            if isinstance(value,str) and len(value)==1 and self.native_scalar_type(source) in ('char','Character'):value=ord(value)
            if wanted=='double' and type(value) in (int,float):return float(value),'Double'
            if wanted in ('byte','short','int','long') and type(value) is int:
                bits={'byte':8,'short':16,'int':32,'long':64}[wanted]
                if -(1<<(bits-1))<=value<(1<<(bits-1)):return value,self.declared_kind(wanted)
            self.approximate=True
            self.warnings.add('primitive assignment conversion is not modeled: '+written)
            return U,None
        if self.native_scalar_type(wanted) or any(self.standard_type(wanted,t) for t in ('java.lang.Number','java.io.Serializable','java.lang.Comparable')):
            value=self.reference_check(value,kind,wanted,text(node) if node is not None else written)
        return value,kind

    def record_proves_type(self,value,written):
        if not isinstance(value,JavaRecord) or '<' in written:return False
        meta=self.p.methods[self.method]
        target=self.p.resolve_type(written,meta['module'],meta['file'])
        owner=self.p.resolve_type(value.declared_type,meta['module'],meta['file'])
        pending,seen=[owner],set()
        while pending:
            current=pending.pop()
            if current is None or current in seen:continue
            if current==target:return True
            context=self.p.nodes[current]
            for parent in self.p.generic_parents.get(current,()):
                base,_=type_parts(parent)
                if self.standard_type(base,written,context):return True
            seen.add(current);pending.extend(self.p.type_parents.get(current,[]))
        return False

    def generic_field(self,info):
        return bool(set(re.findall(r'(?<![\w.])[\w$]+',info['type'])) & self.p.type_variables.get(info['declaring_type'],{}).keys())

    def source_qualifier_type(self,node):
        qualifier=node.child_by_field_name('object')
        return self.source_type(qualifier) if qualifier is not None else self.receiver_type

    def mark_raw_record(self,obj,owner):
        if isinstance(obj,JavaRecord):
            names={name for name,info in self.p.type_fields.get(owner,{}).items() if self.generic_field(info)}
            obj._unchecked_generic_fields=set(getattr(obj,'_unchecked_generic_fields',()))|names

    def field_read(self,node,obj,name,info=None):
        if isinstance(obj,JavaEnumValue) and info:
            self.remember_reference_kind(self.declared_kind(info['type'],self.p.nodes[info['declaring_type']]))
        if isinstance(obj,JavaRecord):
            if self.field_slot(node,obj,name)[1]=='unresolved':return U
            kinds=getattr(obj,'_native_field_kinds',{})
            kind=kinds.get(name)
            if name in kinds or info and self.generic_field(info):self.remember_reference_kind(kind)
            if info and self.generic_field(info):
                projected=compiled_type(self,node)
                erased=declaration_erasure(self,info['type'],owner=info['declaring_type'])
                if projected and declaration_erasure(self,projected)!=erased:
                    return self.native_read_cast(member(obj,name),kind,node,text(node))
        return member(obj,name)

    def generic_binding(self,value,written,provided):
        base,args=type_parts(written)
        if value is None or value is U or not args:return value
        _,source_args=type_parts(provided)
        if source_args is None or source_args:return value
        meta=self.p.methods[self.method]
        target=self.p.resolve_type(base,meta['module'],meta['file'])
        scope=member_scope(self.p,provided,target,meta) if target else None
        if scope is not None and scope[1]:self.mark_raw_record(value,target)
        return value

    def lvalue(self,node,env):
        """Capture storage once; simple assignment checks it after the RHS."""
        while node.type=='parenthesized_expression':
            node=next(c for c in node.named_children if c.type not in ('line_comment','block_comment'))
        if node.type=='identifier':
            name=text(node)
            if name in env:return node,'local',env,name
            owner = self.initializer_context[0] if self.initializer_context and self.method == self.initializer_context[1] else self.p.methods[self.method]['owner']
            if name in self.p.type_fields.get(owner,{}):
                return self.field_slot(node,env.get('this',U),name)
        if node.type=='field_access':
            qualifier=node.child_by_field_name('object');name=text(node.child_by_field_name('field'))
            obj=self.value(qualifier,env)
            meta=self.p.methods[self.method]
            owner=self.p.resolve_type(self.source_type(qualifier),meta['module'],meta['file'])
            if name in self.p.type_fields.get(owner,{}):return self.field_slot(node,obj,name)
            # Static storage and unresolved field declarations are not instance
            # slots, even when their qualifier happens to have a dictionary value.
            self.approximate=True
            self.warnings.add('unsupported static or unresolved Java field write: '+text(node))
            return node,'unresolved',obj,name
        if node.type=='array_access':
            obj=self.value(node.child_by_field_name('array'),env)
            index_node=node.child_by_field_name('index')
            index=self.unbox(self.value(index_node,env),index_node)
            return node,'array',obj,index
        self.approximate=True
        self.warnings.add('unsupported Java writable operand: '+text(node))
        return node,'unresolved',U,None

    def field_slot(self,node,obj,name):
        if isinstance(obj,dict):
            meta=self.p.methods[self.method]
            owner=self.p.resolve_type(getattr(obj,'declared_type',obj.get('__type__','')),meta['module'],meta['file'])
            cache=self.p.__dict__.setdefault('_hidden_field_cache',{})
            if (owner,name) not in cache:
                pending,seen,declaring=[owner],set(),set()
                while pending:
                    current=pending.pop()
                    if current is None or current in seen:continue
                    seen.add(current)
                    info=self.p.type_fields.get(current,{}).get(name)
                    if info:declaring.add(info.get('declaring_type',current))
                    pending.extend(self.p.type_parents.get(current,[]))
                cache[owner,name]=len(declaring)>1
            if cache[owner,name]:
                self.approximate=True
                self.warnings.add('hidden Java fields require separate declaring-class storage: '+text(node))
                return node,'unresolved',obj,name
        return node,'field',obj,name

    def lvalue_valid(self,slot):
        node,kind,obj,key=slot
        if kind in ('field','array') and obj is None:raise JavaThrow({'__type__':'NullPointerException'})
        if kind=='array' and isinstance(obj,list) and type(key) is int:
            if not 0<=key<len(obj):raise JavaThrow({'__type__':'ArrayIndexOutOfBoundsException'})
            if self.source_type(node.child_by_field_name('array')).endswith('[]'):return True
        if kind in ('field','local') and isinstance(obj,dict):return True
        self.approximate=True
        self.warnings.add('unresolved Java writable location: '+text(node))
        return False

    def lvalue_read(self,slot):
        if not self.lvalue_valid(slot):return U
        _,kind,obj,key=slot
        if kind=='array' and len(obj)>1 and not getattr(obj,'order_known',True):
            self.approximate=True;self.warnings.add('array encounter order is unspecified: '+text(slot[0]));return U
        return obj[key] if kind=='array' else obj.get(key,U)

    def lvalue_write(self,slot,value,reference_kind=None,reference_type=''):
        node,kind,obj,key=slot
        if not self.lvalue_valid(slot):
            if kind=='array' and isinstance(obj,list):
                # An unknown index may select any component. Keep only values
                # that agree with the possible write, without inventing an index.
                for index,old in enumerate(obj):obj[index]=merge(old,value)
            elif kind=='unresolved' and isinstance(obj,dict) and key is not None:obj[key]=U
            return
        if kind=='array' and self.source_type(node) not in ('byte','short','char','int','long','float','double','boolean') and value is not None:
            if isinstance(obj,JavaArray):
                try:value=self.reference_check(value,reference_kind,obj.component,text(node))
                except JavaThrow as failure:
                    if exception_type(failure.value)==native_type('ClassCastException'):
                        raise JavaThrow({'__type__':'ArrayStoreException'}) from None
                    raise
            else:
                self.approximate=True
                self.warnings.add('reference array store runtime component type is not modeled: '+text(node))
                value=U
        if kind=='array' and len(obj)>1 and not getattr(obj,'order_known',True):
            self.approximate=True;self.warnings.add('array store position has unspecified prior order: '+text(node))
            for index in range(len(obj)):obj.set_value(index,U,None)
            obj.opaque=True
            return
        if kind=='field' and isinstance(obj,JavaRecord):
            receiver=self.source_qualifier_type(node)
            meta=self.p.methods[self.method]
            owner=self.p.resolve_type(receiver,meta['module'],meta['file'])
            info=self.p.type_fields.get(owner,{}).get(key)
            if info:
                obj._native_field_kinds={**getattr(obj,'_native_field_kinds',{}),key:reference_kind}
                obj._field_reference_types={**getattr(obj,'_field_reference_types',{}),key:reference_type}
                scope=member_scope(self.p,receiver,info['declaring_type'],meta)
                if scope is None or scope[1]:self.mark_raw_record(obj,owner)
        if kind=='array' and isinstance(obj,JavaArray):obj.set_value(key,value,reference_kind)
        else:obj[key]=value
        if kind=='local' and isinstance(obj,JavaFrame):obj.kinds[key]=reference_kind

    def increment_value(self,old,node,delta):
        old=self.primitive_value(self.unbox(old,node),self.source_type(node))
        typ=self.native_scalar_type(self.source_type(node))
        typ={'Integer':'int','Long':'long','Byte':'byte','Short':'short','Character':'char','Float':'float','Double':'double'}.get(typ,typ)
        if typ=='char' and isinstance(old,str) and len(old)==1 and ord(old)<=65535:
            return chr((ord(old)+delta)%65536)
        if typ in ('byte','short','int','long') and type(old) is int:
            return self.narrow_integer(old+delta,typ)
        if typ=='double' and type(old) in (int,float):return float(old)+delta
        self.approximate=True
        self.warnings.add(('float rounding is not modeled for Java update: ' if typ=='float' else
                           'unresolved numeric operand for Java update: ')+text(node))
        return U

    def compound_value(self,old,value,lhs,rhs,op):
        left_type=self.native_scalar_type(self.source_type(lhs))
        right_type=self.native_scalar_type(self.source_type(rhs))
        aliases={'Integer':'int','Long':'long','Byte':'byte','Short':'short','Character':'char','Float':'float','Double':'double'}
        lt,rt=aliases.get(left_type,left_type),aliases.get(right_type,right_type)
        try:
            if op not in ('+=','-='):raise TypeError
            operation=operator.add if op=='+=' else operator.sub
            if left_type=='String' and op=='+=' and isinstance(old,str) and isinstance(value,str):return concat_text(old,value)
            if 'float' in (lt,rt):
                self.warnings.add('float rounding is not modeled for Java compound assignment: '+text(lhs))
                raise TypeError
            if lt=='char' and isinstance(old,str) and len(old)==1 and ord(old)<=65535:old=ord(old)
            if rt=='char' and isinstance(value,str) and len(value)==1 and ord(value)<=65535:value=ord(value)
            if lt=='double' and rt in ('byte','short','char','int','long','double') and type(old) in (int,float) and type(value) in (int,float):
                return operation(float(old),float(value))
            if lt in ('byte','short','char','int','long') and rt in ('byte','short','char','int','long') and type(old) is int and type(value) is int:
                result=operation(old,value)
                return chr(result%65536) if lt=='char' else self.narrow_integer(result,lt)
        except TypeError:pass
        self.approximate=True
        self.warnings.add('unsupported Java compound assignment conversion or operator: '+text(lhs))
        return U

    def binary_unboxes(self,node,side):
        op=text(node.child_by_field_name('operator'))
        if op in ('==','!='):
            other=node.child_by_field_name('right' if side=='left' else 'left')
            return self.source_type(other) in ('int','long','short','byte','float','double','char','boolean')
        if op=='+':
            return not any(self.standard_type(self.source_type(node.child_by_field_name(key)),'java.lang.String')
                           for key in ('left','right'))
        return op in ('-','*','/','%','<','>','<=','>=','&','|','^','<<','>>','>>>','&&','||')

    def execute(self, node, env):
        if node is None:
            return U, None
        typ = node.type
        if typ in ('block', 'constructor_body'):
            names=[text(var.child_by_field_name('name')) for child in node.named_children
                   if child.type=='local_variable_declaration' for var in child.named_children if var.type=='variable_declarator']
            with self.binding_scope(env,names):
                for child in node.named_children:
                    value, control = self.execute(child, env)
                    if control:
                        return value, control
            return U, None
        if typ in ('return_statement', 'throw_statement'):
            value = self.value(node.named_children[0], env) if node.named_children else None
            if typ=='return_statement':
                returned=self.return_type_override or self.p.methods[self.method].get('return_raw','')
                kind=self.source_reference_kind(node.named_children[0],self.last_reference_kind) if node.named_children else None
                value,self.current_return_kind=self.assignment_value(value,kind,returned,node.named_children[0] if node.named_children else None)
            if typ=='throw_statement' and value is None:value={'__type__':'NullPointerException'}
            return value, 'return' if typ == 'return_statement' else 'throw'
        if typ in ('switch_expression','switch_statement'):
            result,control = self.execute_switch(node,env)
            return (U,None) if control=='yield' else (result,control)
        if typ=='yield_statement':
            return self.value(node.named_children[0],env),'yield'
        if typ == 'if_statement':
            condition=node.child_by_field_name('condition')
            cond = self.unbox(self.value(condition, env),condition)
            self.conditions.append({'method': self.method, 'line': node.start_point.row + 1,
                                    'condition': text(node.child_by_field_name('condition')),
                                    'value': cond if isinstance(cond, bool) else 'unknown'})
            if isinstance(cond, bool):
                with self.event_guard(text(condition), cond):
                    return self.execute(node.child_by_field_name('consequence' if cond else 'alternative'), env)
            decision = self.choose(self.method + ':' + str(node.start_point.row + 1), [True, False])
            if decision is not None:
                if self.use_constraints:
                    refined = assume(node.child_by_field_name('condition'), env, decision,
                                     self.variable_types, self.constraint_symbol)
                    self.conditions[-1]['refined'] = refined
                with self.event_guard(text(condition), decision, True):
                    return self.execute(node.child_by_field_name('consequence' if decision else 'alternative'), env)
            return self.fork_join(['consequence', 'alternative'], env, [],
                lambda branch, owned, _: self.execute(node.child_by_field_name(branch), owned))
        if typ == 'enhanced_for_statement':
            source=node.child_by_field_name('value')
            values = self.value(source, env)
            from .persistence import load_collection
            values=load_collection(self,values,self.method+':'+str(node.start_point.row+1))
            if values is None:raise JavaThrow({'__type__':'NullPointerException'})
            if (values is U or self.opaque(values) or isinstance(values,JavaList) and values.opaque or
                    isinstance(values,JavaMapView) and not isinstance(values.backing.mapping,dict) or
                    not isinstance(values,(list,JavaMapView))):
                # No body execution is established. In particular, an opaque
                # empty carrier cannot prove zero iterations or zero writes.
                affected=list(owned_objects(env))
                for value in affected:widen(value)
                reason=self.method+':'+str(node.start_point.row+1)
                self.effect_events.append({'model_version':'unknown-foreach-boundary/1',
                    'operation':'foreach','callsite':reason,'heap_roots':sorted(env),
                    'affected_native_objects':len(affected),'global_footprint':'reachable native heap',
                    'callbacks':'not executed; membership unknown','completions':'unresolved'})
                raise AnalysisBoundary('iteration over unknown collection membership: '+reason,
                                       category='unsupported_semantics')
            name = text(node.child_by_field_name('name'))
            from .map_loop_proof import prove as map_noop
            if map_noop(self,node,values,env):return U,None
            if self.commuting_map_copy(node,values,env):return U,None
            from .map_filter_proof import certify as map_filter
            commuting_filter=map_filter(self,node,values,env)
            certain=isinstance(values,list) or isinstance(values,JavaMapView) and isinstance(values.backing.mapping,dict)
            native_iteration=isinstance(values,JavaList) and (not isinstance(values,JavaArray) or not values.order_known)
            reason=self.method+':'+str(node.start_point.row+1)
            items = ([(JavaMapEntry(values.backing,entry),None) for entry in values.backing.entries()] if commuting_filter else
                     self.view_items(values,env,reason) if isinstance(values,JavaMapView) else
                     native_list_iteration(self,values,reason) if native_iteration else values if isinstance(values,list) else [U])
            if isinstance(items,list) and len(items) > 64:
                self.approximate = True
                self.warnings.add('loop collection widened after 64 elements')
                items = items[:64] + [U]
            with self.binding_scope(env,[name]):
                written=text(node.child_by_field_name('type'))
                collection_type=compiled_type(self,source)
                element=collection_type[:-2] if collection_type.endswith('[]') else self.stream_element_type(source)
                if written=='var' and not self.p.resolve_type('var',self.p.methods[self.method]['module'],self.p.methods[self.method]['file']):
                    written=element
                self.variable_types[name]=written
                for index,item in enumerate(items):
                    if isinstance(values,JavaMapView) or native_iteration:item,actual=item
                    else:actual=items.kinds[index] if isinstance(items,JavaList) else self.declared_kind(element) if collection_type.endswith('[]') and element in PRIMITIVES else None
                    # Iteration unboxes the declared element before primitive
                    # widening, while an Object loop variable needs no cast.
                    expected=element if written in PRIMITIVES else declaration_erasure(self,written)
                    if expected in PRIMITIVES:expected='java.lang.'+self.declared_kind(expected)
                    item=self.reference_check(item,actual,expected,text(node),'unresolved_collection_cast','iteration')
                    item,actual=self.assignment_value(item,actual,written,None,element if written in PRIMITIVES else None)
                    if isinstance(env,JavaFrame):env.set_value(name,item,actual)
                    else:env[name]=item
                    result, control = self.execute(node.child_by_field_name('body'), env)
                    if control in ('return', 'throw') and certain:
                        return result, control
                    if control == 'break': break
            return U, None
        if typ in ('for_statement', 'while_statement', 'do_statement'):
            init = node.child_by_field_name('init')
            names=[text(var.child_by_field_name('name')) for var in init.named_children if var.type=='variable_declarator'] if init is not None and init.type=='local_variable_declaration' else []
            with self.binding_scope(env,names):
                if init: self.execute(init, env)
                condnode = node.child_by_field_name('condition')
                for iteration in range(64):
                    cond = True if typ == 'do_statement' and iteration == 0 else self.unbox(self.value(condnode, env),condnode) if condnode else True
                    if cond is False: break
                    if cond is U:
                        decision = self.choose(self.method + ':loop:' + str(node.start_point.row + 1), [True, False])
                        if decision is False:
                            break
                        if decision is True:
                            cond = True
                        else:
                            def unknown_iteration(entered,owned,_):
                                if not entered:return U,None
                                self.uncertain+=1
                                try:
                                    result,control=self.execute(node.child_by_field_name('body'),owned)
                                finally:self.uncertain-=1
                                return (result,control) if control in ('return','throw') else (U,None)
                            result,control=self.fork_join([False,True],env,[],unknown_iteration)
                            if control in ('return','throw'):return result,control
                            self.assume('unknown loop termination and repetition are bounded at '+self.method+':'+str(node.start_point.row+1))
                            self.fallback(self.method)
                            break
                    result, control = self.execute(node.child_by_field_name('body'), env)
                    if cond is U: self.uncertain -= 1
                    if control in ('return', 'throw') and cond is True: return result, control
                    if control == 'break': break
                    update = node.child_by_field_name('update')
                    if update: self.value(update, env)
                    if cond is not True:
                        self.warnings.add('unknown loop bounded to one pass: ' + self.method)
                        break
                else:
                    self.approximate = True
                    self.warnings.add('loop bounded after 64 passes: ' + self.method)
                    self.fallback(self.method)
                return U, None
        if typ == 'try_statement' or typ == 'try_with_resources_statement':
            resources = node.child_by_field_name('resources')
            if resources:
                self.value(resources, env)
            try:
                result, control = self.execute(node.child_by_field_name('body'), env)
            except JavaThrow as exc:
                result, control = exc.value, 'throw'
            if control == 'throw':
                for child in node.named_children:
                    if child.type == 'catch_clause':
                        parameter = next(c for c in child.named_children if c.type=='catch_formal_parameter')
                        types = next(c for c in parameter.named_children if c.type=='catch_type')
                        thrown = exception_type(result)
                        matches = [assignable(thrown,self.catch_type(text(c)),self.p) for c in types.named_children]
                        match = True if True in matches else U if U in matches else False
                        if match is U:
                            self.approximate = True
                            self.warnings.add('unknown exception assignability: '+text(types)+' at '+self.method)
                            match = self.choose(self.method+':catch:'+str(child.start_point.row+1),[True,False])
                            if match is None:
                                self.fallback(self.method)
                                break
                        if match:
                            name=text(parameter.child_by_field_name('name'))
                            with self.binding_scope(env,[name]):
                                self.variable_types[name]=text(types)
                                env[name] = result
                                try:
                                    result, control = self.execute(child.child_by_field_name('body'), env)
                                except JavaThrow as exc:
                                    result,control = exc.value,'throw'
                            break
            for child in node.named_children:
                if child.type == 'finally_clause':
                    try:
                        final, fc = self.execute(child.named_children[-1], env)
                    except JavaThrow as exc:
                        final,fc = exc.value,'throw'
                    if fc:
                        return final, fc
            return result, control
        if typ == 'local_variable_declaration':
            for child in node.named_children:
                if child.type == 'variable_declarator':
                    name = text(child.child_by_field_name('name'))
                    written=text(node.child_by_field_name('type'))
                    if written=='var' and not self.p.resolve_type('var',self.p.methods[self.method]['module'],self.p.methods[self.method]['file']):
                        written=compiled_type(self,child.child_by_field_name('value'))
                        if not written:
                            self.approximate=True
                            self.warnings.add('unresolved source type for local var initializer: '+self.method)
                    self.variable_types[name]=written
                    initializer=child.child_by_field_name('value')
                    value=self.value(initializer,env)
                    kind=self.source_reference_kind(initializer,self.last_reference_kind)
                    value,kind=self.assignment_value(value,kind,written,initializer)
                    value=self.generic_binding(value,self.declared_type(written),self.source_type(initializer))
                    if isinstance(env,JavaFrame):env.set_value(name,value,kind)
                    else:env[name]=value
            return U, None
        if typ in ('break_statement', 'continue_statement'):
            return U, 'break' if typ == 'break_statement' else 'continue'
        if typ in ('line_comment', 'block_comment'):
            return U, None
        return self.value(node, env), None

    def execute_switch(self,node,env):
        selected = self.value(node.child_by_field_name('condition'),env)
        groups = [g for g in node.child_by_field_name('body').named_children
                  if g.type not in ('line_comment','block_comment')]
        possible,default,unknown,found = [],None,selected is U,False
        for index,group in enumerate(groups):
            label = group.named_children[0]
            if text(label)=='default':
                default = index
                continue
            for case in label.named_children:
                value = self.value(case,env)
                if value is U and isinstance(selected,JavaEnumValue):
                    key = selected.enum_key.rsplit('.',1)[0]+'.'+text(case)
                    value = self.p.enum_objects.get(key,U)
                equal = key_equal(selected,value)
                if equal is True:
                    possible = [index]
                    found = True
                    break
                if equal is U:
                    unknown = True
                    possible.append(index)
            if found:
                unknown = False
                break
        if selected is None and not possible:
            raise JavaThrow({'__type__':'NullPointerException'})
        if unknown:
            choices = sorted(set(possible+[default if default is not None else -1]))
            start = self.choose(self.method+':switch:'+str(node.start_point.row+1),choices)
            if start is None:
                self.warnings.add('unresolved switch control flow: '+self.method)
                self.fallback(self.method)
                return U,None
        else:
            start = possible[0] if possible else default
        if start is None or start == -1:
            return U,None
        for group in groups[start:]:
            result = U
            for statement in group.named_children[1:]:
                result,control = self.execute(statement,env)
                if control == 'break':return U,None
                if control:return result,control
            if group.type=='switch_rule':
                return result,'yield'
        return U,None

    def value(self, node, env):
        self.value_frames.append({})
        self.last_reference_kind=NO_KIND
        try:result=self.expression_value(node,env)
        finally:frame=self.value_frames.pop()
        self.last_reference_kind=frame.get('kind','Boolean' if type(result) is bool else NO_KIND)
        if self.last_reference_kind=='Float' and result is not U and result is not None and not (type(result) is float and result==0.0):
            self.approximate=True
            self.warnings.add('float scalar promotion or rounding is not modeled: '+self.method)
            result=U
        return result

    def expression_value(self, node, env):
        if node is None:
            return U
        typ, raw = node.type, text(node)
        if typ == 'identifier':
            if raw in env:
                if isinstance(env,JavaFrame) and raw in env.kinds:self.remember_reference_kind(env.kinds[raw])
                return env[raw]
            enum_owner=self.p.methods[self.method]['owner']
            if enum_owner in self.p.enum_members:
                enum=self.p.enum_reference(self.p.nodes[enum_owner]['fqn']+'.'+raw,self.method)
                if enum:return deepcopy(self.p.enum_objects[enum])
            from .persistence import load
            load(self,env.get('this'),raw,self.p.methods[self.method]['file']+':'+str(node.start_point.row+1))
            owner=self.initializer_context[0] if self.initializer_context and self.method==self.initializer_context[1] else self.p.methods[self.method]['owner']
            info=self.p.type_fields.get(owner,{}).get(raw)
            return self.field_read(node,env.get('this'),raw,info)
        if typ in ('true', 'false'):
            return typ == 'true'
        if typ == 'null_literal':
            return None
        if typ == 'character_literal':
            content=raw[1:-1]
            if len(content)==1:return content
            if content=="\\'":return "'"
            if content=='\\s':return ' '
            if re.fullmatch(r'\\[0-7]{1,3}',content) and int(content[1:],8)<=255:return chr(int(content[1:],8))
            try:
                decoded=json.loads('"'+content+'"')
                if len(decoded.encode('utf-16-le',errors='surrogatepass'))==2:return decoded
            except ValueError:pass
            self.approximate=True
            self.warnings.add('unsupported Java character literal: '+self.method)
            return U
        if typ == 'string_literal':
            try:
                return json.loads(raw)
            except ValueError:
                return raw[1:-1]
        if typ in ('decimal_integer_literal', 'decimal_floating_point_literal'):
            if typ=='decimal_floating_point_literal' and raw.lower().endswith('f'):
                self.approximate=True
                self.warnings.add('float scalar promotion or literal rounding is not modeled: '+self.method)
                return U
            try:
                return float(raw.rstrip('fFdD')) if '.' in raw else int(raw.rstrip('lL'))
            except ValueError:
                return U
        if typ == 'this':
            return env.get('this', U)
        if typ == 'parenthesized_expression':
            value=self.value(next(c for c in node.named_children if c.type not in ('line_comment','block_comment')), env)
            self.remember_reference_kind(self.last_reference_kind)
            return value
        if typ == 'cast_expression':
            value = self.value(node.named_children[-1], env)
            actual_kind=self.source_reference_kind(node.named_children[-1],self.last_reference_kind)
            if isinstance(value,JsonText):actual_kind='String'
            target = text(node.child_by_field_name('type'))
            value=self.primitive_value(value,target)
            meta=self.p.methods[self.method]
            erased_target=declaration_erasure(self,target)
            if isinstance(value,JavaArray) and target not in PRIMITIVES:
                return self.reference_check(value,actual_kind,erased_target,text(node))
            if target.endswith('[]'):
                return self.reference_check(value,actual_kind,erased_target,text(node))
            if target in PRIMITIVES:
                operand=node.named_children[-1]
                source=compiled_type(self,operand)
                if target=='float' or source=='float' or self.native_scalar_type(source)=='Float':
                    self.approximate=True
                    self.warnings.add('float primitive cast or rounding is not modeled: '+text(node))
                    return U
                if source not in PRIMITIVES:
                    scalar=self.native_scalar_type(source)
                    required=source if scalar else 'java.lang.'+self.declared_kind(target)
                    value=self.reference_check(value,actual_kind,required,text(node))
                if value is U:return U
            if self.has_type_variables(target,meta) or '<' in target:
                # The VM checks the erased class. Type arguments are checked
                # only when later source consumers require a narrower class.
                value=self.reference_check(value,actual_kind,erased_target,text(node),'unresolved_generic_cast','cast')
                self.remember_reference_kind(actual_kind)
                return value
            native=self.native_scalar_type(erased_target)
            if native in ('String','Boolean','Byte','Short','Character','Integer','Long','Float','Double'):
                value=self.reference_check(value,actual_kind,erased_target,text(node))
                self.remember_reference_kind(actual_kind)
                return value
            if self.standard_type(erased_target,'java.lang.Object'):
                self.remember_reference_kind(actual_kind)
                return value
            if self.p.resolve_type(erased_target,meta['module'],meta['file']):
                return self.reference_check(value,actual_kind,erased_target,text(node))
            elif any(self.standard_type(erased_target,name) for name in ('java.lang.Number','java.io.Serializable','java.lang.Comparable')):
                value=self.reference_check(value,actual_kind,erased_target,text(node))
                self.remember_reference_kind(actual_kind)
            if isinstance(value,(JavaJsonMapper,JacksonFeature)):
                allowed=('java.lang.Object','java.io.Serializable')+(
                    ('com.fasterxml.jackson.databind.ObjectMapper','com.fasterxml.jackson.core.ObjectCodec','com.fasterxml.jackson.core.TreeCodec','com.fasterxml.jackson.core.Versioned')
                    if isinstance(value,JavaJsonMapper) else ('com.fasterxml.jackson.databind.DeserializationFeature','java.lang.Enum','java.lang.Comparable'))
                if any(self.standard_type(target,fqn) for fqn in allowed):return value
                meta=self.p.methods[self.method]
                if self.p.resolve_type(target,meta['module'],meta['file']) or target.endswith('[]') or target in ('int','long','short','byte','char','boolean','float','double') or self.standard_type(target,'java.lang.String'):
                    raise JavaThrow({'__type__':'ClassCastException'})
                self.json_issue('JSON codec reference cast is not proven compatible',self.method)
                self.fallback(self.method)
                return U
            if isinstance(value,(JavaMapView,JavaMapEntry,JavaMapIterator)):
                base,_=type_parts(target)
                allowed=['java.lang.Object']
                if isinstance(value,JavaMapView):
                    allowed+=['java.lang.Iterable','java.util.Collection','java.util.AbstractCollection']
                    if value.kind!='values':allowed+=['java.util.Set','java.util.AbstractSet']
                elif isinstance(value,JavaMapEntry):allowed+=['java.util.Map.Entry']
                else:allowed+=['java.util.Iterator']
                if any(self.standard_type(base,fqn) for fqn in allowed) or isinstance(value,JavaMapEntry) and base=='Map.Entry' and self.standard_type('Map','java.util.Map'):
                    return value
                meta=self.p.methods[self.method]
                owner=self.p.resolve_type(base,meta['module'],meta['file'])
                if owner or base in ('int','long','short','byte','char','boolean','float','double') or base.endswith('[]') or self.standard_type(base,'java.lang.String'):
                    raise JavaThrow({'__type__':'ClassCastException'})
                self.approximate=True
                self.warnings.add('Map view/entry/iterator reference cast is unresolved: '+self.method)
                self.fallback(self.method)
                return U
            if target=='char':
                source=self.source_type(node.named_children[-1])
                if type(value) is int:return chr(value%65536)
                if isinstance(value,str) and (source=='char' or self.standard_type(source,'java.lang.Character')) and len(value.encode('utf-16-le',errors='surrogatepass'))==2:return value
                self.approximate=True
                self.warnings.add('unsupported Java char conversion: '+self.method)
                return U
            if isinstance(value,(str,JsonText)):
                base=target.split('<',1)[0]
                meta=self.p.methods[self.method]
                owner=self.p.resolve_type(base,meta['module'],meta['file'])
                source_incompatible=owner and self.p.nodes[owner]['fqn'] not in ('java.lang.String','java.lang.Object')
                if source_incompatible or any(self.standard_type(base,'java.util.'+name) for name in ('Map','HashMap','LinkedHashMap')):
                    raise JavaThrow({'__type__':'ClassCastException'})
            if isinstance(value,JavaMap):
                return self.reference_check(value,actual_kind,erased_target,text(node))
            if target in PRIMITIVES and target!='char' and actual_kind=='Character' and isinstance(value,str) and len(value)==1:
                value=ord(value)
            if target=='double':
                if type(value) in (int,float):return float(value)
                self.approximate=True;self.warnings.add('double primitive cast value is unresolved: '+text(node));return U
            limits = {'byte': (-128, 127), 'short': (-32768, 32767),
                      'int': (-2147483648, 2147483647), 'long': (-9223372036854775808, 9223372036854775807)}
            if target in limits:
                if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
                    narrowed = int(value)
                    if limits[target][0] <= narrowed <= limits[target][1]:
                        return narrowed
                self.approximate = True
                self.warnings.add('unsupported numeric cast outside modeled finite range: ' + text(node))
                return U
            return value if target in PRIMITIVES else self.reference_check(value,actual_kind,erased_target,text(node))
        if typ == 'field_access':
            if raw in self.p.constants:
                self.remember_reference_kind(self.p.constant_kinds.get(raw))
                return self.p.constants[raw]
            constants = {'Float.MAX_VALUE': 3.4028235e38, 'Double.MAX_VALUE': 1.7976931348623157e308,
                         'Long.MAX_VALUE': 9223372036854775807, 'Integer.MAX_VALUE': 2147483647}
            qualifier=node.child_by_field_name('object')
            if raw in constants and text(qualifier) not in self.variable_types and self.standard_type(text(qualifier),'java.lang.'+text(qualifier)):
                self.remember_reference_kind(text(qualifier))
                return constants[raw]
            if raw.startswith(('HttpMethod.', 'HttpStatus.', 'Calendar.')):
                return raw.split('.')[-1]
            enum = self.p.enum_reference(raw, self.method)
            if enum:
                return deepcopy(self.p.enum_objects[enum])
            qualifier=node.child_by_field_name('object')
            field=text(node.child_by_field_name('field'))
            root=text(qualifier).split('.')[0]
            meta=self.p.methods[self.method]
            class_name=qualifier.type in ('identifier','scoped_identifier','field_access') and root not in env and root not in self.variable_types and root not in self.p.type_fields.get(meta['owner'],{})
            if class_name and field=='HS256' and self.standard_type(text(qualifier),'io.jsonwebtoken.SignatureAlgorithm'):
                from .jjwt import Algorithm
                return Algorithm(field)
            if field in JavaJsonMapper.defaults and ((class_name and self.standard_type(text(qualifier),'com.fasterxml.jackson.databind.DeserializationFeature'))
                    or self.standard_type(self.source_type(qualifier),'com.fasterxml.jackson.databind.DeserializationFeature')):
                if not class_name:self.value(qualifier,env)
                return JacksonFeature(field)
            obj = self.value(node.child_by_field_name('object'), env)
            field = text(node.child_by_field_name('field'))
            from .persistence import load
            load(self,obj,field,self.p.methods[self.method]['file']+':'+str(node.start_point.row+1))
            if obj is None:
                declared=self.source_type(node.child_by_field_name('object'))
                constant=self.p.constants.get(declared.split('.')[-1]+'.'+field,U)
                if constant is not U:
                    self.remember_reference_kind(self.p.constant_kinds.get(declared.split('.')[-1]+'.'+field))
                    return constant
                owner=self.p.resolve_type(declared,self.p.methods[self.method]['module'],self.p.methods[self.method]['file'])
                if field in self.p.type_fields.get(owner,{}) or declared.endswith('[]') and field=='length':
                    raise JavaThrow({'__type__':'NullPointerException'})
                self.approximate=True
                self.warnings.add('unresolved static/instance field access through null: '+raw)
            meta=self.p.methods[self.method]
            owner=self.p.resolve_type(self.source_type(node.child_by_field_name('object')),meta['module'],meta['file'])
            info=self.p.type_fields.get(owner,{}).get(field)
            return U if self.opaque(obj) else len(obj) if isinstance(obj, list) and field == 'length' else self.field_read(node,obj,field,info)
        if typ == 'unary_expression':
            operand=node.child_by_field_name('operand') or node.named_children[-1]
            arg = self.unbox(self.value(operand, env),operand)
            if arg is U:
                return U
            if raw.startswith('!') and isinstance(arg, bool):
                return not arg
            if raw.startswith('-') and isinstance(arg, (int, float)):
                return self.narrow_integer(-arg,self.numeric_type(node)) if type(arg) is int else -arg
            self.approximate=True
            self.warnings.add('unsupported Java unary operation: '+raw)
            return U
        if typ == 'binary_expression':
            op = text(node.child_by_field_name('operator'))
            a = self.value(node.child_by_field_name('left'), env)
            left_kind=self.source_reference_kind(node.child_by_field_name('left'),self.last_reference_kind)
            if a is None and self.binary_unboxes(node,'left'):self.unbox(a,node.child_by_field_name('left'))
            if (op == '&&' and a is False) or (op == '||' and a is True):
                return a
            b = self.value(node.child_by_field_name('right'), env)
            right_kind=self.source_reference_kind(node.child_by_field_name('right'),self.last_reference_kind)
            if b is None and self.binary_unboxes(node,'right'):self.unbox(b,node.child_by_field_name('right'))
            if op in ('==','!=') and a is not None and b is not None and not self.binary_unboxes(node,'left') and not self.binary_unboxes(node,'right'):
                if left_kind and right_kind:
                    equal=scalar_reference_equal(self,node.child_by_field_name('left'),node.child_by_field_name('right'),a,b,left_kind,right_kind)
                    if equal is U:
                        self.approximate=True
                        self.warnings.add('immutable scalar reference identity is unresolved: '+raw)
                    return equal if equal is U or op=='==' else not equal
            if op == '&&' and b is False:
                return False
            if op == '||' and b is True:
                return True
            if a is U or b is U:
                if op=='+' and any(self.standard_type(self.source_type(node.child_by_field_name(side)),'java.lang.String') or
                                   is_symbolic(v) and v.get('__type__') in ('String','java.lang.String')
                                   for side,v in zip(('left','right'),(a,b))):
                    # String concatenation preserves its literal parts even
                    # when one operand's text (including delimiters) is unknown.
                    a={'__symbol__':self.constraint_symbol(),'__type__':'String'} if a is U else a
                    b={'__symbol__':self.constraint_symbol(),'__type__':'String'} if b is U else b
                else:return U
            # A Java char is represented by one UTF-16 code unit, but participates
            # in numeric promotion unless this is a source-typed String concat.
            operand_types=[self.numeric_type(node.child_by_field_name(side)) for side in ('left','right')]
            if all(t in ('byte','short','char','int','long','float','double') for t in operand_types):
                converted=[]
                for value,source_type in zip((a,b),operand_types):
                    if source_type=='char' and isinstance(value,str):
                        units=value.encode('utf-16-le',errors='surrogatepass')
                        if len(units)==2:value=int.from_bytes(units,'little')
                        else:
                            value=U;self.approximate=True
                            self.warnings.add('unresolved Java char code unit: '+self.method)
                    converted.append(value)
                a,b=converted
                if a is U or b is U:return U
            if op in ('==','!=') and any(isinstance(value,(JavaRecord,JavaMap,JavaMapView,JavaMapEntry,JavaMapIterator,JavaEnumValue,JavaTypeToken,JavaTypeFactory,JavaJsonMapper,JacksonFeature,JavaList,JavaListIterator)) for value in (a,b)):
                equal=reference_equal(a,b)
                if equal is U:
                    self.approximate=True
                    self.warnings.add('unresolved Java reference identity: '+raw)
                return equal if equal is U or op=='==' else not equal
            if op=='+' and any(type(v) is dict and v.get('__type__') in ('String','java.lang.String')
                               and '__symbol__' in v for v in (a,b)):
                def string_part(value):
                    if value is None:return 'null'
                    if type(value) is bool:return str(value).lower()
                    if type(value) in (str,int):return str(value)
                    if isinstance(value,datetime):return java_date_text(value)
                    return value
                return concat_text(string_part(a),string_part(b))
            if any(is_symbolic(v) for v in (a, b)):
                if op in ('==','!='):
                    equal=key_equal(a,b)
                    if equal is not U:return equal if op=='==' else not equal
                if self.use_constraints:
                    constrained = compare(a, op, b)
                    if constrained is not U:
                        return constrained
                if op in ('==', '!=') and a == b:
                    return op == '=='
                return U
            if op in ('==','!=') and any(isinstance(v,dict) and '__type__' in v for v in (a,b)):
                if a is b:equal=True
                elif a is None or b is None or key_equal(a,b) is False:equal=False
                else:
                    equal=U
                    self.approximate=True
                    self.warnings.add('unresolved Java reference identity: '+raw)
                return equal if equal is U or op=='==' else not equal
            ops = {'==': operator.eq, '!=': operator.ne, '<': operator.lt, '>': operator.gt,
                   '<=': operator.le, '>=': operator.ge, '+': operator.add, '-': operator.sub,
                   '*': operator.mul, '/': operator.truediv, '&&': lambda x, y: x and y,
                   '||': lambda x, y: x or y}
            if op == '+' and (isinstance(a, str) or isinstance(b, str) or
                              (a is None or b is None) and any(self.standard_type(self.source_type(node.child_by_field_name(side)),'java.lang.String') for side in ('left','right'))):
                def scalar(value):
                    if value is None:return 'null'
                    if type(value) is bool:return str(value).lower()
                    if isinstance(value,(str,int)):return str(value)
                    if type(value) is float and math.isfinite(value) and 'e' not in repr(value):return str(value)
                    if isinstance(value,datetime):return java_date_text(value)
                    return U
                left,right=scalar(a),scalar(b)
                if left is U or right is U:
                    self.approximate=True
                    self.warnings.add('unsupported Java object string conversion: '+raw)
                    return U
                return concat_text(left,right)
            try:
                promoted=self.numeric_type(node)
                if op in ('+','-','*','/','%') and type(a) in (int,float) and type(b) in (int,float):
                    if promoted=='float' or (not promoted and (type(a) is float or type(b) is float)):
                        self.approximate=True
                        self.warnings.add('float rounding or floating-point source type is not modeled: '+raw)
                        return U
                    if promoted=='double':a,b=float(a),float(b)
                if op in ('/', '%') and type(a) is int and type(b) is int:
                    if b==0:raise JavaThrow({'__type__':'ArithmeticException'})
                    quotient = (abs(a) // abs(b)) * (-1 if (a < 0) != (b < 0) else 1)
                    return self.narrow_integer(quotient if op=='/' else a-quotient*b,self.numeric_type(node))
                if op in ops:
                    result=ops[op](a,b)
                    return self.narrow_integer(result,self.numeric_type(node)) if type(result) is int else result
                self.approximate = True
                self.warnings.add('unsupported Java binary operator: ' + op)
                return U
            except (TypeError, ValueError, ZeroDivisionError):
                self.approximate = True
                self.warnings.add('unsupported or failing Java arithmetic: ' + raw)
                return U
        if typ == 'update_expression':
            child=next(c for c in node.named_children if c.type not in ('line_comment','block_comment'))
            op=next(c for c in node.children if c.type in ('++','--'))
            slot=self.lvalue(child,env)
            old=self.lvalue_read(slot)
            new=self.increment_value(old,slot[0],1 if op.type=='++' else -1)
            self.lvalue_write(slot,new,self.declared_kind(compiled_type(self,child)))
            return new if op.start_byte<child.start_byte else old
        if typ == 'assignment_expression':
            lhs, rhs = node.child_by_field_name('left'), node.child_by_field_name('right')
            op = text(node.child_by_field_name('operator'))
            slot=self.lvalue(lhs,env)
            target=slot[0]
            old = self.unbox(self.lvalue_read(slot),target) if op!='=' else U
            result = self.value(rhs, env)
            reference_kind=self.source_reference_kind(rhs,self.last_reference_kind)
            reference_type=self.source_type(rhs)
            if op != '=':
                result=self.compound_value(old,result,target,rhs,op)
                reference_kind=self.declared_kind(compiled_type(self,target))
            elif slot[1] in ('local','field'):
                result,reference_kind=self.assignment_value(result,reference_kind,storage_type(self,target),rhs)
            result=self.generic_binding(result,self.source_type(target),reference_type)
            self.lvalue_write(slot,result,reference_kind,reference_type)
            return result
        if typ == 'ternary_expression':
            condition=node.child_by_field_name('condition')
            c = self.unbox(self.value(condition, env),condition)
            if isinstance(c, bool):
                chosen=node.child_by_field_name('consequence' if c else 'alternative')
                value=self.value(chosen,env)
                self.remember_reference_kind(self.source_reference_kind(chosen,self.last_reference_kind))
                return self.primitive_value(value,self.source_type(node))
            decision = self.choose(self.method + ':ternary:' + str(node.start_point.row + 1), [True, False])
            if decision is not None:
                chosen=node.child_by_field_name('consequence' if decision else 'alternative')
                value=self.value(chosen,env)
                self.remember_reference_kind(self.source_reference_kind(chosen,self.last_reference_kind))
                return self.primitive_value(value,self.source_type(node))
            def ternary_alternative(branch,owned,_):
                chosen=node.child_by_field_name(branch)
                value=self.value(chosen,owned)
                self.remember_reference_kind(self.source_reference_kind(chosen,self.last_reference_kind))
                return value,None
            result,control=self.fork_join(['consequence','alternative'],env,[],ternary_alternative)
            if control=='throw':raise JavaThrow(result)
            return result
        if typ in ('switch_expression', 'switch_statement'):
            result,control = self.execute_switch(node,env)
            if control=='throw':raise JavaThrow(result)
            return result if control=='yield' else U
        if typ in ('lambda_expression','method_reference'):
            return ('lambda' if typ=='lambda_expression' else 'method_reference', node, env.copy(), self.method, dict(self.variable_types),dict(self.source_bindings),self.receiver_type)
        if typ in ('method_invocation', 'object_creation_expression'):
            return self.call(node, env)
        if typ == 'array_initializer':
            return [self.value(child, env) for child in node.named_children]
        if typ == 'array_access':
            arr = self.value(node.child_by_field_name('array'), env)
            idx = self.value(node.child_by_field_name('index'), env)
            if arr is None:raise JavaThrow({'__type__':'NullPointerException'})
            if isinstance(arr,list) and type(idx) is int and not 0<=idx<len(arr):
                raise JavaThrow({'__type__':'ArrayIndexOutOfBoundsException'})
            if isinstance(arr,list) and len(arr)>1 and not getattr(arr,'order_known',True):
                self.approximate=True;self.warnings.add('array encounter order is unspecified: '+text(node));return U
            if isinstance(arr,JavaArray) and type(idx) is int and 0<=idx<len(arr):self.remember_reference_kind(arr.kinds[idx])
            return U if self.opaque(arr) else arr[idx] if isinstance(arr, list) and isinstance(idx, int) and 0 <= idx < len(arr) else U
        if typ == 'expression_statement':
            return self.value(node.named_children[0], env)
        if typ=='class_literal':return JavaTypeToken(raw.removesuffix('.class'),self.p.methods[self.method],'Class')
        if typ in ('type_identifier', 'scoped_type_identifier', 'generic_type', 'class_literal', 'line_comment', 'block_comment'):
            return U
        self.approximate=True
        self.warnings.add('unsupported Java expression '+typ+': '+self.method+':'+str(node.start_point.row+1))
        for child in node.named_children:
            if child.type.endswith('statement') or child.type in ('block', 'local_variable_declaration'):
                self.execute(child, env)
            else:
                self.value(child, env)
        if typ in ('switch_expression', 'switch_statement'):
            self.warnings.add('switch alternatives conservatively retained: ' + self.method)
        return U

    def numeric_type(self,node):
        """Source types for Java integer promotion; values alone lose long vs int."""
        if node is None:return ''
        kind,raw=node.type,text(node)
        aliases={'Integer':'int','Long':'long','Short':'short','Byte':'byte','Double':'double','Float':'float','Character':'char','Boolean':'boolean'}
        if kind=='decimal_integer_literal':return 'long' if raw.lower().endswith('l') else 'int'
        if kind=='decimal_floating_point_literal':return 'float' if raw.lower().endswith('f') else 'double'
        if kind=='character_literal':return 'char'
        if kind in ('true','false'):return 'boolean'
        if kind=='identifier':
            typ=self.native_scalar_type(self.source_type(node))
            return aliases.get(typ,typ)
        if kind in ('parenthesized_expression','unary_expression','update_expression','expression_statement','yield_statement'):
            typ=self.numeric_type(next(c for c in node.named_children if c.type not in ('line_comment','block_comment')))
            return 'int' if kind=='unary_expression' and typ in ('byte','short','char') else typ
        if kind=='assignment_expression':return self.numeric_type(node.child_by_field_name('left'))
        if kind=='cast_expression':
            typ=self.native_scalar_type(self.declared_type(text(node.child_by_field_name('type'))))
            return aliases.get(typ,typ)
        if kind in ('field_access','array_access'):
            typ=self.native_scalar_type(self.source_type(node))
            return aliases.get(typ,typ)
        if kind=='binary_expression':
            op=text(node.child_by_field_name('operator'))
            if op in ('==','!=','<','>','<=','>=','&&','||'):return 'boolean'
            types=[self.numeric_type(node.child_by_field_name(side)) for side in ('left','right')]
            if op in ('+','-','*','/','%','&','|','^') and all(t in ('byte','short','char','int','long','float','double') for t in types):
                return next((t for t in ('double','float','long') if t in types),'int')
        if kind=='ternary_expression':
            types=[self.numeric_type(node.child_by_field_name(side)) for side in ('consequence','alternative')]
            if types[0] and types[0]==types[1]:return types[0]
            if all(t in ('int','long','float','double') for t in types):
                return next((t for t in ('double','float','long') if t in types),'int')
        if kind=='method_invocation':
            name=text(node.child_by_field_name('name'))
            inferred=self.source_type(node).split('.')[-1]
            if inferred:return aliases.get(inferred,inferred)
            site=self.p.site(self.method,node)
            declared=self.p.targets(self.method,site) if site else self.p.source_targets(self.method,node)
            meta=self.p.methods[self.method]
            owner=self.p.resolve_type(self.source_type(node.child_by_field_name('object')),meta['module'],meta['file'])
            arguments=node.child_by_field_name('arguments')
            arity=len(arguments.named_children) if arguments is not None else 0
            if declared or owner and self.p.inherited_methods(owner,name,arity):return ''
            if name in ('length','size','parseInt','intValue','indexOf'):return 'int'
            if name in ('parseLong','longValue','getTime'):return 'long'
            if name in ('parseDouble','doubleValue'):return 'double'
            if name in ('parseFloat','floatValue'):return 'float'
        if kind=='switch_expression':
            types=[]
            for group in node.child_by_field_name('body').named_children:
                if group.type=='switch_rule' and len(group.named_children)==2:
                    types.append(self.numeric_type(group.named_children[1]))
            if types and all(t in ('int','long','float','double') for t in types):
                return next((t for t in ('double','float','long') if t in types),'int')
        return ''

    def source_type(self,node):
        """Declared expression types, including bean fields and collection elements."""
        if node is None:return ''
        kind,raw=node.type,text(node)
        meta=self.p.methods[self.method]
        if kind=='string_literal':return 'java.lang.String'
        if kind=='class_literal':
            written=raw.removesuffix('.class')
            target=self.declared_type(written) or written
            if target in PRIMITIVES or target=='void':
                target='java.lang.'+{'boolean':'Boolean','byte':'Byte','short':'Short','char':'Character',
                    'int':'Integer','long':'Long','float':'Float','double':'Double','void':'Void'}[target]
            return 'java.lang.Class<'+target+'>'
        if kind=='character_literal':return 'char'
        if kind in ('true','false'):return 'boolean'
        if kind in ('decimal_integer_literal','decimal_floating_point_literal'):return self.numeric_type(node)
        if kind=='this':return self.receiver_type or self.p.nodes[meta['owner']]['fqn']
        if kind=='identifier':
            if raw in self.variable_types:
                written=self.variable_types[raw]
                qualified=self.declared_type(written)
                return qualified if qualified or self.has_type_variables(written,meta) else written
            info=self.p.type_fields.get(meta['owner'],{}).get(raw)
            if not info:
                field = (self.p.static_field_declaration(meta['owner'], raw)
                         or self.p.imported_static_field(meta['file'], meta['module'], raw))
                if field:
                    declared, written = field
                    return render_source_type(self.p, written, self.p.nodes[declared], {}, self.standard_type) or written
                return ''
            return self.source_member_type(self.receiver_type or self.p.nodes[meta['owner']]['fqn'],info)
        if kind=='parenthesized_expression':return self.source_type(next(c for c in node.named_children if c.type not in ('line_comment','block_comment')))
        if kind=='update_expression':return self.source_type(next(c for c in node.named_children if c.type not in ('line_comment','block_comment')))
        if kind=='assignment_expression':return self.source_type(node.child_by_field_name('left'))
        if kind in ('cast_expression','object_creation_expression'):
            written=text(node.child_by_field_name('type'))
            qualified=self.declared_type(written)
            return qualified if qualified or self.has_type_variables(written,meta) or '<>' in written else written
        if kind=='array_access':return self.source_type(node.child_by_field_name('array')).removesuffix('[]')
        if kind=='binary_expression':
            if text(node.child_by_field_name('operator'))=='+':
                types=[self.source_type(node.child_by_field_name(side)) for side in ('left','right')]
                if any(self.standard_type(t,'java.lang.String') for t in types):return 'java.lang.String'
            return self.numeric_type(node)
        if kind=='unary_expression':return 'boolean' if raw.startswith('!') else self.numeric_type(node)
        if kind=='ternary_expression':
            types=[self.source_type(node.child_by_field_name(side)) for side in ('consequence','alternative')]
            if types[0] and types[0]==types[1]:return types[0]
            if all(self.standard_type(t,'java.lang.String') for t in types):return 'java.lang.String'
            return self.numeric_type(node)
        if kind not in ('method_invocation','field_access'):return ''
        obj=node.child_by_field_name('object')
        receiver=self.source_type(obj) if obj is not None else self.receiver_type or self.p.nodes[meta['owner']]['fqn']
        if kind=='field_access' and receiver.endswith('[]') and text(node.child_by_field_name('field'))=='length':return 'int'
        owner=self.p.resolve_type(receiver,meta['module'],meta['file'])
        if kind=='field_access':
            name=text(node.child_by_field_name('field'))
            qualifier=text(obj)
            shadowed=qualifier in self.variable_types or qualifier in self.p.type_fields.get(meta['owner'],{})
            if not shadowed and self.standard_type(qualifier,'java.util.Locale') and name in ('ROOT','ENGLISH','US'):
                return 'java.util.Locale'
            static_owner = owner if owner is not None else self.p.resolve_type(qualifier, meta['module'], meta['file']) if not shadowed else None
            field = self.p.static_field_declaration(static_owner, name)
            if field:
                declared, written = field
                return render_source_type(self.p, written, self.p.nodes[declared], {}, self.standard_type) or written
            if name=='MAX_VALUE' and not shadowed:
                for boxed,primitive in (('Integer','int'),('Long','long'),('Float','float'),('Double','double')):
                    if self.standard_type(qualifier,'java.lang.'+boxed):return primitive
            prefix=(self.p.nodes[owner]['fqn'].rsplit('.',1)[-1] if owner else qualifier)
            key=prefix+'.'+name
            if key in self.p.constant_types:return self.declared_type(self.p.constant_types[key]) or self.p.constant_types[key]
        if kind=='method_invocation':
            site=self.p.site(self.method,node)
            targets=self.p.targets(self.method,site) if site else self.p.source_targets(self.method,node)
            if not targets and owner is not None:
                name=text(node.child_by_field_name('name'))
                arguments=node.child_by_field_name('arguments')
                count=len(arguments.named_children) if arguments is not None else 0
                owners=set(self.p.type_parents.get(owner,set()))|{owner}
                targets=[target for target in self.p.by_name.get(name,[]) if self.p.methods[target]['owner'] in owners
                         and len(self.p.parameters(target))==count]
            types={self.source_return_type(target,receiver,node) for target in targets}
            if len(types)==1:return next(iter(types))
            name=text(node.child_by_field_name('name'))
            arguments=node.child_by_field_name('arguments')
            count=len(arguments.named_children) if arguments is not None else 0
            native=resolve_native_call(receiver,name,[self.source_type(arg) for arg in arguments.named_children
                if arg.type not in ('line_comment','block_comment')],self.standard_type) if not targets else None
            if native:return native.result_type
            if any(self.standard_type(receiver,fqn) for fqn in ('org.springframework.web.client.RestTemplate','org.springframework.web.client.RestOperations')) and name in ('getForObject','getForEntity','postForObject','postForEntity','exchange'):
                index=3 if name=='exchange' else 2 if name.startswith('post') else 1
                nodes=[arg for arg in arguments.named_children if arg.type not in ('line_comment','block_comment')]
                if len(nodes)>index:
                    token=nodes[index];written=''
                    if token.type=='class_literal':written=text(token).removesuffix('.class')
                    elif token.type=='object_creation_expression':
                        root,params=type_parts(text(token.child_by_field_name('type')))
                        if self.standard_type(root,'org.springframework.core.ParameterizedTypeReference') and params and len(params)==1:written=params[0]
                    if written:
                        result=self.declared_type(written) or written
                        return 'org.springframework.http.ResponseEntity<'+result+'>' if name in ('exchange','getForEntity','postForEntity') else result
            base,type_arguments=type_parts(receiver)
            if count==0 and name=='stream' and type_arguments and len(type_arguments)==1 and any(self.standard_type(base,'java.util.'+kind) for kind in ('List','ArrayList','LinkedList','Set','Collection')):
                return 'java.util.stream.Stream<'+type_arguments[0]+'>'
            if self.standard_type(base,'java.util.stream.Stream') and type_arguments and len(type_arguments)==1:
                if name=='filter' and count==1:return receiver
                if name=='map' and count==1:
                    callback=arguments.named_children[0]
                    if callback.type in ('method_reference','lambda_expression'):
                        reference=('method_reference' if callback.type=='method_reference' else 'lambda',callback,{},self.method,dict(self.variable_types),dict(self.source_bindings),self.receiver_type)
                        result=self.callback_return_type(reference,type_arguments[0])
                        if result:return 'java.util.stream.Stream<'+result+'>'
                if name=='collect' and count==1 and re.fullmatch(r'(?:java\.util\.stream\.)?Collectors\.toList\(\)',text(arguments.named_children[0])):
                    if self.standard_type('Collectors','java.util.stream.Collectors') or text(arguments.named_children[0]).startswith('java.util.stream.Collectors.'):
                        return 'java.util.List<'+type_arguments[0]+'>'
            native_entry=(self.standard_type(base,'java.util.Map.Entry') or base=='Map.Entry' and self.standard_type('Map','java.util.Map'))
            if native_entry and type_arguments and len(type_arguments)==2 and count==0 and name in ('getKey','getValue'):
                return type_arguments[0 if name=='getKey' else 1]
            if type_arguments:
                if name=='next' and count==0 and len(type_arguments)==1 and self.standard_type(base,'java.util.Iterator'):return type_arguments[0]
                if name=='iterator' and count==0 and len(type_arguments)==1 and any(self.standard_type(base,'java.util.'+kind) for kind in ('Set','Collection','List')):
                    return 'java.util.Iterator<'+type_arguments[0]+'>'
                if count==0 and len(type_arguments)==2 and any(self.standard_type(base,'java.util.'+kind) for kind in ('Map','HashMap','LinkedHashMap')):
                    if name=='keySet':return 'java.util.Set<'+type_arguments[0]+'>'
                    if name=='values':return 'java.util.Collection<'+type_arguments[1]+'>'
                    if name=='entrySet':return 'java.util.Set<java.util.Map.Entry<'+','.join(type_arguments)+'>>'
            shadowed=text(obj) in self.variable_types or text(obj) in self.p.type_fields.get(meta['owner'],{})
            if name=='parseInt' and not shadowed and not receiver and self.standard_type(text(obj),'java.lang.Integer') and count in (1,2):return 'int'
            if name=='asList' and count and not shadowed and self.standard_type(text(obj),'java.util.Arrays'):
                types={self.scalar_or_source_type(self.source_type(arg)) for arg in arguments.named_children}
                if len(types)==1 and '' not in types:return 'java.util.List<'+next(iter(types))+'>'
            if self.standard_type(receiver,'java.lang.String'):
                if (name=='substring' and count in (1,2)) or (name in ('toString','trim','toLowerCase','toUpperCase') and count==0):return 'java.lang.String'
                if name=='charAt' and count==1:return 'char'
                if name=='split' and count in (1,2):return 'java.lang.String[]'
                if name=='length' and count==0:return 'int'
                if (name in ('equals','equalsIgnoreCase','contains','startsWith','endsWith') and count==1) or (name=='isEmpty' and count==0):return 'boolean'
            if owner is None and any(self.standard_type(base,'java.util.'+kind) for kind in ('List','ArrayList','LinkedList')):
                element=type_arguments[0] if type_arguments and len(type_arguments)==1 else 'java.lang.Object'
                if name=='get' and count==1 or name=='set' and count==2:return element
                if name=='remove' and count==1:
                    first=next((c for c in arguments.named_children if c.type not in ('line_comment','block_comment')),None)
                    return element if self.source_type(first) in ('byte','short','char','int') else 'boolean'
                if name=='size' and count==0:return 'int'
            if name=='next' and count==0 and self.standard_type(base,'java.util.Iterator') and not type_arguments:return 'java.lang.Object'
            if name=='get' and count==1 and owner is None:
                if any(self.standard_type(base,'java.util.'+kind) for kind in ('Map','HashMap','LinkedHashMap')):
                    return type_arguments[1] if type_arguments and len(type_arguments)==2 else 'java.lang.Object'
            if self.standard_type(base,'java.util.Optional') and name in ('get','orElse','orElseThrow'):
                return type_arguments[0] if type_arguments and len(type_arguments)==1 else 'java.lang.Object'
            if self.standard_type(receiver,'java.security.Principal') and name=='getName' and count==0:return 'java.lang.String'
            if count==0:
                generated=generated_accessor(self.p,owner,name,0,self.standard_type)
                if generated:
                    info=self.p.type_fields.get(generated['owner'],{}).get(generated['member'])
                    if info:return self.source_member_type(receiver,info)
            if count==0 and name.startswith(('get','is')):
                name=name[3:] if name.startswith('get') else name[2:]
                field=name[:1].lower()+name[1:]
            else:return ''
        else:field=text(node.child_by_field_name('field'))
        pending,seen=[owner],set()
        while pending:
            current=pending.pop()
            if current is None or current in seen:continue
            seen.add(current)
            info=self.p.type_fields.get(current,{}).get(field)
            if info:return self.source_member_type(receiver,info)
            pending.extend(self.p.resolve_type(parent,self.p.nodes[current]['module'],self.p.nodes[current]['file'])
                           for parent in self.p.framework_types.get(current,set()))
        return ''

    def map_key_type(self,node):
        """Use source types for boxing, never the shape of a Python scalar."""
        typ=self.source_type(node) or self.numeric_type(node)
        return self.native_scalar_type(typ) or 'unresolved'

    def native_scalar_type(self,typ):
        if typ in ('byte','short','char','int','long','float','double','boolean'):return typ
        for name in ('String','Integer','Long','Byte','Short','Character','Boolean','Double','Float'):
            if self.standard_type(typ,'java.lang.'+name):return name
        return ''

    def declared_type(self,written):
        meta=self.p.methods[self.method]
        return render_source_type(self.p,written,meta,source_environment(self.source_bindings,meta),self.standard_type,self.type_variable_scope(meta))

    def source_member_type(self,receiver,info):
        meta=self.p.methods[self.method]
        return member_type(self.p,receiver,info['declaring_type'],info['type'],meta,self.standard_type)

    def generic_call_context(self,target,node,receiver=None):
        meta=self.p.methods[self.method]
        if receiver is None:
            receiver=(self.declared_type(text(node.child_by_field_name('type'))) if node.type=='object_creation_expression' else
                      self.source_type(node.child_by_field_name('object')) if node.child_by_field_name('object') is not None else
                      self.receiver_type or self.p.nodes[meta['owner']]['fqn'])
        arguments=node.child_by_field_name('arguments')
        types=[self.source_type(arg) for arg in arguments.named_children if arg.type not in ('line_comment','block_comment')] if arguments is not None else []
        explicit=node.child_by_field_name('type_arguments')
        explicit=[self.declared_type(text(arg)) for arg in explicit.named_children if arg.type not in ('line_comment','block_comment')] if explicit is not None else None
        return call_context(self.p,target,receiver,meta,types,explicit,self.standard_type,'static' in self.method_modifiers(target))

    def source_return_type(self,target,receiver,node):
        return self.generic_call_context(target,node,receiver)[2]

    def scalar_or_source_type(self,written):
        """Qualify a bounded generic argument in the current source namespace."""
        boxed={'byte':'Byte','short':'Short','int':'Integer','long':'Long','char':'Character',
               'boolean':'Boolean','double':'Double','float':'Float'}
        if written in boxed:return 'java.lang.'+boxed[written]
        return self.declared_type(written)

    def stream_element_type(self,node):
        written=compiled_type(self,node)
        base,args=type_parts(written)
        if args and len(args)==1 and any(self.standard_type(base,'java.util.'+kind) for kind in ('List','ArrayList','LinkedList','Collection','Set')):
            return self.scalar_or_source_type(args[0])
        if any(self.standard_type(base,'java.util.'+kind) for kind in ('List','ArrayList','LinkedList','Collection','Set')):return 'java.lang.Object'
        return ''

    def narrow_integer(self,value,typ):
        bits={'byte':8,'short':16,'int':32,'long':64}.get(typ)
        if bits:return (value+(1<<(bits-1)))%(1<<bits)-(1<<(bits-1))
        self.approximate=True
        self.warnings.add('unknown Java integer width; numeric result retained as unknown: '+self.method)
        return U

    def catch_type(self,written):
        meta=self.p.methods[self.method]
        owner=self.p.resolve_type(written,meta['module'],meta['file'])
        if owner:return self.p.nodes[owner]['fqn']
        for fqn in NATIVE_TYPES.values():
            if self.standard_type(written,fqn):return fqn
        # Preserve explicit foreign imports instead of matching their short name.
        for node in self.p.trees[meta['file']].root_node.named_children:
            match=re.fullmatch(r'import\s+([\w.]+)\s*;',text(node)) if node.type=='import_declaration' else None
            if match and match[1].rsplit('.',1)[-1]==written:return match[1]
        return written

    def standard_type(self,name,fqn,meta=None):
        """A source-proven JDK type, rather than an unrelated namesake."""
        meta=self.p.methods[self.method] if meta is None else meta
        # Project source and namespaces are immutable during a run. Type proofs
        # are reused across paths, unlike values or local variable bindings.
        cache=self.p.__dict__.setdefault('_standard_type_cache',{})
        variables=self.type_variable_scope(meta)
        key=(name,fqn,meta['module'],meta['file'],tuple(sorted(variables)))
        if key not in cache:cache[key]=name not in variables and self.prove_standard_type(name,fqn,meta)
        return cache[key]

    def type_variable_scope(self,meta):
        owner=meta.get('owner')
        if owner is None:return frozenset()
        methods=self.p.__dict__.get('_method_meta_ids')
        if methods is None:
            methods={id(value):mid for mid,value in self.p.methods.items()}
            self.p._method_meta_ids=methods
        mid=methods.get(id(meta))
        cache=self.p.__dict__.setdefault('_type_variable_scope_cache',{})
        if mid in cache:return cache[mid]
        names=set(self.p.type_variables.get(owner,{}))
        node=self.p.ast.get(mid)
        parameters=node.child_by_field_name('type_parameters') if node is not None else None
        if parameters is not None:
            names.update(text(child) for par in parameters.named_children for child in par.named_children if child.type=='type_identifier')
        result=frozenset(names)
        if mid is not None:cache[mid]=result
        return result

    def has_type_variables(self,written,meta):
        variables=self.type_variable_scope(meta)
        return bool(variables and set(re.findall(r'(?<![\w.])[\w$]+',written)) & variables)

    def prove_standard_type(self,name,fqn,meta):
        if self.p.resolve_type(name,meta['module'],meta['file']):
            return False
        if name==fqn:return True
        if name!=fqn.rsplit('.',1)[-1]:return False
        imports=[match[1] for node in self.p.trees[meta['file']].root_node.named_children if node.type=='import_declaration'
                 for match in [re.search(r'\bimport\s+(?:static\s+)?([\w.*]+)\s*;',text(node))] if match]
        explicit=[item for item in imports if item.rsplit('.',1)[-1]==name]
        if explicit:return explicit==[fqn]
        return fqn.startswith('java.lang.') or fqn.rsplit('.',1)[0]+'.*' in imports

    def method_modifiers(self,target):
        source=self.p.ast.get(target)
        flags={keyword.type for child in source.named_children if child.type=='modifiers'
               for keyword in child.children if not keyword.is_named} if source is not None else set()
        if source is not None and source.parent.parent.type=='interface_declaration' and 'private' not in flags:
            flags.add('public')
        return flags

    def concrete_dispatch(self,owner,name,arity,targets,declared,reason):
        """Refine the supplied declaration by class and parameter signature."""
        if (targets and all(self.p.ast.get(target) is None for target in targets)
                and generated_accessor(self.p,owner,name,arity,self.standard_type)):
            return targets
        anchors=[target for target in declared if target in self.p.methods] or targets
        if any(self.method_modifiers(target) & {'static','private'} for target in anchors):return targets
        ancestry,level=set(),[owner]
        levels=[]
        while level:
            levels.append(set(level));ancestry.update(level)
            level=sorted({parent for current in level for parent in self.p.type_parents.get(current,[]) if parent not in ancestry})
        signatures={self.p.dispatch_signature(target) for target in anchors}
        candidates=[target for target in self.p.by_name.get(name,[]) if self.p.methods[target]['owner'] in ancestry
                    and len(self.p.parameters(target))==arity and not self.p.methods[target].get('abstract')
                    and not self.method_modifiers(target) & {'static','private'}
                    and self.p.ix.unit_of(self.method) in self.p.ix.units.get(self.p.methods[target]['module'],())]
        if None in signatures or any(self.p.dispatch_signature(target) is None for target in candidates):
            self.approximate=True
            self.warnings.add('generic or unresolved dispatch signature; alternatives retained: '+reason)
            return sorted(set(targets)|set(candidates))
        selected=[]
        parents={}
        def ancestors(current):
            if current not in parents:
                found,pending=set(),list(self.p.type_parents.get(current,[]))
                while pending:
                    parent=pending.pop()
                    if parent in found:continue
                    found.add(parent);pending.extend(self.p.type_parents.get(parent,[]))
                parents[current]=found
            return parents[current]
        def package(target):
            return self.p.nodes[self.p.methods[target]['owner']]['fqn'].rpartition('.')[0]
        for anchor in anchors:
            if self.p.methods[anchor]['owner'] not in ancestry:
                self.approximate=True
                self.warnings.add('declared dispatch owner is not a proven receiver supertype: '+reason)
                return targets
            signature=self.p.dispatch_signature(anchor)
            eligible={anchor}
            matching=[target for target in candidates if self.p.dispatch_signature(target)==signature]
            changed=True
            while changed:
                changed=False
                for target in matching:
                    if target in eligible:continue
                    if any(self.p.methods[base]['owner'] in ancestors(self.p.methods[target]['owner'])
                           and (self.method_modifiers(base) & {'public','protected'} or package(base)==package(target))
                           for base in eligible):
                        eligible.add(target);changed=True
            for level in levels:
                nearest=[target for target in matching if target in eligible and self.p.methods[target]['owner'] in level]
                if nearest:
                    selected.extend(nearest)
                    break
        return sorted(set(selected)) or targets

    def map_initializer(self,node,args,env,reason):
        """Native Map subclasses with put-only instance blocks and no overrides."""
        typ=text(node.child_by_field_name('type'))
        base=typ.split('<',1)[0]
        if not any(self.standard_type(base,'java.util.'+name) for name in ('HashMap','LinkedHashMap')):return False,U
        handled,mapping=construct(typ,args,self.state.now)
        if not handled or not isinstance(mapping,JavaMap):return False,U
        body=next(child for child in node.named_children if child.type=='class_body')
        blocks=[child for child in body.named_children if child.type not in ('line_comment','block_comment')]
        if any(block.type!='block' for block in blocks):return False,U
        invocations=[]
        for block in blocks:
            for statement in block.named_children:
                if statement.type in ('line_comment','block_comment'):continue
                if statement.type!='expression_statement' or len(statement.named_children)!=1:return False,U
                call=statement.named_children[0]
                if call.type!='method_invocation' or text(call.child_by_field_name('name'))!='put' or text(call.child_by_field_name('object')) not in ('','this'):return False,U
                values=[child for child in call.child_by_field_name('arguments').named_children if child.type not in ('line_comment','block_comment')]
                if len(values)!=2:return False,U
                if any(child.type=='this' or child.type=='method_invocation' and child.child_by_field_name('object') is None
                       for value in values for child in walk(value)):return False,U
                invocations.append(values)
        for nodes in invocations:
            values=[self.value(value,env) for value in nodes]
            key_type=self.map_key_type(nodes[0])
            _,result=library('put',mapping,values,'this',self.state.now,key_type=key_type,value_type=self.map_key_type(nodes[1]))
            if result is U or any(value is U for value in values):
                self.approximate=True
                self.warnings.add('native Map initializer contains an unresolved key or value: '+reason)
                self.operation_issues[(mapping.last_issue or 'unknown_map_value','initializer.put')]+=1
        return True,mapping

    def initialize_instance(self, tid, obj, reason):
        """Evaluate field and instance initializers in source order, before body."""
        if not tid:return
        cache=self.p.__dict__.setdefault('_instance_initializers',{})
        if tid not in cache:
            meta=self.p.nodes[tid]
            declarations=[node for node in walk(self.p.trees[meta['file']].root_node)
                          if node.type=='class_declaration' and declaration_matches(node,meta['fqn'])]
            items=[]
            if len(declarations)==1:
                for child in declarations[0].child_by_field_name('body').named_children:
                    if child.type=='block':items.append((None,child))
                    if child.type=='field_declaration' and 'static' not in keywords(child):
                        items.extend((text(var.child_by_field_name('name')),var.child_by_field_name('value'))
                                     for var in child.named_children if var.type=='variable_declarator' and var.child_by_field_name('value') is not None)
            cache[tid]=items
        constructors=[mid for mid in self.p.methods_of(tid,'<init>') if self.p.ast.get(mid) is not None]
        previous, types = self.method, self.variable_types
        previous_context = self.initializer_context
        previous_receiver,previous_bindings=self.receiver_type,self.source_bindings
        context=self.method if self.method in constructors else constructors[0] if constructors else None
        if context:self.method=context
        else:self.implicit_initializer+=1
        if context != previous:
            self.receiver_type=self.p.nodes[tid]['fqn']
            self.source_bindings={}
        self.initializer_context=(tid,self.method,not bool(context))
        self.variable_types={name:field['type'] for name,field in self.p.type_fields.get(tid,{}).items()}
        env={'this':obj}
        try:
            for field,node in cache[tid]:
                if field is None:
                    value,control=self.execute(node,env)
                    if control=='throw':raise JavaThrow(value)
                    if control:
                        self.approximate=True;self.warnings.add('unsupported initializer completion: '+reason)
                else:
                    value=self.value(node,env)
                    kind=self.source_reference_kind(node,self.last_reference_kind)
                    value,kind=self.assignment_value(value,kind,self.p.type_fields[tid][field]['type'],node)
                    obj[field]=value
                    obj._native_field_kinds={**getattr(obj,'_native_field_kinds',{}),field:kind}
        finally:
            self.method,self.variable_types=previous,types
            self.initializer_context=previous_context
            self.receiver_type,self.source_bindings=previous_receiver,previous_bindings
            if not context:self.implicit_initializer-=1

    def call(self, node, env, synthetic=False):
        mid = self.method
        site = None if synthetic else self.p.site(mid, node)
        cs = self.p.nodes.get(site, {})
        name = '<init>' if node.type == 'object_creation_expression' else text(node.child_by_field_name('name'))
        objnode = node.child_by_field_name('object')
        obj = self.value(objnode, env) if objnode else env.get('this', U)
        receiver_kind=self.source_reference_kind(objnode,self.last_reference_kind) if objnode is not None else None
        argnode = node.child_by_field_name('arguments')
        declared=None
        args=[]
        argument_kinds=[]
        for child in argnode.named_children if argnode else []:
            if child.type in ('line_comment','block_comment'):continue
            value=self.value(child,env)
            if value is None:
                if declared is None:declared=self.p.targets(mid,site) if site else self.p.source_targets(mid,node)
                parameters=[self.p.parameters(target) for target in declared]
                expected={pars[len(args)][1] for pars in parameters if len(pars)>len(args)}
                if len(expected)==1 and all(len(pars)>len(args) for pars in parameters):
                    value=self.primitive_value(value,next(iter(expected)))
            args.append(value)
            argument_kinds.append(self.source_reference_kind(child,self.last_reference_kind))
        reason = site or f"{self.p.methods[mid]['file']}:{node.start_point.row + 1}"
        from .persistence import load_collection
        obj=load_collection(self,obj,reason)
        if name=='<init>' and text(node.child_by_field_name('type')).split('<')[0].rsplit('.',1)[-1] in ('ArrayList','LinkedList','HashSet'):
            args=[load_collection(self,value,reason) for value in args]
        if name=='doFilter' and type(obj) is dict and '__filter_chain__' in obj:
            self.continue_filter(*obj['__filter_chain__'])
            return None
        if type(obj) is dict and obj.get('__type__')=='HttpServletResponse':
            if name in ('setStatus','sendError') and args:
                obj['status']=status_code(args[0])
                return None
            if name=='getStatus':return obj['status']
        if type(obj) is dict and obj.get('__type__')=='HttpServletRequest':
            if name=='getMethod' and not args:return obj['method']
            if name=='getRequestURI' and not args:return obj['uri']
            if name=='getHeader' and len(args)==1 and isinstance(args[0],str):
                headers=obj['headers']
                found=headers.get(args[0].lower(),U if headers.get('__rest_unknown__') else None) if isinstance(headers,dict) else U
                return found[0] if isinstance(found,list) and found else found
        wiring = self.p.edges.get(site, {})
        targets = self.p.targets(mid, site) if site else self.p.source_targets(mid, node)
        if not targets and not wiring.get('data_access'):
            targets=self.p.source_targets(mid,node)
        receiver_type = cs.get('receiver_type')
        from .feign_client import operation as feign_operation
        handled,value=feign_operation(self,node,args,reason) if objnode is not None else (False,U)
        if handled:return value
        argument_nodes=[child for child in argnode.named_children if child.type not in ('line_comment','block_comment')] if argnode else []
        native=resolve_native_call(self.source_type(objnode),name,[self.source_type(arg) for arg in argument_nodes],self.standard_type) if not targets else None
        if native:
            if native.owner=='org.slf4j.Logger':
                return self.slf4j_call(native,obj,args,reason,env)
            if native.owner!='java.lang.String':
                if obj is U or obj is None:return unknown_observer(self,native,obj,reason)
                native=None
        if native:
            self.remember_reference_kind(self.declared_kind(native.result_type))
            locale=self.state.context.get('java_default_locale',U)
            if name in ('toLowerCase','toUpperCase') and argument_nodes:
                locale_node=argument_nodes[0]
                if locale_node.type=='field_access' and self.standard_type(text(locale_node.child_by_field_name('object')),'java.util.Locale'):
                    locale={'ROOT':'root','ENGLISH':'en','US':'en'}.get(text(locale_node.child_by_field_name('field')),U)
                elif isinstance(args[0],dict):locale=args[0].get('language',U)
            def issue(message):
                self.approximate=True;self.warnings.add(message+': '+reason)
                self.operation_issues[('known_native_operation_unknown_value',name)]+=1
            value=string_call(native,obj,args,self.constraint_symbol,issue,locale)
            if native.result_type=='java.lang.String[]' and isinstance(value,list):value=JavaArray(value,'java.lang.String',['String']*len(value))
            return value
        if name=='<init>' and self.standard_type(text(node.child_by_field_name('type')),'java.util.Locale'):
            return {'__type__':'java.util.Locale','language':args[0].lower() if args and isinstance(args[0],str) else U}
        if not targets and args and self.standard_type(text(objnode),'org.springframework.util.Assert') and name in ('hasLength','isNull','notNull','isTrue','state'):
            argument=args[0]
            accepted=(argument is None if name=='isNull' else argument is not None if name=='notNull' else
                      bool(argument) if name=='hasLength' and isinstance(argument,str) else
                      argument if name in ('isTrue','state') and type(argument) is bool else U)
            if argument is U:accepted=U
            if accepted is U:
                label=reason+':assertion'
                accepted=self.choose(label,[True,False])
                if accepted is None and self.path_replay:raise CompletionRequired(str(self.branch_index)+':'+label,[True,False])
                if accepted is None:self.assume('unresolved assertion continuation: '+reason)
            if accepted is False:raise JavaThrow({'__type__':'IllegalStateException' if name=='state' else 'IllegalArgumentException'})
            return None
        if name=='<init>' and any(child.type=='class_body' for child in node.named_children):
            base,type_args=type_parts(text(node.child_by_field_name('type')))
            body=next(child for child in node.named_children if child.type=='class_body')
            if not args and type_args and len(type_args)==1 and type_args[0] and not any(child.type not in ('line_comment','block_comment') for child in body.named_children):
                for fqn in ('org.springframework.core.ParameterizedTypeReference','com.fasterxml.jackson.core.type.TypeReference'):
                    if self.standard_type(base,fqn):return JavaTypeToken(type_args[0],self.p.methods[mid],fqn.rsplit('.',1)[-1])
            handled,value=self.map_initializer(node,args,env,reason) if not targets else (False,U)
            if handled:return value
            self.approximate=True
            self.warnings.add('anonymous class construction or initializer is not modeled: '+reason)
            self.operation_issues[('unsupported_java_construction','anonymous_class')]+=1
            self.fallback(mid)
            return U
        if name != '<init>' and isinstance(obj,JavaObject) and text(objnode) != 'super':
            owner=self.p.resolve_type(obj.java_type,self.p.methods[mid]['module'],self.p.methods[mid]['file'])
            if owner and targets:
                targets=self.concrete_dispatch(owner,name,len(args),targets,wiring.get('calls',set()),reason)
        if objnode is not None and obj is None:
            static = targets and all('static' in self.method_modifiers(target) for target in targets)
            if not static:
                if targets or self.standard_type(self.source_type(objnode),'com.fasterxml.jackson.databind.ObjectMapper') or name in ('equals','equalsIgnoreCase','toString','length','isEmpty','isBlank','orElseThrow','getForObject','getForEntity','postForObject','postForEntity','exchange'):
                    raise JavaThrow({'__type__':'NullPointerException'})
                self.approximate=True
                self.warnings.add('unresolved static/instance invocation on null: '+reason)
                return U
        if not targets and name == 'builder' and receiver_type in self.p.builder_types:
            fields = self.p.builder_types[receiver_type]
            return {'__builder__': receiver_type, 'fields': {n: False if t == 'boolean' else 0 if t in ('int', 'long', 'double', 'float') else None for n, t in fields}}
        if not targets and type(obj) is dict and '__builder__' in obj:
            if name == 'build':
                value=JavaRecord(obj['__builder__'],{'__type__': obj['__builder__'], **deepcopy(obj['fields'])},obj['fields'])
                value.source_owner=self.p.resolve_type(obj['__builder__'],self.p.methods[mid]['module'],self.p.methods[mid]['file'])
                return value
            if name in obj['fields'] and len(args) == 1:
                obj['fields'][name] = args[0]
                return obj
        if not targets and name == 'values' and not args:
            meta = self.p.methods[mid]
            tid = self.p.resolve_type(text(objnode), meta['module'], meta['file'])
            values = [deepcopy(self.p.enum_objects[key]) for key in self.p.enum_members.get(tid, [])]
            if values: return values
        if not targets and isinstance(obj,JavaEnumValue) and name=='name' and not args:
            self.remember_reference_kind('String')
            return obj.enum_name
        if not targets:
            from .spring_formatter import call as formatter_call
            handled,value=formatter_call(self,node,name,obj,args,reason)
            if handled:return value
            from .jjwt import native_call as jwt_call
            handled,value=jwt_call(self,node,name,obj,args,reason)
            if handled:return value
            from .security import native_call
            handled,value=native_call(self,node,name,obj,args,env,reason)
            if handled:return value
        if not targets and isinstance(obj, dict) and (isinstance(obj,(JavaRecord,JavaEnumValue)) or type(obj) is dict and obj.get('__type__')) and name != '<init>':
            runtime_type = obj.declared_type if isinstance(obj,JavaRecord) else self.p.nodes[obj.enum_owner]['fqn'] if isinstance(obj,JavaEnumValue) else self.p.nodes[obj['__enum_type__']]['fqn'] if obj.get('__enum_type__') else obj['__type__']
            runtime_owner=self.p.resolve_type(runtime_type,self.p.methods[mid]['module'],self.p.methods[mid]['file'])
            targets = [m for m in self.p.inherited_methods(runtime_owner,name,len(args))
                       if not self.p.methods[m].get('abstract')
                       and self.p.ix.unit_of(mid) in self.p.ix.units.get(self.p.methods[m]['module'], ())]
        if name == '<init>':
            typ = text(node.child_by_field_name('type'))
            obj = {'__type__': typ}
            tid = self.p.resolve_type(typ, self.p.methods[mid]['module'], self.p.methods[mid]['file'])
            if tid:
                obj = JavaObject(self.p.nodes[tid]['fqn'],{'__type__': self.p.nodes[tid]['fqn'], '__http_entity__': False},wire_fields=self.p.type_fields.get(tid,{}))
            for field, info in self.p.type_fields.get(tid, {}).items():
                default = False if info['type']=='boolean' else '\0' if info['type']=='char' else 0 if info['type'] in ('int','long','double','float','short','byte') else None
                if info.get('declaring_type') != tid:
                    default = info['default'] if info['has_initializer'] else default
                obj[field] = deepcopy(default)
                kind=self.declared_kind(info['type']) if info['type'] in PRIMITIVES else None
                if isinstance(obj,JavaRecord):obj._native_field_kinds={**getattr(obj,'_native_field_kinds',{}),field:kind}
            if tid:
                if targets:obj._pending_initializer=tid
                else:self.initialize_instance(tid,obj,reason)
            collection_base,_=type_parts(typ);collection_name=collection_base.rsplit('.',1)[-1]
            if not tid and collection_name in ('ArrayList','LinkedList','List','HashSet','Set'):
                if collection_name not in ('ArrayList','LinkedList','HashSet') or not self.standard_type(collection_base,'java.util.'+collection_name):
                    self.approximate=True
                    self.warnings.add('native collection constructor kind or namespace is not modeled: '+reason)
                    return U
                if len(args)==1 and args[0] is None:raise JavaThrow({'__type__':'NullPointerException'})
                if len(args)==1 and type(args[0]) is int and collection_name=='ArrayList':
                    if args[0]<0:raise JavaThrow({'__type__':'IllegalArgumentException'})
                elif args and (len(args)!=1 or not isinstance(args[0],list) or isinstance(args[0],JavaArray)):
                    self.approximate=True;self.warnings.add('native List constructor overload is not modeled: '+reason);return U
                kinds=args[0].kinds if args and isinstance(args[0],JavaList) else None
                obj=JavaList(() if collection_name=='HashSet' else args[0] if args and isinstance(args[0],list) else (),
                             None if collection_name=='HashSet' else kinds)
                obj.flavor=collection_name
                obj.order_known=collection_name!='HashSet' and (not args or getattr(args[0],'order_known',True))
                obj.opaque=bool(args and (self.opaque(args[0]) or isinstance(args[0],JavaList) and args[0].opaque))
                if collection_name=='HashSet' and args and not obj.opaque:
                    from .java_sets import call as set_call
                    set_call(self,'addAll',obj,args,argument_kinds,reason)
        if not targets and name=='sort' and args and isinstance(args[0],list) and len(args[0])<=1 and not self.opaque(args[0]) and not getattr(args[0],'opaque',False) and self.standard_type(text(objnode),'org.springframework.beans.support.PropertyComparator'):
            return None
        if not targets and name=='unmodifiableList' and len(args)==1 and self.standard_type(text(objnode),'java.util.Collections'):
            if args[0] is None:raise JavaThrow({'__type__':'NullPointerException'})
            if isinstance(args[0],JavaList):
                from .native_storage import ReadOnlyList
                return ReadOnlyList(args[0])
            return U
        if name == '<init>':
            base=typ.split('<')[0]
            if not tid and not targets and self.standard_type(base,'com.fasterxml.jackson.databind.ObjectMapper'):
                if not args:return JavaJsonMapper()
                self.json_issue('JSON mapper constructor overload is not modeled',reason)
                return U
            unresolved_map=not tid and base.rsplit('.',1)[-1] in ('Map','HashMap','LinkedHashMap') and not self.standard_type(base,'java.util.'+base.rsplit('.',1)[-1])
            handled, value = (True,U) if unresolved_map else construct(typ, args, self.state.now) if not tid and not targets else (False, U)
            if handled:
                obj = value
                if value is U:
                    self.approximate=True
                    self.warnings.add('unresolved modeled constructor: '+typ+' at '+reason)
            elif not targets and receiver_type in self.p.all_args_types:
                fields = self.p.all_args_types[receiver_type]
                if len(fields) == len(args): obj = JavaObject(self.p.nodes[tid]['fqn'],{'__type__': receiver_type, **{n: v for (n, _), v in zip(fields, args)}},wire_fields=self.p.type_fields.get(tid,{})) if tid else {'__type__': receiver_type, **{n: v for (n, _), v in zip(fields, args)}}
        if name=='<init>' and tid and isinstance(obj,JavaRecord):obj.source_owner=tid
        if isinstance(obj,JavaRecord) and targets and all(self.p.ast.get(target) is None for target in targets):
            actual=getattr(obj,'source_owner',None) or self.p.resolve_type(obj.declared_type,self.p.methods[mid]['module'],self.p.methods[mid]['file'])
            if generated_accessor(self.p,actual,name,len(args),self.standard_type):targets=[]
            elif name=='<init>' and not args and actual in self.p.type_fields:
                plan=default_bean_plan(self.p,actual,'deserialize',self.standard_type)
                if plan['complete'] and plan['constructor']['kind'] in ('implicit','generated'):targets=[]
        local_union = False
        if len(targets) > 1:
            selected = self.choose(reason + ':dispatch', targets)
            if selected is not None:
                targets = [selected]
            else:
                local_union = True
        result = U
        result_kinds=[]
        contexts={target:self.generic_call_context(target,node)[:2] for target in targets}
        receiver=self.declared_type(text(node.child_by_field_name('type'))) if name=='<init>' else self.source_type(objnode) if objnode is not None else self.receiver_type
        def invoke_alternative(target, owned, values):
            actual_args,actual_obj=values
            if isinstance(actual_obj,JavaRecord) and 'static' not in self.method_modifiers(target):
                scope=member_scope(self.p,receiver,self.p.methods[target]['owner'],self.p.methods[mid])
                source=self.p.ast.get(target)
                if scope is None or scope[1]:
                    if source is None or name=='<init>' or any(n.type in ('assignment_expression','update_expression','method_invocation','object_creation_expression') for n in walk(source)):
                        self.mark_raw_record(actual_obj,self.p.methods[target]['owner'])
            from .event_values import witness
            arguments=witness(actual_args)
            try:value=self.invoke(target,actual_args,actual_obj,reason,contexts[target],argument_kinds)
            finally:
                if self.last_invoke_started and self.source_call_visible():self.add(mid,'calls',target,reason,arguments)
            result_kinds.append(self.last_invoke_kind)
            return value,None
        if local_union:
            result,control=self.fork_join(targets,env,[args,obj],invoke_alternative)
            if control=='throw':raise JavaThrow(result)
        else:
            for index,target in enumerate(targets):
                value,_=invoke_alternative(target,env,[args,obj])
                result=value if index==0 else merge(result,value)
        if wiring.get('data_access') and not any(not self.p.methods[target].get('abstract') for target in targets):
            return self.repository(mid, cs, args, sorted(wiring['data_access']), reason)
        remote = sorted(wiring.get('remote_call', set()) | wiring.get('message_delivery', set()))
        http_verb = (args[1] if name=='exchange' and len(args)>1 and isinstance(args[1],str) else
                     'GET' if name in ('getForObject','getForEntity') else
                     'POST' if name in ('postForObject','postForEntity') else None)
        url=args[0] if args else None
        client_type=self.source_type(objnode) or receiver_type
        is_http_client=(not targets and name in ('exchange','getForEntity','postForEntity','getForObject','postForObject')
                        and any(self.standard_type(client_type or '',fqn) for fqn in
                                ('org.springframework.web.client.RestTemplate','org.springframework.web.client.RestOperations')))
        if is_http_client and (isinstance(url,str) or is_symbolic(url)):
            url=self.expand_http_template(url,args,name,reason)
        address=self.request_address(url) if remote or is_http_client else None
        if isinstance(url,dict) and any(isinstance(part,dict) and part.get('__java_date_text__') for part in url.get('__text_parts__',[])):
            self.approximate=True
            self.warnings.add('Date URL path assumes a standard time zone abbreviation without path delimiters: '+reason)
        if not remote and is_http_client and address and address['hostname'] and address['segments'] is not None:
            remote = sorted(m for m in self.p.ix.handlers_for(http_verb, address['segments'], address['hostname'])
                            if self.p.enabled_type(self.p.methods[m]['owner']))
        if remote:
            if address and address['hostname'] and address['segments'] is not None:
                matched = {m for m in self.p.ix.handlers_for(http_verb, address['segments'], address['hostname'])
                           if self.p.enabled_type(self.p.methods[m]['owner'])}
                if http_verb is None:
                    self.approximate = True
                    self.warnings.add('unknown HTTP method: '+reason)
                remote = sorted(matched)
                if not remote:
                    self.approximate = True
                    self.warnings.add('known HTTP URL has no matching source handler: ' + reason)
            else:
                self.approximate = True
                self.warnings.add('remote target is approximated from static wiring: ' + reason)
            results = []
            request = args[2] if name == 'exchange' and len(args) > 2 else args[1] if name.startswith('post') and len(args) > 1 else None
            headers=header_values(request.get('headers',U)) if http_entity(request) else {}
            body = unwrap(request) if http_entity(request) else request if name.startswith('post') else None if request is None else U
            original_body=body
            if isinstance(original_body,(dict,list,JsonText)) and isinstance(headers,dict) and 'content-type' not in headers:
                headers={**headers,'content-type':['application/json']}
            try:body=self.json_wire(body,reason)
            except JavaThrow as failure:
                if isinstance(failure.value,dict) and failure.value.get('__serialization_failure__'):
                    self.warnings.add('default HTTP request serialization failed: '+reason)
                    raise JavaThrow({'__type__':'HttpMessageNotWritableException'})
                raise
            if isinstance(original_body,JavaEnumValue) and body is not U:body=JsonText(body)
            def remote_alternative(target, owned, values):
                url, headers, body, args = values
                address = self.request_address(url)
                if address and address['hostname']:
                    module=self.p.methods[target]['module']
                    declared_names={module,*self.p.ix.units.get(module,())}
                    declared_names.update(str(item['value']) for item in self.p.config
                                          if item.get('module')==module and item['key'].endswith('application.name'))
                    if address['hostname'] not in declared_names:
                        self.approximate=True
                        self.warnings.add('HTTP host resolution uses a module-name heuristic: '+reason)
                remote_request = Request.http(self.p.ix.unit_of(target), http_verb, url, headers, body,
                                              provenance={'source_callsite': reason})
                def on_entry(target_request):
                    if self.p.ix.unit_of(mid)!=self.p.ix.unit_of(target):
                        self.add(mid,'remote',target,reason,{'target_request':target_request,'url':url,'method':http_verb})
                try:response,entered = self.http_invoke(target,
                    lambda: self.bind_request(target,remote_request,reason),reason,remote_request,on_entry)
                except JavaThrow as failure:
                    entered=getattr(failure,'http_entered',False)
                    response={'__type__':'ResponseEntity','__http_entity__':True,'body':U,
                              'status':self.server_error_status(target,failure)}
                status = response.get('status',U) if http_entity(response) else 200
                custom=self.p.ix.unit_of(mid) in self.p.custom_http_error_units
                if custom:
                    self.approximate=True
                    self.warnings.add('custom HTTP error handling is not modeled; return/throw are alternatives: '+reason)
                    rejected=self.choose(reason+':custom-http-error-policy',[True,False])
                    if rejected is True:raise JavaThrow(U)
                    if rejected is None:
                        self.fallback(mid)
                        response=U
                elif status is U:
                    self.approximate = True
                    self.warnings.add('unknown HTTP response status: '+reason)
                    rejected=self.choose(reason+':unknown-http-status-error',[True,False])
                    if rejected is True:raise JavaThrow(U)
                    if rejected is None:self.fallback(mid)
                elif status >= 400:
                    raise JavaThrow({'__type__':'HttpClientErrorException' if status<500 else 'HttpServerErrorException','status':status})
                try:payload=self.json_wire(unwrap(response),reason)
                except JavaThrow as failure:
                    if isinstance(failure.value,dict) and failure.value.get('__serialization_failure__'):
                        self.warnings.add('default HTTP JSON serialization failed on cyclic object graph: '+reason)
                        raise JavaThrow({'__type__':'HttpServerErrorException','status':500})
                    raise
                class_index=3 if name=='exchange' else 2 if name.startswith('post') else 1
                token=args[class_index] if len(args)>class_index else None
                allowed=('Class','ParameterizedTypeReference') if name=='exchange' else ('Class',)
                response_type=token.written if isinstance(token,JavaTypeToken) and token.kind in allowed else None
                type_context=token.context if response_type is not None else self.p.methods[mid]
                native_string=response_type is not None and self.standard_type(response_type,'java.lang.String',type_context)
                if native_string and type(payload) in (int,bool):payload=str(payload).lower()
                elif native_string and (type(payload) is float or is_symbolic(payload) and payload.get('__type__') not in ('String','java.lang.String')):
                    payload=JsonText(payload)
                if native_string and (isinstance(payload,(dict,list)) or isinstance(unwrap(response),JavaEnumValue)) and not isinstance(payload,JsonText) and not (type(payload) is dict and '__symbol__' in payload):
                    payload=JsonText(payload)
                elif not native_string and isinstance(payload,JsonText):
                    payload=payload.payload
                if response_type and not native_string:
                    def unresolved_json(message):
                        self.approximate=True
                        self.warnings.add(message+': '+reason)
                        self.operation_issues[('http_json_binding',message)]+=1
                    payload=decode_response(self.p,payload,response_type,type_context,self.standard_type,unresolved_json,
                                            lifecycle=BeanLifecycle(self,reason))
                if response_type is None:
                    self.json_issue('HTTP response type descriptor is not modeled',reason)
                    payload=U
                return {'payload': payload, 'status': status, 'native_string': native_string, 'body_kind': self.declared_kind(response_type,type_context) if response_type else None}, None
            if len(remote) > 1:
                selected = self.choose(reason + ':remote', remote)
                if selected is not None:remote = [selected]
            if len(remote) > 1:
                response, control = self.fork_join(remote, env, [url, headers, body, args], remote_alternative)
                if control == 'throw':raise JavaThrow(response)
            elif remote:
                response, _ = remote_alternative(remote[0], env, [url, headers, body, args])
            else:
                return U
            value = response.get('payload', U) if isinstance(response, dict) else U
            status = response.get('status', U) if isinstance(response, dict) else U
            body_kind=response.get('body_kind') if isinstance(response,dict) else None
            if name in ('getForObject','postForObject') and (isinstance(value,(str,JsonText)) or isinstance(response,dict) and response.get('native_string') is True):
                self.remember_reference_kind('String')
                body_kind='String'
            elif name in ('getForObject','postForObject'):self.remember_reference_kind(body_kind)
            return {'__type__': 'ResponseEntity', '__http_entity__': True, '__body_kind__':body_kind, 'body': value, 'status': status} if name in ('exchange', 'getForEntity', 'postForEntity') else value
        if name == '<init>':
            scope=member_scope(self.p,self.declared_type(typ),tid,self.p.methods[mid]) if tid else None
            if scope is not None and scope[1]:self.mark_raw_record(obj,tid)
            return obj
        if not targets:
            arguments=[child for child in argnode.named_children if child.type not in ('line_comment','block_comment')]
            handled,value=native_list_call(self,name,obj,args,argument_kinds,arguments,node,reason)
            if handled:return value
        if not targets and isinstance(obj,list) and name in ('contains','indexOf') and len(args)==1:
            return self.collection_membership(obj,args[0],name,reason,argument_kinds[0])
        if not targets and name=='getClass' and not args and isinstance(obj,dict) and (isinstance(obj,JavaRecord) or type(obj) is dict and obj.get('__type__')):
            if isinstance(obj,JavaRecord) and not isinstance(obj,JavaObject):
                self.approximate=True
                self.warnings.add('DTO declared type does not prove its exact runtime class: '+reason)
                return U
            actual=obj.java_type if isinstance(obj,JavaObject) else obj['__type__']
            tid=self.p.resolve_type(actual,self.p.methods[mid]['module'],self.p.methods[mid]['file'])
            return {'__java_class__':self.p.nodes[tid]['fqn'] if tid else actual}
        if not targets and name=='equals' and len(args)==1 and isinstance(obj,JavaObject):
            owner=self.p.resolve_type(obj.java_type,self.p.methods[mid]['module'],self.p.methods[mid]['file'])
            pending,seen=[owner],set()
            while pending:
                current=pending.pop()
                if current in seen:continue
                seen.add(current)
                node=self.p.nodes.get(current,{})
                generated=any(a['name'].split('.')[-1] in ('Data','EqualsAndHashCode','Value') for a in node.get('annotations',[]))
                parents=self.p.framework_types.get(current,set())
                if generated or any(parent not in ('Object','java.lang.Object') and not self.p.resolve_type(parent,node.get('module'),node.get('file')) for parent in parents):
                    self.approximate=True
                    self.warnings.add('project or generated Object.equals implementation is unresolved: '+reason)
                    return U
                pending.extend(parent for parent in self.p.type_parents.get(current,[]) if parent not in seen)
            equal=reference_equal(obj,args[0])
            if equal is U:
                self.approximate=True
                self.warnings.add('Object.equals reference identity is unresolved: '+reason)
            return equal
        if not targets:
            handled, value = self.stream_call(name, obj, args, text(objnode), reason, env,
                                              self.stream_element_type(objnode) if name=='stream' else '')
            if handled:
                return value
        if not targets and isinstance(obj,JavaTypeFactory):
            if name=='constructParametricType' and len(args)>=2 and all(isinstance(arg,JavaTypeToken) and arg.kind=='Class' and arg.context==args[0].context for arg in args):
                return JavaTypeToken(args[0].written+'<'+','.join(arg.written for arg in args[1:])+'>',args[0].context,'JavaType')
            self.json_issue('JSON type factory overload or type context is not modeled',reason)
            return U
        if not targets and isinstance(obj,JavaJsonMapper):
            issue=lambda message:self.json_issue(message,reason)
            if name=='equals' and len(args)==1:
                equal=reference_equal(obj,args[0])
                if equal is U:issue('JSON mapper reference identity is unresolved')
                return equal
            if name=='getClass' and not args:return {'__java_class__':'com.fasterxml.jackson.databind.ObjectMapper'}
            handled,result=codec_operation(obj,name,args,issue)
            if handled:return result
            value=codec_conversion(obj,name,args,self.p,self.standard_type,issue,BeanLifecycle(self,reason,True))
            if isinstance(value,(str,JsonText)):self.remember_reference_kind('String')
            return value
        if not targets and isinstance(obj,JacksonFeature):
            if name=='equals' and len(args)==1:
                equal=reference_equal(obj,args[0])
                if equal is U:self.json_issue('JSON feature enum reference identity is unresolved',reason)
                return equal
            if name=='name' and not args:return obj.name
            self.json_issue('JSON feature enum operation is not modeled: '+name,reason)
            return U
        if not targets and name in ('writeValueAsString','readValue','convertValue','getTypeFactory'):
            self.json_issue('JSON mapper ownership or configuration is not proven',reason)
            return U
        if not targets and isinstance(obj,JsonText):
            if name=='toString' and not args:return obj
            if name=='equals' and len(args)==1 and obj is args[0]:return True
            self.json_issue('JSON text scalar operation is not modeled: '+name,reason)
            return U
        if not targets and isinstance(obj,JavaEnumValue) and name=='equals' and len(args)==1:
            equal=reference_equal(obj,args[0])
            if equal is U:self.json_issue('enum reference identity is unresolved',reason)
            return equal
        if not targets and name=='equals' and isinstance(obj,JavaRecord):
            self.approximate=True
            self.warnings.add('DTO reference equality requires concrete runtime identity: '+reason)
            return U
        if not targets and self.opaque(obj):
            self.approximate=True
            self.warnings.add('escaped collection state is unknown: '+reason)
            return U
        key_type=None
        value_type=None
        if isinstance(obj,(JavaMap,JavaMapView,JavaMapEntry,JavaMapIterator)) and args:
            first=next(child for child in argnode.named_children if child.type not in ('line_comment','block_comment'))
            key_type=self.map_key_type(first)
            if argument_kinds:key_type=argument_kinds[0] or 'unresolved'
            nodes=[child for child in argnode.named_children if child.type not in ('line_comment','block_comment')]
            if name=='put' and len(nodes)==2:
                value_type=self.map_key_type(nodes[1])
                value_type=argument_kinds[1] or 'unresolved'
            elif isinstance(obj,(JavaMapView,JavaMapEntry)):value_type=self.map_key_type(first)
        handled, value = library(name, obj, args, text(objnode), self.state.now,key_type=key_type,
                                 json_issue=lambda message:self.json_issue(message,reason),value_type=value_type,
                                 choose=lambda label,options:self.choose_map_order(reason+':'+label,options)) if not targets else (False, U)
        if handled:
            if value is U and isinstance(obj,Decimal):
                self.approximate=True
                self.warnings.add('BigDecimal operation precision or argument class is not modeled: '+reason)
                self.operation_issues[('numeric_library_boundary',name)]+=1
            if optional_value(obj) and name=='orElse':
                self.remember_reference_kind(argument_kinds[0] if obj['optional'] is None and argument_kinds else obj.get('__optional_kind__',NO_KIND))
            if name=='asList' and self.standard_type(text(objnode),'java.util.Arrays') and isinstance(value,list):
                source_nodes=[c for c in argnode.named_children if c.type not in ('line_comment','block_comment')]
                if len(args)==1 and compiled_type(self,source_nodes[0]).endswith('[]'):
                    component=compiled_type(self,source_nodes[0])[:-2]
                    if component in PRIMITIVES:value=JavaList([args[0]],[None])
                    elif isinstance(args[0],JavaArray):value=ArrayListView(args[0])
                    else:
                        self.approximate=True
                        self.warnings.add('Arrays.asList array backing and runtime component type are not fully modeled: '+reason)
                        value=JavaList(value,[self.declared_kind(component)]*len(value))
                else:value=JavaList(args,argument_kinds)
                value.fixed_size=True
                value.flavor='Arrays.ArrayList'
            if name=='split' and isinstance(obj,str) and receiver_kind=='String' and isinstance(value,list):
                value=JavaArray(value,'java.lang.String',['String']*len(value))
            if type(value) is dict and '__symbol__' in value and value.get('__type__') in ('String','java.lang.String'):
                self.remember_reference_kind('String')
            if name in ('toString','format') and not isinstance(obj,(JavaMap,JavaMapEntry,JavaMapView,JavaMapIterator)):
                self.remember_reference_kind('String')
            if isinstance(obj,datetime) and name=='getTime' or name=='currentTimeMillis' and text(objnode) in ('System','java.lang.System'):
                self.remember_reference_kind('Long')
            if name in ('intValue','doubleValue') and isinstance(obj,(Decimal,int,float)):
                self.remember_reference_kind('Integer' if name=='intValue' else 'Double')
            if isinstance(obj,JavaMap) and name=='get' and len(args)==1:
                key=key_spec(args[0],key_type)
                slot=obj.slot(key) if key is not None else None
                actual=slot.get('value_kind') if isinstance(slot,dict) else None
                self.remember_reference_kind(actual)
                value=self.native_read_cast(value,actual,node,reason)
            if value is not U and value is not None and not args and (
                    isinstance(obj,JavaMapEntry) and name in ('getKey','getValue') or
                    isinstance(obj,JavaMapIterator) and name=='next' and obj.view.kind!='entries'):
                mapping=obj.backing if isinstance(obj,JavaMapEntry) else obj.view.backing
                slot=mapping.slot(obj.key if isinstance(obj,JavaMapEntry) else obj.last)
                key_result=name=='getKey' or isinstance(obj,JavaMapIterator) and obj.view.kind=='keys'
                actual=slot.get('kind' if key_result else 'value_kind') if isinstance(slot,dict) else None
                self.remember_reference_kind(actual)
                value=self.native_read_cast(value,actual,node,reason)
            if isinstance(obj,(JavaMap,JavaMapView,JavaMapEntry,JavaMapIterator)) and value is U:
                self.approximate=True
                self.warnings.add('Java Map operation remains unresolved: '+name+' at '+reason)
                kind=obj.last_issue or 'unknown_map_value'
                self.operation_issues[(kind,name)]+=1
            if type(obj) is dict and obj.get('__type__') in ('SimpleDateFormat','DecimalFormat') and name in ('format','parse'):
                self.approximate=True
                self.warnings.add('formatter default locale/time zone not supplied; numeric date fields and dot decimal symbols modeled: '+reason)
            return value
        if targets:
            actual=result_kinds[0] if result_kinds and len(set(result_kinds))==1 else None
            if actual is NO_KIND:actual=self.source_reference_kind(node)
            self.remember_reference_kind(actual)
            projected=compiled_type(self,node)
            erased={declaration_erasure(self,self.p.methods[target].get('return_raw',''),method=target) for target in targets}
            if projected and erased!={declaration_erasure(self,projected)}:
                result=self.native_read_cast(result,actual,node,reason)
            return result
        if not args and isinstance(obj,JavaRecord) and any(info.get('record_component') for info in self.p.type_fields.get(
                getattr(obj,'source_owner',None) or self.p.resolve_type(obj.declared_type,self.p.methods[mid]['module']),{}).values()):
            owner=getattr(obj,'source_owner',None) or self.p.resolve_type(obj.declared_type,self.p.methods[mid]['module'])
            accessor=generated_accessor(self.p,owner,name,0,self.standard_type)
            if accessor:
                return self.field_read(node,obj,accessor['member'],self.p.type_fields[owner][accessor['member']])
        if name.startswith(('get', 'is')) and not args:
            prop = name[3:] if name.startswith('get') else name[2:]
            prop = prop[:1].lower() + prop[1:]
            if isinstance(obj, dict):
                from .persistence import load
                load(self,obj,prop,reason)
                if prop=='body' and http_entity(obj):self.remember_reference_kind(obj.get('__body_kind__'))
                if isinstance(obj,JavaRecord):
                    owner=self.p.resolve_type(self.source_qualifier_type(node),self.p.methods[mid]['module'],self.p.methods[mid]['file'])
                    generated=generated_accessor(self.p,owner,name,0,self.standard_type)
                    if generated:prop=generated['member'];owner=generated['owner']
                    info=self.p.type_fields.get(owner,{}).get(prop)
                    if info:return self.field_read(node,obj,prop,info)
                value = member(obj, prop)
                if value is not U:
                    return value
        if name.startswith('set') and len(args) == 1 and isinstance(obj, dict):
            prop = name[3:4].lower() + name[4:]
            if isinstance(obj,JavaRecord):
                owner=self.p.resolve_type(self.source_qualifier_type(node),self.p.methods[mid]['module'],self.p.methods[mid]['file'])
                generated=generated_accessor(self.p,owner,name,1,self.standard_type)
                if generated:
                    prop=generated['member'];owner=generated['owner']
                    if generated['non_null'] and args[0] is None:raise JavaThrow({'__type__':'NullPointerException'})
                info=self.p.type_fields.get(owner,{}).get(prop)
                if info:
                    argument=next(child for child in argnode.named_children if child.type not in ('line_comment','block_comment'))
                    provided=self.source_type(argument)
                    value=self.generic_binding(args[0],self.source_member_type(self.source_qualifier_type(node),info),provided)
                    self.lvalue_write(self.field_slot(node,obj,prop),value,argument_kinds[0],provided)
                    return None
            obj[prop] = args[0]
            return None
        if result is not U:
            return result
        if name in ('orElseThrow','get') and optional_value(obj):
            value = member(obj, 'optional')
            if '__repository_presence__' in obj:
                from .repository_values import presence
                present=presence(self,obj,reason)
                if present is True:return value
                if present is False:value=None
            self.remember_reference_kind(obj.get('__optional_kind__',NO_KIND))
            if value is not U and value is not None:
                return value
            if value is U:
                self.approximate = True
                self.warnings.add('unknown Optional presence: '+reason)
                empty = self.choose(reason+':optional-empty',[True,False])
                if empty is False:return U
                if empty is None:self.fallback(self.method)
            for arg in args:
                if isinstance(arg, tuple) and arg[0] == 'lambda':
                    exception = self.callback_value(arg,[])
                    raise JavaThrow({'__type__':'NullPointerException'} if exception is None else exception)
            if args:
                if args[0] is None:raise JavaThrow({'__type__':'NullPointerException'})
                self.approximate=True
                self.warnings.add('unsupported exception supplier: '+reason)
                raise JavaThrow(U)
            raise JavaThrow({'__type__':'NoSuchElementException'})
        if name in ('ifPresent','ifPresentOrElse') and optional_value(obj) and args:
            value=obj['optional']
            optional_types=type_parts(self.source_type(objnode))[1]
            element=optional_types[0] if optional_types and len(optional_types)==1 else ''
            def visit(present,owned,values):
                actual,callbacks=values
                if present:self.callback_value(callbacks[0],[actual],element,[None])
                elif len(callbacks)>1:self.callback_value(callbacks[1],[])
                return None,None
            present=value is not None if value is not U else self.choose(reason+':Optional presence',[False,True])
            if present is None:
                result,control=self.fork_join([False,True],env,[value,args],visit)
                if control=='throw':raise JavaThrow(result)
            else:visit(present,env,[value,args])
            return None
        if name in ('isPresent','isEmpty') and optional_value(obj) and '__repository_presence__' in obj:
            from .repository_values import presence
            present=presence(self,obj,reason)
            return present if name=='isPresent' or present is U else not present
        if name == 'isPresent' and optional_value(obj):
            val = member(obj, 'optional')
            return val is not None if val is not U else U
        if name in ('isEmpty', 'isBlank'):
            value = args[0] if args else obj
            if name == 'isBlank' and isinstance(value, str):
                from .java_strings import is_blank
                return is_blank(value)
            return value is None or value == '' or value == [] if value is not U else U
        if name in ('equals', 'equalsIgnoreCase') and args:
            if name=='equals' and (receiver_kind is not None or argument_kinds[0] is not None):
                equal=boxed_equal(obj,args[0],receiver_kind,argument_kinds[0],key_equal)
                if equal is U:
                    self.approximate=True
                    self.warnings.add('boxed equals runtime classes or values are unresolved: '+reason)
                return equal
            return (obj == args[0] if name == 'equals' else str(obj).lower() == str(args[0]).lower()) if known(obj) and known(args[0]) else U
        if name == 'startsWith' and args and isinstance(obj, str) and isinstance(args[0], str):
            return obj.startswith(args[0])
        if name == 'toString':
            self.remember_reference_kind('String')
            return str(obj) if isinstance(obj, (str, int, float)) else U
        if name=='fromString' and not self.source_type(objnode) and self.standard_type(text(objnode),'java.util.UUID') and args:
            converted=uuid_value(args[0])
            if converted is not U:return converted
        if name=='parseInt' and not self.source_type(objnode) and self.standard_type(text(objnode),'java.lang.Integer'):
            if len(args) not in (1,2):
                self.approximate=True
                self.warnings.add('unsupported Integer.parseInt overload: '+reason)
                return U
            value=parse_integer(*args)
            if value is U:
                self.approximate=True
                self.warnings.add('Integer.parseInt value, radix or Unicode digit rules are unresolved: '+reason)
                valid=self.choose(reason+':parse-int-valid',[True,False])
                if valid is False:raise JavaThrow({'__type__':'NumberFormatException'})
                if valid is None:self.fallback(mid)
            return value
        if name in ('parseDouble', 'parseFloat') and args and args[0] is not U:
            if name=='parseFloat':
                self.approximate=True;self.warnings.add('float scalar promotion or parse rounding is not modeled: '+reason);return U
            try:
                return int(args[0]) if name == 'parseInt' else float(args[0]) if name in ('parseDouble', 'parseFloat') else args[0]
            except (ValueError, TypeError):
                return U
        if name == 'size' and isinstance(obj, list):
            return len(obj)
        if name == 'get' and isinstance(obj, list) and args and isinstance(args[0], int):
            if not 0<=args[0]<len(obj):raise JavaThrow({'__type__':'IndexOutOfBoundsException'})
            actual=obj.kinds[args[0]] if isinstance(obj,JavaList) else None
            return self.native_read_cast(obj[args[0]],actual,node,reason)
        if name in ('add', 'addAll') and isinstance(obj, list) and args:
            if isinstance(obj,JavaList):
                if name=='addAll' and isinstance(args[0],list):obj.extend(args[0]);return bool(args[0])
                if name=='add' and len(args)==1:obj.append(args[0],argument_kinds[0]);return True
                if name=='add' and len(args)==2 and type(args[0]) is int:
                    if not 0<=args[0]<=len(obj):raise JavaThrow({'__type__':'IndexOutOfBoundsException'})
                    obj.insert(args[0],args[1],argument_kinds[1]);return None
            else:
                self.approximate=True
                self.warnings.add('native collection mutation lacks element storage provenance: '+reason)
                obj.extend(args[0] if name=='addAll' and isinstance(args[0],list) else [args[0]])
                return True
        if name=='set' and isinstance(obj,JavaList) and len(args)==2 and type(args[0]) is int:
            index=args[0]
            if not 0<=index<len(obj):raise JavaThrow({'__type__':'IndexOutOfBoundsException'})
            previous,kind=obj[index],obj.kinds[index]
            obj.set_value(index,args[1],argument_kinds[1])
            return self.native_read_cast(previous,kind,node,reason)
        if name == 'randomUUID':
            if not self.source_type(objnode) and self.standard_type(text(objnode),'java.util.UUID'):
                return self.state.generated_value('UUID','java.util.UUID.randomUUID')
        declared=self.source_type(objnode)
        if name in ('print','println') and text(objnode) in ('System.out','System.err') and self.standard_type('System','java.lang.System'):
            return None
        self.approximate = True
        self.warnings.add('unsupported call: ' + reason + ' ' + name)
        kind=('unknown_receiver' if obj is U and declared else 'unresolved_external_type' if obj is U
              else 'unresolved_source_method' if isinstance(obj,JavaObject)
              else 'unsupported_collection_operation' if isinstance(obj,list)
              else 'unresolved_object_model' if isinstance(obj,dict) else 'unsupported_library_operation')
        self.operation_issues[(kind,name)]+=1
        from .call_effects import apply_unknown
        return apply_unknown(self,name,obj,args,env,declared,reason)

    def slf4j_call(self,contract,logger,args,reason,env):
        """SLF4J MessageFormatter callbacks; argument expressions ran already.

        The provider transport is a declared native boundary. Source logger
        implementations still dispatch normally before reaching this contract.
        """
        if logger is None:raise JavaThrow({'__type__':'NullPointerException'})
        self.warnings.add('SLF4J native contract: provider transport failures are not modeled; source formatting callbacks and their caught throwables are modeled')
        values=list(args[1:])
        if values and isinstance(values[-1],dict):
            thrown=exception_type(values[-1])
            if isinstance(thrown,str) and assignable(thrown,'java.lang.Throwable',self.p) is True:values.pop()
        pattern=args[0]
        count=len(re.findall(r'(?<!\\)(?:\\\\)*\{\}',pattern)) if isinstance(pattern,str) else len(values)
        values=values[:count]
        if len(values)==1 and isinstance(values[0],JavaArray):values=list(values[0])[:count]
        def callbacks(value,seen=None):
            seen=set() if seen is None else seen
            if id(value) in seen:return []
            seen.add(id(value))
            if isinstance(value,(list,JavaArray)):
                return [item for child in value for item in callbacks(child,seen)]
            if isinstance(value,JavaRecord):
                owner=self.p.resolve_type(value.declared_type,self.p.methods[self.method]['module'],self.p.methods[self.method]['file'])
                targets=[target for target in self.p.inherited_methods(owner,'toString',0) if not self.p.methods[target].get('abstract')]
                if len(targets)==1:return [(targets[0],value)]
            return []
        if not any(callbacks(value) for value in values):return None
        policy=self.state.context.get('logging',{})
        enabled=policy.get('enabled',U) if isinstance(policy,dict) else U
        if isinstance(enabled,dict):enabled=enabled.get(contract.name,U)
        def format_values(active,owned,actual_values):
            if active:
                for argument in actual_values:
                    for target,value in callbacks(argument):
                        try:self.invoke(target,[],value,reason+' SLF4J formatting callback')
                        except JavaThrow:pass # MessageFormatter.safeObjectAppend catches Throwable.
                        finally:
                            if self.last_invoke_started:self.add(self.method,'calls',target,reason+' SLF4J formatting callback')
            return None,None
        if type(enabled) is bool:format_values(enabled,env,values)
        else:
            self.approximate=True
            self.warnings.add('SLF4J enabled level is unknown; enabled and disabled formatting effects are joined: '+reason)
            self.fork_join([False,True],env,values,format_values)
        return None

    def choose_map_order(self,reason,options):
        self.approximate=True
        self.warnings.add('Map iteration or removal order is unspecified: '+reason)
        self.operation_issues[('unordered_map_iteration',reason.rsplit(':',1)[-1])]+=1
        return self.choose(reason,options)

    def widen_map_iteration(self,env,reason):
        self.approximate=True
        self.warnings.add('Map iteration budget or contents remain unresolved: '+reason)
        self.operation_issues[('unknown_map_iteration','foreach')]+=1
        for value in owned_objects(env):widen(value)
        self.fallback(self.method)

    def view_items(self,view,env,reason):
        iterator=JavaMapIterator(view)
        if not isinstance(iterator.remaining,list):
            self.widen_map_iteration(env,reason);return
        count=len(iterator.remaining)
        for _ in range(min(count,64)):
            value=iterator_next(iterator,lambda label,options:self.choose_map_order(reason+':'+label,options))
            if iterator.last_issue:
                self.widen_map_iteration(env,reason);return
            slot=view.backing.slot(iterator.last)
            kind=slot.get('kind') if view.kind=='keys' else slot.get('value_kind') if view.kind=='values' else None
            yield value,kind
        if count>64:self.widen_map_iteration(env,reason)

    def commuting_map_copy(self,node,view,env):
        """Summarize only disjoint native writes dst.put(k, source.get(k))."""
        if not isinstance(view,JavaMapView) or view.kind!='keys':return False
        source=view.backing
        if not isinstance(source.mapping,dict) or source.flavor not in ('HashMap','LinkedHashMap'):return False
        body=node.child_by_field_name('body')
        if body.type=='block':
            statements=[child for child in body.named_children if child.type not in ('line_comment','block_comment')]
            if len(statements)!=1:return False
            body=statements[0]
        if body.type!='expression_statement' or len(body.named_children)!=1:return False
        put=body.named_children[0]
        if put.type!='method_invocation' or text(put.child_by_field_name('name'))!='put':return False
        receiver=put.child_by_field_name('object')
        arguments=put.child_by_field_name('arguments')
        if receiver is None or receiver.type!='identifier' or arguments is None:return False
        args=[child for child in arguments.named_children if child.type not in ('line_comment','block_comment')]
        name=text(node.child_by_field_name('name'))
        if len(args)!=2 or args[0].type!='identifier' or text(args[0])!=name:return False
        get=args[1]
        if get.type!='method_invocation' or text(get.child_by_field_name('name'))!='get':return False
        origin=get.child_by_field_name('object');lookup=get.child_by_field_name('arguments')
        if origin is None or origin.type!='identifier' or env.get(text(origin)) is not source or lookup is None:return False
        keys=[child for child in lookup.named_children if child.type not in ('line_comment','block_comment')]
        if len(keys)!=1 or keys[0].type!='identifier' or text(keys[0])!=name:return False
        destination=env.get(text(receiver))
        if not isinstance(destination,JavaMap) or not isinstance(destination.mapping,dict) or destination.flavor not in ('HashMap','LinkedHashMap'):return False
        kind=self.native_scalar_type(text(node.child_by_field_name('type')))
        entries=source.entries()
        # No implicit conversion, custom equality, abrupt completion or writes
        # through the iteration variable may be hidden by this proof.
        if not kind or kind[:1].islower() or len(entries)>10000:return False
        if any(entry['kind']!=kind or type(entry['key']) not in (str,int,bool) for entry in entries):return False
        slots=[destination.slot(entry) for entry in entries]
        if any(slot is U for slot in slots):return False
        new_keys=sum(slot is None for slot in slots)
        if not isinstance(source.order,list) and new_keys>1:destination.order=U
        for entry in entries:
            destination.put({'kind':entry['kind'],'key':entry['key']},entry['value'],entry.get('value_kind'))
        return True

    def collection_membership(self,items,value,name,reason,value_kind=None):
        unknown=False
        for index,item in enumerate(items):
            equal=U
            if isinstance(value,dict) and '__type__' in value and '__symbol__' not in value:
                tid=self.p.resolve_type(value.declared_type if isinstance(value,JavaRecord) else value['__type__'],self.p.methods[self.method]['module'],self.p.methods[self.method]['file'])
                pending,seen=[tid],set()
                targets=[]
                while pending and not targets:
                    targets=[mid for mid in self.p.by_name.get('equals',[]) if self.p.methods[mid]['owner'] in pending
                             and self.p.methods[mid].get('params_as_written',[]) in (['Object'],['java.lang.Object'])
                             and not self.p.methods[mid].get('abstract')]
                    seen.update(pending)
                    pending=sorted({parent for owner in pending for parent in self.p.type_parents.get(owner,[]) if parent not in seen})
                if len(targets)==1:
                    equal=self.invoke(targets[0],[item],value,'Java collection equals callback at '+reason)
                else:
                    annotations=self.p.nodes.get(tid,{}).get('annotations',[])
                    has_generated=any(a['name'].split('.')[-1] in ('Data','EqualsAndHashCode') for a in annotations)
                    source=self.p.sources.get(self.p.nodes.get(tid,{}).get('file'),b'').decode()
                    generated=(has_generated and not any(a['name'].split('.')[-1]=='EqualsAndHashCode' and a.get('args') for a in annotations)
                               and not re.search(r'EqualsAndHashCode\.(?:Include|Exclude)',source))
                    if generated and not self.p.type_parents.get(tid):equal=key_equal(value,item)
                    elif value is item:equal=True
                    elif not has_generated and not targets and key_equal(value,item) is False:equal=False
            elif value is None:equal=item is None if item is not U else U
            elif not isinstance(value,dict) or '__symbol__' in value:
                actual=items.kinds[index] if isinstance(items,JavaList) else None
                equal=boxed_equal(value,item,value_kind,actual,key_equal)
            if equal is U:
                unknown=True
                self.approximate=True
                self.warnings.add('collection equality is not fully known: '+reason)
            elif equal is True:
                return True if name=='contains' else U if unknown else index
        return U if unknown else False if name=='contains' else -1

    def stream_call(self, name, obj, args, receiver, reason, env,element_type=''):
        """Sequential lazy filter/map pipelines over a known ordered collection."""
        if name == 'stream' and isinstance(obj, list) and not args:
            return True, {'__stream__': obj, 'operations': [], 'linked': False, 'lifecycle': {'consumed': False},'element_type':element_type}
        if name == 'toList' and not args and receiver in ('Collectors', 'java.util.stream.Collectors'):
            meta = self.p.methods[self.method]
            source = text(self.p.trees[meta['file']].root_node)
            imported = bool(re.search(r'\bimport\s+java\.util\.stream\.(?:Collectors|\*)\s*;', source))
            shadowed = receiver in env or self.p.resolve_type(receiver, meta['module'], meta['file'])
            if not shadowed and (receiver.startswith('java.') or imported):
                return True, {'__collector__': 'java.util.stream.Collectors.toList'}
        if type(obj) is not dict or '__stream__' not in obj:
            return False, U
        if obj['lifecycle']['consumed'] or obj['linked']:
            self.approximate = True
            self.warnings.add('stream reused after consumption: ' + reason)
            return True, U
        if name in ('filter', 'map') and len(args) == 1 and isinstance(args[0], tuple) and args[0][0] in ('lambda','method_reference'):
            obj['linked'] = True
            incoming=obj.get('element_type','')
            outgoing=self.callback_return_type(args[0],incoming) if name=='map' else incoming
            return True, {**obj, 'linked': False, 'operations': [*obj['operations'], (name, args[0],incoming)],'element_type':outgoing}
        if name != 'collect' or args != [{'__collector__': 'java.util.stream.Collectors.toList'}]:
            self.approximate = True
            self.warnings.add('unsupported stream operation: ' + reason + ' ' + name)
            return True, U
        obj['lifecycle']['consumed'] = True
        if len(obj['__stream__'])>1 and not getattr(obj['__stream__'],'order_known',True):
            raise AnalysisBoundary('stream encounter order needs isolated callback continuations: '+reason,category='unsupported_semantics')
        if len(obj['__stream__']) > 10000:
            self.warnings.add('stream collection budget exceeded: ' + reason)
            self.fallback(self.method)
            return True, U
        output = JavaList()
        source=obj['__stream__'];length=len(source)
        version=source.structural_version if isinstance(source,JavaList) else None
        for index in range(length):
            item=source[index]
            kind=source.kinds[index] if isinstance(source,JavaList) else None
            keep = True
            for operation, callback, input_type in obj['operations']:
                value = self.callback_value(callback, [item],input_type,[kind],
                                            'java.lang.Object' if operation=='map' else 'boolean')
                if operation == 'map':
                    item = value
                    kind=self.last_callback_kind
                    continue
                if type(value) is not bool:
                    value = self.choose(reason + ':stream-filter', [True, False])
                    if value is None:
                        self.warnings.add('unknown stream membership: ' + reason)
                        self.fallback(self.method)
                        return True, U
                if not value:
                    keep = False
                    break
            if keep:
                output.append(item,kind)
            if isinstance(source,JavaList) and (source.opaque or source.structural_version!=version):
                if index==length-1 and source.flavor=='ArrayList' and not source.opaque and version is not None:
                    raise JavaThrow({'__type__':'ConcurrentModificationException'})
                self.approximate=True
                self.warnings.add('stream interference before remaining callbacks is not fully modeled: '+reason)
                self.fallback(self.method)
                raise JavaThrow(U)
        return True, output

    def callback_parameter_types(self,node,inferred):
        parameters=node.child_by_field_name('parameters')
        if parameters is None:return {}
        if parameters.type=='identifier':return {text(parameters):inferred} if inferred else {}
        result={text(par.child_by_field_name('name')):text(par.child_by_field_name('type'))
                for par in parameters.named_children if par.type=='formal_parameter'}
        if not result and inferred and len(parameters.named_children)==1:
            result[text(parameters.named_children[0])]=inferred
        return result

    def callback_return_type(self,callback,inferred):
        node,_,owner,types=callback[1:5]
        previous,previous_types=self.method,self.variable_types
        previous_bindings,previous_receiver=self.source_bindings,self.receiver_type
        previous_return_kind=self.current_return_kind
        self.method,self.variable_types=owner,{**types,**self.callback_parameter_types(node,inferred)}
        self.source_bindings,self.receiver_type=callback[5:] if len(callback)==7 else ({},'')
        try:
            if callback[0]=='method_reference':
                qualifier,_,name=text(node).rpartition('::')
                if name=='new':return self.declared_type(qualifier) or qualifier
                return ''
            body=node.child_by_field_name('body')
            if body.type!='block':return self.scalar_or_source_type(self.source_type(body))
            def returns(current):
                if current.type in ('lambda_expression','class_body','method_declaration'):return
                if current.type=='return_statement' and current.named_children:
                    yield self.scalar_or_source_type(self.source_type(current.named_children[0]))
                else:
                    for child in current.named_children:yield from returns(child)
            types=set(returns(body))
            return next(iter(types)) if len(types)==1 else ''
        finally:
            self.method,self.variable_types=previous,previous_types
            self.source_bindings,self.receiver_type=previous_bindings,previous_receiver
            self.current_return_kind=previous_return_kind

    def callback_value(self, callback, arguments,inferred='',argument_kinds=None,return_type='java.lang.Object'):
        if callback[0]=='method_reference':return self.method_reference_value(callback,arguments,inferred,argument_kinds)
        node, captured, owner, types = callback[1:5]
        parameters = node.child_by_field_name('parameters')
        names = ([text(parameters)] if parameters is not None and parameters.type == 'identifier' else
                 [text(child.child_by_field_name('name') or child) for child in parameters.named_children]
                 if parameters is not None else [])
        if len(names) != len(arguments):
            self.approximate = True
            self.warnings.add('unsupported callback parameters: ' + text(node))
            return U
        local = JavaFrame(captured,getattr(captured,'kinds',{}))
        previous, previous_types = self.method, self.variable_types
        previous_bindings,previous_receiver=self.source_bindings,self.receiver_type
        previous_return_kind=self.current_return_kind
        previous_return_type=self.return_type_override
        self.current_return_kind=NO_KIND
        self.return_type_override=return_type
        self.method, self.variable_types = owner, dict(types)
        self.source_bindings,self.receiver_type=callback[5:] if len(callback)==7 else ({},'')
        self.variable_types.update(self.callback_parameter_types(node,inferred))
        returned_kind=None
        try:
            for index,(name,value) in enumerate(zip(names,arguments)):
                actual=argument_kinds[index] if argument_kinds is not None else None
                written=self.variable_types.get(name,'')
                value=self.reference_check(value,actual,declaration_erasure(self,written),text(node),'unresolved_callback_cast','parameter')
                value,actual=self.assignment_value(value,actual,written,None)
                local.set_value(name,value,actual)
            body = node.child_by_field_name('body')
            if body.type != 'block':
                value=self.value(body,local)
                actual=self.source_reference_kind(body,self.last_reference_kind)
                value,returned_kind=self.assignment_value(value,actual,return_type,body)
                return value
            value, control = self.execute(body, local)
            if control == 'throw':
                raise JavaThrow(value)
            returned_kind=self.current_return_kind if control=='return' else None
            return value if control == 'return' else U
        finally:
            self.method, self.variable_types = previous, previous_types
            self.source_bindings,self.receiver_type=previous_bindings,previous_receiver
            self.current_return_kind=previous_return_kind
            self.return_type_override=previous_return_type
            self.last_callback_kind=returned_kind

    def expand_http_template(self,url,args,name,reason):
        variables=args[4 if name=='exchange' else 3 if name.startswith('post') else 2:]
        mapping=variables[0].mapping if len(variables)==1 and isinstance(variables[0],JavaMap) else None
        if mapping is not None and not isinstance(mapping,dict):
            self.approximate=True
            self.warnings.add('unresolved Java Map URI variables: '+reason)
            return U
        configuration=self.p.__dict__.setdefault('_custom_uri_template_units',None)
        if configuration is None:
            configuration={self.p.ix.unit_of(site['method']) for site in self.p.nodes.values()
                           if site.get('kind')=='call_site' and site.get('callee') in ('setUriTemplateHandler','setEncodingMode','setParsePath','setDefaultUriVariables')
                           and site.get('method') in self.p.methods}
            self.p._custom_uri_template_units=configuration
        if self.p.ix.unit_of(self.method) in configuration:
            self.approximate=True
            self.warnings.add('custom URI template handler or encoding mode is not modeled: '+reason)
            return U
        if isinstance(url,str) and ('{' in re.sub(r'\{([A-Za-z_]\w*)\}','',url) or '}' in re.sub(r'\{([A-Za-z_]\w*)\}','',url)):
            self.approximate=True
            self.warnings.add('unsupported URI template syntax: '+reason)
            return U
        position=0
        def lookup(key):
            nonlocal position
            if mapping is not None and key not in mapping or mapping is None and position>=len(variables):
                raise JavaThrow({'__type__':'IllegalArgumentException'})
            value=mapping[key] if mapping is not None else variables[position]
            position+=1
            return value
        def unknown():
            self.approximate=True
            self.warnings.add('unresolved URI template value: '+reason)
            return {'__symbol__':self.constraint_symbol(),'__type__':'String'}
        return client_template(url,lookup,unknown)

    request_address = staticmethod(request_address)

    def route_path_values(self,target,address):
        if not address or address['segments'] is None:return None
        segments=address['segments']
        for mid, _, template in self.p.ix.handlers:
            if mid == target and len(template) == len(segments) and all(
                    key.startswith('{') or key in ('*', '**') or key == val for key, val in zip(template, segments)):
                if any(key.startswith('{') and ':' in key for key in template):
                    self.approximate=True
                    self.warnings.add('request route regular-expression constraints are not fully modeled: '+target)
                return {key[1:-1].split(':',1)[0]:deepcopy(value)
                        for key,value in zip(template,segments) if key.startswith('{')}
        return None

    def path_parameters(self, target, url):
        # Raw values for source grounding; actual HTTP conversion is deferred
        # until filters have admitted the request.
        address=self.request_address(url)
        values=self.route_path_values(target,address)
        if values is None:return {}
        path=dict(values)
        for par in self.p.http_parameters(target):
            if par['kind']=='PathVariable' and par['wire_name'] in path:
                values[par['name']]=path[par['wire_name']]
            elif par['kind']=='RequestParam':
                found=address['query'].get(par['wire_name']) if address['query_complete'] else U
                if found is U:values[par['name']]=U
                elif found is None or found==['']:
                    if par['default'] is not U:values[par['name']]=par['default']
                    elif found is None and not par['required']:values[par['name']]=None
                    elif found==['']:values[par['name']]=''
                else:values[par['name']]=found[0] if len(found)==1 else found
        return values

    def request_arguments(self,target,url,headers,body,reason):
        request=Request.http(self.p.ix.unit_of(target),U,url,headers,body,
                             provenance={'source_callsite':reason})
        return self.bind_request(target,request,reason)

    def bind_request(self,target,request,reason):
        from .http_contracts import check_request
        check_request(self,target,request)
        url,headers,body=request.url,request.headers,request.body
        address={'segments':[thaw(part) for part in request.path] if request.path is not None else None,
                 'query':thaw(request.query),'query_complete':request.query_complete}
        path=self.route_path_values(target,address)
        parameters={p['name']:p for p in self.p.http_parameters(target)}
        values=[]
        for name,typ in self.p.parameters(target):
            parameter=parameters.get(name,{})
            kind=parameter.get('kind')
            if http_headers_type(typ):
                value={'__type__':'HttpHeaders','__http_headers__':True,'headers':deepcopy(headers)}
            elif self.standard_type(typ,'java.security.Principal',self.p.methods[target]):
                session=thaw(request.session)
                principal=session.get('principal',U) if isinstance(session,dict) else U
                value=({'__type__':'java.security.Principal',**deepcopy(principal)} if isinstance(principal,dict) else None if principal is None else U)
            elif kind in ('PathVariable','RequestParam','RequestHeader'):
                wire_name=parameter['wire_name']
                if kind=='PathVariable':found=U if path is None else [path[wire_name]] if wire_name in path else None
                elif kind=='RequestParam':
                    found=address['query'].get(wire_name) if address and address['query_complete'] else U
                    media=headers.get('content-type',[]) if isinstance(headers,dict) else U
                    if body is not None and (media is U or any('form' in value or 'multipart' in value for value in media if isinstance(value,str))):
                        found=U
                else:
                    found=headers.get(wire_name.lower(),U if headers.get('__rest_unknown__') else None) if isinstance(headers,dict) else U
                value=bind_named(self,target,parameter,found)
            elif kind=='RequestBody':
                if body is MISSING or body is None:
                    if parameter['required']:
                        raise BindingFailure('missing required RequestBody: '+name)
                    value=None
                else:value=self.bind_http_body(body,typ,target,reason,thaw(request.body_properties).get(name,{}))
            else:
                value=body.payload if typ.split('.')[-1]!='String' and isinstance(body,JsonText) else body
                target_type=self.p.resolve_type(typ,self.p.methods[target]['module'],self.p.methods[target]['file'])
                if target_type in self.p.type_fields and isinstance(value,dict) and '__symbol__' not in value:
                    value={**self.p.request_body_defaults(target),**deepcopy(value)}
                    if '__type__' not in self.p.type_fields[target_type]:value['__type__']=self.p.nodes[target_type]['fqn']
                    if '__http_entity__' not in self.p.type_fields[target_type]:value['__http_entity__']=False
                    value=JavaRecord(self.p.nodes[target_type]['fqn'],value,self.p.type_fields[target_type])
                    value.source_owner=target_type
            values.append(value)
        return values

    def method_reference_value(self,callback,arguments,inferred,argument_kinds):
        from tree_sitter import Language,Parser
        import tree_sitter_java
        node,captured,owner,types=callback[1:5]
        qualifier,_,name=text(node).rpartition('::')
        names=['__reference_argument_'+str(index) for index in range(len(arguments))]
        expression=('new '+qualifier if name=='new' else qualifier+'.'+name)+'('+','.join(names)+')'
        cache=self.p.__dict__.setdefault('_method_reference_nodes',{})
        if expression not in cache:
            tree=Parser(Language(tree_sitter_java.language())).parse(('class Reference {Object value(){return '+expression+';}}').encode())
            cache[expression]=next(child for child in walk(tree.root_node) if child.type=='return_statement').named_children[0]
        previous=(self.method,self.variable_types,self.source_bindings,self.receiver_type)
        self.method=owner;self.variable_types={**types,**{key:inferred for key in names}}
        self.source_bindings,self.receiver_type=callback[5:] if len(callback)==7 else ({},'')
        env=JavaFrame(captured,getattr(captured,'kinds',{}))
        for index,(key,value) in enumerate(zip(names,arguments)):
            env.set_value(key,value,argument_kinds[index] if argument_kinds else None)
        try:
            value=self.call(cache[expression],env,synthetic=True)
            self.last_callback_kind=self.source_reference_kind(cache[expression],self.last_reference_kind)
            return value
        finally:self.method,self.variable_types,self.source_bindings,self.receiver_type=previous

    def repository(self, mid, cs, args, resources, reason):
        from . import persistence
        result = U
        primary=persistence.primary_resources(self,cs.get('receiver_type'))
        for rid in resources:
            if primary and rid not in primary:
                self.candidate_edges.add((mid,'data',rid))
                continue
            name = cs.get('callee', '')
            if self.p.nodes[rid].get('collection_of'):
                self.candidate_edges.add((mid,'data',rid))
                continue
            query_key = (cs.get('receiver_type'), name)
            if not name.startswith(('save','insert','delete','find','query','get','read','exists','count')) and name != 'flush' and query_key not in self.p.repository_queries:
                self.candidate_edges.add((mid,'data',rid))
                self.approximate=True
                self.warnings.add('repository wiring has no supported SQL operation: '+reason)
                continue
            if name in ('getReferenceById','getById','getOne') and args:
                result = persistence.lazy(self,rid,args[0])
                if result is U:
                    self.approximate=True;self.warnings.add('lazy entity identity is not modeled: '+reason)
                continue
            tx = persistence.transaction(self)
            if name == 'flush':
                persistence.flush(self,reason)
                result = None
                continue
            if name == 'findById' and args and tx:
                existing = persistence.cached(self,rid,args[0])
                if existing is not U:
                    declared_owner=self.p.resolve_type(cs.get('receiver_type',''),self.p.methods[mid]['module'],self.p.methods[mid]['file'])
                    returns=[method.get('return_raw','') for method in self.p.methods.values()
                             if method['owner']==declared_owner and method['name']==name]
                    result = {'__optional__': True, 'optional': existing} if not returns or 'Optional' in returns[0] else existing
                    continue
            operation = {'method': mid, 'resource': rid, 'operation': name,
                         'arguments': deepcopy(args), 'source_site': reason,
                         'uncertain_write': bool(self.uncertain)}
            from .java_sets import shapes
            shape=shapes(args,'arguments')
            if shape:operation['collection_shapes']=shape
            if name.startswith(('save','insert','delete')):
                persistence.queue(self,operation)
            else:
                if tx:persistence.flush(self,reason)
                persistence.sql(self,operation)
            resource = self.p.nodes[rid]
            rows = self.state.database.rows(resource)
            if rows is None or resource.get('collection_of'):
                self.approximate = True
                self.warnings.add('ORM access is approximated from static mapping: ' + rid)
                from .repository_values import unknown_result
                result=unknown_result(self,cs)
                continue
            entity = self.p.entities.get(rid)
            if name.startswith(('save', 'insert', 'delete')):
                assumptions = self.input_assumptions + self.execution_assumptions
                if assumptions:
                    self.state.resource_assumptions[rid] = sorted(set(self.state.resource_assumptions.get(rid, []) + assumptions))
            else:
                self.execution_assumptions = list(dict.fromkeys(self.execution_assumptions +
                    self.state.resource_assumptions.get(rid, []) + self.state.unscoped_state_assumptions))
            if name.startswith(('save', 'insert')) and args and isinstance(args[0], dict):
                record = deepcopy(args[0])
                if self.uncertain:
                    self.warnings.add('possible database write not committed: ' + reason)
                    self.state.database.invalidate(rows)
                    result=U
                    continue
                else:
                    generated = self.p.generated_ids.get(rid)
                    if generated and record.get(generated, U) in (U, None):
                        field=self.p.type_fields.get(entity,{}).get(generated,{})
                        record[generated] = self.state.generated_value(field.get('type','Object'),'ORM generated identifier',
                                                                       [row.get(generated,U) for row in rows])
                        if field.get('uuid_generated') and field.get('type','').split('.')[-1]=='String':
                            record[generated].update(__uuid_text__=True,__length__=36,
                                                     __generation__='org.hibernate.id.UUIDGenerator')
                        args[0][generated] = record[generated]
                        if isinstance(args[0],JavaRecord):
                            args[0]._native_field_kinds={**getattr(args[0],'_native_field_kinds',{}),generated:self.declared_kind(field.get('type','Object'))}
                    keys = self.p.id_fields.get(rid, [])
                    key = tuple(record.get(k, U) for k in keys) if keys else U
                    existing = next((r for r in rows if key is not U and U not in key and all(self.p.materialize(self.state.database, rid, r).get(k, U) == record.get(k, U) for k in keys)), None)
                    if existing is None and keys and any(key_equal({k:self.p.materialize(self.state.database,rid,r).get(k,U) for k in keys},
                                                                 {k:record.get(k,U) for k in keys}) is U for r in rows):
                        self.approximate=True
                        self.warnings.add('opaque primary-key upsert overlap is not modeled; abstract write identity retained: '+reason)
                    if existing is None:
                        rows.append(record)
                        self.created_objects.append({**deepcopy(record), '__resource__': rid,
                                                     '__type__': self.p.nodes[entity]['fqn'] if entity else record.get('__type__', '')})
                    else:
                        existing.update(record)
                result = persistence.manage(self,rid,args[0] if existing is None else record)
                if name == 'saveAndFlush':persistence.flush(self,reason)
                continue
            selected = [self.p.materialize(self.state.database, rid, r) for r in rows]
            find = re.search(r'(?:find|query|get|delete|exists).*?By(.+)', name)
            unknown_query = False
            query_key = (cs.get('receiver_type'), name)
            declared_query = query_key in self.p.repository_queries
            query = self.p.repository_queries.get(query_key)
            primary_keys = self.p.id_fields.get(rid, [])
            pairs = []
            comparisons = []
            if declared_query:
                if query is None or any(int(index) > len(args) or int(index) < 1 for _, _, index in query):
                    unknown_query = True
                else:
                    from .state import camel
                    pairs = [(camel(field) + ('In' if op.lower() == 'in' else ''), args[int(index)-1])
                             for field, op, index in query if op.lower() in ('=','in')]
                    comparisons = [(camel(field),op,args[int(index)-1]) for field,op,index in query if op.lower() not in ('=','in')]
            elif name == 'findAllById' and args and isinstance(args[0], list):
                if len(primary_keys) == 1:
                    selected = [r for r in selected if r.get(primary_keys[0]) in args[0]]
                else:
                    unknown_query = True
            elif find:
                fields = re.split('And', find[1])
                pairs = [(field, value) for field, value in zip(fields, args)]
                if len(fields) != len(args):
                    unknown_query = True
                if name in ('findById', 'getById', 'getReferenceById', 'existsById', 'deleteById') and len(primary_keys) == 1 and args:
                    pairs = [(primary_keys[0], args[0])]
            elif name not in ('findAll', 'count'):
                unknown_query = True
            for field, value in pairs:
                in_query = field.endswith('In')
                field = field[:-2] if in_query else field
                prop = field[:1].lower() + field[1:]
                symbolic_query = is_symbolic(value)
                if not known(value) and not symbolic_query:
                    unknown_query = True
                else:
                    def matches(row):
                        nonlocal unknown_query
                        stored = member(row, prop)
                        if declared_query and (stored is None or value is None):
                            return False
                        if symbolic_query or isinstance(stored, dict) and '__symbol__' in stored:
                            equal = key_equal(stored, value)
                            if equal is U:
                                unknown_query = True
                            return equal is not False
                        if not known(stored):
                            unknown_query = True
                            return True
                        if isinstance(stored, dict) and isinstance(value, dict):
                            equal = key_equal(stored, value)
                            if equal is U: unknown_query = True
                            return equal is not False
                        return stored in value if in_query and isinstance(value, list) else stored == value
                    selected = [r for r in selected if matches(r)]
            for field,op,value in comparisons:
                kept=[]
                for row in selected:
                    stored=member(row,field)
                    # A SQL comparison involving NULL is never TRUE in WHERE.
                    if stored is None or value is None:
                        continue
                    numeric=all(type(item) in (int,float) and math.isfinite(item) for item in (stored,value))
                    if not numeric:
                        unknown_query=True
                        kept.append(row)
                        continue
                    passed={'>':operator.gt,'>=':operator.ge,'<':operator.lt,'<=':operator.le,'!=':operator.ne,'<>':operator.ne}[op](stored,value)
                    if passed:kept.append(row)
                selected=kept
            if (unknown_query and not declared_query and len(primary_keys)==1 and args and
                    name in ('findById','getById','getReferenceById','existsById')):
                exact=[row for row in selected if key_equal(member(row,primary_keys[0]),args[0]) is True]
                # A declared primary key is unique in a valid database state.
                # One exact symbolic identity excludes all other row identities.
                if len(exact)==1:selected,unknown_query=exact,False
            if unknown_query and not selected and ((declared_query and query is not None)
                    or not declared_query and find and len(pairs)==len(args)):
                unknown_query=False
            if unknown_query:
                self.approximate = True
                self.warnings.add('repository predicate is not fully modeled: ' + reason)
            if name.startswith('delete'):
                if not self.uncertain and not unknown_query:
                    if primary_keys:
                        removed = [tuple(row.get(key, U) for key in primary_keys) for row in selected]
                        rows[:] = [row for row in rows if tuple(self.p.materialize(self.state.database, rid, row).get(key, U)
                                                               for key in primary_keys) not in removed]
                    else:
                        self.approximate = True
                        self.warnings.add('deletion without an identifiable primary key: ' + reason)
                else:
                    self.warnings.add('possible deletion not committed: ' + reason)
                    self.state.database.invalidate(rows)
                result = None
                continue
            if name == 'count':
                result = len(rows); continue
            if name.startswith('exists'):
                result = U if unknown_query else bool(selected)
                continue
            materialized = JavaList()
            for row in selected:
                record = {'__type__': self.p.nodes[entity]['fqn'] if entity else '', **deepcopy(row)}
                if entity:
                    record=persistence.materialize_record(self,entity,record,reason)
                    record=persistence.attach_collections(self,rid,record,reason)
                materialized.append(persistence.manage(self,rid,record))
            if unknown_query:
                from .repository_values import unknown_result
                result = unknown_result(self,cs)
                continue
            # Repository declarations are indexed even though their bodies are abstract.
            declared_owner=self.p.resolve_type(cs.get('receiver_type',''),self.p.methods[mid]['module'],self.p.methods[mid]['file'])
            declared = [m.get('return_raw', '') for m in self.p.methods.values()
                        if m['name'] == name and m['owner']==declared_owner]
            return_type = declared[0] if declared else ('Optional' if name == 'findById' else '')
            first = materialized[0] if materialized else None
            result = {'__optional__': True, 'optional': first} if 'Optional' in return_type else materialized if any(t in return_type for t in ('List', 'Set', 'Collection')) or name == 'findAll' else first
        return result
