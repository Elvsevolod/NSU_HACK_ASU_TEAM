"""Focused behaviour tests for the native_storage metadata carriers."""
from copy import copy, deepcopy

import pytest

from analyzer.java_collections import JavaIdentity
from analyzer.native_storage import JavaFrame, JavaList


def test_frame_missing_evidence_is_not_guessed():
    frame = JavaFrame({'count': 1, 'text': 'x', 'flag': True})
    assert frame.kinds == {'count': None, 'text': None, 'flag': None}


def test_frame_last_write_wins_for_recorded_evidence():
    frame = JavaFrame({'value': 1}, {'value': 'Long'})
    assert frame.kinds['value'] == 'Long'
    frame['value'] = 1
    assert frame.kinds['value'] is None
    frame.set_value('value', 1, 'Integer')
    assert frame.kinds['value'] == 'Integer'
    frame.set_value('value', 1)
    assert frame.kinds['value'] is None


def test_frame_update_pop_and_clear_stay_aligned():
    frame = JavaFrame({'kept': 1, 'changed': 1}, {'kept': 'Long', 'changed': 'Integer'})
    frame.update({'changed': 1})
    assert frame.kinds == {'kept': 'Long', 'changed': None}
    frame |= {'added': 1}
    assert frame.kinds == {'kept': 'Long', 'changed': None, 'added': None}
    assert frame.setdefault('kept', 0) == 1
    assert frame.kinds['kept'] == 'Long'
    assert frame.setdefault('fresh', 0) == 0
    assert frame.kinds['fresh'] is None
    assert frame.pop('added') == 1 and 'added' not in frame.kinds
    assert frame.pop('missing', 5) == 5 and 'missing' not in frame.kinds
    del frame['changed']
    assert 'changed' not in frame.kinds
    remaining = dict(frame.kinds)
    name, value = frame.popitem()
    assert name in ('kept', 'fresh')
    assert frame.kinds == {key: kind for key, kind in remaining.items() if key != name}
    frame.clear()
    assert frame.kinds == {} and len(frame) == 0


def test_frame_shallow_copy_shares_payloads_and_copies_evidence():
    shared = [1]
    frame = JavaFrame({'value': shared, 'text': 'x'}, {'value': 'Long', 'text': 'String'})
    clone = frame.copy()
    assert clone['value'] is shared
    assert clone.kinds == frame.kinds and clone.kinds is not frame.kinds
    clone.set_value('value', [2], 'Integer')
    assert frame.kinds['value'] == 'Long' and frame['value'] is shared
    shared.append(2)
    assert frame['value'] == [1, 2] and clone['value'] == [2]
    followed = copy(frame)
    assert followed['value'] is shared
    assert followed.kinds == frame.kinds and followed.kinds is not frame.kinds


def test_frame_deepcopy_preserves_aliases_cycles_and_memo():
    alias = {'field': 1}
    frame = JavaFrame()
    frame.set_value('left', alias, 'Long')
    frame.set_value('right', alias, 'Long')
    frame.set_value('loop', frame, 'Object')
    clone = deepcopy(frame, {})
    assert clone is not frame
    assert clone['left'] is clone['right'] and clone['left'] is not alias
    assert clone['loop'] is clone
    assert clone.kinds == {'left': 'Long', 'right': 'Long', 'loop': 'Object'}
    marker = object()
    kept = deepcopy(JavaFrame({'marker': marker}), {id(marker): marker})
    assert kept['marker'] is marker


def test_list_missing_evidence_is_not_guessed():
    values = JavaList([1, 'x', True])
    assert values.kinds == [None, None, None]


def test_list_constructor_validates_supplied_kinds():
    assert JavaList([1, 2], ['Integer', 'Long']).kinds == ['Integer', 'Long']
    with pytest.raises(ValueError):
        JavaList([1, 2], ['Long'])


def test_list_simple_mutations_stay_aligned():
    values = JavaList()
    values.append(1, 'Integer')
    values.extend([2, 3], ['Long', None])
    values.insert(0, 'a', 'String')
    assert list(values) == ['a', 1, 2, 3]
    assert values.kinds == ['String', 'Integer', 'Long', None]
    values.set_value(-1, 4, 'Integer')
    assert values.kinds == ['String', 'Integer', 'Long', 'Integer']
    assert values.pop(0) == 'a'
    assert values.kinds == ['Integer', 'Long', 'Integer']
    values.clear()
    assert list(values) == [] and values.kinds == []


