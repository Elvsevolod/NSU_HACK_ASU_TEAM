"""Explicit labelled numeric extraction: narrow, evidence-only behavior."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzer.state import U
from analyzer.structured_literals import literal_value


def test_labelled_integer_sequence_preserves_order():
    value, quote = literal_value('Add experiment with temperatures 0, 100 and 250', 'temperatures', 'List<Integer>')
    assert value == [0, 100, 250]
    assert quote == 'temperatures 0, 100 and 250'


def test_scalar_float_requires_explicit_caller_label():
    assert literal_value('Add reagent with basic rate 0.5', 'basicPriceRate', 'double') == (U, '')
    assert literal_value('Add reagent with basic rate 0.5', 'basicPriceRate', 'double', ('basic rate',)) == (0.5, 'basic rate 0.5')


def test_conflicting_repeated_labels_are_refused():
    assert literal_value('Set temperature 10 and temperature 20', 'temperature', 'int') == (U, '')
    assert literal_value('temperatures 10 and temperatures 20', 'temperatures', 'List<Integer>') == (U, '')


def test_malformed_collection_item_rejects_the_whole_list():
    assert literal_value('temperatures 0, 100.5 and 250', 'temperatures', 'List<Integer>') == (U, '')
    assert literal_value('temperatures 0, hot and 250', 'temperatures', 'List<Integer>') == (U, '')
    assert literal_value('temperatures 2026-10-17', 'temperatures', 'List<Integer>') == (U, '')
    assert literal_value('temperatures 0, 100 and 250 with a catalyst', 'temperatures', 'List<Integer>') == ([0, 100, 250], 'temperatures 0, 100 and 250')


def test_partial_and_unrelated_numbers_are_ignored():
    assert literal_value('Set temperature 0.5', 'temperature', 'int') == (U, '')
    assert literal_value('Set temperature 09:00', 'temperature', 'int') == (U, '')
    assert literal_value('Set temperature 2026-10-17', 'temperature', 'int') == (U, '')
    assert literal_value('Add 3 experiments in room 5', 'temperature', 'int') == (U, '')
    assert literal_value('Add temperatureSensor value 100', 'temperature', 'int') == (U, '')
    assert literal_value('Add temperature2 value 100', 'temperature', 'int') == (U, '')
    assert literal_value('Add 4 runs', 'temperatures', 'List<Integer>') == (U, '')
