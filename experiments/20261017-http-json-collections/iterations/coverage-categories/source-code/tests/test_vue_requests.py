from analyzer.frontend import Frontend
from builders import build, LIBRARY


LOANS = {
    'LoanController.java': '''import org.springframework.web.bind.annotation.*;
    @RestController class LoanController {
      @PostMapping("/loans") Loan add(@RequestBody Loan input) { return input; }
    }''',
    'ReturnController.java': '''import org.springframework.web.bind.annotation.*;
    @RestController class ReturnController {
      @PostMapping("/returns") Loan handBack(@RequestBody Loan input) { return input; }
    }''',
    'Loan.java': 'class Loan { String card; String title; }',
}

SHELVES = {
    'ShelfController.java': '''import org.springframework.web.bind.annotation.*;
    @RestController class ShelfController {
      @GetMapping("/shelves/{shelfId}") String one(@PathVariable String shelfId) { return "one"; }
      @GetMapping("/shelves/{shelfId}/labels") String labels(@PathVariable String shelfId) { return "labels"; }
      @GetMapping("/shelves/floor/{floorId}/shelves/{shelfId}") String nested(@PathVariable String floorId, @PathVariable String shelfId) { return "nested"; }
    }''',
}


def test_same_object_this_wrapper_restores_url_and_body(tmp_path):
    project, _, ids = build(tmp_path, LOANS, module='library')
    (tmp_path / 'desk.js').write_text('''var desk = new Vue({
      methods: {
        queryHelper: function (path, body) { $.ajax({url: path, type: "POST", data: JSON.stringify(body)}); },
        addLoan: function () {
          var request = new Object();
          request.card = $("#card").val();
          request.title = $("#title").val();
          this.queryHelper("/loans", request);
        }
      }
    });
    ''')
    frontend = Frontend(project)
    assert len(frontend.sites) == 1
    site = next(iter(frontend.sites.values()))
    assert site['handlers'] == [ids['LoanController.add']]
    assert site['url_shape'] == ['loans']
    assert site['body_fields'] == {'card': '$("#card").val()', 'title': '$("#title").val()'}
    assert site['body_complete'] is True
    assert site['stringified'] is True
    assert site['action_label'] == 'addLoan'
    assert 'this.queryHelper' in site['source']
    assert '$.ajax' in site['helper_source']


def test_sibling_objects_keep_same_named_helpers_separate(tmp_path):
    project, _, ids = build(tmp_path, LOANS, module='library')
    (tmp_path / 'desk.js').write_text('''var returnsDesk = new Vue({
      methods: {
        queryHelper: function (path, body) { $.ajax({url: path, type: "POST", data: JSON.stringify(body)}); },
        record: function () { this.queryHelper("/returns", {card: "r1"}); }
      }
    });
    var loanDesk = new Vue({
      methods: {
        queryHelper: function (path, body) { $.ajax({url: path, type: "POST", data: JSON.stringify(body)}); },
        record: function () { this.queryHelper("/loans", {card: "l1"}); }
      }
    });
    ''')
    frontend = Frontend(project)
    actual = {tuple(site['handlers']): (site['body_fields'], site['action_label']) for site in frontend.sites.values()}
    assert actual == {(ids['ReturnController.handBack'],): ({'card': '"r1"'}, 'record'),
                      (ids['LoanController.add'],): ({'card': '"l1"'}, 'record')}


def test_nested_plain_function_does_not_inherit_this(tmp_path):
    project, _, _ = build(tmp_path, LOANS, module='library')
    (tmp_path / 'desk.js').write_text('''var desk = new Vue({
      methods: {
        queryHelper: function (path, body) { $.ajax({url: path, type: "POST", data: JSON.stringify(body)}); },
        record: function () {
          function inner() { this.queryHelper("/loans", {card: "x"}); }
          inner();
        }
      }
    });
    ''')
    frontend = Frontend(project)
    assert not frontend.sites
    assert any('unresolved request URL' in warning for warning in frontend.warnings)


def test_arrow_callback_keeps_object_this(tmp_path):
    project, _, ids = build(tmp_path, LOANS, module='library')
    (tmp_path / 'desk.js').write_text('''var desk = new Vue({
      methods: {
        queryHelper: function (path, body) { $.ajax({url: path, type: "POST", data: JSON.stringify(body)}); },
        record: function () { var run = () => this.queryHelper("/loans", {card: "a"}); run(); }
      }
    });
    ''')
    frontend = Frontend(project)
    assert len(frontend.sites) == 1
    site = next(iter(frontend.sites.values()))
    assert site['handlers'] == [ids['LoanController.add']]
    assert site['body_fields'] == {'card': '"a"'}
    assert site['action_label'] == 'record'


