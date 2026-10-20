"""Bounded JDK String bytes and basic Base64; charset is an observed input."""
import base64
from dataclasses import dataclass
from .native_arrays import JavaArray
from .java_exceptions import JavaThrow
from .project import text
from .state import U


@dataclass(frozen=True)
class Charset:
    name: str


class BasicEncoder:pass


CHARSETS={'UTF_8':'utf-8','US_ASCII':'ascii','ISO_8859_1':'latin-1',
          'UTF_16BE':'utf-16-be','UTF_16LE':'utf-16-le','UTF_16':'utf-16-be'}


def boundary(message):
    from .engine import AnalysisBoundary
    raise AnalysisBoundary('JDK byte conversion boundary: '+message,category='unsupported_semantics')


def call(engine,node,name,receiver,args,reason):
    qualifier=node.child_by_field_name('object')
    if name=='getBytes' and len(args)<=1 and engine.standard_type(engine.source_type(qualifier),'java.lang.String'):
        if receiver is None or args and args[0] is None:raise JavaThrow({'__type__':'NullPointerException'})
        if not isinstance(receiver,str):boundary('String input is unknown: '+reason)
        if args:charset=args[0].name if isinstance(args[0],Charset) else args[0]
        else:
            supplied=engine.state.context;raw=supplied.get('raw',{})
            charset=supplied.get('java_default_charset',supplied.get('charset',raw.get('java_default_charset',raw.get('charset'))))
            if not charset:boundary('platform default charset is not supplied: '+reason)
        if not isinstance(charset,str):boundary('charset is unknown: '+reason)
        key=charset.upper().replace('-','_')
        if key not in CHARSETS:boundary('charset is outside the supported standard subset: '+charset)
        if any(0xd800<=ord(c)<=0xdfff for c in receiver):boundary('malformed UTF-16 replacement policy is outside scope')
        payload=receiver.encode(CHARSETS[key],errors='replace')
        if key=='UTF_16':payload=b'\xfe\xff'+payload
        return True,JavaArray([value if value<128 else value-256 for value in payload],'byte',['Byte']*len(payload))
    if name=='getEncoder' and not args and engine.standard_type(text(qualifier),'java.util.Base64'):
        return True,BasicEncoder()
    if isinstance(receiver,BasicEncoder) and name=='encodeToString' and len(args)==1:
        values=args[0]
        if values is None:raise JavaThrow({'__type__':'NullPointerException'})
        if (not isinstance(values,JavaArray) or values.component!='byte' or values.opaque or not values.order_known
                or any(type(value) is not int or not -128<=value<=127 for value in values)):
            boundary('Base64 byte sequence is not observed: '+reason)
        engine.remember_reference_kind('String')
        return True,base64.b64encode(bytes(value%256 for value in values)).decode('ascii')
    return False,U
