"""SQLGlot read-only relational plans over supplied in-memory snapshots.

The upstream optimizer/planner/executor performs selection, joins, ordering
and COUNT. This adapter binds inputs, checks its supported semantic boundary,
projects source effects and supplies tables. No database connection is made.
"""
from math import prod

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError
from sqlglot.executor import execute
from sqlglot.executor.table import Table
from sqlglot.tokens import TokenType

from .values import Unknown, unknown


# Restrict execution to the tested integer/boolean/string/NULL subset. In
# particular no user-defined functions, filesystem tables or arbitrary code.
SUPPORTED = {"Select", "From", "Table", "TableAlias", "Identifier", "Column", "Star", "Alias",
             "Literal", "Boolean", "Null", "Neg", "Paren", "Where", "And", "Or", "Not", "Is",
             "EQ", "NEQ", "GT", "GTE", "LT", "LTE", "Join", "Order", "Ordered", "Limit", "Offset",
             "Count", "Distinct", "Group", "Having", "Placeholder", "In", "Tuple"}


def evaluate(engine, source, params, span):
    def unresolved(message):
        engine.note("sql-query-unknown", message, span)
        return Unknown(message)

    if not isinstance(source, str):
        return unresolved("SQL text is not statically known")
    dialect = engine.context.get("sql_dialect", "mysql")
    try:
        # Token offsets, rather than a regex, preserve '?' inside SQL strings.
        markers = [token for token in sqlglot.tokenize(source, read=dialect) if token.token_type == TokenType.PLACEHOLDER and token.text == "?"]
        positional = list(params) if isinstance(params, (tuple, list)) else []
        values = dict(params) if isinstance(params, dict) else {}
        for index, token in reversed(list(enumerate(markers))):
            key = "__polygraph_arg_" + str(index)
            source = source[:token.start] + ":" + key + source[token.end + 1:]
            values[key] = positional[index] if index < len(positional) else Unknown("missing positional SQL input")
        node = sqlglot.parse_one(source, read=dialect)
    except SqlglotError as exc:
        return unresolved("SQLGlot parse failed: " + str(exc)[:160])
    if not isinstance(node, exp.Select) or any(type(item).__name__ not in SUPPORTED for item in node.walk()):
        if not isinstance(node, exp.Select):
            engine.state.store.havoc()
        return unresolved("SQL query is outside the tested read-only relational subset")
    for item in list(node.find_all(exp.Placeholder)):
        value = values.get(item.name, Unknown("missing named SQL input", origin=item.name))
        from .java_boxing import boxed,unbox
        if boxed(value):value=unbox(value)
        if type(value) not in {str, int, bool, type(None)}:
            return unresolved("SQL input is symbolic or has an unsupported scalar type")
        item.replace(exp.convert(value))
    if any(isinstance(item, exp.Literal) and not item.is_string and not item.is_int for item in node.walk()):
        return unresolved("Non-integer SQL numeric semantics are not verified")
    tables, schema, cardinalities = {}, {}, []
    for table in node.find_all(exp.Table):
        rid = engine.p.table_id(table.name, table.db)
        if not rid:
            return unresolved("SQL table does not map uniquely to the input skeleton: " + table.sql())
        engine.add(engine.method.skeleton_id if engine.method else "", "data", rid, span, "source SQL parsed by SQLGlot")
        rows = engine.state.store.read(rid)
        if isinstance(rows, Unknown):
            return unresolved(rows.reason)
        columns = dict(engine.state.store.schemas.get(rid, {}))
        for row in rows:
            for column, value in row.items():
                if type(value) not in {str, int, bool, type(None)}:
                    return unresolved("SQL snapshot contains unknown or unsupported scalar values")
                inferred = "BOOLEAN" if type(value) is bool else "BIGINT" if type(value) is int else "TEXT" if isinstance(value, str) else "UNKNOWN"
                if columns.get(column, "UNKNOWN") == "UNKNOWN":
                    columns[column] = inferred
        for info in engine.p.types.values():
            if info.table == rid:
                for field, (typ, _) in engine.p.type_fields(info.key).items():
                    columns.setdefault(info.columns.get(field, field), "BIGINT" if typ in {"int", "Integer", "long", "Long"} else "BOOLEAN" if typ in {"bool", "boolean"} else "TEXT")
        if not columns:
            # An empty supplied table still suffices for COUNT(*)/SELECT *.
            # Explicit unknown column references are rejected by the optimizer.
            columns = {"__empty_snapshot": "UNKNOWN"}
        if any(set(columns) - set(row) for row in rows):
            return unresolved("Snapshot omits column values required by its schema")
        name = "snapshot_" + str(len(tables))
        tables[name] = Table(columns, [tuple(row[column] for column in columns) for row in rows])
        schema[name] = columns
        cardinalities.append(len(rows))
        alias = table.alias_or_name
        table.set("this", exp.to_identifier(name))
        table.set("db", None)
        table.set("catalog", None)
        table.set("alias", exp.TableAlias(this=exp.to_identifier(alias)))
    for column in node.find_all(exp.Column):
        column.set("db", None)
        column.set("catalog", None)
    work = prod(cardinalities) if cardinalities else 1
    if work > engine.step_limit - engine.operations:
        engine.unsupported("SQL snapshot row-product exceeds the operation budget", span)
    engine.operations += work
    try:
        result = execute(node, schema=schema, tables=tables, dialect=dialect)
    except (SqlglotError, ValueError, TypeError, KeyError, IndexError, NotImplementedError) as exc:
        return unresolved("SQLGlot relational evaluation failed: " + str(exc)[:160])
    return [dict(zip(result.columns, row)) for row in result.rows]
