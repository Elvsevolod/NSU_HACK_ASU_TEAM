"""Credential ownership is evidence from context, never from startup defaults."""
import re
from .actors import canonical_role
from .state import U


def from_context(raw,spans,pairs):
    actors={};unowned=[]
    def add(actor,facts):
        if actor in actors:
            if any(actors[actor].get(name,{}).get('value')!=fact['value'] for name,fact in facts.items()):
                actors[actor]={}
                message='Conflicting credential sets for actor '+actor
                if message not in unowned:unowned.append(message)
        else:actors[actor]=facts
    for pair in pairs:
        username=spans[pair['username']]
        source=str(username['source']);text=str(raw.get(source,'')) if isinstance(raw,dict) else str(raw)
        position=text.find(username['quote'])
        prefix=re.split(r'[;\n]',text[:max(0,position)])[-1]
        owner=re.fullmatch(r'([\w-]+)[ _-](?:account|credentials?)',source,re.I)
        role=re.search(r'\b(?:the\s+)?([\w-]+)\s+is\s+(?:the\s+)?(?:pre-registered\s+)?(?:user|account)\b',prefix,re.I)
        labelled=re.search(r'\b([\w-]+)\s+(?:credentials?|account)\b',prefix,re.I)
        actor=canonical_role((owner or role or labelled)[1]) if owner or role or labelled else canonical_role(str(username['value']))
        facts={name:{**spans[ref],'kind':'credential','reference':ref,'actor':actor} for name,ref in pair.items()}
        add(actor,facts)
    for group in ('actors','accounts'):
        values=raw.get(group) if isinstance(raw,dict) else None
        for actor,value in values.items() if isinstance(values,dict) else []:
            if not isinstance(value,dict) or not all(isinstance(value.get(k),str) for k in ('username','password')):continue
            identity=canonical_role(actor)
            facts={name:{'value':value[name],'quote':value[name],'source':group+'.'+actor+'.'+name,
                'reference':group+'.'+actor+'.'+name,'kind':'credential','actor':identity} for name in ('username','password')}
            add(identity,facts)
    chosen=canonical_role(raw['default_actor']) if isinstance(raw,dict) and isinstance(raw.get('default_actor'),str) else next(iter(actors)) if len(actors)==1 else U
    default=chosen if chosen in actors else U
    return actors,default,unowned


def selected_actor(action,state,context):
    from .actors import actor_role
    explicit=actor_role(action)
    if explicit is not U:return explicit
    current=state.browser.get('actor',U)
    return current if current is not U else context.get('default_actor',U)


def facts_for(context,actor):
    scoped=context.get('actor_facts')
    if scoped is None:
        return {name:fact for name,fact in context.get('facts',{}).items()
            if fact.get('kind')!='credential' or actor is U or fact.get('actor')==actor}
    return {**{name:fact for name,fact in context.get('facts',{}).items() if fact.get('kind')!='credential'},
        **scoped.get(actor,{})}
