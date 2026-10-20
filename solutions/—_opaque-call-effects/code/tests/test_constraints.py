from analyzer.paths import run_paths
from analyzer.state import ScenarioState, U
from builders import build


def execute(tmp_path, body, typ='int', params=None, constraints=True):
    sources = {'Rules.java': 'class Rules { int apply(' + typ + ' x) {' + body + '} }'}
    project, db, ids = build(tmp_path, sources)
    paths = run_paths(project, ScenarioState(db), ids['Rules.apply'], params or {}, 16, constraints=constraints)
    return paths


def test_nested_opposite_numeric_guard_is_infeasible(tmp_path):
    code = 'if (x > 5) { if (x <= 5) { return 99; } return 1; } return 2;'
    before = execute(tmp_path / 'before', code, constraints=False)
    after = execute(tmp_path / 'after', code)
    assert {p['result'] for p in before} == {1, 2, 99}
    assert {p['result'] for p in after} == {1, 2}
    assert len(after) == 2
    assert any(c.get('refined') for p in after for c in p['engine'].conditions)


def test_integer_boundary_and_reversed_comparison(tmp_path):
    paths = execute(tmp_path, 'if (5 < x) { if (x >= 6) { return 1; } return 99; } return 2;')
    assert {p['result'] for p in paths} == {1, 2}


def test_floating_point_guard_keeps_noninteger_interval(tmp_path):
    paths = execute(tmp_path, 'if (x > 5) { if (x >= 5.5) { return 1; } return 3; } return 2;', 'double')
    assert {p['result'] for p in paths} == {1, 2, 3}
    assert len(paths) == 3


def test_assignment_invalidates_previous_bound(tmp_path):
    paths = execute(tmp_path, 'if (x > 5) { x = 3; if (x > 5) { return 99; } return 1; } return 2;')
    assert {p['result'] for p in paths} == {1, 2}


def test_unknown_reassignment_does_not_keep_stale_bound(tmp_path):
    paths = execute(tmp_path, 'if (x > 5) { x = external(); if (x > 5) { return 1; } return 3; } return 2;')
    assert {p['result'] for p in paths if p['engine'].outcome=='returned'} == {1, 2, 3}
    assert any(p['engine'].outcome=='uncaught application exception' for p in paths)


def test_boolean_constraints_remain_path_local(tmp_path):
    paths = execute(tmp_path, 'if (x) { if (!x) { return 99; } return 1; } return 2;', 'boolean')
    assert {p['result'] for p in paths} == {1, 2}
    assert len(paths) == 2


def test_equality_and_exclusion(tmp_path):
    paths = execute(tmp_path, 'if (x != 4) { if (x == 4) { return 99; } return 1; } return 2;')
    assert {p['result'] for p in paths} == {1, 2}


def test_disjunction_does_not_assume_both_operands(tmp_path):
    code = 'if (x > 5 || x < 0) { if (x <= 5) { return 3; } return 1; } return 2;'
    paths = execute(tmp_path, code)
    assert {p['result'] for p in paths} == {1, 2, 3}


def test_constraints_disabled_reproduces_unconstrained_paths(tmp_path):
    code = 'if (x > 5) { if (x <= 5) { return 99; } return 1; } return 2;'
    a = execute(tmp_path / 'a', code, constraints=False)
    b = execute(tmp_path / 'b', code, constraints=False)
    assert sorted(p['result'] for p in a) == sorted(p['result'] for p in b)


def test_source_assignment_and_local_numeric_type(tmp_path):
    paths = execute(tmp_path, 'int y = x; if (y > 3) { if (y < 4) { return 99; } return 1; } return 2;')
    assert {p['result'] for p in paths} == {1, 2}


def test_infeasible_path_does_not_add_project_calls(tmp_path):
    sources = {'Rules.java': '''class Rules {
      int apply(int x) { if (x > 5) { if (x < 6) { return forbidden(); } return allowed(); } return 0; }
      int forbidden() { return 99; }
      int allowed() { return 1; }
    }'''}
    project, db, ids = build(tmp_path, sources)
    paths = run_paths(project, ScenarioState(db), ids['Rules.apply'], {}, 16)
    executed = {t for p in paths for _, relation, t in p['engine'].edges if relation == 'executes'}
    assert ids['Rules.allowed'] in executed
    assert ids['Rules.forbidden'] not in executed


def test_constraint_does_not_refine_an_untracked_alias(tmp_path):
    code = 'int y = x; if (x > 5) { if (y < 0) { return 3; } return 1; } return 2;'
    paths = execute(tmp_path, code)
    # Correlation of two initially unknown locals is outside this interval domain.
    assert {p['result'] for p in paths} == {1, 2, 3}


def test_lower_and_upper_bounds_are_both_retained(tmp_path):
    code = 'if (x >= 2 && x <= 4) { if (x > 4 || x < 2) { return 99; } return 1; } return 2;'
    paths = execute(tmp_path, code)
    assert {p['result'] for p in paths} == {1, 2}


def test_false_float_guard_keeps_the_nan_case(tmp_path):
    code = 'if (x > 5) { return 1; } if (x <= 5) { return 2; } return 3;'
    paths = execute(tmp_path, code, 'double')
    assert {p['result'] for p in paths} == {1, 2, 3}


def test_float_alias_can_change_without_mutating_original_bounds(tmp_path):
    code = 'if (x > 5) { double y = x; x = 2; if (y <= 5) { return 99; } return 1; } return 2;'
    paths = execute(tmp_path, code, 'double')
    assert {p['result'] for p in paths} == {1, 2}


def test_contradiction_inside_one_conjunction_is_pruned(tmp_path):
    paths = execute(tmp_path, 'if (x > 5 && x < 6) { return 99; } return 1;')
    assert {p['result'] for p in paths} == {1}


def test_equality_in_a_conjunction_does_not_erase_a_bound(tmp_path):
    paths = execute(tmp_path, 'if (x > 5 && x == 3) { return 99; } return 1;')
    assert {p['result'] for p in paths} == {1}


def test_numeric_promotion_does_not_lose_a_possible_integer(tmp_path):
    # 16777219F rounds to 16777220; x=16777220 takes the second return in Java.
    paths = execute(tmp_path, 'if (x > 16777219F) { return 1; } if (x == 16777220) { return 2; } return 3;')
    assert {p['result'] for p in paths} == {1, 2, 3}


def test_mutation_in_a_compound_guard_does_not_refine_the_old_value(tmp_path):
    paths = execute(tmp_path, 'if (x > 5 && --x < 6) { if (x == 5) { return 1; } return 3; } return 2;')
    assert 1 in {p['result'] for p in paths}
