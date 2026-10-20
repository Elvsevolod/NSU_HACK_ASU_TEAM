"""Independent adversarial checks for request extraction and scope isolation."""
from analyzer.frontend import Frontend
from analyzer.state import ScenarioState, U
from builders import LIBRARY, build


def frontend(tmp_path, script, sources=None):
    project, db, ids = build(tmp_path, sources or LIBRARY)
    (tmp_path / 'actions.js').write_text(script)
    return Frontend(project), db, ids


def test_shadowed_bare_wrapper_does_not_capture_inner_call(tmp_path):
    f, _, _ = frontend(tmp_path, '''function send(path, body) { $.ajax({url:path,type:"POST",data:body}); }
      function fake() { function send(path, body) {} send("/books", {key:"wrong"}); }
      function real() { send("/books", {key:"right"}); }''')
    assert len(f.sites) == 1
    assert next(iter(f.sites.values()))['body_fields'] == {'key': '"right"'}


def test_object_wrapper_does_not_capture_bare_function(tmp_path):
    f, _, _ = frontend(tmp_path, '''var desk = {
      send(path, body) { $.ajax({url:path,type:"POST",data:body}); },
      fake() { function send(path,body) {} send("/books", {key:"wrong"}); },
      real() { this.send("/books", {key:"right"}); }
    };''')
    assert len(f.sites) == 1
    assert next(iter(f.sites.values()))['body_fields'] == {'key': '"right"'}


def test_nested_function_definitions_do_not_replace_active_payload(tmp_path):
    f, _, _ = frontend(tmp_path, '''function add() {
      var body = {key:"right"};
      function unrelated() { var body = {key:"wrong"}; }
      $.ajax({url:"/books",type:"POST",data:body});
    }''')
    assert next(iter(f.sites.values()))['body_fields'] == {'key': '"right"'}


def test_conditional_write_does_not_become_a_known_value(tmp_path):
    f, db, _ = frontend(tmp_path, '''function add() {
      var body = new Object(); body.key="k2";
      if (unknown()) { body.title="conditional"; }
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }''')
    site = next(iter(f.sites.values()))
    assert site['body_complete'] is False
    assert f.evaluate(site['body_fields'].get('title', ''), ScenarioState(db), definitions=site['definitions']) is U


def test_parenthesized_url_literals_keep_their_segments(tmp_path):
    f, _, ids = frontend(tmp_path, '$.ajax({url:("/books/")+key,type:"GET"});')
    assert len(f.sites) == 1
    assert next(iter(f.sites.values()))['handlers'] == [ids['BookController.lookup']]


def test_one_dynamic_segment_does_not_supply_two_path_arguments(tmp_path):
    sources = dict(LIBRARY)
    sources['Chapter.java'] = '''@RestController class Chapter {
      @GetMapping("/books/{key}/{chapter}") String lookup(String key, String chapter) { return chapter; }
    }'''
    f, _, ids = frontend(tmp_path, '$.ajax({url:"/books/"+key,type:"GET"});', sources)
    assert next(iter(f.sites.values()))['handlers'] == [ids['BookController.lookup']]


def test_conditional_overwrite_does_not_keep_the_old_known_value(tmp_path):
    f, db, _ = frontend(tmp_path, '''function add() {
      var body=new Object(); body.key="old";
      if (unknown()) { body.key="new"; }
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }''')
    site = next(iter(f.sites.values()))
    assert site['body_complete'] is False
    assert f.evaluate(site['body_fields'].get('key', ''), ScenarioState(db), definitions=site['definitions']) is U


def test_mutated_object_literal_is_not_a_complete_omission_proof(tmp_path):
    f, db, _ = frontend(tmp_path, '''function add() {
      var body={key:"old"}; body.title="present";
      if (unknown()) { body.key="new"; }
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }''')
    site = next(iter(f.sites.values()))
    assert site['body_complete'] is False
    assert f.evaluate(site['body_fields'].get('key', ''), ScenarioState(db), definitions=site['definitions']) is U


def test_computed_write_invalidates_prior_object_fields(tmp_path):
    f, db, _ = frontend(tmp_path, '''function add() {
      var body={key:"old"}; body[unknown()]="new";
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }''')
    site = next(iter(f.sites.values()))
    assert site['body_complete'] is False
    assert f.evaluate(site['body_fields'].get('key', ''), ScenarioState(db), definitions=site['definitions']) is U


def test_conditional_only_write_invalidates_literal_field(tmp_path):
    f, db, _ = frontend(tmp_path, '''function add() {
      var body={key:"old"}; if (unknown()) {body.key="new";}
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }''')
    site = next(iter(f.sites.values()))
    assert site['body_complete'] is False
    assert f.evaluate(site['body_fields'].get('key', ''), ScenarioState(db), definitions=site['definitions']) is U


def test_reassigned_payload_does_not_keep_old_literal(tmp_path):
    f, _, _ = frontend(tmp_path, '''function add() {
      var body={key:"old"}; body=unknown();
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }''')
    site = next(iter(f.sites.values()))
    assert site['body_complete'] is False
    assert site['body_fields'] == {}


def test_reassigned_unknown_url_does_not_keep_old_route(tmp_path):
    f, _, _ = frontend(tmp_path, '''function add() {
      var path="/books"; path=unknown();
      $.ajax({url:path,type:"POST",data:{key:"k2"}});
    }''')
    assert not f.sites
    assert any('unresolved request URL' in warning for warning in f.warnings)


def test_conditional_declaration_does_not_prove_a_known_payload(tmp_path):
    f, _, _ = frontend(tmp_path, '''function add() {
      if (unknown()) { var body={key:"conditional"}; }
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }''')
    site = next(iter(f.sites.values()))
    assert site['body_complete'] is False
    assert site['body_fields'] == {}


def test_function_parameter_can_shadow_a_request_wrapper(tmp_path):
    f, _, _ = frontend(tmp_path, '''function send(path,body) { $.ajax({url:path,type:"POST",data:body}); }
      function fake(send) { send("/books",{key:"wrong"}); }
      function real() { send("/books",{key:"right"}); }''')
    assert len(f.sites) == 1
    assert next(iter(f.sites.values()))['body_fields'] == {'key': '"right"'}
