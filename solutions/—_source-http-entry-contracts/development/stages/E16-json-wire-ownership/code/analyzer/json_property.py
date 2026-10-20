"""Literal Jackson JsonProperty facts; namesakes cannot supply native policy."""
import json,re
from baseline_closure import _split_args
from .project import text

FQN='com.fasterxml.jackson.annotation.JsonProperty'


def annotation(entries,project,context,standard,issue):
    found=[args for name,args in entries if standard(name,FQN,context)]
    result={'explicit':bool(found),'name':None,'access':'AUTO'}
    if not found:return result
    if len(found)!=1:issue('duplicate JsonProperty annotations are not modeled');return result
    seen=set()
    for part in _split_args(found[0]):
        pair=re.fullmatch(r'([\w]+)\s*=\s*(.*)',part,re.S)
        key,value=(pair[1],pair[2]) if pair else ('value',part)
        if key in seen:issue('duplicate JsonProperty argument: '+key);continue
        seen.add(key)
        if key in ('value','defaultValue','required'):
            try:literal=json.loads(value)
            except ValueError:literal=None
            if key=='required':
                if type(literal) is not bool:issue('JsonProperty required metadata is not a boolean literal')
            elif not isinstance(literal,str):issue('JsonProperty '+key+' is not a supported literal')
            elif key=='value':result['name']=literal or None
            # required/defaultValue are metadata, not field validation/defaulting.
        elif key=='access':
            qualifier,_,leaf=value.strip().rpartition('.')
            if not qualifier:
                leaf=value.strip();tree=project.trees.get(context['file'])
                imports=[text(n).replace(' ','').replace('\n','') for n in tree.root_node.named_children
                    if n.type=='import_declaration'] if tree else []
                proved=any(s in imports for s in ('importstatic'+FQN+'.Access.'+leaf+';',
                    'importstatic'+FQN+'.Access.*;'))
            else:
                proved=standard(qualifier,FQN+'.Access',context) or (
                    qualifier.endswith('.Access') and standard(qualifier[:-7],FQN,context))
            if proved and leaf in ('AUTO','READ_ONLY','WRITE_ONLY','READ_WRITE'):result['access']=leaf
            else:issue('JsonProperty access enum identity or value is unresolved')
        else:issue('JsonProperty argument is outside the supported policy: '+key)
    return result


def member(prop,policy,visible=True,ignored=False):
    return {**prop,'_json_property':policy,'_visible':visible,'_ignored':ignored}


def clean(prop):
    return {key:value for key,value in prop.items() if key not in ('_json_property','_visible','_ignored')}
