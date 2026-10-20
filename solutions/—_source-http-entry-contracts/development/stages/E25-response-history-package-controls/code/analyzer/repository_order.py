"""Bounded numeric repository ordering, ties and explicit encounter choices."""
from itertools import permutations,product
from functools import cmp_to_key
from decimal import Decimal
import math,re
from .state import U


def query_order(source):
    match=re.search(r'\border\s+by\s+(.+?)\s*$',source,re.I|re.S)
    if not match:return []
    specs=[]
    for clause in match[1].split(','):
        field=re.fullmatch(r'\s*(?:\w+\.)?(\w+)(?:\s+(asc|desc))?(?:\s+nulls\s+(first|last))?\s*',clause,re.I)
        if not field:return None
        specs.append((field[1],(field[2] or 'asc').lower(),(field[3] or 'native').lower()))
    return specs


def derived(name):
    predicate,separator,suffix=name.partition('OrderBy');specs=[]
    if separator:
        while suffix:
            match=re.match(r'([A-Z][A-Za-z0-9_]*?)(Asc|Desc)(?=[A-Z]|$)',suffix)
            if not match:return predicate,None,None
            specs.append((match[1][:1].lower()+match[1][1:],match[2].lower(),'native'))
            suffix=suffix[match.end():]
    limit_match=re.match(r'(?:find|read|query|get)(?:First|Top)(\d*)By',predicate)
    limit=int(limit_match[1] or 1) if limit_match else None
    if limit_match:predicate='findBy'+predicate[limit_match.end():]
    return predicate,specs,limit


def apply(values,specs,source):
    values.order_known=len(values)<=1
    values.repository_order={'source':source,'specs':specs,'supported':True,'variants':[]}
    if values.order_known:return
    if specs is None:
        values.repository_order.update(supported=False,reason='unsupported ordering expression');return
    if not specs:
        values.repository_order['variants']=[[list(range(len(values)))]];return
    for row in values:
        for field,_,_ in specs:
            value=row.get(field,U)
            if value is not None and not (type(value) in (int,float,Decimal) and
                    (type(value) is not float or math.isfinite(value)) and
                    (type(value) is not Decimal or value.is_finite())):
                values.repository_order.update(supported=False,reason='unproved numeric comparator/collation: '+field);return
    native=[index for index,(_,_,nulls) in enumerate(specs) if nulls=='native' and any(row.get(specs[index][0]) is None for row in values)]
    if len(native)>3:
        values.repository_order.update(supported=False,reason='null-order variant scope exceeded');return
    variants=[]
    for choices in product(('first','last'),repeat=len(native)):
        policy=dict(zip(native,choices))
        def compare(left,right):
            for index,(field,direction,nulls) in enumerate(specs):
                a,b=values[left].get(field,U),values[right].get(field,U)
                if a is None or b is None:
                    if a is b:continue
                    first=(policy.get(index,nulls)=='first')
                    return -1 if (a is None)==first else 1
                if a!=b:return (-1 if a<b else 1)*(-1 if direction=='desc' else 1)
            return 0
        ordered=sorted(range(len(values)),key=cmp_to_key(compare));groups=[]
        for index in ordered:
            if not groups or compare(groups[-1][0],index):groups.append([index])
            else:groups[-1].append(index)
        if groups not in variants:variants.append(groups)
    values.repository_order['variants']=variants
    if len(variants)==1 and all(len(group)==1 for group in variants[0]):
        reorder(values,[group[0] for group in variants[0]])


def reorder(values,indices):
    items=[values[i] for i in indices];kinds=[values.kinds[i] for i in indices]
    list.__setitem__(values,slice(None),items);values.kinds[:]=kinds;values.order_known=True


def realize(engine,values,reason):
    if values.order_known:return
    from .engine import AnalysisBoundary,CompletionRequired
    info=getattr(values,'repository_order',None)
    if not info:return
    if not info['supported']:raise AnalysisBoundary('repository order comparator is outside scope: '+info.get('reason',''),category='unsupported_semantics')
    if len(values)>6:raise AnalysisBoundary('repository ordinal order needs more than the six-row permutation scope: '+reason,category='unsupported_semantics')
    if not engine.path_replay:raise AnalysisBoundary('repository encounter order requires path replay: '+reason,category='unsupported_semantics')
    options=[]
    for groups in info['variants']:
        for parts in product(*(list(permutations(group)) for group in groups)):
            order=tuple(i for group in parts for i in group)
            if order not in options:options.append(order)
    label=reason+':repository-order'
    selected=engine.choose(label,options) if len(options)>1 else options[0]
    if selected is None:
        if not engine.allow_completion_splits:raise AnalysisBoundary('repository order completion budget: '+reason)
        raise CompletionRequired(str(engine.branch_index)+':'+label,options)
    reorder(values,selected)
    values.repository_order={**info,'realized_order':list(selected),'proof':'isolated path alternative'}
