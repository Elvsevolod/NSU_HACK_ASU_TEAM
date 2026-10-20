"""Canonical decimal wire text of a proven non-null Java integral value.

The origin remains symbolic. No concrete generated ID, digit count or sign is
chosen. Same-width default Spring parsing can recover that original value;
narrowing, custom converters and arbitrary opaque strings cannot.
"""
from copy import deepcopy

WIDTHS={'byte':8,'Byte':8,'short':16,'Short':16,'int':32,'Integer':32,'long':64,'Long':64}


def integral_text(value):
    if type(value) is not dict or not isinstance(value.get('__symbol__'),str) or not value['__symbol__']:return None
    written=value.get('__type__','')
    kind=written.removeprefix('java.lang.')
    bits=WIDTHS.get(kind)
    if bits is None or written!=kind and (kind[0].islower() or written!='java.lang.'+kind):return None
    if kind[0].isupper() and (not isinstance(value.get('__constraints__'),list) or 'non_null' not in value['__constraints__']):return None
    return {'__symbol__':value['__symbol__']+':decimal','__type__':'String','__constraints__':['non_null'],
            '__integral_text__':True,'__integral_bits__':bits,'__integral_origin__':deepcopy(value)}


def integral_origin(value):
    if type(value) is not dict or value.get('__integral_text__') is not True:return None
    origin=value.get('__integral_origin__')
    if value!=integral_text(origin):return None
    return deepcopy(origin),value['__integral_bits__']
