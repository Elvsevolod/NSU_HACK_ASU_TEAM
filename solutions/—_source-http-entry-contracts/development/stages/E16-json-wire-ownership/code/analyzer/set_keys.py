"""HashSet key callbacks and a deliberately small default Lombok leaf model."""
from .state import U
from .java_collections import JavaRecord,reference_equal
from .boxed_values import boxed_equal
from .bean_properties import declaration,annotations
from .project import text,keywords

SCALARS=('String','Integer','Long','Short','Byte','Character','Boolean')


def stop(reason):
    from .engine import AnalysisBoundary
    raise AnalysisBoundary('Java Set '+reason,category='unsupported_semantics')


def signed(value):return (value+2**31)%2**32-2**31


def scalar_hash(value,kind):
    if value is None:return 0
    if value is U:return U
    if kind=='String' and type(value) is str:
        raw=value.encode('utf-16-be',errors='surrogatepass');result=0
        for index in range(0,len(raw),2):result=signed(31*result+int.from_bytes(raw[index:index+2],'big'))
        return result
    if kind in ('Integer','Short','Byte') and type(value) is int:return signed(value)
    if kind=='Long' and type(value) is int:return signed((value&((1<<64)-1)) ^ ((value&((1<<64)-1))>>32))
    if kind=='Character' and type(value) is str and len(value)==1 and ord(value)<=65535:return ord(value)
    if kind=='Boolean' and type(value) is bool:return 1231 if value else 1237
    return U


def owner(engine,value):
    if not isinstance(value,JavaRecord):return None
    meta=engine.p.methods[engine.method]
    return getattr(value,'source_owner',None) or engine.p.resolve_type(value.declared_type,meta['module'],meta['file'])


def source_method(engine,tid,name):
    methods=[mid for mid in engine.p.by_name.get(name,()) if engine.p.methods[mid]['owner']==tid
        and engine.p.ast.get(mid) is not None and not engine.p.methods[mid].get('abstract')
        and engine.p.methods[mid].get('params_as_written') in (([],) if name=='hashCode' else (['Object'],['java.lang.Object']))]
    return methods[0] if len(methods)==1 else None


def generated_plan(engine,tid):
    cache=engine.p.__dict__.setdefault('_set_generated_leaf_plans',{})
    if tid in cache:return cache[tid]
    meta=engine.p.nodes.get(tid,{});decl=declaration(engine.p,tid) if tid else None
    result=None
    if decl is not None and not engine.p.type_parents.get(tid) and not engine.p.framework_types.get(tid):
        attrs=annotations(decl)
        standard=[(name,args) for name,args in attrs if any(engine.standard_type(name,'lombok.'+leaf,meta)
            for leaf in ('Data','Value','EqualsAndHashCode'))]
        options=all(args in ('','()') for _,args in standard)
        config=engine.p.__dict__.get('_set_lombok_config_present')
        if config is None:
            config=any(engine.p.root.rglob('lombok.config'));engine.p._set_lombok_config_present=config
        fields=[];valid=bool(standard) and options and not config
        body=decl.child_by_field_name('body')
        if any('EqualsAndHashCode.' in name for child in body.named_children for name,_ in annotations(child)):valid=False
        for child in body.named_children:
            if child.type!='field_declaration' or keywords(child)&{'static','transient'}:continue
            written=text(child.child_by_field_name('type'));kind=engine.declared_kind(written,meta)
            if kind not in SCALARS:valid=False
            for var in child.named_children:
                if var.type!='variable_declarator':continue
                name=text(var.child_by_field_name('name'))
                if name.startswith('$'):continue
                getters=['get'+name[:1].upper()+name[1:],'is'+name[:1].upper()+name[1:]]
                if any(engine.p.methods_of(tid,getter) for getter in getters):valid=False
                fields.append((name,written,kind))
        if valid:result=fields
    cache[tid]=result
    return result


def hash_value(engine,value,kind,reason):
    if value is None or kind in SCALARS:return scalar_hash(value,kind)
    tid=owner(engine,value)
    if not tid or engine.p.type_parents.get(tid) or engine.p.framework_types.get(tid,set())-{'Object','java.lang.Object'}:
        stop('element equality/hash owner or inheritance is outside the leaf contract: '+reason)
    target=source_method(engine,tid,'hashCode')
    if target:
        value=engine.invoke(target,[],value,'HashSet hashCode callback at '+reason)
        if type(value) is not int or engine.last_invoke_kind!='Integer':stop('source hashCode result/kind is unresolved: '+reason)
        return signed(value)
    if source_method(engine,tid,'equals'):stop('source equals has no supported source hashCode: '+reason)
    plan=generated_plan(engine,tid)
    if plan is None:stop('element equality/hash callbacks are outside the supported source/generated contract: '+reason)
    result=1
    for field,written,actual in plan:
        item=value.get(field,U);observed=getattr(value,'_native_field_kinds',{}).get(field)
        if item is not None and observed!=actual:stop('generated key field kind is unresolved: '+reason+' '+field)
        part=(79 if item else 97) if written=='boolean' and type(item) is bool else scalar_hash(item,actual)
        if item is None:part=43
        if part is U:stop('generated key field value is unresolved: '+reason+' '+field)
        result=signed(result*59+part)
    engine.effect_events.append({'model_version':'lombok-default-scalar-key/1','operation':'hashCode',
        'owner':tid,'fields':[f for f,_,_ in plan],'callsite':reason,'resource_writes':[],
        'generated_method_id':None,'origin':'source annotation and scalar declarations'})
    return result


def equal(engine,value,item,kind,item_kind,reason):
    if value is None:return item is None if item is not U else U
    if kind in SCALARS:return boxed_equal(value,item,kind,item_kind,lambda a,b:a==b)
    identity=reference_equal(value,item)
    if identity is True:return True
    tid=owner(engine,value);target=source_method(engine,tid,'equals') if tid else None
    if target:
        result=engine.invoke(target,[item],value,'HashSet equals callback at '+reason,argument_kinds=[item_kind])
        if type(result) is not bool:stop('source equals result is unresolved: '+reason)
        return result
    plan=generated_plan(engine,tid) if tid else None
    if plan is None:return False if identity is False else U
    if owner(engine,item)!=tid:return False
    for field,_,actual in plan:
        result=boxed_equal(value.get(field,U),item.get(field,U),
            getattr(value,'_native_field_kinds',{}).get(field),getattr(item,'_native_field_kinds',{}).get(field),lambda a,b:a==b)
        if result is not True:return result
    return True
