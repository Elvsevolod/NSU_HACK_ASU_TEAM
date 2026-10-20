"""Explicit uncertainty and object identity shared by both language adapters."""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import math
import operator


@dataclass(frozen=True)
class Unknown:
    reason: str
    typ: str = ""
    origin: str = ""

    def __bool__(self):
        raise TypeError("Unknown must be branched explicitly")


@dataclass(frozen=True)
class Symbol:
    identity: str
    typ: str
    nonnull: bool = True
    sort: str = ""


@dataclass(frozen=True)
class OpaqueString(Symbol):
    """A generated string whose actual random bytes are not source facts."""
    nonempty: bool = True


@dataclass(frozen=True)
class Formula:
    op: str
    args: tuple
    sort: str
    language: str
    operand_sort: str = ""


@dataclass(frozen=True)
class Text:
    """A string with symbolic pieces; it is never mistaken for concrete bytes."""
    parts: tuple


@dataclass
class Object:
    identity: str
    typ: str
    fields: dict = field(default_factory=dict)
    provided: set | None = None


@dataclass(frozen=True)
class TypeRef:
    name: str


@dataclass(frozen=True)
class FunctionRef:
    name: str


@dataclass(frozen=True)
class MethodRef:
    receiver: object
    name: str
    owner: str
    span: object
    qualifier_type: str = ''
    return_type: str = ''


@dataclass
class Awaitable:
    method: str
    args: tuple
    kwargs: dict
    receiver: object = None
    span: object = None
    library: bool = False


@dataclass
class Response:
    body: object = None
    status: object = 200
    headers: dict = field(default_factory=dict)
    headers_readonly: bool | None = None


@dataclass(frozen=True)
class Predicate:
    field: str
    op: str
    value: object


@dataclass
class Query:
    entity: str
    predicates: list = field(default_factory=list)
    offset: int = 0
    limit: int | None = None
    count: bool = False
    delete: bool = False


class Raised(Exception):
    def __init__(self, typ, value=None):
        super().__init__(typ)
        self.typ, self.value = typ, value


def unknown(value):
    return isinstance(value, (Unknown, Symbol, Text, Formula))


def symbolic(value):
    return isinstance(value, (Symbol, Formula)) and value.sort in {"bool", "int", "bv32", "bv64"}


def formula(op, left, right, language, typ=""):
    if not (symbolic(left) or symbolic(right)):
        return None
    if not all(symbolic(value) or type(value) in {int, bool} for value in (left, right)):
        return None
    comparisons = {"==", "!=", ">", "<", ">=", "<="}
    operations = comparisons | {"+", "-", "*", "//", "%", "&", "|", "^", "<<", ">>"}
    if language == "java":
        operations.update({"/", ">>>"})
    if op not in operations:
        return None
    if any(getattr(value, "sort", "") == "bool" for value in (left, right)) and op not in {"==", "!="}:
        return None
    wide = typ in {"long", "Long"} or getattr(left, "sort", "") == "bv64" or op not in {"<<", ">>", ">>>"} and getattr(right, "sort", "") == "bv64"
    operand_sort = "bool" if any(getattr(v, "sort", "") == "bool" for v in (left, right)) else "bv64" if language == "java" and wide else "bv32" if language == "java" else "int"
    return Formula(op, (left, right), "bool" if op in comparisons else operand_sort, language, operand_sort)


def truth(value, language="python"):
    if isinstance(value,OpaqueString) and language == 'python' and value.nonempty:
        return True
    if isinstance(value, (Unknown, Text, Formula)):
        return None
    if isinstance(value, Symbol):
        return None
    if language == "java":
        return value if type(value) is bool else None
    return bool(value)


