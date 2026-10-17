from analyzer.frontend import Frontend
from builders import build


def test_one_helper_keeps_distinct_valid_routes_and_payloads(tmp_path):
    sources = {'Entry.java': '''@RestController class Entry {
      @PostMapping("/left") void left(@RequestBody Input request) {}
      @PostMapping("/right") void right(@RequestBody Input request) {}
    }
    class Input { String key; String title; }'''}
    project, _, ids = build(tmp_path, sources)
    (tmp_path / 'ui.js').write_text('''function send(path, body) {
      $.ajax({url:path,type:"POST",data:JSON.stringify((body))});
    }
    function left() { send("/left", {key:"left-key"}); }
    function right() { send("/right", {title:"right-title"}); }
    ''')
    frontend = Frontend(project)
    assert len(frontend.sites) == 2
    actual = {tuple(site['handlers']): site['body_fields'] for site in frontend.sites.values()}
    assert actual == {(ids['Entry.left'],): {'key': '"left-key"'},
                      (ids['Entry.right'],): {'title': '"right-title"'}}
