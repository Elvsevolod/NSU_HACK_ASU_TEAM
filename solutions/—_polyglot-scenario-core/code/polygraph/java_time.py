"""Bounded Java time bridge over CPython datetime and pinned IANA tzdata.

No host clock or system timezone files are read. Regional rules require an
explicit target tzdb version. Nanoseconds and years outside CPython's range
remain unsupported rather than rounded into different Java values.
"""
from datetime import date,datetime,time,timedelta,timezone
from functools import lru_cache
from importlib.resources import files
import re
from zoneinfo import ZoneInfo

import tzdata

from .values import Object,TypeRef,Unknown,Raised,unknown
from .models import NOT_HANDLED

EPOCH=datetime(1970,1,1,tzinfo=timezone.utc)
TYPES={'java.time.LocalDate','java.time.LocalDateTime','java.time.ZonedDateTime','java.time.Instant','java.util.Date'}


@lru_cache(maxsize=128)
def zone(name):
    # Validate resource components before opening package data, never TZPATH.
    if not re.fullmatch(r'[A-Za-z0-9_+-]+(?:/[A-Za-z0-9_+-]+)*',name):raise ValueError('Unsupported zone ID')
    with files('tzdata.zoneinfo').joinpath(*name.split('/')).open('rb') as stream:
        return ZoneInfo.from_file(stream,key=name)


def timezone_value(engine,value,span):
    if not isinstance(value,Object) or value.typ!='java.time.ZoneId':engine.unsupported('Unresolved Java timezone',span)
    name=value.fields.get('name')
    if not isinstance(name,str):engine.unsupported('Unknown Java timezone identifier',span)
    if name not in {'UTC','GMT','UT','Etc/UTC','Etc/GMT'} and engine.context.get('timezone_database')!=tzdata.IANA_VERSION:
        engine.unsupported('Regional Java time requires an explicit matching timezone_database ('+tzdata.IANA_VERSION+')',span)
    try:return zone('UTC' if name=='UT' else name)
    except (ValueError,OSError):engine.unsupported('Java ZoneId needs a fixed-offset, alias or unavailable IANA contract',span)


def now(engine,span):
    from .security_models import clock
    raw=engine.context.get('clock')
    if isinstance(raw,str) and re.search(r'\.\d{7,}',raw):engine.unsupported('Java nanosecond clock precision exceeds the datetime bridge',span)
    result=clock(engine)
    if unknown(result):engine.unsupported('Java current time requires an explicit analysis clock',span)
    try:return result.astimezone(timezone.utc)
    except OverflowError:engine.unsupported('Java clock exceeds the datetime bridge range',span)


def wrapped(engine,typ,value):return engine.state.new(typ,{'value':value})


def value(engine,obj,typ,span):
    if obj is None:raise Raised('NullPointerException')
    if not isinstance(obj,Object) or obj.typ!=typ or unknown(obj.fields.get('value')):
        engine.unsupported('Unresolved '+typ+' value',span)
    result=obj.fields.get('value')
    if typ=='java.time.LocalDate' and type(result) is date:return result
    if type(result) is datetime and ((result.tzinfo is None)==(typ=='java.time.LocalDateTime')):return result
    engine.unsupported('Invalid native value for '+typ,span)


def millis(instant):
    delta=instant-EPOCH
    return (delta.days*86400+delta.seconds)*1000+delta.microseconds//1000


def date_construct(engine,typ,args,kwargs,span):
    from .java_boxing import boxed,unbox
    args=tuple(unbox(value) if boxed(value) else value for value in args)
    qualified=engine.p.resolve_import(typ,span.file) or typ
    if qualified!='java.util.Date':return NOT_HANDLED
    if kwargs:return NOT_HANDLED
    if not args:instant=now(engine,span)
    elif len(args)==1 and type(args[0]) is int:
        try:instant=EPOCH+timedelta(milliseconds=args[0])
        except OverflowError:engine.unsupported('Java Date exceeds the datetime bridge year range',span)
    else:engine.unsupported('Unmodeled Java Date constructor overload',span)
    return wrapped(engine,'java.util.Date',EPOCH+timedelta(milliseconds=millis(instant)))


