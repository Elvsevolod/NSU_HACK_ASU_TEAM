"""Bounded abstract interpretation of Java source, with explicit unknown values.

Only source text is interpreted. This module never loads JVM classes or contacts
the application's services. Unresolved branches retain both possible paths.
"""
from collections import defaultdict,Counter
from copy import deepcopy
import json
import operator
import math
import re
from urllib.parse import urlsplit, parse_qsl, unquote

from .project import text,walk
from .state import U
from .models import construct, library, known, unwrap, wire, key_equal, http_entity, optional_value, status_code, header_values
from .constraints import assume, compare
from .java_exceptions import JavaThrow, assignable
from .symbolic_text import concat_text, http_text_parts
from .models import java_date_text, uuid_value, http_headers_type
from .java_collections import JavaObject, JavaRecord, JavaMap, JavaEnumValue, JavaTypeToken, JavaTypeFactory, JsonObject, JsonText, reference_equal, is_symbolic
from .java_numbers import parse_integer
from .http_json import decode_response,type_parts
from .map_keys import same_key
from datetime import datetime


def member(obj, key):
    if not isinstance(obj, dict):
        return U
    if key in obj:
        return obj[key]
    normalized = re.sub(r'[^a-z0-9]', '', key.lower())
    return next((v for k, v in obj.items() if re.sub(r'[^a-z0-9]', '', k.lower()) == normalized), U)


def exception_type(value):
    return value.java_type if isinstance(value,JavaObject) else value.get('__type__',U) if type(value) is dict else U


def merge(a, b, active=None):
    if a is b:return a
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
            fields={key:merge(a.get(key,U),b.get(key,U),active) for key in sorted(a.keys()|b.keys())}
            wire_fields=a.wire_fields|b.wire_fields
            if isinstance(a,JavaObject) and isinstance(b,JavaObject):
                identity=a.java_identity if a.java_identity is b.java_identity else None
                return JavaObject(a.java_type,fields,identity,wire_fields)
            return JavaRecord(a.declared_type,fields,wire_fields)
        if isinstance(a,JavaMap) or isinstance(b,JavaMap):
            if not isinstance(a,JavaMap) or not isinstance(b,JavaMap):return U
            identity=a.java_identity if a.java_identity is b.java_identity else None
            if (not isinstance(a.mapping,dict) or not isinstance(b.mapping,dict) or a.mapping.keys()!=b.mapping.keys()
                    or len(a.typed_entries)!=len(b.typed_entries)
                    or any(same_key(left,right) is not True for left,right in zip(a.typed_entries,b.typed_entries))):
                return JavaMap(U,identity)
            typed=[{**left,'value':merge(left['value'],right['value'],active)} for left,right in zip(a.typed_entries,b.typed_entries)]
            origin=a.origin_type if a.origin_type==b.origin_type else None
            return JavaMap({key:merge(value,b.mapping[key],active) for key,value in a.mapping.items()},identity,typed,origin)
        if isinstance(a,JsonText) or isinstance(b,JsonText):
            return JsonText(merge(a.payload,b.payload,active)) if isinstance(a,JsonText) and isinstance(b,JsonText) else U
        if isinstance(a,JsonObject) or isinstance(b,JsonObject):
            if not isinstance(a,JsonObject) or not isinstance(b,JsonObject):return U
            fields={key:merge(a.get(key,U),b.get(key,U),active) for key in a.keys()|b.keys()}
            return JsonObject(fields,a.origin_type if a.origin_type==b.origin_type else None)
        if isinstance(a, dict) and isinstance(b, dict):
            return {key: merge(a.get(key, U), b.get(key, U),active) for key in sorted(a.keys() | b.keys(), key=lambda k: (type(k).__name__, str(k)))}
        if isinstance(a,list) and isinstance(b,list):
            if len(a)!=len(b):return U
            joined=[merge(left,right,active) for left,right in zip(a,b)]
            return a if joined==a and joined==b else U
        if type(a) is type(b) and a == b:return a
        return U
    finally:
        active.remove(pair)