def equal(left, right):
    symbolic_result = formula("==", left, right, "python")
    if symbolic_result is not None:
        return symbolic_result
    if isinstance(left, (Unknown, Text)) or isinstance(right, (Unknown, Text)):
        return Unknown("comparison depends on unknown value", "bool")
    if isinstance(left, Symbol) or isinstance(right, Symbol):
        if left == right:
            return True
        if left is None or right is None:
            symbol = right if left is None else left
            if isinstance(symbol, Symbol) and symbol.nonnull:
                return False
        return Unknown("symbolic equality", "bool")
    if isinstance(left, Object) or isinstance(right, Object):
        if isinstance(left, Object) and isinstance(right, Object):
            from .java_boxing import boxed
            if boxed(left) and boxed(right) and left.identity!=right.identity and left.typ==right.typ:
                value=equal(left.fields.get('value'),right.fields.get('value'))
                if value is not False and not (left.fields.get('fresh') or right.fields.get('fresh')):
                    return Unknown('Wrapper reference identity outside a guaranteed shared cache','boolean')
            return left.identity == right.identity
        return False
    return left == right


def integer(value, typ):
    widths = {"byte": 8, "short": 16, "int": 32, "Integer": 32, "long": 64, "Long": 64}
    if type(value) is int and typ in widths:
        bits = widths[typ]
        return (value + (1 << (bits - 1))) % (1 << bits) - (1 << (bits - 1))
    if symbolic(value) and typ in widths:
        # Narrow casts are sign-extended back to the Java arithmetic width.
        return Formula("cast:" + str(widths[typ]), (value,), "bv64" if widths[typ] == 64 else "bv32", "java")
    return value


def binary(op, left, right, language, typ=""):
    if language=='java':
        from .java_boxing import boxed,unbox
        references=op in {'==','!=','is','is not'}
        if not references or boxed(left) and type(right) in {int,bool,float} or boxed(right) and type(left) in {int,bool,float}:
            if boxed(left):left=unbox(left)
            if boxed(right):right=unbox(right)
    if language=='java' and isinstance(left,TypeRef) and isinstance(right,TypeRef) and op in {'==','!='}:
        return (left.name==right.name) if op=='==' else (left.name!=right.name)
    if isinstance(left, TypeRef) and op in {"==", "!=", ">", "<", ">=", "<="}:
        return Predicate(left.name, op, right)
    if op in {"/", "//", "%"} and type(right) is int and right == 0 and (type(left) is int or symbolic(left)):
        raise Raised("ArithmeticException" if language == "java" else "ZeroDivisionError")
    symbolic_result = formula(op, left, right, language, typ)
    if symbolic_result is not None:
        return symbolic_result
    if op in {"==", "is", "!=", "is not"}:
        result = equal(left, right)
        return (not result if op in {"!=", "is not"} else result) if type(result) is bool else result
    if op == "+" and (isinstance(left, Text) or isinstance(right, Text) or
                       language == "java" and (isinstance(left, str) or isinstance(right, str))):
        if isinstance(left, Unknown) or isinstance(right, Unknown):
            return Unknown("unknown string operand", "str")
        if isinstance(left, (Text, Symbol)) or isinstance(right, (Text, Symbol)):
            def pieces(value):
                return value.parts if isinstance(value, Text) else (value if isinstance(value, (str, Symbol)) else str(value),)
            return Text(pieces(left) + pieces(right))
    if unknown(left) or unknown(right):
        return Unknown("unknown operand: " + op, typ)
    if op == "+" and language == "java" and (isinstance(left, str) or isinstance(right, str)):
        def string(v):
            from .java_boxing import boxed,unbox
            if boxed(v):v=unbox(v)
            return "null" if v is None else str(v).lower() if type(v) is bool else str(v)
        return string(left) + string(right)
    if (left is None or right is None) and language == "java":
        raise Raised("NullPointerException")
    if language == "java" and op in {"/", "%"} and type(left) is int and type(right) is int:
        if right == 0:
            raise Raised("ArithmeticException")
        quotient = (abs(left) // abs(right)) * (-1 if (left < 0) != (right < 0) else 1)
        return integer(quotient if op == "/" else left - quotient * right, typ or "int")
    if language == "java" and op in {"<<", ">>", ">>>"} and type(left) is int and type(right) is int:
        width = 64 if typ in {"long", "Long"} else 32
        distance = right & (width - 1)
        result = left << distance if op == "<<" else (left & ((1 << width) - 1)) >> distance if op == ">>>" else left >> distance
        return integer(result, "long" if width == 64 else "int")
    operations = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv,
                  "//": operator.floordiv, "%": operator.mod, "**": operator.pow,
                  ">": operator.gt, "<": operator.lt, ">=": operator.ge, "<=": operator.le,
                  "in": lambda a, b: a in b, "not in": lambda a, b: a not in b,
                  "&": operator.and_, "|": operator.or_, "^": operator.xor,
                  "<<": operator.lshift, ">>": operator.rshift}
    if op not in operations:
        return Unknown("unsupported binary operator " + op, typ)
    try:
        result = operations[op](left, right)
        return integer(result, typ or "int") if language == "java" else result
    except (ValueError, TypeError, IndexError, ZeroDivisionError, OverflowError) as exc:
        raise Raised(type(exc).__name__) from None


