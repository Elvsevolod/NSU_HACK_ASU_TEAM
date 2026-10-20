"""Resolved native signatures shared by type inference and execution.

These are language/library contracts, never project method-name shortcuts.
Unsupported values keep the resolved return type without an opaque heap effect.
"""
from dataclasses import dataclass

from .state import U
from .java_exceptions import JavaThrow
from .java_strings import split, is_blank


@dataclass(frozen=True)
class NativeCall:
    owner: str
    name: str
    parameters: tuple
    result_type: str
    effects: tuple = ()
    completions: tuple = ('normal', 'specified_runtime_exception')


def resolve(receiver, name, arguments, standard):
    if standard(receiver,'org.slf4j.Logger'):
        logging=name in ('debug','info','warn','error','trace')
        if logging and arguments and standard(arguments[0],'java.lang.String'):
            return NativeCall('org.slf4j.Logger',name,tuple(arguments),'void',('formatting_callbacks',),('normal','provider_failure_boundary'))
    if not standard(receiver, 'java.lang.String'):return None
    string=lambda typ:standard(typ,'java.lang.String') or standard(typ,'java.lang.CharSequence')
    integer=lambda typ:typ in ('byte','short','char','int')
    count=len(arguments)
    result=None
    if name in ('toString','trim','strip') and count==0:result='java.lang.String'
    elif name in ('toLowerCase','toUpperCase') and (count==0 or count==1 and standard(arguments[0],'java.util.Locale')):result='java.lang.String'
    elif name=='replace' and count==2 and (all(typ=='char' for typ in arguments) or all(string(typ) for typ in arguments)):result='java.lang.String'
    elif name=='substring' and count in (1,2) and all(integer(typ) for typ in arguments):result='java.lang.String'
    elif name=='charAt' and count==1 and integer(arguments[0]):result='char'
    elif name=='split' and count in (1,2) and string(arguments[0]) and (count==1 or integer(arguments[1])):result='java.lang.String[]'
    elif name=='length' and count==0:result='int'
    elif name in ('isEmpty','isBlank') and count==0:result='boolean'
    elif name in ('equals','equalsIgnoreCase','contains','startsWith','endsWith') and count==1:result='boolean'
    if result:return NativeCall('java.lang.String',name,tuple(arguments),result)
    return None


def utf16(value):
    raw=value.encode('utf-16-le',errors='surrogatepass')
    return ''.join(chr(int.from_bytes(raw[index:index+2],'little')) for index in range(0,len(raw),2))


def from_utf16(value):
    return b''.join(ord(char).to_bytes(2,'little') for char in value).decode('utf-16-le',errors='surrogatepass')


def string_call(contract, receiver, arguments, symbol, issue, locale=U):
    name=contract.name
    def unknown(reason=None, length=None):
        if reason:issue(reason)
        if contract.result_type!='java.lang.String':return U
        result={'__symbol__':symbol(),'__type__':'String','__constraints__':['non_null'],
                '__generation__':'java.lang.String.'+name}
        if length is not None:result['__length__']=length
        return result
    if receiver is None:raise JavaThrow({'__type__':'NullPointerException'})
    if name in ('contains','startsWith','endsWith','equalsIgnoreCase','replace','split') and any(arg is None for arg in arguments):
        # equalsIgnoreCase(null) is false; equals(null) is handled below.
        if name=='equalsIgnoreCase':return False
        raise JavaThrow({'__type__':'NullPointerException'})
    if isinstance(receiver,dict) and receiver.get('__type__') in ('String','java.lang.String'):
        if name=='toString':return receiver
        if name=='length':
            if '__length__' in receiver:return receiver['__length__']
            if '__min_length__' in receiver:return {'__symbol__':receiver['__symbol__']+':length','__type__':'int',
                '__interval__':{'low':receiver['__min_length__'],'low_closed':True,'high':None}}
            return U
        if name=='isEmpty' and '__length__' in receiver:return receiver['__length__']==0
        length=receiver.get('__length__') if name=='replace' and contract.parameters==('char','char') else None
        return unknown(length=length)
    if not isinstance(receiver,str):return unknown('String receiver value is unknown')
    if name=='toString':return receiver
    if name=='length':return len(utf16(receiver))
    if name=='isEmpty':return not receiver
    if name=='isBlank':return is_blank(receiver)
    if name=='trim':return receiver.strip(''.join(chr(i) for i in range(33)))
    if name=='strip':
        start,end=0,len(receiver)
        while start<end and is_blank(receiver[start]):start+=1
        while end>start and is_blank(receiver[end-1]):end-=1
        return receiver[start:end]
    if name in ('toLowerCase','toUpperCase'):
        if locale is U:
            # All supported Java locale variants agree on plain ASCII text
            # except i/I. This is an invariant, not an assumed default locale.
            sensitive='I' if name=='toLowerCase' else 'i'
            if receiver.isascii() and sensitive not in receiver:
                return receiver.lower() if name=='toLowerCase' else receiver.upper()
            return unknown('String case conversion requires a known default or explicit locale')
        # Stable mappings common to the supported Java Unicode versions. Do
        # not use Python's entire Unicode database as an unstated JVM version.
        if not all(ord(char)<256 or char in 'İı' or '\uff00'<=char<='\uffef' for char in receiver):
            return unknown('String case conversion outside the supported Unicode mapping subset')
        if locale not in ('root','en','tr','az'):
            return unknown('String case conversion locale is outside the supported subset')
        if locale in ('tr','az'):
            receiver=receiver.replace('I','ı').replace('İ','i') if name=='toLowerCase' else receiver.replace('i','İ').replace('ı','I')
        return receiver.lower() if name=='toLowerCase' else receiver.upper()
    if name=='replace':
        if not all(isinstance(arg,str) for arg in arguments):return unknown('String replacement value is unknown')
        return from_utf16(utf16(receiver).replace(*(utf16(arg) for arg in arguments)))
    if name in ('substring','charAt'):
        if not all(type(arg) is int for arg in arguments):return unknown('String index value is unknown')
        value=utf16(receiver)
        start=arguments[0];end=arguments[1] if len(arguments)>1 else len(value)
        if start<0 or start>len(value) or end<start or end>len(value) or name=='charAt' and start==len(value):
            raise JavaThrow({'__type__':'StringIndexOutOfBoundsException'})
        return value[start] if name=='charAt' else from_utf16(value[start:end])
    if name=='split':return split(receiver,arguments[0],arguments[1] if len(arguments)>1 else 0,issue)
    if name=='equals':return receiver==arguments[0] if type(arguments[0]) in (str,bool,int,float) or arguments[0] is None else U
    if name=='equalsIgnoreCase':
        if not isinstance(arguments[0],str):return U
        if receiver.isascii() and arguments[0].isascii():return receiver.lower()==arguments[0].lower()
        issue('String.equalsIgnoreCase non-ASCII character mapping is unresolved');return U
    if name in ('contains','startsWith','endsWith'):
        if not isinstance(arguments[0],str):return U
        return arguments[0] in receiver if name=='contains' else receiver.startswith(arguments[0]) if name=='startsWith' else receiver.endswith(arguments[0])
    return unknown()
