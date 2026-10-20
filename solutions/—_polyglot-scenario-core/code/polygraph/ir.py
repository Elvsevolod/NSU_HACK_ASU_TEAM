"""The shared IR. It contains no parser nodes and no application-specific rules."""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Span:
    file: str = ""
    line: int = 0
    column: int = 0


@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple = ()
    value: Any = None
    span: Span = Span()
    typ: str = ""
    bindings: tuple = ()
    operand_type: str = ""


@dataclass(frozen=True)
class Stmt:
    op: str
    args: tuple = ()
    body: tuple = ()
    other: tuple = ()
    value: Any = None
    span: Span = Span()


@dataclass
class Parameter:
    name: str
    typ: str = ""
    location: str = ""
    alias: str = ""
    default: Expr | None = None
    dependency: str = ""
    annotations: dict = field(default_factory=dict)


@dataclass
class Method:
    key: str
    name: str
    owner: str
    module: str
    language: str
    span: Span
    params: list[Parameter]
    return_type: str = ""
    skeleton_id: str = ""
    body: tuple | None = None
    abstract: bool = False
    transaction: bool = False
    doc: str = ""
    annotations: dict = field(default_factory=dict)


@dataclass
class TypeInfo:
    key: str
    name: str
    module: str
    language: str
    span: Span
    fields: dict = field(default_factory=dict)
    parents: list = field(default_factory=list)
    methods: list = field(default_factory=list)
    table: str = ""
    columns: dict = field(default_factory=dict)
    primary_key: str = "id"
    generated_key: bool = False
    repository_entity: str = ""
    annotations: dict = field(default_factory=dict)


@dataclass
class Endpoint:
    method: str
    verb: str
    path: str
    module: str
    framework: str
    status: int = 200
    dependencies: list = field(default_factory=list)
    conditions: dict = field(default_factory=dict)
    response_type: str = ""


def pack(value):
    if isinstance(value, (Expr, Stmt, Span)):
        return {"@": type(value).__name__, **{k: pack(v) for k, v in vars(value).items()}}
    if isinstance(value, tuple):
        return {"@": "tuple", "items": [pack(v) for v in value]}
    if isinstance(value, list):
        return [pack(v) for v in value]
    if isinstance(value, dict):
        return {k: pack(v) for k, v in value.items()}
    return value


def unpack(value):
    if isinstance(value, list):
        return [unpack(v) for v in value]
    if isinstance(value, dict):
        kind = value.get("@")
        if kind == "tuple":
            return tuple(unpack(v) for v in value["items"])
        if kind in {"Expr", "Stmt", "Span"}:
            cls = {"Expr": Expr, "Stmt": Stmt, "Span": Span}[kind]
            return cls(**{k: unpack(v) for k, v in value.items() if k != "@"})
        return {k: unpack(v) for k, v in value.items()}
    return value