class AlternativeRequired(Exception):
    def __init__(self, key, choices):
        self.key, self.choices = key, choices


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
        self.params = {}
        self.uncertain = 0
        self.decisions = decisions or {}
        self.conservative = conservative
        self.branch_index = 0
        self.approximate = False
        self.outcome = 'returned' 
        self.use_constraints = constraints
        self.variable_types = {}
        self.constraint_sequence = 0
        self.filter_frames = []
        self.operation_issues=Counter()

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

    def add(self, source, relation, target, reason):
        self.edges.add((source, relation, target))
        self.evidence[(source, relation, target)].add(reason)

    def executed(self, mid, reason):
        self.add('', 'executes', mid, reason)

    def json_issue(self,message,reason):
        self.approximate=True
        self.warnings.add(message+': '+reason)
        self.operation_issues[('http_json_binding',message)]+=1

    def json_wire(self,value,reason):
        return wire(value,lambda message:self.json_issue(message,reason),self.p.json_model_limits)

    def run(self, entry, params):
        self.params = params
        self.entry = entry
        try:
            args = [self.input_value(name, typ, params) for name, typ in self.p.parameters(entry)]
            result,_ = self.http_invoke(entry, args, 'scenario request')
            if any(entry==handler for handler,_,_ in self.p.ix.handlers):
                try:self.json_wire(unwrap(result),entry)
                except JavaThrow as failure:
                    if isinstance(failure.value,dict) and failure.value.get('__serialization_failure__'):
                        self.outcome='HTTP serialization failure'
                        self.warnings.add('default HTTP JSON serialization failed on cyclic object graph: '+entry)
                        return U
                    raise
            if http_entity(result) and type(result.get('status')) is int and result['status']>=400:
                self.outcome='HTTP error response'
        except JavaThrow as exc:
            self.outcome = 'uncaught application exception'
            self.warnings.add('uncaught Java exception: '+str(exception_type(exc.value)))
            return U
        return unwrap(result)

    def http_invoke(self,entry,args,reason):
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
        frame = {'entry':entry,'args':args,'filters':filters,'reason':reason,'entered':False,'result':U,
                 'response':response,'request':{'__type__':'HttpServletRequest'}}
        self.filter_frames.append(frame)
        try:
            self.continue_filter(len(self.filter_frames)-1,0)
            if frame['entered']:return frame['result'],True
            if len(self.filter_frames)==1:self.outcome='request stopped by filter'
            return {'__type__':'ResponseEntity','__http_entity__':True,'body':response['body'],'status':response['status']},False
        finally:
            self.filter_frames.pop()

    def continue_filter(self,frame_index,position):
        frame = self.filter_frames[frame_index]
        if position==len(frame['filters']):
            frame['entered']=True
            frame['result']=self.invoke(frame['entry'],frame['args'],reason=frame['reason'])
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

    def input_value(self, name, typ, params):
        if typ.split('.')[-1].lstrip('?')=='HttpHeaders':
            return {'__type__': 'HttpHeaders','__http_headers__':True,'headers':U}
        if name in params:
            target=self.method or getattr(self,'entry','')
            if any(p['name']==name and p['kind']=='RequestBody' for p in self.p.http_parameters(target)):
                if self.standard_type(typ,'java.lang.String',self.p.methods[target]):
                    return deepcopy(params[name]) if isinstance(params[name],JsonText) else self.coerce(params[name],typ)
                return self.bind_http_body(params[name],typ,target,'scenario request')
            return self.coerce(params[name], typ)
        if typ.split('.')[-1] in ('String', 'UUID', 'int', 'double', 'boolean', 'Date', 'Long'):
            return U
        value = {'__type__': typ, **deepcopy(params)}
        method = self.method or getattr(self, 'entry', '')
        meta = self.p.methods.get(method, {})
        tid = self.p.resolve_type(typ, meta.get('module'), meta.get('file'))
        if tid in self.p.type_fields and not typ.startswith('org.springframework.http.'):
            if '__http_entity__' not in self.p.type_fields[tid]:value['__http_entity__'] = False
            value=JavaRecord(self.p.nodes[tid]['fqn'],value,self.p.type_fields[tid])
        return value

    def bind_http_body(self,value,typ,target,reason):
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
        owner=self.p.resolve_type(typ,meta['module'],meta['file'])
        if owner in self.p.type_fields and isinstance(payload,dict) and not is_symbolic(payload):
            payload=JsonObject({**self.p.request_body_defaults(target),**payload},getattr(payload,'origin_type',None))
        return decode_response(self.p,payload,typ,meta,self.standard_type,lambda message:self.json_issue(message,reason))

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

    def invoke(self, mid, args, receiver=None, reason='source call'):
        self.executed(mid, reason)
        meta = self.p.methods[mid]
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
        if transactional:
            self.approximate = True
            self.warnings.add('transaction dirty checking is not fully modeled: ' + mid)
        signature = (mid, json.dumps(args, sort_keys=True, default=str))
        if signature in self.active or self.calls >= 12000 or len(self.active) >= 64:
            self.warnings.add('recursion or context budget: conservative closure used')
            self.fallback(mid)
            return U
        node = self.p.ast.get(mid)
        if node is None:
            self.warnings.add('no source body: ' + mid)
            self.fallback(mid)
            return U
        self.calls += 1
        self.active.add(signature)
        previous = self.method
        previous_types = self.variable_types
        self.method = mid
        self.variable_types = dict(self.p.parameters(mid))
        env = {name: args[i] if i < len(args) else U for i, (name, _) in enumerate(self.p.parameters(mid))}
        env['this'] = receiver if isinstance(receiver, dict) else {}
        body = node.child_by_field_name('body')
        data_start, failed = len(self.data_operations), True
        try:
            try:
                result, control = self.execute(body, env)
            except (TypeError, ValueError, IndexError, KeyError, AttributeError, ZeroDivisionError) as exc:
                self.approximate = True
                self.warnings.add('unsupported value operation in ' + mid + ': ' + type(exc).__name__)
                self.fallback(mid)
                result, control = U, None
            failed = control == 'throw'
        finally:
            if transactional and failed:
                for operation in self.data_operations[data_start:]:
                    rows = self.state.database.rows(self.p.nodes[operation['resource']])
                    if rows is not None:
                        self.state.database.invalidate(rows)
                self.approximate = True
                self.warnings.add('transaction failure: rollback/commit is unknown; touched tables widened: ' + mid)
            self.method = previous
            self.variable_types = previous_types
            self.active.remove(signature)
        if control == 'throw':
            raise JavaThrow(result)
        return result

    def fallback(self, mid):
        self.approximate = True
        methods, calls, remote, data = self.p.ix.closure({mid})
        for method in methods:
            self.executed(method, 'unresolved source: may-call closure')
        for relation, pairs in [('calls', calls), ('remote', remote), ('data', data)]:
            for source, target in pairs:
                self.add(source, relation, target, 'unresolved source: may-call closure')
                if relation == 'data':
                    rows = self.state.database.rows(self.p.nodes[target])
                    if rows is not None:
                        self.state.database.invalidate(rows)

    def execution_fork(self,state):
        # Method execution never mutates completed request observations. Share
        # their payloads, but own the journal list and all mutable execution data.
        return deepcopy(state,{id(state.history):list(state.history)})

    def execute(self, node, env):
        if node is None:
            return U, None
        typ = node.type
        if typ in ('block', 'constructor_body'):
            for child in node.named_children:
                value, control = self.execute(child, env)
                if control:
                    return value, control
            return U, None
        if typ in ('return_statement', 'throw_statement'):
            value = self.value(node.named_children[0], env) if node.named_children else None
            if typ=='throw_statement' and value is None:value={'__type__':'NullPointerException'}
            return value, 'return' if typ == 'return_statement' else 'throw'
        if typ in ('switch_expression','switch_statement'):
            result,control = self.execute_switch(node,env)
            return (U,None) if control=='yield' else (result,control)
        if typ=='yield_statement':
            return self.value(node.named_children[0],env),'yield'
        if typ == 'if_statement':
            cond = self.value(node.child_by_field_name('condition'), env)
            self.conditions.append({'method': self.method, 'line': node.start_point.row + 1,
                                    'condition': text(node.child_by_field_name('condition')),
                                    'value': cond if isinstance(cond, bool) else 'unknown'})
            if isinstance(cond, bool):
                return self.execute(node.child_by_field_name('consequence' if cond else 'alternative'), env)
            decision = self.choose(self.method + ':' + str(node.start_point.row + 1), [True, False])
            if decision is not None:
                if self.use_constraints:
                    refined = assume(node.child_by_field_name('condition'), env, decision,
                                     self.variable_types, self.constraint_symbol)
                    self.conditions[-1]['refined'] = refined
                return self.execute(node.child_by_field_name('consequence' if decision else 'alternative'), env)
            before_state = self.state
            left, right = deepcopy(env), deepcopy(env)
            self.state = self.execution_fork(before_state)
            a, ac = self.execute(node.child_by_field_name('consequence'), left)
            left_state = self.state
            self.state = self.execution_fork(before_state)
            b, bc = self.execute(node.child_by_field_name('alternative'), right)
            right_state = self.state
            self.state = left_state
            # Keep agreed writes; conflicting contents are unavailable to queries.
            self.state.database.unknown_tables.update(left_state.database.unknown_tables | right_state.database.unknown_tables)
            for table in set(left_state.database.tables) | set(right_state.database.tables):
                if left_state.database.tables.get(table) != right_state.database.tables.get(table):
                    self.state.database.unknown_tables.add(table)
            self.state.symbol_sequence=max(left_state.symbol_sequence,right_state.symbol_sequence)
            self.state.input_sequence=max(left_state.input_sequence,right_state.input_sequence)
            env.update(merge(left, right))
            return (merge(a, b), ac) if ac == bc and ac else (U, None)
        if typ == 'enhanced_for_statement':
            values = self.value(node.child_by_field_name('value'), env)
            name = text(node.child_by_field_name('name'))
            items = values if isinstance(values, list) else [U]
            if len(items) > 64:
                self.approximate = True
                self.warnings.add('loop collection widened after 64 elements')
                items = items[:64] + [U]
            for item in items:
                env[name] = item
                result, control = self.execute(node.child_by_field_name('body'), env)
                if control in ('return', 'throw') and isinstance(values, list):
                    return result, control
                if control == 'break': break
            return U, None
        if typ in ('for_statement', 'while_statement', 'do_statement'):
            init = node.child_by_field_name('init')
            if init: self.execute(init, env)
            condnode = node.child_by_field_name('condition')
            for iteration in range(64):
                cond = self.value(condnode, env) if condnode else U
                if cond is False and not (typ == 'do_statement' and iteration == 0): break
                if cond is U:
                    decision = self.choose(self.method + ':loop:' + str(node.start_point.row + 1), [True, False])
                    if decision is False:
                        break
                    if decision is True:
                        cond = True
                    else:
                        self.uncertain += 1
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
                        matches = [assignable(thrown,text(c),self.p) for c in types.named_children]
                        match = True if True in matches else U if U in matches else False
                        if match is U:
                            self.approximate = True
                            self.warnings.add('unknown exception assignability: '+text(types)+' at '+self.method)
                            match = self.choose(self.method+':catch:'+str(child.start_point.row+1),[True,False])
                            if match is None:
                                self.fallback(self.method)
                                break
                        if match:
                            env[text(parameter.child_by_field_name('name'))] = result
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
                    self.variable_types[name] = text(node.child_by_field_name('type'))
                    env[name] = self.value(child.child_by_field_name('value'), env)
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
        if node is None:
            return U
        typ, raw = node.type, text(node)
        if typ == 'identifier':
            return env.get(raw, member(env.get('this'), raw))
        if typ in ('true', 'false'):
            return typ == 'true'
        if typ == 'null_literal':
            return None
        if typ == 'character_literal':
            return raw[1:-1]
        if typ == 'string_literal':
            try:
                return json.loads(raw)
            except ValueError:
                return raw[1:-1]
        if typ in ('decimal_integer_literal', 'decimal_floating_point_literal'):
            try:
                return float(raw.rstrip('fFdD')) if '.' in raw else int(raw.rstrip('lL'))
            except ValueError:
                return U
        if typ == 'this':
            return env.get('this', U)
        if typ == 'parenthesized_expression':
            return self.value(node.named_children[-1], env)
        if typ == 'cast_expression':
            value = self.value(node.named_children[-1], env)
            target = text(node.child_by_field_name('type'))
            if isinstance(value,(str,JsonText)):
                base=target.split('<',1)[0]
                meta=self.p.methods[self.method]
                owner=self.p.resolve_type(base,meta['module'],meta['file'])
                source_incompatible=owner and self.p.nodes[owner]['fqn'] not in ('java.lang.String','java.lang.Object')
                if source_incompatible or any(self.standard_type(base,'java.util.'+name) for name in ('Map','HashMap','LinkedHashMap')):
                    raise JavaThrow({'__type__':'ClassCastException'})
            if isinstance(value,JavaMap):
                meta=self.p.methods[self.method]
                owner=self.p.resolve_type(target,meta['module'],meta['file'])
                allowed=('java.util.Map','java.util.HashMap','java.util.AbstractMap',
                         'java.lang.Object','java.lang.Cloneable','java.io.Serializable')
                if any(self.standard_type(target,typ) for typ in allowed):return value
                if target.endswith('[]') or owner and not self.p.nodes[owner]['fqn'].startswith('java.'):
                    raise JavaThrow({'__type__':'ClassCastException'})
                self.approximate=True
                self.warnings.add('Java Map reference cast is not proven compatible: '+text(node))
                return U
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
            return value
        if typ == 'field_access':
            if raw in self.p.constants: return self.p.constants[raw]
            constants = {'Float.MAX_VALUE': 3.4028235e38, 'Double.MAX_VALUE': 1.7976931348623157e308,
                         'Long.MAX_VALUE': 9223372036854775807, 'Integer.MAX_VALUE': 2147483647}
            if raw in constants: return constants[raw]
            if raw.startswith(('HttpMethod.', 'HttpStatus.', 'Calendar.')):
                return raw.split('.')[-1]
            enum = self.p.enum_reference(raw, self.method)
            if enum:
                return deepcopy(self.p.enum_objects[enum])
            obj = self.value(node.child_by_field_name('object'), env)
            field = text(node.child_by_field_name('field'))
            if obj is None:
                declared=self.source_type(node.child_by_field_name('object'))
                constant=self.p.constants.get(declared.split('.')[-1]+'.'+field,U)
                if constant is not U:return constant
                owner=self.p.resolve_type(declared,self.p.methods[self.method]['module'],self.p.methods[self.method]['file'])
                if field in self.p.type_fields.get(owner,{}) or declared.endswith('[]') and field=='length':
                    raise JavaThrow({'__type__':'NullPointerException'})
                self.approximate=True
                self.warnings.add('unresolved static/instance field access through null: '+raw)
            return len(obj) if isinstance(obj, list) and field == 'length' else member(obj, field)
        if typ == 'unary_expression':
            arg = self.value(node.child_by_field_name('operand') or node.named_children[-1], env)
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
            if (op == '&&' and a is False) or (op == '||' and a is True):
                return a
            b = self.value(node.child_by_field_name('right'), env)
            if op == '&&' and b is False:
                return False
            if op == '||' and b is True:
                return True
            if a is U or b is U:
                return U
            if op in ('==','!=') and any(isinstance(value,(JavaRecord,JavaMap,JavaEnumValue,JavaTypeToken,JavaTypeFactory)) for value in (a,b)):
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
            if op == '+' and (isinstance(a, str) or isinstance(b, str)):
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
            child = node.named_children[0]
            old = self.value(child, env)
            new = old + (1 if '++' in raw else -1) if isinstance(old, (int, float)) else U
            if type(new) is int:new=self.narrow_integer(new,self.numeric_type(child))
            if child.type == 'identifier': env[text(child)] = new
            return new if raw.startswith(('++', '--')) else old
        if typ == 'assignment_expression':
            lhs, rhs = node.child_by_field_name('left'), node.child_by_field_name('right')
            result = self.value(rhs, env)
            op = text(node.child_by_field_name('operator'))
            if op != '=':
                old = self.value(lhs, env)
                try: result = {'+=': operator.add, '-=': operator.sub}[op](old, result)
                except (KeyError, TypeError): result = U
                if type(result) is int:result=self.narrow_integer(result,self.numeric_type(lhs))
            if lhs.type == 'identifier':
                env[text(lhs)] = result
            elif lhs.type == 'field_access':
                obj = self.value(lhs.child_by_field_name('object'), env)
                if obj is None:
                    owner=self.p.resolve_type(self.source_type(lhs.child_by_field_name('object')),self.p.methods[self.method]['module'],self.p.methods[self.method]['file'])
                    if text(lhs.child_by_field_name('field')) in self.p.type_fields.get(owner,{}):
                        raise JavaThrow({'__type__':'NullPointerException'})
                    self.approximate=True
                    self.warnings.add('unresolved static/instance field write through null: '+text(lhs))
                if isinstance(obj, dict):
                    obj[text(lhs.child_by_field_name('field'))] = result
            return result
        if typ == 'ternary_expression':
            c = self.value(node.child_by_field_name('condition'), env)
            if isinstance(c, bool):
                return self.value(node.child_by_field_name('consequence' if c else 'alternative'), env)
            decision = self.choose(self.method + ':ternary:' + str(node.start_point.row + 1), [True, False])
            if decision is not None:
                return self.value(node.child_by_field_name('consequence' if decision else 'alternative'), env)
            self.uncertain += 1
            self.approximate = True
            result = merge(self.value(node.child_by_field_name('consequence'), deepcopy(env)),
                         self.value(node.child_by_field_name('alternative'), deepcopy(env)))
            self.uncertain -= 1
            return result
        if typ in ('switch_expression', 'switch_statement'):
            result,control = self.execute_switch(node,env)
            if control=='throw':raise JavaThrow(result)
            return result if control=='yield' else U
        if typ == 'lambda_expression':
            return ('lambda', node, dict(env), self.method, dict(self.variable_types))
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
            return arr[idx] if isinstance(arr, list) and isinstance(idx, int) and 0 <= idx < len(arr) else U
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
        aliases={'Integer':'int','Long':'long','Short':'short','Byte':'byte','Double':'double','Float':'float'}
        if kind=='decimal_integer_literal':return 'long' if raw.lower().endswith('l') else 'int'
        if kind=='decimal_floating_point_literal':return 'float' if raw.lower().endswith('f') else 'double'
        if kind=='identifier':
            info=self.p.type_fields.get(self.p.methods[self.method]['owner'],{}).get(raw,{})
            typ=self.variable_types.get(raw,info.get('type','')).split('.')[-1]
            return aliases.get(typ,typ)
        if kind in ('parenthesized_expression','unary_expression','update_expression','expression_statement','yield_statement'):
            typ=self.numeric_type(node.named_children[-1])
            return 'int' if kind=='unary_expression' and typ in ('byte','short','char') else typ
        if kind=='cast_expression':return text(node.child_by_field_name('type'))
        if kind=='field_access':
            if raw.startswith(('Integer.','Long.')):return 'int' if raw.startswith('Integer.') else 'long'
            obj=node.child_by_field_name('object');field=text(node.child_by_field_name('field'))
            owner=self.p.methods[self.method]['owner'] if text(obj)=='this' else self.p.resolve_type(self.variable_types.get(text(obj),text(obj)),self.p.methods[self.method]['module'])
            typ=self.p.type_fields.get(owner,{}).get(field,{}).get('type','').split('.')[-1]
            return aliases.get(typ,typ) or ('int' if field=='length' else '')
        if kind=='binary_expression':
            types=[self.numeric_type(node.child_by_field_name(side)) for side in ('left','right')]
            if all(t in ('byte','short','char','int','long','float','double') for t in types):
                return next((t for t in ('double','float','long') if t in types),'int')
        if kind=='method_invocation':
            name=text(node.child_by_field_name('name'))
            inferred=self.source_type(node).split('.')[-1]
            if inferred:return aliases.get(inferred,inferred)
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
        if kind=='this':return self.p.nodes[meta['owner']]['fqn']
        if kind=='identifier':return self.variable_types.get(raw,self.p.type_fields.get(meta['owner'],{}).get(raw,{}).get('type',''))
        if kind=='parenthesized_expression':return self.source_type(node.named_children[-1])
        if kind in ('cast_expression','object_creation_expression'):return text(node.child_by_field_name('type'))
        if kind=='array_access':return self.source_type(node.child_by_field_name('array')).removesuffix('[]')
        if kind not in ('method_invocation','field_access'):return ''
        obj=node.child_by_field_name('object')
        receiver=self.source_type(obj) if obj is not None else self.p.nodes[meta['owner']]['fqn']
        owner=self.p.resolve_type(receiver,meta['module'],meta['file'])
        if kind=='method_invocation':
            site=self.p.site(self.method,node)
            targets=self.p.targets(self.method,site) if site else self.p.source_targets(self.method,node)
            types={self.p.methods[target].get('return_raw','') for target in targets}
            if len(types)==1:return next(iter(types))
            name=text(node.child_by_field_name('name'))
            arguments=node.child_by_field_name('arguments')
            count=len(arguments.named_children) if arguments is not None else 0
            if name=='get' and count==1 and owner is None:
                collection=re.fullmatch(r'(?:java\.util\.)?(?:List|ArrayList|LinkedList)\s*<\s*([\w.]+)\s*>',receiver)
                if collection:return collection[1]
                mapping=re.fullmatch(r'(?:java\.util\.)?(?:Map|HashMap|LinkedHashMap)\s*<\s*[\w.]+\s*,\s*([\w.]+)\s*>',receiver)
                if mapping:return mapping[1]
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
            if info:return info['type']
            pending.extend(self.p.resolve_type(parent,self.p.nodes[current]['module'],self.p.nodes[current]['file'])
                           for parent in self.p.framework_types.get(current,set()))
        return ''

    def narrow_integer(self,value,typ):
        bits={'byte':8,'short':16,'int':32,'long':64}.get(typ)
        if bits:return (value+(1<<(bits-1)))%(1<<bits)-(1<<(bits-1))
        self.approximate=True
        self.warnings.add('unknown Java integer width; numeric result retained as unknown: '+self.method)
        return U

    def standard_type(self,name,fqn,meta=None):
        """A source-proven JDK type, rather than an unrelated namesake."""
        meta=self.p.methods[self.method] if meta is None else meta
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
            key_type={'string_literal':'String','character_literal':'char','true':'boolean','false':'boolean'}.get(nodes[0].type)
            key_type=key_type or self.numeric_type(nodes[0]) or 'unresolved'
            _,result=library('put',mapping,values,'this',self.state.now,key_type=key_type)
            if result is U or any(value is U for value in values):
                self.approximate=True
                self.warnings.add('native Map initializer contains an unresolved key or value: '+reason)
                self.operation_issues[(mapping.last_issue or 'unknown_map_value','initializer.put')]+=1
        return True,mapping

    def call(self, node, env):
        mid = self.method
        site = self.p.site(mid, node)
        cs = self.p.nodes.get(site, {})
        name = '<init>' if node.type == 'object_creation_expression' else text(node.child_by_field_name('name'))
        objnode = node.child_by_field_name('object')
        obj = self.value(objnode, env) if objnode else env.get('this', U)
        argnode = node.child_by_field_name('arguments')
        args = [self.value(child, env) for child in argnode.named_children
                if child.type not in ('line_comment', 'block_comment')] if argnode else []
        reason = site or f"{self.p.methods[mid]['file']}:{node.start_point.row + 1}"
        if name=='doFilter' and type(obj) is dict and '__filter_chain__' in obj:
            self.continue_filter(*obj['__filter_chain__'])
            return None
        if type(obj) is dict and obj.get('__type__')=='HttpServletResponse':
            if name in ('setStatus','sendError') and args:
                obj['status']=status_code(args[0])
                return None
            if name=='getStatus':return obj['status']
        wiring = self.p.edges.get(site, {})
        targets = self.p.targets(mid, site) if site else self.p.source_targets(mid, node)
        if not targets and not wiring.get('data_access'):
            targets=self.p.source_targets(mid,node)
        receiver_type = cs.get('receiver_type')
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
                if targets or name in ('equals','equalsIgnoreCase','toString','length','isEmpty','isBlank','orElseThrow','getForObject','getForEntity','postForObject','postForEntity','exchange'):
                    raise JavaThrow({'__type__':'NullPointerException'})
                self.approximate=True
                self.warnings.add('unresolved static/instance invocation on null: '+reason)
                return U
        if not targets and name == 'builder' and receiver_type in self.p.builder_types:
            fields = self.p.builder_types[receiver_type]
            return {'__builder__': receiver_type, 'fields': {n: False if t == 'boolean' else 0 if t in ('int', 'long', 'double', 'float') else None for n, t in fields}}
        if not targets and type(obj) is dict and '__builder__' in obj:
            if name == 'build': return JavaRecord(obj['__builder__'],{'__type__': obj['__builder__'], **deepcopy(obj['fields'])},obj['fields'])
            if name in obj['fields'] and len(args) == 1:
                obj['fields'][name] = args[0]
                return obj
        if not targets and name == 'values' and not args:
            meta = self.p.methods[mid]
            tid = self.p.resolve_type(text(objnode), meta['module'], meta['file'])
            values = [deepcopy(self.p.enum_objects[key]) for key in self.p.enum_members.get(tid, [])]
            if values: return values
        if not targets and isinstance(obj,JavaEnumValue) and name=='name' and not args:return obj.enum_name
        if not targets and name == 'encode' and receiver_type and 'PasswordEncoder' in receiver_type and args and isinstance(args[0], str):
            # Abstract non-null encoding; no hashing or authentication is executed.
            return 'encoded:' + args[0]
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
                default = info['default']
                if default is U and not info['has_initializer']:
                    default = False if info['type'] == 'boolean' else 0 if info['type'] in ('int', 'long', 'double', 'float', 'short', 'byte') else None
                elif default is U:
                    self.approximate = True
                    self.warnings.add('unsupported instance initializer: ' + str(tid) + '.' + field)
                obj[field] = deepcopy(default)
            if typ.split('.')[-1] == 'UsernamePasswordAuthenticationToken':
                obj.update(principal=args[0] if args else U, credentials=args[1] if len(args) > 1 else U)
            if not tid and re.match(r'(ArrayList|LinkedList|List|HashSet|Set)', typ):
                obj = list(args[0]) if args and isinstance(args[0], list) else []
        if name == '<init>':
            base=typ.split('<')[0]
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
        if len(targets) > 1:
            selected = self.choose(reason + ':dispatch', targets)
            if selected is not None:
                targets = [selected]
            else:
                self.uncertain += 1
        result = U
        for target_index, target in enumerate(targets):
            self.add(mid, 'calls', target, reason)
            value = self.invoke(target, args, obj, reason)
            result = value if target_index == 0 else merge(result, value)
        if wiring.get('data_access'):
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
        if is_http_client and isinstance(url,str) and ('{' in url or '}' in url):
            url=self.expand_http_template(url,args,name,reason)
        address=self.request_address(url) if remote or is_http_client else None
        if isinstance(url,dict) and any(isinstance(part,dict) and part.get('__java_date_text__') for part in url.get('__text_parts__',[])):
            self.approximate=True
            self.warnings.add('Date URL path assumes a standard time zone abbreviation without path delimiters: '+reason)
        if not remote and is_http_client and address and address['hostname']:
            remote = sorted(m for m in self.p.ix.handlers_for(http_verb, address['segments'], address['hostname'])
                            if self.p.enabled_type(self.p.methods[m]['owner']))
        if remote:
            if address and address['hostname']:
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
            try:body=self.json_wire(body,reason)
            except JavaThrow as failure:
                if isinstance(failure.value,dict) and failure.value.get('__serialization_failure__'):
                    self.warnings.add('default HTTP request serialization failed on cyclic object graph: '+reason)
                    raise JavaThrow({'__type__':'HttpMessageNotWritableException'})
                raise
            if isinstance(original_body,JavaEnumValue) and body is not U:body=JsonText(body)
            if len(remote) > 1:
                selected = self.choose(reason + ':remote', remote)
                if selected is not None:
                    remote = [selected]
                else:
                    self.uncertain += 1
            for target in remote:
                if address and address['hostname']:
                    module=self.p.methods[target]['module']
                    declared_names={module,*self.p.ix.units.get(module,())}
                    declared_names.update(str(item['value']) for item in self.p.config
                                          if item.get('module')==module and item['key'].endswith('application.name'))
                    if address['hostname'] not in declared_names:
                        self.approximate=True
                        self.warnings.add('HTTP host resolution uses a module-name heuristic: '+reason)
                values = []
                route_values = self.path_parameters(target, url)
                parameters={parameter['name']:parameter for parameter in self.p.http_parameters(target)}
                for par, typ in self.p.parameters(target):
                    if par in route_values:
                        values.append(self.coerce(route_values[par], typ))
                    elif http_headers_type(typ):
                        values.append({'__type__':'HttpHeaders','__http_headers__':True,'headers':deepcopy(headers)})
                    elif parameters.get(par,{}).get('kind')=='RequestHeader':
                        parameter=parameters[par]
                        found=headers.get(parameter['wire_name'].lower(),U if headers.get('__rest_unknown__') else []) if isinstance(headers,dict) else U
                        if found==[] and parameter['default'] is not U:
                            value=parameter['default']
                        elif found==[] and parameter['required']:
                            self.warnings.add('HTTP binding rejected missing required header: '+parameter['wire_name'])
                            raise JavaThrow({'__type__':'HttpClientErrorException','status':400})
                        elif found==[]:value=None
                        elif isinstance(found,list) and len(found)==1 and isinstance(found[0],str):value=self.coerce(found[0],typ)
                        else:
                            value=U
                            self.approximate=True
                            self.warnings.add('unresolved remote request header: '+parameter['wire_name'])
                        values.append(value)
                    elif parameters.get(par,{}).get('kind') in ('PathVariable','RequestParam'):
                        values.append(U)
                        self.approximate=True
                        self.warnings.add('unresolved remote route parameter: '+par+' at '+reason)
                    elif parameters.get(par,{}).get('kind')=='RequestBody':
                        values.append(self.bind_http_body(body,typ,target,reason))
                    else:
                        decoded=body
                        if typ.split('.')[-1]!='String' and isinstance(decoded,JsonText):
                            decoded=decoded.payload
                        target_type=self.p.resolve_type(typ,self.p.methods[target]['module'],self.p.methods[target]['file'])
                        if target_type in self.p.type_fields and isinstance(decoded,dict) and '__symbol__' not in decoded:
                            decoded={**self.p.request_body_defaults(target),**deepcopy(decoded)}
                            if '__type__' not in self.p.type_fields[target_type]:decoded['__type__']=self.p.nodes[target_type]['fqn']
                            if '__http_entity__' not in self.p.type_fields[target_type]:decoded['__http_entity__']=False
                            decoded=JavaRecord(self.p.nodes[target_type]['fqn'],decoded,self.p.type_fields[target_type])
                        values.append(decoded)
                response,entered = self.http_invoke(target, values, reason)
                if entered and self.p.ix.unit_of(mid)!=self.p.ix.unit_of(target):
                    self.add(mid,'remote',target,reason)
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
                    payload=decode_response(self.p,payload,response_type,type_context,self.standard_type,unresolved_json)
                if response_type is None:
                    self.json_issue('HTTP response type descriptor is not modeled',reason)
                    payload=U
                results.append(payload)
            value = results[0] if len(results) == 1 else U
            return {'__type__': 'ResponseEntity', '__http_entity__': True, 'body': value,'status':status if len(results)==1 else U} if name in ('exchange', 'getForEntity', 'postForEntity') else value
        if name == 'authenticate' and 'AuthenticationManager' in (cs.get('receiver_type') or ''):
            self.authentication(mid, args, reason)
        if name == '<init>':
            return obj
        if not targets and isinstance(obj,list) and name in ('contains','indexOf') and len(args)==1:
            return self.collection_membership(obj,args[0],name,reason)
        if not targets and name=='getClass' and not args and isinstance(obj,dict) and (isinstance(obj,JavaObject) or obj.get('__type__')):
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
            handled, value = self.stream_call(name, obj, args, text(objnode), reason, env)
            if handled:
                return value
        if not targets and isinstance(obj,JavaTypeFactory):
            if name=='constructParametricType' and len(args)>=2 and all(isinstance(arg,JavaTypeToken) and arg.kind=='Class' and arg.context==args[0].context for arg in args):
                return JavaTypeToken(args[0].written+'<'+','.join(arg.written for arg in args[1:])+'>',args[0].context,'JavaType')
            self.json_issue('JSON type factory overload or type context is not modeled',reason)
            return U
        if not targets and name in ('writeValueAsString','readValue','convertValue','getTypeFactory'):
            mapper_type=self.source_type(objnode)
            if not self.standard_type(mapper_type,'com.fasterxml.jackson.databind.ObjectMapper'):
                self.approximate=True
                self.warnings.add('unresolved JSON mapper type: '+reason)
                return U
            if name=='getTypeFactory' and not args:return JavaTypeFactory()
            if name=='writeValueAsString' and len(args)==1:
                return JsonText(self.json_wire(args[0],reason))
            if len(args)==2 and isinstance(args[1],JavaTypeToken) and args[1].kind in ('Class','JavaType','TypeReference') and (name=='convertValue' or isinstance(args[0],JsonText)):
                payload=self.json_wire(args[0],reason) if name=='convertValue' else args[0].payload
                return decode_response(self.p,payload,args[1].written,args[1].context,self.standard_type,
                                       lambda message:self.json_issue(message,reason))
            self.json_issue('JSON mapper overload or text representation is not modeled',reason)
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
        key_type=None
        if isinstance(obj,JavaMap) and args:
            first=next(child for child in argnode.named_children if child.type not in ('line_comment','block_comment'))
            key_type={'string_literal':'String','character_literal':'char','true':'boolean','false':'boolean'}.get(first.type)
            if key_type is None:key_type=self.numeric_type(first) or 'unresolved'
        handled, value = library(name, obj, args, text(objnode), self.state.now,key_type=key_type,
                                 json_issue=lambda message:self.json_issue(message,reason)) if not targets else (False, U)
        if handled:
            if isinstance(obj,JavaMap) and value is U:
                self.approximate=True
                self.warnings.add('Java Map operation remains unresolved: '+name+' at '+reason)
                kind=obj.last_issue or 'unknown_map_value'
                self.operation_issues[(kind,name)]+=1
            if type(obj) is dict and obj.get('__type__') in ('SimpleDateFormat','DecimalFormat') and name in ('format','parse'):
                self.approximate=True
                self.warnings.add('formatter default locale/time zone not supplied; numeric date fields and dot decimal symbols modeled: '+reason)
            return value
        if targets:
            return result
        if name.startswith(('get', 'is')) and not args:
            prop = name[3:] if name.startswith('get') else name[2:]
            prop = prop[:1].lower() + prop[1:]
            if isinstance(obj, dict):
                value = member(obj, prop)
                if value is not U:
                    return value
        if name.startswith('set') and len(args) == 1 and isinstance(obj, dict):
            prop = name[3:4].lower() + name[4:]
            obj[prop] = args[0]
            return None
        if result is not U:
            return result
        if name in ('orElseThrow','get') and optional_value(obj):
            value = member(obj, 'optional')
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
        if name == 'isPresent' and optional_value(obj):
            val = member(obj, 'optional')
            return val is not None if val is not U else U
        if name in ('isEmpty', 'isBlank'):
            value = args[0] if args else obj
            return value is None or value == '' or value == [] if value is not U else U
        if name in ('equals', 'equalsIgnoreCase') and args:
            return (obj == args[0] if name == 'equals' else str(obj).lower() == str(args[0]).lower()) if known(obj) and known(args[0]) else U
        if name == 'startsWith' and args and isinstance(obj, str) and isinstance(args[0], str):
            return obj.startswith(args[0])
        if name == 'toString':
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
            try:
                return int(args[0]) if name == 'parseInt' else float(args[0]) if name in ('parseDouble', 'parseFloat') else args[0]
            except (ValueError, TypeError):
                return U
        if name == 'size' and isinstance(obj, list):
            return len(obj)
        if name == 'get' and isinstance(obj, list) and args and isinstance(args[0], int):
            if not 0<=args[0]<len(obj):raise JavaThrow({'__type__':'IndexOutOfBoundsException'})
            return obj[args[0]]
        if name in ('add', 'addAll') and isinstance(obj, list) and args:
            obj.extend(args[0] if name == 'addAll' and isinstance(args[0], list) else [args[0]])
            return True
        if name == 'randomUUID':
            if not self.source_type(objnode) and self.standard_type(text(objnode),'java.util.UUID'):
                return self.state.generated_value('UUID','java.util.UUID.randomUUID')
        if name not in ('debug', 'info', 'warn', 'error', 'trace', 'println', 'print'):
            self.approximate = True
            self.warnings.add('unsupported call: ' + reason + ' ' + name)
            declared=self.source_type(objnode)
            kind=('unknown_receiver' if obj is U and declared else 'unresolved_external_type' if obj is U
                  else 'unresolved_source_method' if isinstance(obj,JavaObject)
                  else 'unsupported_collection_operation' if isinstance(obj,list)
                  else 'unresolved_object_model' if isinstance(obj,dict) else 'unsupported_library_operation')
            self.operation_issues[(kind,name)]+=1
        return U

    def collection_membership(self,items,value,name,reason):
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
            elif not isinstance(value,dict) or '__symbol__' in value:equal=key_equal(value,item)
            if equal is U:
                unknown=True
                self.approximate=True
                self.warnings.add('collection equality is not fully known: '+reason)
            elif equal is True:
                return True if name=='contains' else U if unknown else index
        return U if unknown else False if name=='contains' else -1

    def stream_call(self, name, obj, args, receiver, reason, env):
        """Sequential lazy filter/map pipelines over a known ordered collection."""
        if name == 'stream' and isinstance(obj, list) and not args:
            return True, {'__stream__': obj, 'operations': [], 'linked': False, 'lifecycle': {'consumed': False}}
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
        if name in ('filter', 'map') and len(args) == 1 and isinstance(args[0], tuple) and args[0][0] == 'lambda':
            obj['linked'] = True
            return True, {**obj, 'linked': False, 'operations': [*obj['operations'], (name, args[0])]}
        if name != 'collect' or args != [{'__collector__': 'java.util.stream.Collectors.toList'}]:
            self.approximate = True
            self.warnings.add('unsupported stream operation: ' + reason + ' ' + name)
            return True, U
        obj['lifecycle']['consumed'] = True
        if len(obj['__stream__']) > 10000:
            self.warnings.add('stream collection budget exceeded: ' + reason)
            self.fallback(self.method)
            return True, U
        output = []
        for item in obj['__stream__']:
            keep = True
            for operation, callback in obj['operations']:
                value = self.callback_value(callback, [item])
                if operation == 'map':
                    item = value
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
                output.append(item)
        return True, output

    def callback_value(self, callback, arguments):
        node, captured, owner, types = callback[1:]
        parameters = node.child_by_field_name('parameters')
        names = ([text(parameters)] if parameters is not None and parameters.type == 'identifier' else
                 [text(child.child_by_field_name('name') or child) for child in parameters.named_children]
                 if parameters is not None else [])
        if len(names) != len(arguments):
            self.approximate = True
            self.warnings.add('unsupported callback parameters: ' + text(node))
            return U
        local = {**captured, **dict(zip(names,arguments))}
        previous, previous_types = self.method, self.variable_types
        self.method, self.variable_types = owner, dict(types)
        try:
            body = node.child_by_field_name('body')
            if body.type != 'block':
                return self.value(body, local)
            value, control = self.execute(body, local)
            if control == 'throw':
                raise JavaThrow(value)
            return value if control == 'return' else U
        finally:
            self.method, self.variable_types = previous, previous_types

    def expand_http_template(self,url,args,name,reason):
        variables=args[4 if name=='exchange' else 3 if name.startswith('post') else 2:]
        mapping=variables[0].mapping if len(variables)==1 and isinstance(variables[0],JavaMap) else None
        if mapping is not None and not isinstance(mapping,dict):
            self.approximate=True
            self.warnings.add('unresolved Java Map URI variables: '+reason)
            return U
        placeholders=list(re.finditer(r'\{([A-Za-z_]\w*)\}',url))
        rest=re.sub(r'\{([A-Za-z_]\w*)\}','',url)
        result,offset='',0
        for index,placeholder in enumerate(placeholders):
            value=mapping.get(placeholder[1],U) if mapping is not None else variables[index] if index<len(variables) else U
            if type(value) is bool:value=str(value).lower()
            if type(value) is int:value=str(value)
            supported=(isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9._~-]*',value) is not None
                       or isinstance(value,dict) and value.get('__uuid_text__') is True)
            if not supported or '{' in rest or '}' in rest:
                self.approximate=True
                self.warnings.add('unresolved URI template expansion or encoding: '+reason)
                return U
            result=concat_text(concat_text(result,url[offset:placeholder.start()]),value)
            offset=placeholder.end()
        if not placeholders:
            self.approximate=True
            self.warnings.add('unsupported URI template syntax: '+reason)
            return U
        return concat_text(result,url[offset:])

    @staticmethod
    def request_address(url):
        if isinstance(url,str):
            try:parsed=urlsplit(url)
            except ValueError:return None
            return {'hostname':parsed.hostname,'segments':parsed.path.strip('/').split('/') if parsed.path.strip('/') else [],
                    'query':dict(parse_qsl(parsed.query,keep_blank_values=True))}
        parsed=http_text_parts(url)
        if parsed is None and isinstance(url,dict):
            parts=url.get('__text_parts__',[])
            if parts and isinstance(parts[0],str) and parts[0].startswith('/') and not parts[0].startswith('//'):
                # Parsing base only; no concrete runtime URL or value is introduced.
                parsed=http_text_parts(concat_text('http://relative.invalid',url))
                if parsed:parsed['hostname']=None
        return {**parsed,'query':{}} if parsed else None

    def path_parameters(self, target, url):
        address=self.request_address(url)
        if address is None:
            return {}
        segments=address['segments']
        for mid, _, template in self.p.ix.handlers:
            if mid == target and len(template) == len(segments) and all(
                    key.startswith('{') or key in ('*', '**') or key == val for key, val in zip(template, segments)):
                if any(key.startswith('{') and ':' in key for key in template):
                    self.approximate=True
                    self.warnings.add('request route regular-expression constraints are not fully modeled: '+target)
                values = {key[1:-1].split(':', 1)[0]: unquote(value) if isinstance(value,str) else deepcopy(value)
                          for key, value in zip(template, segments) if key.startswith('{')}
                query=address['query']
                for par in self.p.http_parameters(target):
                    source = values if par['kind'] == 'PathVariable' else query if par['kind'] == 'RequestParam' else {}
                    if par['wire_name'] in source:
                        values[par['name']] = source[par['wire_name']]
                    elif par['kind'] == 'RequestParam' and par['default'] is not U:
                        values[par['name']] = par['default']
                    elif par['kind'] == 'RequestParam' and not par['required']:
                        values[par['name']] = None
                return values
        return {}

    def authentication(self, mid, args, reason):
        module = self.p.methods[mid]['module']
        principal = member(args[0], 'principal') if args else U
        self.approximate = True
        self.warnings.add('authentication provider result is abstracted')
        for callback in self.p.by_name.get('loadUserByUsername', []):
            if self.p.methods[callback]['module'] == module and not self.p.methods[callback].get('abstract'):
                self.invoke(callback, [principal], reason='Spring authentication callback at ' + reason)
        for name in ('getPassword', 'getAuthorities', 'isAccountNonExpired', 'isAccountNonLocked', 'isCredentialsNonExpired', 'isEnabled'):
            for callback in self.p.by_name.get(name, []):
                meta = self.p.methods[callback]
                if meta['module'] == module and any(a.split('.')[-1] == 'UserDetails' for a in self.p.framework_types.get(meta['owner'], set())):
                    self.invoke(callback, [], reason='UserDetails authentication callback at ' + reason)

    def repository(self, mid, cs, args, resources, reason):
        result = U
        for rid in resources:
            self.add(mid, 'data', rid, reason)
            self.data_operations.append({'method': mid, 'resource': rid, 'operation': cs.get('callee'),
                                         'arguments': deepcopy(args), 'source_site': reason,
                                         'uncertain_write': bool(self.uncertain)})
            resource = self.p.nodes[rid]
            rows = self.state.database.rows(resource)
            if rows is None or resource.get('collection_of'):
                self.approximate = True
                self.warnings.add('ORM access is approximated from static mapping: ' + rid)
                continue
            name = cs.get('callee', '')
            entity = self.p.entities.get(rid)
            if name.startswith(('save', 'insert')) and args and isinstance(args[0], dict):
                record = deepcopy(args[0])
                if self.uncertain:
                    self.warnings.add('possible database write not committed: ' + reason)
                    self.state.database.invalidate(rows)
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
                result = record
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
            materialized = []
            for row in selected:
                record = {'__type__': self.p.nodes[entity]['fqn'] if entity else '', **deepcopy(row)}
                if entity:record=JavaRecord(self.p.nodes[entity]['fqn'],record,self.p.type_fields.get(entity,{}))
                if entity:
                    for ctor in self.p.methods_of(entity, '<init>'):
                        if not self.p.methods[ctor].get('params_as_written'):
                            # Constructor is reached through materialization, not a direct project call.
                            if any(self.p.targets(ctor, site) for site in self.p.sites.get(ctor, [])):
                                self.invoke(ctor, [], deepcopy(record), 'entity materialization with project calls at ' + reason)
                materialized.append(record)
            if unknown_query:
                result = U
                continue
            # Repository declarations are indexed even though their bodies are abstract.
            declared_owner=self.p.resolve_type(cs.get('receiver_type',''),self.p.methods[mid]['module'],self.p.methods[mid]['file'])
            declared = [m.get('return_raw', '') for m in self.p.methods.values()
                        if m['name'] == name and m['owner']==declared_owner]
            return_type = declared[0] if declared else ('Optional' if name == 'findById' else '')
            first = materialized[0] if materialized else None
            result = {'__optional__': True, 'optional': first} if 'Optional' in return_type else materialized if any(t in return_type for t in ('List', 'Set', 'Collection')) or name == 'findAll' else first
        return result