def test_one_helper_keeps_bodies_paired_with_callers(tmp_path):
    project, _, ids = build(tmp_path, LOANS, module='library')
    (tmp_path / 'desk.js').write_text('''var desk = new Vue({
      methods: {
        queryHelper(path, body) { $.ajax({url: path, type: "POST", data: JSON.stringify(body)}); },
        record() { this.queryHelper("/loans", {card: "l9"}); },
        handBack() { this.queryHelper("/returns", {card: "r9"}); }
      }
    });
    ''')
    frontend = Frontend(project)
    actual = {tuple(site['handlers']): (site['body_fields'], site['action_label']) for site in frontend.sites.values()}
    assert actual == {(ids['LoanController.add'],): ({'card': '"l9"'}, 'record'),
                      (ids['ReturnController.handBack'],): ({'card': '"r9"'}, 'handBack')}


def test_dynamic_url_shape_excludes_shorter_routes(tmp_path):
    project, _, ids = build(tmp_path, SHELVES, module='catalog')
    (tmp_path / 'shelves.js').write_text('''
    function openShelf() { $.ajax({url: "/shelves/" + $("#shelf").val(), type: "GET", data: {}}); }
    function openLabels() { $.ajax({url: "/shelves/" + $("#shelf").val() + "/labels", type: "GET", data: {}}); }
    function openNested() {
      $.ajax({url: "/shelves/floor/" + $("#floor").val() + "/shelves/" + $("#shelf").val(), type: "GET", data: {}});
    }
    ''')
    frontend = Frontend(project)
    actual = {tuple(site['url_shape']): site['handlers'] for site in frontend.sites.values()}
    assert actual == {('shelves', '{}'): [ids['ShelfController.one']],
                      ('shelves', '{}', 'labels'): [ids['ShelfController.labels']],
                      ('shelves', 'floor', '{}', 'shelves', '{}'): [ids['ShelfController.nested']]}


def test_constant_url_needs_the_full_route(tmp_path):
    missing = tmp_path / 'missing'
    project, _, _ = build(missing, LIBRARY, module='catalog')
    (missing / 'ui.js').write_text('$.ajax({url: "/books", type: "GET", data: {}});')
    frontend = Frontend(project)
    assert not frontend.sites

    exact = tmp_path / 'exact'
    project, _, ids = build(exact, LIBRARY, module='catalog')
    (exact / 'ui.js').write_text('$.ajax({url: "/books/b1", type: "GET", data: {}});')
    frontend = Frontend(project)
    assert len(frontend.sites) == 1
    site = next(iter(frontend.sites.values()))
    assert site['handlers'] == [ids['BookController.lookup']]
    assert site['url_shape'] == ['books', 'b1']


def test_unknown_bodies_stay_incomplete(tmp_path):
    project, _, ids = build(tmp_path, LOANS, module='library')

    (tmp_path / 'ui.js').write_text('''
    function send(path, body) { $.ajax({url: path, type: "POST", data: JSON.stringify(body)}); }
    function addLoan() { send("/loans", pickCard()); }
    ''')
    frontend = Frontend(project)
    assert len(frontend.sites) == 1
    site = next(iter(frontend.sites.values()))
    assert site['body_fields'] == {}
    assert site['body_complete'] is False
    assert site['stringified'] is True

    (tmp_path / 'ui.js').write_text('''
    function send(path, body) { $.ajax({url: path, type: "POST", data: JSON.stringify(body)}); }
    function addLoan() {
      var request = new Object();
      if (flag) { request.card = "conditional"; }
      request.title = "fixed";
      send("/loans", request);
    }
    ''')
    frontend = Frontend(project)
    site = next(iter(frontend.sites.values()))
    assert site['body_complete'] is False

    (tmp_path / 'ui.js').write_text('''
    function addLoan() {
      var extras = {card: "c"};
      $.ajax({url: "/loans", type: "POST", data: JSON.stringify({title: "t", ...extras})});
    }
    ''')
    frontend = Frontend(project)
    site = next(iter(frontend.sites.values()))
    assert site['body_fields'] == {'title': '"t"'}
    assert site['body_complete'] is False
