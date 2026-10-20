"""Bounded Spring MVC named-value binding, separate from Java/JSON coercion.

Inputs are HTTP occurrences, None (proven absent), or U (unknown presence or
value). Failures are resolved at the dispatcher boundary, after servlet filters
and before invoking the handler. Custom conversion is explicitly unresolved.
"""
from copy import deepcopy
import re

from .state import U
from .generic_types import type_parts
from .java_exceptions import JavaThrow
from .java_collections import is_symbolic
from .models import uuid_value
from .symbolic_text import concat_text


class BindingFailure(Exception):
    def __init__(self, message, status=400):
        self.status = status
        super().__init__(message)


def conversion_customized(project, target):
    unit = project.ix.unit_of(target)
    cache = project.__dict__.setdefault('_http_binding_customizations', {})
    if unit not in cache:
        methods = [m for mid, m in project.methods.items() if project.ix.unit_of(mid) == unit]
        cache[unit] = any(m['name'] in ('addFormatters', 'addArgumentResolvers', 'setConversionService') or
                         any(a['name'].split('.')[-1] == 'InitBinder' for a in m.get('annotations', []))
                         for m in methods)
        for owner, parents in project.generic_parents.items():
            if unit not in project.ix.units.get(project.nodes[owner].get('module'), ()):
                continue
            for written in parents:
                base,args=type_parts(written)
                kind=base.rsplit('.',1)[-1]
                if kind in ('GenericConverter','Formatter','WebBindingInitializer'):
                    cache[unit]=True
                elif kind in ('Converter','ConverterFactory') and (not args or args[0] in ('String','java.lang.String','Object','java.lang.Object')):
                    cache[unit]=True
    return cache[unit]


def bind_named(engine, target, parameter, occurrences):
    meta = engine.p.methods[target]
    name, written = parameter['wire_name'], parameter['type']
    base, arguments = type_parts(written)
    native = lambda typ, fqn: engine.standard_type(typ, fqn, meta)

    def unknown(message):
        engine.approximate = True
        engine.assume('HTTP binding: ' + message + ': ' + name)
        engine.warnings.add('unresolved HTTP request binding: ' + message + ': ' + name)
        engine.operation_issues[('http_request_binding', message)] += 1
        return U

    optional = native(base, 'java.util.Optional')
    if parameter.get('binding_metadata_unknown'):
        return unknown('annotation constant or expression')
    if parameter['kind']=='RequestParam' and not parameter.get('explicit_name') and any(
            native(base,fqn) for fqn in ('java.util.Map','org.springframework.util.MultiValueMap')):
        return unknown('whole query map binding')
    if optional:
        if arguments is None or len(arguments) != 1:
            return unknown('Optional type argument')
        written = arguments[0]
    required = parameter['required'] and not optional
    if occurrences is U:
        return unknown('parameter presence or URL layout')
    default = parameter['default']
    if default is not U and ('${' in default or '#{' in default):
        return unknown('configured default expression')
    if occurrences is None and default is not U or occurrences == [''] and default is not U:
        occurrences = [default]
    if occurrences is None and required:
        raise BindingFailure('missing required ' + parameter['kind'] + ': ' + name,
                             500 if parameter['kind'] == 'PathVariable' else 400)
    if occurrences is not None and (conversion_customized(engine.p, target) or parameter.get('custom_conversion')):
        return unknown('custom converter or binder')

    def convert(values, typ):
        typ, args = type_parts(typ)
        if values is None:
            return None
        if values is U:
            return unknown('unknown parameter value')
        list_type = any(native(typ, 'java.util.' + n) for n in ('List', 'Collection', 'ArrayList'))
        if typ.endswith('[]') or list_type:
            element = typ[:-2] if typ.endswith('[]') else args[0] if args and len(args) == 1 else None
            if not element:
                return unknown('collection element type')
            if len(values) == 1:
                if not isinstance(values[0], str):
                    return unknown('comma-separated collection layout')
                values = [] if values[0] == '' else [s.strip() for s in values[0].split(',')]
            return [convert([value], element) for value in values]
        if native(typ, 'java.lang.String'):
            result = ''
            for i, value in enumerate(values):
                if value is U:
                    return unknown('unknown parameter text')
                result = concat_text(result, ',' if i else '')
                result = concat_text(result, value)
            return result
        if not values:
            return None
        # Spring's ArrayToObjectConverter uses the first value for scalars.
        value = values[0]
        if value is U or is_symbolic(value):
            if native(typ, 'java.util.UUID') and is_symbolic(value) and value.get('__uuid_text__'):
                return uuid_value(value)
            return unknown('unknown scalar conversion')
        if not isinstance(value, str):
            return unknown('non-text HTTP occurrence')
        widths = {'byte': 8, 'short': 16, 'int': 32, 'long': 64}
        boxes = {'Byte': 8, 'Short': 16, 'Integer': 32, 'Long': 64}
        bits = widths.get(typ) or next((bits for box, bits in boxes.items() if native(typ, 'java.lang.'+box)), None)
        if bits:
            if value == '':return None
            if not value.isascii():
                return unknown('non-ASCII number conversion')
            digits = re.sub(r'\s', '', value)
            sign = -1 if digits.startswith('-') else 1
            digits = digits[1:] if digits.startswith(('+', '-')) else digits
            radix = 16 if digits.startswith(('0x', '0X', '#')) else 10
            digits = digits[2:] if digits.startswith(('0x', '0X')) else digits[1:] if digits.startswith('#') else digits
            if not re.fullmatch('[0-9a-fA-F]+' if radix == 16 else '[0-9]+', digits):
                raise BindingFailure('invalid integer: ' + name)
            if len(digits.lstrip('0')) > (16 if radix == 16 else 19):
                raise BindingFailure('integer out of range: ' + name)
            digits=digits.lstrip('0') or '0'
            number = sign * int(digits, radix)
            if not -(1 << (bits-1)) <= number < (1 << (bits-1)):
                raise BindingFailure('integer out of range: ' + name)
            return number
        if typ == 'boolean' or native(typ, 'java.lang.Boolean'):
            value = value.strip().lower()
            if not value:
                return None
            if value in ('true', 'on', 'yes', '1'):
                return True
            if value in ('false', 'off', 'no', '0'):
                return False
            raise BindingFailure('invalid boolean: ' + name)
        if typ == 'char' or native(typ, 'java.lang.Character'):
            if value == '':return None
            if len(value.encode('utf-16-le', errors='surrogatepass')) != 2:
                raise BindingFailure('invalid character: ' + name)
            return value
        if native(typ, 'java.util.UUID'):
            if not value.strip():return None
            try:
                return uuid_value(value.strip())
            except JavaThrow:
                raise BindingFailure('invalid UUID: ' + name) from None
        return unknown('unsupported declared parameter type: ' + typ)

    result = convert(occurrences, written)
    if result is None and default is not U:
        result = convert([default], written)
    if result is None and required:
        raise BindingFailure('required parameter became null: ' + name)
    if result is None and written == 'boolean':
        result = False
    elif result is None and written in ('int', 'long', 'short', 'byte', 'char', 'float', 'double'):
        raise BindingFailure('null cannot bind to primitive: ' + name, 500)
    return {'__optional__': True, 'optional': result} if optional else deepcopy(result)