def wire(value, active=frozenset()):
    if isinstance(value,MethodRef):return Unknown('Callable serialization requires an explicit codec contract')
    if type(value) in {datetime,date,time,timedelta}:
        from pydantic_core import to_jsonable_python
        return to_jsonable_python(value)
    if isinstance(value, (Object, dict, list, tuple)):
        if id(value) in active or len(active) >= 128:
            return Unknown("wire cycle or depth requires an unmodeled serializer")
        active = active | {id(value)}
    if isinstance(value, Object):
        from .java_boxing import boxed,unbox
        if boxed(value):return wire(unbox(value),active)
        if value.typ=='java.util.stream.Stream':return Unknown('Java stream serialization requires an explicit codec contract')
        if value.typ in {'java.util.HashSet','java.util.LinkedHashSet'}:
            items=value.fields.get('values')
            if not isinstance(items,list):return Unknown('Java set state is unknown')
            if value.typ=='java.util.HashSet' and len(items)>1:return Unknown('Unordered Java set serialization requires an order contract')
            return wire(items,active)
        if value.typ.startswith('java.time.') or value.typ=='java.util.Date':
            return Unknown('Java temporal serialization requires an explicit codec contract')
        if value.typ in {'spring.HttpHeaders', 'spring.ReadOnlyHttpHeaders'}:
            return wire(value.fields.get('values'), active)
        return {k: wire(v, active) for k, v in value.fields.items()}
    if isinstance(value, dict):
        from .java_boxing import MapKey
        if any(isinstance(key,MapKey) for key in value):return Unknown('Java map key serialization requires a codec contract')
        return {k: wire(v, active) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [wire(v, active) for v in value]
    return value


def wire_incomplete(value):
    if isinstance(value, Unknown):
        return value.reason in {"wire cycle or depth requires an unmodeled serializer",'Java temporal serialization requires an explicit codec contract','Callable serialization requires an explicit codec contract','Java stream serialization requires an explicit codec contract','Unordered Java set serialization requires an order contract','Java map key serialization requires a codec contract'}
    return any(wire_incomplete(item) for item in (value.values() if isinstance(value, dict) else value)) if isinstance(value, (dict, list, tuple)) else False


def serial(value, active=frozenset()):
    if type(value) in {datetime,date,time,timedelta}:
        from pydantic_core import to_jsonable_python
        return to_jsonable_python(value)
    if isinstance(value, (dict, list, tuple, set)) or hasattr(value, "__dataclass_fields__"):
        if id(value) in active or len(active) >= 128:
            return {"kind": "Unknown", "reason": "diagnostic cycle or depth limit"}
        active = active | {id(value)}
    if isinstance(value, Decimal):
        return {"kind": "Decimal", "value": str(value)}
    if isinstance(value, (Unknown, Symbol, Text, Object, TypeRef, FunctionRef, Awaitable, Response, Query, Predicate)):
        return {"kind": type(value).__name__, **{k: serial(v, active) for k, v in vars(value).items()}}
    if hasattr(value, "__dataclass_fields__"):
        return {"kind": type(value).__name__, **{k: serial(v, active) for k, v in vars(value).items()}}
    if isinstance(value, dict):
        return {str(k): serial(v, active) for k, v in value.items()}
    if isinstance(value, set):
        return [serial(v, active) for v in sorted(value, key=str)]
    if isinstance(value, (list, tuple)):
        return [serial(v, active) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return {"kind": "Unknown", "reason": "nonfinite JSON number"}
    return value
