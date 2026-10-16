"""Check the experimental projection boundary, not hidden-reference quality."""
from types import SimpleNamespace

import pytest
from tree_sitter import Language, Parser
import tree_sitter_java

from analyzer.project import walk
from analyzer.projection import field_only_constructor, project_edges


def constructor(source):
    tree = Parser(Language(tree_sitter_java.language())).parse(source.encode())
    assert not tree.root_node.has_error
    return next(n for n in walk(tree.root_node) if n.type == 'constructor_declaration')


@pytest.mark.parametrize('fields, body, extends, expected', [
    ('int value;', 'this.value = input;', '', True),
    ('int value;', '// assign input\n this.value = input;', '', True),
    ('int value;', 'if (input > 0) this.value = input;', '', False),
    ('int value;', 'this.value = normalize(input);', '', False),
    ('int value;', 'this.value = input; notifyChange();', '', False),
    ('int value;', 'this.value = input + 1;', '', False),
    ('int value;', 'this.value += input;', '', False),
    ('static int value;', 'this.value = input;', '', False),
    ('volatile int value;', 'this.value = input;', '', False),
    ('int value = initialize();', 'this.value = input;', '', False),
    ('int value; { initialize(); }', 'this.value = input;', '', False),
    ('int value;', 'this.value = input;', 'extends Parent', False),
])
def test_constructor_boundary_is_source_based(fields, body, extends, expected):
    for name in ('DataBox', 'CompletelyRenamed'):
        source = f'class {name} {extends} {{ {fields} {name}(int input) {{ {body} }} }}'
        assert field_only_constructor(constructor(source)) is expected


def test_default_constructor_is_kept():
    assert not field_only_constructor(constructor('class Box { Box() {} }'))


def test_projection_preserves_other_calls_and_never_drops_outgoing_activity():
    init = 'method:app:Box#<init>(int)'
    caller, helper = 'method:app:Demo#run()', 'method:app:Demo#helper()'
    project = SimpleNamespace(ast={init: constructor('class Box { int value; Box(int input) { this.value = input; } }')})
    pair = {('', 'executes', init), (caller, 'calls', init)}
    other = {('', 'executes', caller), ('', 'executes', helper), (caller, 'calls', helper)}
    kept, removed = project_edges(project, pair | other, 'field-only')
    assert removed == pair and kept == other
    with_activity = pair | other | {(init, 'calls', helper)}
    assert project_edges(project, with_activity, 'field-only') == (with_activity, set())
    assert project_edges(project, pair | other, 'explicit') == (pair | other, set())
