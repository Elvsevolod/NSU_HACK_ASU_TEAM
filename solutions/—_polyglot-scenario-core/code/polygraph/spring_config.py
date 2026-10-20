"""Bounded, deployment-scoped Spring properties from supplied configuration.

PyYAML and javaproperties own parsing. No process environment, Config Server,
Maven execution, or application initializer is consulted.
"""
from dataclasses import dataclass
from pathlib import PurePosixPath
import re
import xml.etree.ElementTree as ET

import javaproperties
import yaml

from .ir import Span
from .values import Unknown,unknown


@dataclass(frozen=True)
class Entry:
    value: object
    file: str
    line: int
    rank: tuple
    conditional: bool=False


def parse(file,raw):
    """Flattened documents with original key locations; no target code runs."""
    if file.endswith('.properties'):
        values={};line=1
        for item in javaproperties.parse(raw):
            if isinstance(item,javaproperties.KeyValue):values[item.key]=(item.value,line)
            line+=len(item.source.splitlines())
        return [values]
    documents=[];loader=yaml.SafeLoader(raw)
    try:
        while loader.check_data():
            node=loader.get_node();documents.append((loader.construct_document(node),node))
    finally:loader.dispose()
    result=[]
    for document,node in documents:
        if document is None:continue
        if not isinstance(document,dict):raise ValueError('Configuration YAML root is not a mapping')
        values={}
        def visit(value,current,prefix='',active=frozenset()):
            if isinstance(value,(dict,list)):
                if id(value) in active or len(active)>64:raise ValueError('Recursive/deep configuration YAML')
                active=active|{id(value)}
            if isinstance(value,dict):
                locations={key.value:child for key,child in current.value}
                for key,child in value.items():
                    if not isinstance(key,str):raise ValueError('Nonstring YAML configuration key')
                    visit(child,locations[key],prefix+'.'+key if prefix else key,active)
            elif isinstance(value,list):
                for index,child in enumerate(value):visit(child,current.value[index],prefix+'['+str(index)+']',active)
                if not value:values[prefix]=('',current.start_mark.line+1)
            else:values[prefix]=('' if value is None else value,current.start_mark.line+1)
        visit(document,node);result.append(values)
    return result


def names(value):
    if isinstance(value,list):return tuple((str(v).lower() if type(v) is bool else str(v)).strip() for v in value)
    return tuple(v.strip() for v in str(value).split(',') if v.strip())


def matches(expression,profiles):
    if profiles is None or not isinstance(expression,str) or re.search(r'[&|()]',expression):return None
    return any((value[1:] not in profiles) if value.startswith('!') else value in profiles for value in names(expression))


