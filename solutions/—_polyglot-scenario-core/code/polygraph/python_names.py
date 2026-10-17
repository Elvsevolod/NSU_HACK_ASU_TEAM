"""LibCST lexical bindings and lossless, in-memory syntax compatibility.

No FullRepoManager, import machinery, watchman or target Python is executed.
QualifiedNameProvider handles import aliases and lexical shadowing; locations
are converted to AST's UTF-8 column convention before the two trees are joined.
"""
import libcst as cst
from libcst.metadata import FunctionScope, MetadataWrapper, PositionProvider, QualifiedNameProvider, QualifiedNameSource, ScopeProvider


class CompatibleExceptions(cst.CSTTransformer):
    def __init__(self):
        self.changed = False

    def leave_ExceptHandler(self, original_node, updated_node):
        typ = updated_node.type
        if isinstance(typ, cst.Tuple) and not typ.lpar:
            self.changed = True
            return updated_node.with_changes(type=typ.with_changes(lpar=[cst.LeftParen()], rpar=[cst.RightParen()]))
        return updated_node


def parse(source, module, package):
    tree = cst.parse_module(source)
    compatibility = CompatibleExceptions()
    normalized = tree.visit(compatibility)
    wrapper = MetadataWrapper(normalized, unsafe_skip_copy=True)
    metadata = wrapper.resolve_many((QualifiedNameProvider, PositionProvider, ScopeProvider))
    lines = normalized.code.splitlines()
    bindings = {}
    for node, position in metadata[PositionProvider].items():
        if not isinstance(node, (cst.Name, cst.Attribute)):
            continue
        names = metadata[QualifiedNameProvider].get(node, set())
        names = names() if callable(names) else names
        resolved = set()
        for qualified in names:
            value = qualified.name
            if qualified.source == QualifiedNameSource.LOCAL:
                value = "local:" + value if "<locals>" in value else module + "." + value
            elif qualified.source == QualifiedNameSource.IMPORT and value.startswith("."):
                level = len(value) - len(value.lstrip("."))
                prefix = package.split(".")
                value = ".".join(prefix[:len(prefix) - level + 1] + [value[level:]])
            resolved.add(value)
        scope = metadata[ScopeProvider].get(node)
        if isinstance(node, cst.Name) and isinstance(scope, FunctionScope) and any(assignment.name == node.value and assignment.scope is scope for assignment in scope.assignments):
            # QualifiedNameProvider intentionally follows earlier imports on
            # an assignment's RHS; Python runtime binding still treats a name
            # assigned anywhere in this function as local from its beginning.
            resolved = {"local:" + node.value}
        if resolved:
            start = position.start
            byte_column = len(lines[start.line - 1][:start.column].encode("utf-8"))
            # Attribute and its first Name share a start; the AST node kind keeps
            # their bindings separate (e.g. httpx vs httpx.get).
            bindings[start.line, byte_column, "Name" if isinstance(node, cst.Name) else "Attribute"] = tuple(sorted(resolved))
    return normalized.code, bindings, compatibility.changed