def call(engine,receiver,name,args,kwargs,span):
    typ=receiver.name if isinstance(receiver,TypeRef) else receiver.typ if isinstance(receiver,Object) else ''
    if typ not in TYPES|{'java.time.ZoneId'}:return NOT_HANDLED
    if name in {'of','ofEpochMilli'} and typ in {'java.time.LocalDate','java.time.LocalDateTime','java.time.Instant'}:
        from .java_boxing import boxed,unbox
        args=tuple(unbox(value) if boxed(value) else value for value in args)
    if kwargs:return NOT_HANDLED
    static=isinstance(receiver,TypeRef)
    if static and typ=='java.time.ZoneId' and name in {'of','systemDefault'}:
        if name=='systemDefault' and not args:identifier=engine.context.get('timezone')
        elif name=='of' and len(args)==1:identifier=args[0]
        else:return NOT_HANDLED
        if identifier is None:engine.unsupported('Java system timezone is not supplied',span)
        result=engine.state.new(typ,{'name':identifier});timezone_value(engine,result,span)
        return result
    if static and name=='now' and typ in {'java.time.LocalDate','java.time.Instant'}:
        instant=now(engine,span)
        if typ=='java.time.Instant' and not args:return wrapped(engine,typ,instant)
        if typ=='java.time.LocalDate' and len(args)<=1:
            selected=args[0] if args else engine.state.new('java.time.ZoneId',{'name':engine.context.get('timezone')})
            return wrapped(engine,typ,instant.astimezone(timezone_value(engine,selected,span)).date())
        return NOT_HANDLED
    if static and name=='of' and typ in {'java.time.LocalDate','java.time.LocalDateTime'}:
        counts={3} if typ.endswith('.LocalDate') else {5,6}
        if len(args) not in counts or any(type(arg) is not int for arg in args):return NOT_HANDLED
        if not 1<=args[0]<=9999:engine.unsupported('Java time year exceeds the datetime bridge range',span)
        try:result=date(*args) if typ.endswith('.LocalDate') else datetime(*args)
        except ValueError:raise Raised('DateTimeException') from None
        return wrapped(engine,typ,result)
    if static and typ=='java.time.Instant' and name=='ofEpochMilli' and len(args)==1 and type(args[0]) is int:
        try:return wrapped(engine,typ,EPOCH+timedelta(milliseconds=args[0]))
        except OverflowError:engine.unsupported('Java Instant exceeds the datetime bridge range',span)
    if static and typ=='java.util.Date' and name=='from' and len(args)==1:
        instant=value(engine,args[0],'java.time.Instant',span)
        return wrapped(engine,typ,EPOCH+timedelta(milliseconds=millis(instant)))
    if static:engine.unsupported('Java temporal static method '+typ+'.'+name,span)
    if typ=='java.time.ZoneId':
        if name in {'getId','toString'} and not args:return receiver.fields.get('name',Unknown('Unknown Java timezone ID'))
        engine.unsupported('Java ZoneId method '+name,span)
    current=value(engine,receiver,typ,span)
    if typ=='java.time.LocalDate' and name=='atStartOfDay' and not args:
        return wrapped(engine,'java.time.LocalDateTime',datetime.combine(current,time()))
    if typ=='java.time.LocalDateTime' and name=='atZone' and len(args)==1:
        selected=timezone_value(engine,args[0],span)
        # fold=0 selects the earlier offset in overlaps; round-trip through UTC
        # shifts nonexistent local times by the gap, as LocalDateTime.atZone.
        try:result=current.replace(tzinfo=selected,fold=0).astimezone(timezone.utc).astimezone(selected)
        except OverflowError:engine.unsupported('Zoned Java time exceeds the datetime bridge range',span)
        return wrapped(engine,'java.time.ZonedDateTime',result)
    if typ in {'java.time.ZonedDateTime','java.util.Date'} and name=='toInstant' and not args:
        return wrapped(engine,'java.time.Instant',current.astimezone(timezone.utc))
    if typ in {'java.time.Instant','java.util.Date'} and name==('getTime' if typ=='java.util.Date' else 'toEpochMilli') and not args:return millis(current)
    if name in {'equals','isBefore','isAfter','before','after'} and len(args)==1 and typ!='java.time.ZonedDateTime':
        if name=='equals' and (not isinstance(args[0],Object) or args[0].typ!=typ):return False
        other=value(engine,args[0],typ,span)
        return current==other if name=='equals' else current<other if name in {'isBefore','before'} else current>other
    if name=='toEpochDay' and typ=='java.time.LocalDate' and not args:return (current-date(1970,1,1)).days
    if name=='toString' and typ=='java.time.LocalDate' and not args:return current.isoformat()
    engine.unsupported('Java temporal instance method '+typ+'.'+name,span)
