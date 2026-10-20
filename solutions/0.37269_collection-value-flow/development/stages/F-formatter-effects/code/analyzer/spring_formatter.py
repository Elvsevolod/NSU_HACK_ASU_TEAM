"""Default Spring 5 ToStringCreator effects; formatted identity text stays symbolic."""
from dataclasses import dataclass
from .java_collections import JavaRecord,is_symbolic
from .java_exceptions import JavaThrow
from .project import text
from .state import U


@dataclass
class Creator:
    origin: str


def call(engine,node,name,obj,args,reason):
    def boundary(message):
        from .engine import AnalysisBoundary
        raise AnalysisBoundary('Spring ToStringCreator '+message+': '+reason,category='unsupported_semantics')
    def style(value,seen):
        if value is None or type(value) in (str,bool,int,float) or is_symbolic(value):return
        if value is U:boundary('value runtime type/callback is unknown')
        if id(value) in seen:boundary('recursive formatting')
        seen=seen|{id(value)}
        if isinstance(value,list):
            if getattr(value,'opaque',False) or not getattr(value,'order_known',True):boundary('collection order or contents are unknown')
            for child in value:style(child,seen)
            return
        if isinstance(value,JavaRecord):
            meta=engine.p.methods[engine.method]
            owner=engine.p.resolve_type(value.declared_type,meta['module'],meta['file'])
            if not owner:boundary('appended object source is unavailable')
            targets=[mid for mid in engine.p.inherited_methods(owner,'toString',0) if not engine.p.methods[mid].get('abstract')]
            if len(targets)>1:boundary('appended object toString dispatch is ambiguous')
            if targets:
                try:engine.invoke(targets[0],[],value,reason+' default value styling callback')
                finally:
                    if engine.last_invoke_started:engine.add(engine.method,'calls',targets[0],reason+' default value styling callback')
            return # No override: Object.toString uses class and identity, without source mutation.
        boundary('value styling overload is not modeled')
    if name=='<init>' and engine.standard_type(text(node.child_by_field_name('type')),'org.springframework.core.style.ToStringCreator'):
        if len(args)!=1:boundary('custom styler overload is not modeled')
        if args[0] is None:raise JavaThrow({'__type__':'IllegalArgumentException'})
        if isinstance(args[0],list):boundary('array owner styleStart is not modeled')
        return True,Creator(reason)
    if not isinstance(obj,Creator):return False,U
    if name=='append' and len(args) in (1,2):
        if len(args)==2 and not isinstance(args[0],str):boundary('field name is not a known String')
        style(args[-1],set())
        engine.effect_events.append({'model_version':'spring-default-tostring/1','operation':'append',
            'callsite':reason,'heap_roots':[],'resource_writes':[],
            'callbacks':'source toString dispatched above when present','completions':['normal']})
        return True,obj
    if name=='toString' and not args:
        engine.remember_reference_kind('String')
        return True,{'__symbol__':'spring-style:'+obj.origin,'__type__':'String',
                     '__constraints__':['non_null'],'__generation__':'Spring default class/identity formatting'}
    boundary('operation is not modeled')
