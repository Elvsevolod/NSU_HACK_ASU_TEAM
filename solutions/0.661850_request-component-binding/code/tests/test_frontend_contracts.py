from analyzer.frontend import Frontend
from builders import build, LIBRARY


def ui(tmp_path, javascript):
    project, _, ids = build(tmp_path, LIBRARY)
    (tmp_path / 'ui.js').write_text(javascript)
    return Frontend(project), ids


SEND = '''function send(path, payload) {
  $.ajax({url: path, type: "POST", data: JSON.stringify(payload)});
}
'''


def test_stringified_payload_is_resolved_through_wrapper(tmp_path):
    javascript = SEND + 'function add() { var body = {key: "b2", title: "Example"}; send("/books", body); }'
    frontend, ids = ui(tmp_path, javascript)
    assert len(frontend.sites) == 1
    site = next(iter(frontend.sites.values()))
    assert site['handlers'] == [ids['BookController.add']]
    assert site['body_fields'] == {'key': '"b2"', 'title': '"Example"'}
    assert not frontend.warnings


def test_stringified_payload_supports_parentheses_and_local_alias(tmp_path):
    javascript = SEND + 'function add() { var body = {key: "k9"}; var alias = body; send("/books", (alias)); }'
    frontend, ids = ui(tmp_path, javascript)
    assert len(frontend.sites) == 1
    site = next(iter(frontend.sites.values()))
    assert site['handlers'] == [ids['BookController.add']]
    assert site['body_fields'] == {'key': '"k9"'}
    assert not frontend.warnings


def test_helper_calls_do_not_share_urls_or_bodies(tmp_path):
    javascript = SEND + '''
    function add() { var body = {key: "b2", title: "Second"}; send("/books", body); }
    function edit() { var body = {title: "Third"}; send("/books", body); }
    '''
    frontend, ids = ui(tmp_path, javascript)
    assert len(frontend.sites) == 2
    bodies = [site['body_fields'] for site in frontend.sites.values()]
    assert {'key': '"b2"', 'title': '"Second"'} in bodies
    assert {'title': '"Third"'} in bodies
    assert all(site['handlers'] == [ids['BookController.add']] for site in frontend.sites.values())


def test_nested_helper_keeps_the_inner_body(tmp_path):
    javascript = '''function send(path, payload) {
      $.ajax({url: path, type: "POST", data: JSON.stringify(payload)});
    }
    function submit(url, body) { send(url, body); }
    function add() { var body = {key: "nested"}; submit("/books", body); }
    '''
    frontend, ids = ui(tmp_path, javascript)
    assert len(frontend.sites) == 1
    site = next(iter(frontend.sites.values()))
    assert site['handlers'] == [ids['BookController.add']]
    assert site['body_fields'] == {'key': '"nested"'}
    assert not frontend.warnings


def test_dynamic_url_stays_unknown_with_diagnostics(tmp_path):
    javascript = SEND + 'function open() { send(window.location.pathname, {key: "x"}); }'
    frontend, _ = ui(tmp_path, javascript)
    assert not frontend.sites
    assert any('unresolved request URL' in warning for warning in frontend.warnings)


def test_ambiguous_body_stays_unknown_with_diagnostics(tmp_path):
    javascript = SEND + 'function add() { send("/books", picker() ? {key: "a"} : {key: "b"}); }'
    frontend, ids = ui(tmp_path, javascript)
    assert len(frontend.sites) == 1
    site = next(iter(frontend.sites.values()))
    assert site['handlers'] == [ids['BookController.add']]
    assert site['body_fields'] == {}
    assert any('unresolved request body' in warning for warning in frontend.warnings)


def test_direct_ajax_stringified_literal_body_is_unchanged(tmp_path):
    javascript = '$.ajax({url: "/books", type: "POST", data: JSON.stringify({key: "d1"})});'
    frontend, ids = ui(tmp_path, javascript)
    assert len(frontend.sites) == 1
    site = next(iter(frontend.sites.values()))
    assert site['handlers'] == [ids['BookController.add']]
    assert site['body_fields'] == {'key': '"d1"'}
    assert not frontend.warnings
