"""Bounded native List operations; values and runtime classes stay separate."""
from .native_storage import JavaList,JavaListIterator
from .native_arrays import JavaArray
from .java_exceptions import JavaThrow
from .state import U
from .source_conversions import compiled_type


def has_next(iterator):
    values=iterator['backing'];index=iterator['index']
    if type(index) is not int or values.opaque:return U
    if values.flavor=='LinkedList' or values.flavor=='Arrays.ArrayList':return index<len(values)
    if values.flavor=='ArrayList' or index<=len(values):return index!=len(values)
    return U


def iteration(engine,values,reason):
    iterator=JavaListIterator(values);count=0
    while True:
        present=has_next(iterator)
        if present is False:return
        if present is U or iterator['expected'] is None or values.structural_version is None:
            engine.warnings.add('List iteration state or structural version is unresolved: '+reason)
            engine.fallback(engine.method);yield U,None;return
        if iterator['expected']!=values.structural_version:raise JavaThrow({'__type__':'ConcurrentModificationException'})
        if count>=64:
            engine.warnings.add('loop collection widened after 64 elements')
            engine.fallback(engine.method);yield U,None;return
        index=iterator['index'];iterator['index']=index+1;count+=1
        yield values[index],values.kinds[index]


def call(engine,name,obj,args,kinds,nodes,node,reason):
    def unresolved(message,backing=None):
        engine.approximate=True
        engine.warnings.add(message+': '+reason)
        engine.operation_issues[('java_list_boundary',message)]+=1
        if backing is not None:backing.opaque=True
        return True,U
    def resizable(values):
        if values.fixed_size is True:raise JavaThrow({'__type__':'UnsupportedOperationException'})
        return values.fixed_size is False
    if isinstance(obj,JavaListIterator):
        if name=='equals' and len(args)==1:
            from .java_collections import reference_equal
            result=reference_equal(obj,args[0])
            return unresolved('List iterator reference identity is unresolved') if result is U else (True,result)
        values=obj['backing']
        if values.opaque:return unresolved('List iterator backing contents are unresolved')
        if type(obj['index']) is not int:return unresolved('List iterator cursor is unresolved')
        if name=='hasNext' and not args:
            present=has_next(obj)
            return unresolved('List iterator hasNext is unresolved') if present is U else (True,present)
        if name not in ('next','remove') or args:return unresolved('List iterator operation is not modeled',None if name in ('getClass','hashCode','toString') else values)
        if obj['expected'] is None or values.structural_version is None:return unresolved('List iterator structural version is unresolved')
        if obj['expected']!=values.structural_version:raise JavaThrow({'__type__':'ConcurrentModificationException'})
        if name=='next':
            index=obj['index']
            if index>=len(values):raise JavaThrow({'__type__':'NoSuchElementException'})
            obj['index']=index+1;obj['last']=index
            return True,engine.native_read_cast(values[index],values.kinds[index],node,reason)
        if obj['last'] is None:raise JavaThrow({'__type__':'IllegalStateException'})
        if type(obj['last']) is not int:return unresolved('List iterator removal cursor is unresolved',values)
        if not resizable(values):return unresolved('List mutability is unresolved',values)
        values.pop(obj['last']);obj['index']=obj['last'];obj['last']=None;obj['expected']=values.structural_version
        return True,None
    if not isinstance(obj,JavaList) or isinstance(obj,JavaArray):return False,U
    if name=='clear' and not args:
        if obj and not resizable(obj):return unresolved('List mutability is unresolved',obj)
        obj.clear();return True,None
    if obj.opaque:return unresolved('List contents or length are unresolved')
    if name=='iterator' and not args:return True,JavaListIterator(obj)
    if name=='isEmpty' and not args:return True,not obj
    if name=='equals' and len(args)==1:
        other=args[0]
        if obj is other:return True,True
        if not isinstance(other,JavaList) or isinstance(other,JavaArray):
            return (True,False) if other is None or isinstance(other,(JavaArray,str,int,float,bool)) else unresolved('List equality receiver class is unresolved')
        if other.opaque:return unresolved('List equality contents are unresolved')
        if len(obj)!=len(other):return True,False
        unknown=False
        for index,value in enumerate(obj):
            equal=engine.collection_membership(JavaList([other[index]],[other.kinds[index]]),value,'contains',reason,obj.kinds[index])
            if equal is False:return True,False
            unknown|=equal is U
        return True,U if unknown else True
    if name in ('add','addAll'):
        if name=='addAll' and args and isinstance(args[0],JavaList) and args[0].opaque:return unresolved('List bulk source contents are unresolved',obj)
        if name=='addAll' and len(args)==1 and isinstance(args[0],list) and not args[0]:return True,False
        if not resizable(obj):return unresolved('List mutability is unresolved',obj)
        return False,U
    if name=='remove' and len(args)==1:
        source=compiled_type(engine,nodes[0])
        if source in ('byte','short','char','int'):
            index=ord(args[0]) if source=='char' and isinstance(args[0],str) and len(args[0])==1 else args[0]
            if type(index) is not int:return unresolved('List removal index is unresolved',obj)
            if not 0<=index<len(obj):raise JavaThrow({'__type__':'IndexOutOfBoundsException'})
            if not resizable(obj):return unresolved('List mutability is unresolved',obj)
            value,kind=obj[index],obj.kinds[index];obj.pop(index)
            return True,engine.native_read_cast(value,kind,node,reason)
        if not source:return unresolved('List remove overload is unresolved',obj)
        index=engine.collection_membership(obj,args[0],'indexOf',reason,kinds[0])
        if index is U:return unresolved('List removal equality is unresolved',obj)
        if index==-1:return True,False
        if not resizable(obj):return unresolved('List mutability is unresolved',obj)
        obj.pop(index);return True,True
    if name in ('removeAll','retainAll') and len(args)==1:
        other=args[0]
        if other is None:raise JavaThrow({'__type__':'NullPointerException'})
        if not isinstance(other,JavaList) or other.opaque:return unresolved('List bulk membership is unresolved',obj)
        kept=[];evidence=[]
        for index,value in enumerate(obj):
            contains=engine.collection_membership(other,value,'contains',reason,obj.kinds[index])
            if contains is U:return unresolved('List bulk membership is unresolved',obj)
            if contains==(name=='retainAll'):kept.append(value);evidence.append(obj.kinds[index])
        changed=len(kept)!=len(obj)
        if changed:
            if not resizable(obj):return unresolved('List mutability is unresolved',obj)
            obj[:]=kept;obj.kinds[:]=evidence
        return True,changed
    return False,U