class SpringConfiguration:
    def __init__(self,project,sources,build_sources,provided,profiles):
        self.p,self.sources,self.provided=project,sources,provided
        if not isinstance(provided,dict):raise ValueError('Configuration must map deployment names to Spring environments')
        self.entries={};self.profiles={};self.remote_unknown=set();self.unsupported=set();self.used={}
        self.boot={};self.documents={}
        self.explicit_profiles=tuple(dict.fromkeys(profiles))
        for key,meta in project.modules.items():
            module=meta.get('name',key.removeprefix('module:'));root=meta.get('path',meta.get('name','')).strip('/')
            self.boot[module]=self.boot_version(root,build_sources)
            self.load(module,root)

    def docs(self,file):
        if file not in self.documents:
            try:self.documents[file]=parse(file,self.sources[file])
            except (ValueError,RecursionError,yaml.YAMLError,javaproperties.InvalidUEscapeError) as exc:
                self.documents[file]=None
                self.p.warn('configuration-parse','Configuration cannot be resolved: '+str(exc),Span(file,1))
        return self.documents[file]

    @staticmethod
    def boot_version(root,sources):
        file=(root+'/' if root else '')+'pom.xml';seen=set()
        while file in sources and file not in seen:
            seen.add(file)
            try:node=ET.fromstring(sources[file])
            except ET.ParseError:return ''
            parent=node.find('{*}parent')
            if parent is None:return ''
            group=parent.findtext('{*}groupId');artifact=parent.findtext('{*}artifactId');version=parent.findtext('{*}version','')
            if group=='org.springframework.boot' and artifact=='spring-boot-starter-parent':
                return version if '${' not in version else ''
            relative=parent.findtext('{*}relativePath','../pom.xml')
            if not relative:return ''
            parts=[]
            for part in (PurePosixPath(file).parent/PurePosixPath(relative)).parts:
                if part=='..':
                    if not parts:return ''
                    parts.pop()
                elif part!='.':parts.append(part)
            file='/'.join(parts)
        return ''

    def add(self,module,key,value,file,line,rank,conditional=False):
        self.entries.setdefault(module,{}).setdefault(key,[]).append(Entry(value,file,line,rank,conditional))

    def local_files(self,root):
        main=(root+'/' if root else '')+'src/main/resources'
        resource_roots={main} if any(file.startswith(main+'/') for file in self.sources) else set()
        # Small supplied source roots need not be Maven projects.
        if not resource_roots:resource_roots={root or '.'}
        result=[]
        for file in self.sources:
            path=PurePosixPath(file)
            for resource in resource_roots:
                parent=path.parent.as_posix();base=resource.rstrip('/')
                if parent not in {base,base+'/config' if base!='.' else 'config'}:continue
                stem=path.stem;match=re.fullmatch(r'(application|bootstrap)(?:-(.+))?',stem)
                if match:result.append((file,match[1],match[2],int(parent.endswith('/config') or parent=='config')))
        return result

    def load(self,module,root):
        self.entries[module]={};files=self.local_files(root)
        snapshot=self.provided.get(module)
        if snapshot is not None:
            if not isinstance(snapshot,dict) or not isinstance(snapshot.get('propertySources'),list):raise ValueError('Spring environment needs ordered propertySources for '+module)
            if 'profiles' in snapshot and (not isinstance(snapshot['profiles'],list) or any(not isinstance(v,str) for v in snapshot['profiles'])):raise ValueError('Invalid Spring environment profiles for '+module)
            if self.explicit_profiles and 'profiles' in snapshot and self.explicit_profiles!=(tuple(snapshot['profiles']) or ('default',)):raise ValueError('Resolved Spring environment profiles conflict with CLI profiles for '+module)
            for index,source in enumerate(snapshot['propertySources']):
                if not isinstance(source,dict) or not isinstance(source.get('source'),dict) or any(not isinstance(k,str) for k in source['source']):raise ValueError('Invalid Spring property source for '+module)
                for key,value in source['source'].items():
                    if value is not None:self.add(module,key,value,'context:configuration.'+module+'.propertySources.'+str(index),0,(-index,))
            active=self.value(module,'spring.profiles.active',None)
            self.profiles[module]=tuple(snapshot['profiles']) or ('default',) if 'profiles' in snapshot else names(active) if active is not None and not unknown(active) else None
            if self.raw(module,'spring.mvc.servlet.path','/')!='/' or self.raw(module,'server.servlet-path','/')!='/':self.unsupported.add(module)
            return
        # Read bootstrap/application base documents first to establish the
        # supplied active profiles. A sibling deployment cannot affect them.
        for file,kind,profile,location in files:
            if profile:continue
            docs=self.docs(file)
            if docs is None:self.unsupported.add(module);continue
            for index,doc in enumerate(docs):
                if 'spring.profiles' in doc or 'spring.config.activate.on-profile' in doc:continue
                for key,(value,line) in doc.items():self.add(module,key,value,file,line,(kind=='application',0,location,index))
        active=self.value(module,'spring.profiles.active',None)
        if active is None:active=self.value(module,'spring.profiles.default',None)
        self.profiles[module]=self.explicit_profiles or (names(active) if active is not None and not unknown(active) else None)
        self.entries[module]={}
        for file,kind,profile,location in files:
            if profile:
                selected=matches(profile,self.profiles[module])
                if selected is False:continue
            else:selected=True
            docs=self.docs(file)
            if docs is None:self.unsupported.add(module);continue
            for index,doc in enumerate(docs):
                condition=selected
                selector=doc.get('spring.profiles')
                modern=doc.get('spring.config.activate.on-profile')
                version=self.boot[module]
                if modern and not version:self.unsupported.add(module)
                if selector and version and not version.startswith(('1.','2.0.','2.1.','2.2.','2.3.')):self.unsupported.add(module)
                if modern and not version.startswith(('1.','2.0.','2.1.','2.2.','2.3.')):selector=modern
                if selector:
                    current=matches(str(selector[0]),self.profiles[module])
                    condition=False if current is False or condition is False else None if current is None or condition is None else True
                if condition is False:continue
                order=max((self.profiles[module].index(v)+1 for v in names(profile or (selector[0] if selector else '')) if self.profiles[module] and v in self.profiles[module]),default=0)
                for key,(value,line) in doc.items():self.add(module,key,value,file,line,(kind=='application',int(bool(profile or selector)),order,location,index),condition is None)
        enabled=self.value(module,'spring.cloud.config.enabled',True)
        disabled=enabled is False or isinstance(enabled,str) and enabled.lower()=='false'
        if not disabled and self.raw(module,'spring.cloud.config.uri',None) is not None:
            self.remote_unknown.add(module)
            if not self.explicit_profiles:self.profiles[module]=None
        if any(self.raw(module,key,None) is not None for key in ['spring.config.location','spring.config.additional-location','spring.config.import']):self.unsupported.add(module)
        if self.raw(module,'spring.config.name','application')!='application':self.unsupported.add(module)
        if self.raw(module,'spring.mvc.servlet.path','/')!='/' or self.raw(module,'server.servlet-path','/')!='/':self.unsupported.add(module)
        if any(key=='spring.profiles.include' or key.startswith(('spring.profiles.include[','spring.profiles.group.')) or key.startswith('spring.config.activate.') and key!='spring.config.activate.on-profile' for key in self.entries[module]):self.unsupported.add(module)
        if module in self.unsupported:self.profiles[module]=None

    def raw(self,module,key,default=None):
        entries=self.entries.get(module,{}).get(key,[])
        if not entries:return default
        possible=[]
        for rank in sorted({entry.rank for entry in entries},reverse=True):
            group=[entry for entry in entries if entry.rank==rank]
            possible.extend(entry.value for entry in group)
            if any(not entry.conditional for entry in group):break
        else:possible.append(default)
        if any(value!=possible[0] for value in possible[1:]):return Unknown('Conditional/conflicting configuration '+key,origin=module)
        return possible[0]

    def value(self,module,key,default=None,seen=frozenset()):
        if module in self.remote_unknown or module in self.unsupported:return Unknown('Unresolved external/unsupported configuration source',origin=module)
        if key in seen:return Unknown('Cyclic configuration placeholder',origin=key)
        if key not in self.entries.get(module,{}) and key+'[0]' in self.entries.get(module,{}):
            value=[];index=0
            while key+'['+str(index)+']' in self.entries[module]:
                value.append(self.value(module,key+'['+str(index)+']',seen=seen|{key}));index+=1
            return value
        value=self.raw(module,key,default)
        self.used.setdefault(module,set()).add(key)
        if not isinstance(value,str):return value
        for _ in range(32):
            found=re.search(r'\$\{([^{}]+)\}',value)
            if not found:return value
            name,separator,fallback=found[1].partition(':')
            replacement=self.value(module,name,fallback if separator else Unknown('Unresolved configuration placeholder',origin=name),seen|{key})
            if unknown(replacement):return replacement
            if isinstance(replacement,(dict,list)):return Unknown('Non-scalar configuration placeholder',origin=name)
            text=str(replacement).lower() if type(replacement) is bool else str(replacement)
            value=value[:found.start()]+text+value[found.end():]
        return Unknown('Configuration placeholder expansion budget',origin=key)

    def context_path(self,module):
        if module in self.remote_unknown or module in self.unsupported:return Unknown('Unresolved external/unsupported configuration source',origin=module)
        version=self.boot.get(module,'');modern=self.value(module,'server.servlet.context-path',None);legacy=self.value(module,'server.context-path',None)
        if version.startswith('1.'):value=legacy
        elif version:value=modern
        elif modern is not None and legacy is not None and modern!=legacy:return Unknown('Servlet context-path version is ambiguous',origin=module)
        else:value=modern if modern is not None else legacy
        if value is None:return ''
        if unknown(value):return value
        if not isinstance(value,str) or value and (not value.startswith('/') or value.endswith('/') or '?' in value or '#' in value):return Unknown('Invalid/unmodeled servlet context path',origin=module)
        return value

    def summary(self):
        from .values import serial
        return {module:{'spring_boot':self.boot[module],'profiles':self.profiles[module],'context_path':serial(self.context_path(module)),
                        'used':{key:[{'file':entry.file,'line':entry.line,'conditional':entry.conditional} for entry in self.entries.get(module,{}).get(key,[])] for key in sorted(self.used.get(module,set()))}}
                for module in self.entries}
