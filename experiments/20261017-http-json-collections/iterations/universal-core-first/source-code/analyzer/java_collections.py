"""Constructor-owned values: JSON dictionaries cannot forge a Java Map type."""
from .state import U


class JavaObject(dict):
    """An object whose concrete class was observed at a source constructor."""
    def __init__(self, java_type, fields):
        super().__init__(fields)
        self.java_type = java_type


class JavaMap(dict):
    def __init__(self, values=None):
        # Keep the report representation stable, while retaining runtime identity.
        super().__init__(__map__={} if values is None else values)

    @property
    def mapping(self):
        return self['__map__']

    def invalidate(self):
        self['__map__'] = U


def raw_json_map(value):
    """Only called for a proven raw Java Map response type, never by key shape."""
    if isinstance(value,dict):
        # A typed abstract DTO still carries metadata that a JSON codec must
        # resolve from source; do not expose it as a fabricated user map entry.
        if '__type__' in value or any(type(key) is not str for key in value):
            return U
        return JavaMap({key:raw_json_map(item) for key,item in value.items()})
    if isinstance(value,list):
        return [raw_json_map(item) for item in value]
    return value
