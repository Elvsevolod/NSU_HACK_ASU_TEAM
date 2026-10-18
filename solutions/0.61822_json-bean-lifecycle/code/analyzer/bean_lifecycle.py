"""Source bean callbacks at JSON boundaries; conversion recursion stays outside."""
from copy import deepcopy
from itertools import permutations
from .state import U
from .java_collections import JavaObject,JsonObject
from .java_exceptions import JavaThrow,ExceptionBound,assignable
from .generic_types import type_parts,bind_parameters,declaring_bindings
from .source_generics import render,member_scope,call_context
from .project import walk,text
from .heap_join import widen

PRIMITIVES={'boolean','byte','short','char','int','long','float','double'}


def mapping_failure(serialization=False):
    return JavaThrow({'__type__':ExceptionBound('com.fasterxml.jackson.databind.JsonMappingException'),
                      '__serialization_failure__':serialization})


class BeanLifecycle:
    def __init__(self,engine,reason,defaults_certain=False,request_unknowns=None):
        self.e,self.p,self.reason=engine,engine.p,reason
        self.defaults_certain=defaults_certain
        self.request_unknowns=request_unknowns

    def plan(self,owner,direction,issue):
        from .bean_properties import default_bean_plan
        plan=default_bean_plan(self.p,owner,direction,self.e.standard_type)
        for message in plan['issues']:issue('JSON bean plan: '+message)
        return plan

    def owner(self,record):
        owner=getattr(record,'source_owner',None)
        if owner in self.p.nodes and self.p.nodes[owner].get('fqn')==record.declared_type:return owner
        found=[tid for tid,node in self.p.nodes.items() if node['kind']=='type' and node.get('fqn')==record.declared_type]
        return found[0] if len(found)==1 else None

    def callback(self,mid,obj,args,role,kinds=None,argument_types=()):
        owner=self.p.methods[mid]['owner']
        context=getattr(obj,'_json_receiver_context',None) or self.p.nodes[owner]
        receiver=getattr(obj,'_json_receiver_type',None) or obj.declared_type
        generic=call_context(self.p,mid,receiver,context,list(argument_types),None,self.e.standard_type)[:2]
        try:
            return self.e.invoke(mid,args,obj,'JSON '+role+' callback: '+self.reason,generic,kinds,
                                 export_method=role=='setter')
        except JavaThrow as failure:
            thrown=failure.value.get('__type__',U) if isinstance(failure.value,dict) else U
            if assignable(thrown,'java.lang.Error',self.p) is True:raise
            raise mapping_failure(role=='getter') from None

    def pure_getter(self,prop):
        if prop['kind']!='method':return True
        source=self.p.ast.get(prop['member'])
        return source is not None and not any(n.type in ('assignment_expression','update_expression',
            'method_invocation','object_creation_expression','throw_statement','synchronized_statement') for n in walk(source))

    def writer_field(self,prop):
        if prop.get('may_fail'):return None
        if prop['kind']!='method':return frozenset({(prop['owner'],prop['member'])}) if not prop.get('non_null') else None
        source=self.p.ast.get(prop['member']);pars=self.p.parameters(prop['member'])
        if source is None or len(pars)!=1:return None
        body=source.child_by_field_name('body')
        if body is None:return None
        assignments=[n for n in walk(body) if n.type=='assignment_expression']
        statements=[n for n in body.named_children if n.type not in ('line_comment','block_comment','empty_statement')]
        if not statements:return frozenset()
        if all(n.type=='return_statement' and all(c.type in ('this','null_literal','string_literal','decimal_integer_literal','true','false') for c in n.named_children) for n in statements):return frozenset()
        if (len(statements) not in (1,2) or statements[0].type!='expression_statement'
                or len(statements[0].named_children)!=1 or statements[0].named_children[0].type!='assignment_expression'):
            return None
        if len(statements)==2 and not (statements[1].type=='return_statement' and all(
                c.type in ('this','null_literal','string_literal','decimal_integer_literal','true','false') for c in statements[1].named_children)):
            return None
        if len(assignments)!=1 or any(n.type in ('method_invocation','object_creation_expression','update_expression',
              'if_statement','throw_statement','for_statement','while_statement','try_statement') for n in walk(body)):return None
        assignment=assignments[0]
        if text(assignment.child_by_field_name('operator'))!='=' or text(assignment.child_by_field_name('right'))!=pars[0][0]:return None
        target=text(assignment.child_by_field_name('left')).removeprefix('this.')
        field=self.p.type_fields.get(prop['owner'],{}).get(target)
        if not field:return None
        if field['type']!=pars[0][1]:
            field_type=render(self.p,field['type'],self.p.nodes[field['declaring_type']],{},self.e.standard_type)
            param_type=render(self.p,pars[0][1],self.p.methods[prop['member']],{},self.e.standard_type)
            if not field_type or field_type!=param_type:return None
        return frozenset({(field['declaring_type'],target)})

    def uncertain_order(self,props,record,role,issue):
        names=list(props)
        if len(names)<=1:return names
        if role=='getter' and all(self.pure_getter(prop) for prop in props.values()):return names
        fields=[self.writer_field(prop) for prop in props.values()] if role=='setter' else []
        if fields and all(field is not None for field in fields) and sum(map(len,fields))==len(set().union(*fields)):return names
        order=self.e.choose(self.reason+':JSON '+role+' order',list(permutations(names))) if len(names)<=4 else None
        if order is not None:return order
        issue('JSON '+role+' order is unobserved and exceeds the current ordering budget')
        for prop in props.values():
            if prop['kind']=='method':
                with self.e.project_invocation(prop['member'],role=='setter'):self.e.fallback(prop['member'])
        widen(record)
        return None

    def read(self,record,issue):
        owner=self.owner(record)
        if owner is None:
            issue('JSON bean source owner is ambiguous or absent');return U
        plan=self.plan(owner,'serialize',issue)
        if not plan['complete']:return U
        props=plan['properties'];order=self.uncertain_order(props,record,'getter',issue)
        if order is None:return U
        if not props:
            if self.defaults_certain:raise mapping_failure(True)
            issue('HTTP empty-bean serialization requires an observed codec policy');return U
        def pairs():
            for name in order:
                prop=props[name]
                value=(self.callback(prop['member'],record,[],'getter') if prop['kind']=='method'
                       else record.get(prop['member'],U))
                yield name,value
        # A chosen effectful getter order is also the emitted token order.
        # Pure getters commute locally, but their unobserved token order may
        # still matter to a subsequent bean's setters.
        return pairs(),len(props)<=1 or not all(self.pure_getter(prop) for prop in props.values())

    def allocate(self,owner,written,context,bindings,issue):
        obj=JavaObject(self.p.nodes[owner]['fqn'],{'__type__':self.p.nodes[owner]['fqn'],'__http_entity__':False},
                       wire_fields=self.p.type_fields[owner])
        obj.source_owner=owner
        obj._json_receiver_type=render(self.p,written,context,bindings,self.e.standard_type) or self.p.nodes[owner]['fqn']
        obj._json_receiver_context=dict(context)
        obj._native_field_kinds={};obj._field_reference_types={};obj._unchecked_generic_fields=set()
        for field,info in self.p.type_fields[owner].items():
            typ=info['type'];value=deepcopy(info['default'])
            if value is U and not info['has_initializer']:
                value=False if typ=='boolean' else '\0' if typ=='char' else 0.0 if typ in ('float','double') else 0 if typ in ('byte','short','int','long') else None
            elif value is U:issue('JSON instance field initializer is not modeled: '+field)
            kind=info.get('default_kind')
            if typ in PRIMITIVES and value is not U and value is not None:
                if kind=='Character' and typ in ('byte','short','int','long','float','double'):value=ord(value)
                if typ=='double':value=float(value)
                if typ=='float' and value!=0:
                    issue('JSON instance float initializer precision is not modeled');value=U
                kind=self.e.declared_kind(typ,self.p.nodes[info['declaring_type']])
            obj[field]=value;obj._native_field_kinds[field]=kind
            scope=member_scope(self.p,obj._json_receiver_type,info['declaring_type'],context)
            if scope is not None:
                if scope[1]:obj._unchecked_generic_fields.add(field)
                else:obj._field_reference_types[field]=render(self.p,typ,self.p.nodes[info['declaring_type']],scope[0],self.e.standard_type)
        return obj

    def write(self,obj,prop,value,kind,written,issue):
        if prop['kind']=='method':
            self.callback(prop['member'],obj,[value],'setter',[kind],[written]);return
        if prop.get('non_null') and value is None:raise mapping_failure()
        obj[prop['member']]=value
        obj._native_field_kinds[prop['member']]=kind
        obj._field_reference_types[prop['member']]=written

    def decode(self,value,written,owner,context,bindings,codec,certain,decode,kind_of,issue):
        plan=self.plan(owner,'deserialize',issue)
        if not plan['complete']:return U
        base,arguments=type_parts(written)
        local=bind_parameters(self.p,owner,arguments,context,bindings)
        if local is None:issue('JSON DTO generic arguments are not modeled');return U
        construction=plan['constructor']
        if construction['kind']=='missing':
            if codec is not None and certain:raise mapping_failure()
            issue('HTTP JSON default constructor is absent; creator configuration is unobserved');return U
        if construction['kind']=='unsupported':
            issue('JSON DTO construction is not modeled');return U
        obj=self.allocate(owner,written,context,bindings,issue)
        if construction['kind']=='source':self.callback(construction['member'],obj,[],'constructor')
        props=plan['properties']
        ignored=set(plan['ignored_properties'])
        pending=[]
        if self.request_unknowns is not None and value is self.request_unknowns[0]:
            value=deepcopy(value)
            for name,mode in sorted(self.request_unknowns[1].items()):
                if name not in props:continue
                present=True if mode=='present' else self.e.choose(self.reason+':JSON property presence '+name,[False,True])
                if present is True:value[name]=U
                elif present is None:pending.append(props[name])
        ignore_unknown=any(self.e.standard_type(name,'com.fasterxml.jackson.annotation.JsonIgnoreProperties',self.p.nodes[owner])
                           for name in self.p.json_ignore_unknown.get(owner,()))
        flag=codec.get('FAIL_ON_UNKNOWN_PROPERTIES',U) if codec is not None and certain else U
        ignored_policy=codec.get('FAIL_ON_IGNORED_PROPERTIES',U) if codec is not None and certain else U
        if (flag is True and not ignore_unknown and set(value)-props.keys()-ignored
                and construction['kind'] in ('implicit','generated')):
            scalar=True
            for name in value.keys() & props.keys():
                p=props[name];fb=declaring_bindings(self.p,owner,p['owner'],local)
                actual=render(self.p,p['type'],self.p.nodes[p['owner']],fb or {},self.e.standard_type)
                scalar &= p['kind'] in ('field','generated') and (actual in PRIMITIVES or any(
                    self.e.standard_type(actual,'java.lang.'+native,self.p.nodes[p['owner']])
                    for native in ('String','Boolean','Byte','Short','Integer','Long','Float','Double','Character','Object')))
            if scalar:
                # Pure local scalar writes cannot make an unknown-property
                # request succeed. No source callback/order is skipped here.
                raise mapping_failure()
        if isinstance(value,JsonObject) and value.source_pairs is not None:pairs=value.source_pairs
        else:
            present={name:props.get(name,{'kind':'unknown','member':name,'owner':owner,'may_fail':True})
                     for name in value if name in props or (ignored_policy is not False if name in ignored else not (ignore_unknown or flag is False))}
            order=self.uncertain_order(present,obj,'setter',issue)
            if order is None:return U
            pairs=[(name,value[name]) for name in order]
        for name,raw in pairs:
            if name in ignored:
                if ignored_policy is True:raise mapping_failure()
                if ignored_policy is False:continue
                issue('JSON ignored property requires an observed codec failure policy: '+name);return U
            prop=props.get(name)
            if prop is None:
                flag=codec.get('FAIL_ON_UNKNOWN_PROPERTIES',U) if codec is not None and certain else U
                if ignore_unknown or flag is False:continue
                if flag is True:raise mapping_failure()
                issue('JSON property presence requires an observed unknown-property policy: '+name);return U
            declared=prop['owner'];field_bindings=declaring_bindings(self.p,owner,declared,local)
            if field_bindings is None:issue('JSON property generic inheritance is not modeled');return U
            typ=prop['type'];meta=self.p.nodes[declared]
            decoded=decode(raw,typ,meta,field_bindings,certain)
            rendered=render(self.p,typ,meta,field_bindings,self.e.standard_type)
            self.write(obj,prop,decoded,kind_of(decoded,typ,meta,field_bindings),rendered,issue)
        if pending:
            issue('JSON property presence is unobserved; optional writes and callback effects are conservatively retained')
            for prop in pending:
                if prop['kind']=='method':
                    self.e.executed(prop['member'],'unobserved JSON property presence: possible setter')
                    self.e.fallback(prop['member'])
            widen(obj)
        return obj
