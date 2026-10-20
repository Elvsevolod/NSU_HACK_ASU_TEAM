"""Standard HashSet with known scalar equality, without an encounter order."""
from .native_storage import JavaList
from .boxed_values import boxed_equal
from .state import U


def shapes(value,path='body',seen=None):
    seen=set() if seen is None else seen
    if not isinstance(value,(dict,list)) or id(value) in seen:return []
    seen.add(id(value));result=[]
    if isinstance(value,JavaList) and not value.order_known:
        result.append({'path':path,'size':None if value.opaque else len(value),'order':'unspecified'})
    children=value.items() if isinstance(value,dict) else enumerate(value)
    for key,child in children:result.extend(shapes(child,path+'/'+str(key),seen))
    return result


def next_index(engine,iterator,reason):
    remaining=iterator['remaining']
    if not remaining:return None
    selected=engine.choose(reason+':unordered-collection-next',list(range(len(remaining)))) if len(remaining)>1 else 0
    if selected is None:
        from .engine import CompletionRequired,AnalysisBoundary
        if not engine.allow_completion_splits:raise AnalysisBoundary('collection encounter order needs a continuation: '+reason)
        raise CompletionRequired(str(engine.branch_index)+':'+reason+':unordered-collection-next',list(range(len(remaining))))
    return remaining.pop(selected)


def call(engine,name,values,args,kinds,reason):
    if not isinstance(values,JavaList) or values.flavor!='HashSet':return False,U
    if name=='stream' and not args:return False,U
    def boundary(message,write=False):
        engine.approximate=True;engine.warnings.add('Java Set '+message+': '+reason)
        engine.operation_issues[('java_set_boundary',message)]+=1
        if write:values.opaque=True
        return True,U
    def index(value,kind):
        if value is not None and kind not in ('String','Integer','Long','Short','Byte','Character','Boolean'):
            from .engine import AnalysisBoundary
            raise AnalysisBoundary('Java Set element equality/hash callbacks are outside the scalar contract: '+reason,category='unsupported_semantics')
        if value is not None and (kind not in ('String','Integer','Long','Short','Byte','Character','Boolean') or
            type(value) not in (str,int,bool)):return U
        for i,item in enumerate(values):
            equal=boxed_equal(value,item,kind,values.kinds[i],lambda a,b:a==b)
            if equal is True:return i
            if equal is U:return U
        return -1
    if name=='clear' and not args:values.clear();return True,None
    if values.opaque:return boundary('membership is unresolved',name in ('add','addAll','remove','removeAll','retainAll'))
    if name in ('size','isEmpty') and not args:return True,len(values) if name=='size' else not values
    if name in ('add','contains','remove') and len(args)==1:
        found=index(args[0],kinds[0])
        if found is U:return boundary('element equality or hash contract is unresolved',name!='contains')
        if name=='contains':return True,found!=-1
        if name=='add':
            if found!=-1:return True,False
            values.append(args[0],kinds[0]);return True,True
        if found==-1:return True,False
        values.pop(found);return True,True
    if name in ('addAll','removeAll','retainAll') and len(args)==1:
        other=args[0]
        if other is None:
            from .java_exceptions import JavaThrow
            raise JavaThrow({'__type__':'NullPointerException'})
        if not isinstance(other,JavaList) or other.opaque:return boundary('bulk membership is unresolved',True)
        if any(value is not None and kind not in ('String','Integer','Long','Short','Byte','Character','Boolean') for value,kind in zip(other,other.kinds)):
            from .engine import AnalysisBoundary
            raise AnalysisBoundary('Java Set bulk equality/hash callbacks are outside the scalar contract: '+reason,category='unsupported_semantics')
        if name=='addAll':
            changed=False
            for value,kind in zip(list(other),list(other.kinds)):
                _,result=call(engine,'add',values,[value],[kind],reason)
                if result is U:return True,U
                changed|=result
            return True,changed
        kept=[];kept_kinds=[]
        for value,kind in zip(values,values.kinds):
            comparisons=[boxed_equal(value,item,kind,other.kinds[i],lambda a,b:a==b) for i,item in enumerate(other)]
            present=True if True in comparisons else U if U in comparisons else False
            if present is U:return boundary('bulk element equality is unresolved',True)
            if present==(name=='retainAll'):kept.append(value);kept_kinds.append(kind)
        changed=len(kept)!=len(values)
        if changed:values[:]=kept;values.kinds[:]=kept_kinds
        return True,changed
    if name=='iterator' and not args:return False,U
    if name=='equals' and len(args)==1:
        other=args[0]
        if not isinstance(other,JavaList) or other.flavor!='HashSet':return True,False
        if other.opaque:return boundary('equality contents are unresolved')
        if len(values)!=len(other):return True,False
        found=[index(value,kind) for value,kind in zip(other,other.kinds)]
        return boundary('equality is unresolved') if U in found else (True,all(i!=-1 for i in found))
    return boundary('operation is outside the supported scalar contract: '+name)
