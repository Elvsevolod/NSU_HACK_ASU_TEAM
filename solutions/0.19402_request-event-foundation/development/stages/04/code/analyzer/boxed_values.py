"""The Java class of a boxed scalar is separate from its Python payload."""
from .state import U


def value_kind(value,hint=None):
    aliases={'int':'Integer','long':'Long','short':'Short','byte':'Byte','char':'Character',
             'boolean':'Boolean','float':'Float','double':'Double'}
    kind=aliases.get(hint,hint)
    if isinstance(kind,str) and kind.startswith('java.lang.'):kind=kind.removeprefix('java.lang.')
    if kind in ('String','Integer','Long','Short','Byte','Character','Boolean','Float','Double'):return kind
    if type(value) is dict and value.get('__type__') in ('String','java.lang.String') and '__symbol__' in value:return 'String'
    if hint is None:return {str:'String',int:'Integer',bool:'Boolean',float:'Double'}.get(type(value))
    return None


def json_value_kind(value):
    """JSON string/boolean classes, without guessing integer wrapper widths."""
    if type(value) in (str,bool):return value_kind(value)
    if type(value) is dict and value.get('__type__') in ('String','java.lang.String') and '__symbol__' in value:
        return 'String'
    return None


def boxed_equal(left,right,left_kind,right_kind,text_equal):
    if left is U or right is U:return U
    if left is None or right is None:return left is None and right is None
    if left_kind is None or right_kind is None:return U
    if left_kind!=right_kind:return False
    if left_kind in ('String','Character'):
        if isinstance(left,str) and isinstance(right,str):return left==right
        if left_kind=='String' and all(isinstance(value,(str,dict)) for value in (left,right)):
            return text_equal(left,right)
    if left_kind in ('Integer','Long','Short','Byte') and type(left) is int and type(right) is int:return left==right
    if left_kind=='Boolean' and type(left) is bool and type(right) is bool:return left==right
    # Floating-point rounding, signed zero and NaN require their own model.
    return U