def test_list_extend_from_javalist_preserves_explicit_kinds():
    source = JavaList([1, 2], ['Long', None])
    target = JavaList(['x'])
    target.extend(source)
    assert list(target) == ['x', 1, 2]
    assert target.kinds == [None, 'Long', None]
    target.extend([9], ['Integer'])
    assert target.kinds == [None, 'Long', None, 'Integer']
    with pytest.raises(ValueError):
        target.extend([1, 2], ['Long'])
    assert list(target) == ['x', 1, 2, 9]


def test_list_slice_assignment_and_deletion_stay_aligned():
    values = JavaList([1, 2, 3, 4], ['Integer', 'Long', 'Integer', 'Long'])
    values[1:3] = [9]
    assert list(values) == [1, 9, 4] and values.kinds == ['Integer', None, 'Long']
    values = JavaList([1, 2, 3, 4], ['Integer', 'Long', 'Integer', 'Long'])
    values[::2] = ['a', 'b']
    assert list(values) == ['a', 2, 'b', 4] and values.kinds == [None, 'Long', None, 'Long']
    del values[1::2]
    assert list(values) == ['a', 'b'] and values.kinds == [None, None]
    values = JavaList([1, 2, 3, 4], ['Integer', 'Long', 'Integer', 'Long'])
    del values[-2:]
    assert list(values) == [1, 2] and values.kinds == ['Integer', 'Long']


def test_list_equal_payloads_keep_distinct_evidence():
    numbers = JavaList([1, 1], ['Integer', 'Long'])
    numbers[0] = 1
    assert numbers.kinds == [None, 'Long']
    numbers.set_value(0, 1, 'Integer')
    assert numbers.kinds == ['Integer', 'Long']
    numbers.reverse()
    assert numbers.kinds == ['Long', 'Integer']
    letters = JavaList(['a', 'a'], ['Character', 'String'])
    letters[1] = 'a'
    assert letters.kinds == ['Character', None]


def test_list_self_extend_snapshots_once():
    values = JavaList([1, 2], ['Integer', 'Long'])
    values.extend(values)
    assert list(values) == [1, 2, 1, 2]
    assert values.kinds == ['Integer', 'Long', 'Integer', 'Long']
    values += values
    assert list(values) == [1, 2] * 4
    assert values.kinds == ['Integer', 'Long'] * 4


def test_list_shallow_copy_is_new_allocation_sharing_elements():
    inner = [1]
    values = JavaList([inner], ['Long'])
    clone = values.copy()
    assert isinstance(clone, JavaList) and clone is not values
    assert clone[0] is inner and clone.kinds == ['Long'] and clone.kinds is not values.kinds
    assert clone.java_identity is not values.java_identity
    assert isinstance(clone.java_identity, JavaIdentity)
    followed = copy(values)
    assert followed[0] is inner and followed.kinds == ['Long'] and followed.kinds is not values.kinds
    inner.append(2)
    assert values[0] == [1, 2] and clone[0] == [1, 2]


def test_list_deepcopy_preserves_identity_aliases_and_cycles():
    inner = [1]
    values = JavaList([inner, inner], ['Long', 'Long'])
    values.append(values, None)
    clone = deepcopy(values, {})
    assert clone is not values and clone.java_identity is values.java_identity
    assert clone.kinds == ['Long', 'Long', None] and clone.kinds is not values.kinds
    assert clone[0] is clone[1] and clone[0] is not inner
    assert clone[2] is clone and clone[0] == [1]
    marker = object()
    kept = deepcopy(JavaList([marker]), {id(marker): marker})
    assert kept[0] is marker


def test_list_conservative_and_aligned_mutations():
    values = JavaList([2, 1], ['Long', 'Integer'])
    values.sort()
    assert list(values) == [1, 2] and values.kinds == [None, None]
    values = JavaList([1, 2, 3], ['Integer', 'Long', 'Integer'])
    values.remove(2)
    assert list(values) == [1, 3] and values.kinds == ['Integer', 'Integer']
    values = JavaList([1, 2], ['Integer', 'Long'])
    values *= 2
    assert list(values) == [1, 2, 1, 2] and values.kinds == ['Integer', 'Long', 'Integer', 'Long']
    assert len(values.kinds) == len(values)


def test_plain_builtin_views_do_not_mutate_metadata():
    frame = JavaFrame({'value': 1}, {'value': 'Long'})
    snapshot = dict(frame)
    snapshot['value'] = 2
    assert frame['value'] == 1 and frame.kinds['value'] == 'Long'
    values = JavaList([1], ['Long'])
    plain = list(values)
    plain[0] = 2
    assert values[0] == 1 and values.kinds == ['Long']


def test_failed_sort_invalidates_partially_reordered_evidence():
    import pytest
    values=JavaList([2,1,3,'x'],['Long','Integer','Short','String'])
    with pytest.raises(TypeError):values.sort()
    assert values.kinds==[None]*len(values)
