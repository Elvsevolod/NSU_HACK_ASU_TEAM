"""Pure compatibility for the supported native collection runtime classes."""
from .native_arrays import JavaArray
from .native_storage import JavaList


def collection_compatibility(engine, value, wanted):
    """True/False are proved; None leaves other reference rules responsible."""
    kinds = [name for name in ('List', 'Set', 'Collection')
             if engine.standard_type(wanted, 'java.util.' + name)]
    if engine.standard_type(wanted, 'java.lang.Iterable'):
        kinds.append('Iterable')
    if not kinds:
        return None
    if value is None:
        return True
    if isinstance(value, JavaArray):
        return False
    if not isinstance(value, JavaList):
        return None
    flavor = value.flavor
    if flavor not in ('ArrayList', 'LinkedList', 'Arrays.ArrayList', 'List', 'HashSet','Set','Collection'):
        return None
    if kinds[0] in ('Collection', 'Iterable'):
        return True
    if flavor=='Collection':return None
    return (flavor in ('HashSet','Set')) == (kinds[0] == 'Set')
