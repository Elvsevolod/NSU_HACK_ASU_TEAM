"""Deployment-scoped supplied Spring config facts, not a Config Server client.

The graph provides parsed key/file/document facts. A resolved environment may
instead be supplied in context.configuration[module]. No host environment,
filesystem search order, YAML parser or application initializer is inferred.
"""
import re
from pathlib import PurePosixPath
from .state import U


def names(value):
    if value is U:return None
    if isinstance(value,list) and all(isinstance(v,str) for v in value):return tuple(value)
    return tuple(v for v in re.split(r'[,\s]+',str(value)) if v)


def matches(value,profiles):
    if profiles is None or not isinstance(value,str) or re.search(r'[&|()]',value):return U
    return any((part[1:] not in profiles) if part.startswith('!') else part in profiles for part in names(value))


class SourceConfiguration:
    def __init__(self,rows,modules,provided):
        self.entries={};self.profiles={};self.unknown={};self.used={}
        self.rows=rows;provided=provided if isinstance(provided,dict) else {}
        for module in sorted(modules):
            self.used[module]=set();snapshot=provided.get(module)
            if snapshot is not None:
                if not isinstance(snapshot,dict) or not isinstance(snapshot.get('propertySources'),list):
                    raise ValueError('Resolved configuration needs ordered propertySources: '+module)
                entries=[]
                for index,source in enumerate(snapshot['propertySources']):
                    if not isinstance(source,dict) or not isinstance(source.get('source'),dict):raise ValueError('Invalid resolved property source: '+module)
                    entries.extend({'key':key,'value':value,'file':'context:configuration.'+module,
                        'rank':(-index,), 'conditional':False} for key,value in source['source'].items() if value is not None)
                self.entries[module]=entries
                self.profiles[module]=names(snapshot.get('profiles',self.value(module,'spring.profiles.active','default')))
                continue
            self.entries[module]=self.select(module,(),base_only=True)
            active=self.value(module,'spring.profiles.active',None)
            if active is None:active=self.value(module,'spring.profiles.default','default')
            profiles=names(active);self.profiles[module]=() if profiles==('none',) else profiles
            self.entries[module]=self.select(module,self.profiles[module])
            enabled=self.value(module,'spring.cloud.config.enabled',True)
            uri=self.value(module,'spring.cloud.config.uri',None)
            if enabled is not False and str(enabled).lower()!='false' and uri is not None:
                self.unknown[module]='external Config Server environment is not supplied'
            unsupported=('spring.config.import','spring.config.location','spring.config.additional-location','spring.profiles.include')
            if any(self.raw(module,key,None) is not None for key in unsupported):
                self.unknown[module]='external/imported configuration or profile inclusion is outside the supplied fact subset'
            if any(row['key'].startswith('spring.profiles.group.') for row in self.entries[module]):
                self.unknown[module]='profile group expansion is outside the supplied fact subset'
            if module in self.unknown:self.profiles[module]=None

    def select(self,module,profiles,base_only=False):
        groups={}
        for row in self.rows:
            if row['module']==module:groups.setdefault((row.get('file',''),row.get('doc',0)),[]).append(row)
        selected=[]
        for (file,doc),rows in groups.items():
            path=PurePosixPath(file);match=re.fullmatch(r'(application|bootstrap)(?:-(.+))?',path.stem)
            profile=match[2] if match else None
            selectors=[r['value'] for r in rows if r['key'] in ('spring.profiles','spring.config.activate.on-profile')]
            if base_only and (profile or selectors):continue
            conditional=False;selected_profiles=[]
            for expression in ([profile] if profile else [])+selectors:
                result=matches(expression,profiles)
                if result is False:break
                conditional|=result is U;selected_profiles.extend(names(expression) or ())
            else:
                order=max((profiles.index(v)+1 for v in selected_profiles if profiles and v in profiles),default=0)
                rank=(int(not match or match[1]=='application'),int(bool(profile or selectors)),order,
                      int(path.parent.name=='config'),int(path.suffix=='.properties'),doc)
                selected.extend({**row,'rank':rank,'conditional':conditional} for row in rows)
        return selected

    def raw(self,module,key,default=U):
        rows=[row for row in self.entries.get(module,()) if row['key']==key]
        if not rows:return default
        possible=[]
        for rank in sorted({row['rank'] for row in rows},reverse=True):
            group=[row for row in rows if row['rank']==rank];possible.extend(row['value'] for row in group)
            if any(not row['conditional'] for row in group):break
        else:possible.append(default)
        return possible[0] if all(value==possible[0] for value in possible) else U

    def value(self,module,key,default=U,seen=frozenset()):
        self.used.setdefault(module,set()).add(key)
        if module in self.unknown or key in seen:return U
        value=self.raw(module,key,default)
        if not isinstance(value,str):return value
        for _ in range(32):
            match=re.search(r'\$\{([^{}]+)\}',value)
            if not match:return value if '${' not in value else U
            name,separator,fallback=match[1].partition(':')
            replacement=self.value(module,name,fallback if separator else U,seen|{key})
            if replacement is U or isinstance(replacement,(dict,list)):return U
            replacement=str(replacement).lower() if type(replacement) is bool else str(replacement)
            value=value[:match.start()]+replacement+value[match.end():]
        return U

    def context_path(self,module):
        modern=self.value(module,'server.servlet.context-path',None);legacy=self.value(module,'server.context-path',None)
        servlet=self.value(module,'spring.mvc.servlet.path',self.value(module,'server.servlet-path','/'))
        if servlet!='/':return U
        if modern is not None and legacy is not None and modern!=legacy:return U
        value=modern if modern is not None else legacy if legacy is not None else ''
        if value is U or not isinstance(value,str) or value and (not value.startswith('/') or value.endswith('/') or '?' in value or '#' in value):return U
        return value

    def summary(self):
        return {module:{'profiles':list(profiles) if profiles is not None else None,
            'unknown':self.unknown.get(module),'used_keys':sorted(self.used[module]),
            'provenance':[{'key':row['key'],'file':row.get('file'),'doc':row.get('doc'),'conditional':row['conditional']}
                for row in self.entries[module] if row['key'] in self.used[module]]} for module,profiles in self.profiles.items()}
