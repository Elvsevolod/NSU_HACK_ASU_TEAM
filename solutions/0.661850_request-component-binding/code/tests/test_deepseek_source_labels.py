"""Source-only alias extraction for @RequestBody DTO fields."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzer.project import Project
from analyzer.source_labels import field_aliases
from builders import build

BATCH = {'Batch.java': 'class Batch { int premiumSlots; int standardSlots; }'}


def _line(source, needle):
    return next(number for number, line in enumerate(source.splitlines(), 1) if needle in line)


def _manual_project(root, sources, nodes):
    for file, source in sources.items():
        path = root / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
    skeleton = root / 'skeleton.json'
    skeleton.write_text(json.dumps({'project': 'fixture', 'nodes': nodes, 'edges': [], 'context': {}}))
    return Project(skeleton, root)


def test_chained_getter_alias_keeps_method_line_evidence(tmp_path):
    reader = '''class Reader {
  int read(Result result) {
    int priorityTotalCount = result.getBatch().getPremiumSlots();
    int plainCount = result.getBatch().getStandardSlots();
    return priorityTotalCount + plainCount;
  }
}'''
    project, _, ids = build(tmp_path, {'Api.java': 'class Api { void submit(@RequestBody Batch body) { } }',
                                       'Result.java': 'class Result { Batch batch; }',
                                       'Reader.java': reader, **BATCH})
    assert field_aliases(project, ids['Api.submit']) == {
        'premiumSlots': [{'label': 'priorityTotalCount',
                          'reference': f'{ids["Reader.read"]}:{_line(reader, "priorityTotalCount")}'}],
        'standardSlots': [{'label': 'plainCount',
                           'reference': f'{ids["Reader.read"]}:{_line(reader, "plainCount")}'}]}


def test_duplicate_simple_names_in_packages_do_not_cross_bind(tmp_path):
    sources = {
        'app/a/Batch.java': 'package app.a;\nclass Batch { int premiumSlots; }\n',
        'app/b/Batch.java': 'package app.b;\nclass Batch { int premiumSlots; }\n',
        'app/Api.java': 'package app;\nimport app.a.Batch;\nclass Api { void submit(@RequestBody Batch body) { } }\n',
        'app/Reader.java': 'package app;\nimport app.a.Batch;\n'
                           'class Reader { int read() { Batch typed = null; int total = typed.getPremiumSlots(); return total; } }\n',
        'app/Decoy.java': 'package app;\nimport app.b.Batch;\n'
                          'class Decoy { int probe() { Batch other = null; int copy = other.getPremiumSlots(); return copy; } }\n',
    }
    nodes = {'module:m': {'kind': 'module', 'name': 'm', 'deployment_units': ['m']}}
    for tid, fqn, file in (('type:app.a.Batch', 'app.a.Batch', 'app/a/Batch.java'),
                           ('type:app.b.Batch', 'app.b.Batch', 'app/b/Batch.java'),
                           ('type:app.Api', 'app.Api', 'app/Api.java'),
                           ('type:app.Reader', 'app.Reader', 'app/Reader.java'),
                           ('type:app.Decoy', 'app.Decoy', 'app/Decoy.java')):
        nodes[tid] = {'kind': 'type', 'fqn': fqn, 'module': 'm', 'file': file, 'annotations': []}
    for mid, owner, name, file, params in (('method:app.Api#submit', 'type:app.Api', 'submit', 'app/Api.java', ['Batch']),
                                           ('method:app.Reader#read', 'type:app.Reader', 'read', 'app/Reader.java', []),
                                           ('method:app.Decoy#probe', 'type:app.Decoy', 'probe', 'app/Decoy.java', [])):
        nodes[mid] = {'kind': 'method', 'name': name, 'owner': owner, 'module': 'm', 'file': file,
                      'line': 3, 'params_as_written': params, 'annotations': []}
    project = _manual_project(tmp_path, sources, nodes)
    assert field_aliases(project, 'method:app.Api#submit') == {
        'premiumSlots': [{'label': 'total', 'reference': 'method:app.Reader#read:3'}]}


def test_same_getter_on_unrelated_entity_is_refused(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': 'class Api { void submit(@RequestBody Batch body) { } }',
                                       'Invoice.java': 'class Invoice { int premiumSlots; }',
                                       'Reader.java': 'class Reader { int read(Invoice invoice) { '
                                                      'int amount = invoice.getPremiumSlots(); return amount; } }',
                                       **BATCH})
    assert field_aliases(project, ids['Api.submit']) == {}


def test_calculated_or_wrapped_values_are_not_direct_getters(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': 'class Api { void submit(@RequestBody Batch body) { } }',
                                       'Result.java': 'class Result { Batch batch; }',
                                       'Reader.java': '''class Reader { int read(Result result) {
    int bumped = result.getBatch().getPremiumSlots() + 1;
    int wrapped = identity(result.getBatch().getPremiumSlots());
    int indexed = result.getBatch().getPremiumSlots(2);
    int fixed = 7;
    return bumped; } }''',
                                       **BATCH})
    assert field_aliases(project, ids['Api.submit']) == {}


def test_no_requestbody_and_unknown_method_return_empty(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': 'class Api { void plain(Batch body) { } }', **BATCH})
    assert field_aliases(project, ids['Api.plain']) == {}
    assert field_aliases(project, 'method:service:Missing#none()') == {}


def test_explicit_pure_getters_keep_alias(tmp_path):
    batch = ('class Batch { int premiumSlots; int standardSlots; '
             'int getPremiumSlots() { return premiumSlots; } '
             'int getStandardSlots() { return this.standardSlots; } }')
    project, _, ids = build(tmp_path, {
        'Api.java': 'class Api { void submit(@RequestBody Batch body) { } }',
        'Batch.java': batch,
        'Reader.java': 'class Reader { int read(Batch batch) { int first = batch.getPremiumSlots(); '
                       'int second = batch.getStandardSlots(); return first; } }'})
    assert field_aliases(project, ids['Api.submit']) == {
        'premiumSlots': [{'label': 'first', 'reference': f'{ids["Reader.read"]}:1'}],
        'standardSlots': [{'label': 'second', 'reference': f'{ids["Reader.read"]}:1'}]}


def test_explicit_custom_getter_rejects_alias(tmp_path):
    batch = ('class Batch { int premiumSlots; int standardSlots; '
             'int getPremiumSlots() { return standardSlots; } }')
    project, _, ids = build(tmp_path, {
        'Api.java': 'class Api { void submit(@RequestBody Batch body) { } }',
        'Batch.java': batch,
        'Reader.java': 'class Reader { int read(Batch batch) { int total = batch.getPremiumSlots(); return total; } }'})
    assert field_aliases(project, ids['Api.submit']) == {}


def test_custom_chain_getter_rejects_alias(tmp_path):
    project, _, ids = build(tmp_path, {
        'Api.java': 'class Api { void submit(@RequestBody Batch body) { } }',
        'Batch.java': 'class Batch { int premiumSlots; }',
        'Result.java': 'class Result { Batch batch; Batch getBatch() { return null; } }',
        'Reader.java': 'class Reader { int read(Result result) { '
                       'int total = result.getBatch().getPremiumSlots(); return total; } }'})
    assert field_aliases(project, ids['Api.submit']) == {}


def test_shadowed_receiver_name_is_not_resolved(tmp_path):
    holder = ('class Holder { Invoice shelf; int read(Batch batch) { '
              '{ Batch shelf = batch; int inside = shelf.getPremiumSlots(); } '
              'int outside = shelf.getPremiumSlots(); return outside; } }')
    project, _, ids = build(tmp_path, {
        'Api.java': 'class Api { void submit(@RequestBody Batch body) { } }',
        'Batch.java': 'class Batch { int premiumSlots; }',
        'Invoice.java': 'class Invoice { int premiumSlots; }',
        'Holder.java': holder})
    assert field_aliases(project, ids['Api.submit']) == {}


def test_lambda_binding_does_not_leak_into_method_scope(tmp_path):
    reader = ('class Reader { int read(Batch batch) { Runnable task = () -> { '
              'Batch shadow = batch; int inside = shadow.getPremiumSlots(); }; return 0; } }')
    project, _, ids = build(tmp_path, {
        'Api.java': 'class Api { void submit(@RequestBody Batch body) { } }',
        'Batch.java': 'class Batch { int premiumSlots; }',
        'Reader.java': reader})
    assert field_aliases(project, ids['Api.submit']) == {}
