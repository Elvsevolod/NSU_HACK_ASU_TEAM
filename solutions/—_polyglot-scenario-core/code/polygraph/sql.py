"""SQLGlot-backed input adapter. SQL is parsed, never executed.

Only literal CREATE/INSERT snapshots are materialized. An unmodelled mutation
invalidates the affected snapshot instead of silently dropping its rows.
"""
from decimal import Decimal, InvalidOperation
import re

import sqlglot
from sqlglot import exp
from sqlglot.errors import ErrorLevel, SqlglotError
from sqlglot.tokens import TokenType

from .values import Unknown


def statements(source, dialect):
    start = 0
    for token in sqlglot.tokenize(source, read=dialect):
        if token.token_type == TokenType.SEMICOLON:
            yield source[start:token.start]
            start = token.end + 1
    if source[start:].strip():
        yield source[start:]


def parsed_statement(source, dialect):
    tokens = sqlglot.tokenize(source, read=dialect)
    if not tokens:
        # SQLGlot treats MySQL versioned comments as comments. A dump can put
        # executable SQL there. Inspect only lexer-confirmed comment chunks,
        # never regex-rewrite strings containing comment-like text.
        for match in re.finditer(r"/\*!\d*\s*(.*?)\*/", source, re.S):
            yield from parsed_statement(match[1], dialect)
        return
    words = [token.text.upper() for token in tokens]
    if words[0] in {"LOCK TABLES", "UNLOCK TABLES"} or words[:2] in [["LOCK", "TABLES"], ["UNLOCK", "TABLES"]]:
        return
    if len(words) == 5 and words[:2] == ["ALTER", "TABLE"] and words[-2:] in [["DISABLE", "KEYS"], ["ENABLE", "KEYS"]]:
        return
    yield sqlglot.parse_one(source, read=dialect, error_level=ErrorLevel.RAISE)


def literal(node):
    if isinstance(node, exp.Null):
        return None
    if isinstance(node, exp.Boolean):
        return bool(node.this)
    if isinstance(node, exp.Paren):
        return literal(node.this)
    if isinstance(node, exp.Neg):
        value = literal(node.this)
        return -value if isinstance(value, (int, Decimal)) and type(value) is not bool else Unknown("non-numeric SQL negation")
    if isinstance(node, exp.Literal):
        if node.is_string:
            return Unknown("SQL text contains undecodable bytes") if "\ufffd" in node.this else node.this
        try:
            return int(node.this) if node.is_int else Decimal(node.this)
        except (ValueError, InvalidOperation):
            pass
    return Unknown("unsupported SQL expression", origin=node.sql()[:120] if node is not None else "")


def snapshot(source, facts, dialect="mysql"):
    base, schemas, types, warnings, tainted, database = {}, {}, {}, [], set(), ""
    all_tables = {key for key, node in facts.nodes.items() if node.get("kind") == "data_resource"}
    if "\ufffd" in source:
        warnings.append("Context contains non-UTF8 bytes; affected SQL values remain unknown")

    def table_info(node):
        table = node.this if isinstance(node, exp.Schema) else node
        if not isinstance(table, exp.Table):
            return "", "", ""
        schema = table.db or database
        return facts.table_id(table.name, schema), schema, table.name

    def apply(node):
        nonlocal database
        if node is None:
            return
        if isinstance(node, exp.Use):
            database = node.this.name
        elif isinstance(node, exp.Create) and str(node.args.get("kind", "")).upper() == "TABLE":
            rid, schema, table = table_info(node.this)
            columns = [column.name for column in node.this.expressions if isinstance(column, exp.ColumnDef)] if isinstance(node.this, exp.Schema) else []
            schemas[schema, table] = columns
            if rid:
                types[rid] = {column.name: column.kind.sql() for column in node.this.expressions if isinstance(column, exp.ColumnDef)} if isinstance(node.this, exp.Schema) else {}
                base.setdefault(rid, [])
                if not columns or node.expression is not None:
                    tainted.add(rid)
                    warnings.append("CREATE TABLE without a literal column schema: " + rid)
        elif isinstance(node, exp.Insert):
            rid, schema, table = table_info(node.this)
            if not rid:
                warnings.append(f"Unmapped context table: {schema}.{table}")
                return
            columns = [column.name for column in node.this.expressions] if isinstance(node.this, exp.Schema) else schemas.get((schema, table))
            if not columns or not isinstance(node.expression, exp.Values) or node.args.get("conflict"):
                tainted.add(rid)
                warnings.append("INSERT requires known columns and literal VALUES: " + rid)
                return
            for row in node.expression.expressions:
                if not isinstance(row, exp.Tuple) or len(columns) != len(row.expressions):
                    tainted.add(rid)
                    warnings.append("SQL column/value count mismatch: " + rid)
                    continue
                base.setdefault(rid, []).append(dict(zip(columns, map(literal, row.expressions))))
        elif isinstance(node, (exp.Set, exp.Transaction, exp.Commit, exp.Rollback)):
            return
        elif isinstance(node, exp.Create) and str(node.args.get("kind", "")).upper() in {"DATABASE", "SCHEMA", "INDEX"}:
            return
        elif isinstance(node, exp.Drop) and str(node.args.get("kind", "")).upper() == "TABLE":
            rid, _, _ = table_info(node.this)
            if rid:
                base.pop(rid, None)
                tainted.discard(rid)
        elif isinstance(node, exp.Command) and str(node.this).upper() in {"LOCK", "UNLOCK", "DELIMITER"}:
            return
        else:
            tables = list(node.find_all(exp.Table))
            affected = {rid for table in tables if (rid := table_info(table)[0])}
            tainted.update(affected or all_tables)
            warnings.append("Unsupported context SQL statement: " + node.sql()[:120])

    try:
        for statement in statements(source, dialect):
            if not statement.strip():
                continue
            try:
                nodes = list(parsed_statement(statement, dialect))
            except SqlglotError as exc:
                warnings.append("SQLGlot could not parse context statement: " + str(exc)[:160])
                tainted.update(all_tables)
                continue
            for node in nodes:
                apply(node)
    except SqlglotError as exc:
        warnings.append("SQLGlot could not tokenize context: " + str(exc)[:160])
        tainted.update(all_tables)
    return {key: tuple(rows) for key, rows in base.items()}, types, tainted, warnings
