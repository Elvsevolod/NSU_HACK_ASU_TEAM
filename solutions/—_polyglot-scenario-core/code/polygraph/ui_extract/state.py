"""Value sentinels only; no legacy Java state or database layer."""
from enum import Enum

class Unknown(Enum):
    VALUE = 'unknown'


U = Unknown.VALUE


class JavaScriptValue(Enum):
    UNDEFINED = 'javascript undefined'


JS_UNDEFINED = JavaScriptValue.UNDEFINED


class SymbolicValue(dict):
    """Internal value tag; ordinary application dictionaries cannot forge it."""


class JSONObject(dict):
    """Complete JSON/literal object; an absent property is JS undefined."""

