"""Path-local scalar intervals. No solver, guessed values or object-field aliasing."""
from copy import deepcopy
import math
import re

from .project import text, walk
from .state import U


INTEGERS = {'byte', 'short', 'int', 'long', 'Byte', 'Short', 'Integer', 'Long'}
NUMBERS = INTEGERS | {'float', 'double', 'Float', 'Double'}
INVERSE = {'>': '<=', '>=': '<', '<': '>=', '<=': '>', '==': '!=', '!=': '=='}
REVERSE = {'>': '<', '>=': '<=', '<': '>', '<=': '>=', '==': '==', '!=': '!='}


class InfeasiblePath(Exception):
    """A selected branch contradicts constraints already established on this path."""


def scalar(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def interval(value):
    return value.get('__interval__') if isinstance(value, dict) else None


def compare(left, op, right):
    """Decide only predicates true or false for every value of an interval."""
    bounds = interval(left)
    if not bounds and interval(right) and scalar(left):
        left, right, op = right, left, REVERSE.get(op, op)
        bounds = interval(left)
    if not bounds or not scalar(right) or op not in INVERSE:
        return U
    low, high = bounds.get('low'), bounds.get('high')
    low_closed, high_closed = bounds.get('low_closed', False), bounds.get('high_closed', False)
    if op == '>':
        if low is not None and (low > right or low == right and not low_closed): return True
        if high is not None and high <= right: return False
    elif op == '>=':
        if low is not None and low >= right: return True
        if high is not None and (high < right or high == right and not high_closed): return False
    elif op == '<':
        other = compare(left, '>=', right)
        return not other if other is not U else U
    elif op == '<=':
        other = compare(left, '>', right)
        return not other if other is not U else U
    elif op in ('==', '!='):
        outside = (low is not None and (right < low or right == low and not low_closed)
                   or high is not None and (right > high or right == high and not high_closed)
                   or right in bounds.get('excluded', []))
        singleton = low is not None and low == high == right and low_closed and high_closed
        equal = False if outside else True if singleton else U
        return equal if op == '==' or equal is U else not equal
    return U


def unparenthesized(node):
    while node and node.type == 'parenthesized_expression':
        node = node.named_children[0] if node.named_children else None
    return node


def literal(node):
    node = unparenthesized(node)
    if node is None:
        return U
    raw = text(node)
    if node.type == 'unary_expression' and raw.startswith('-'):
        value = literal(node.named_children[-1])
        return -value if scalar(value) else U
    if node.type in ('decimal_integer_literal', 'decimal_floating_point_literal'):
        raw = raw.replace('_', '').rstrip('lLfFdD')
        try:
            return float(raw) if re.search(r'[.eE]', raw) else int(raw)
        except ValueError:
            return U
    if node.type in ('true', 'false'):
        return node.type == 'true'
    if node.type == 'string_literal':
        import json
        try:
            return json.loads(raw)
        except ValueError:
            return U
    return U


def assume(node, env, truth, types, symbol):
    """Refine supported locals in one selected path; assignments replace these values."""
    node = unparenthesized(node)
    if node is None:
        return False
    if any(n.type in ('assignment_expression', 'update_expression') for n in walk(node)):
        return False
    if node.type == 'unary_expression' and text(node).startswith('!'):
        return assume(node.named_children[-1], env, not truth, types, symbol)
    if node.type == 'identifier':
        name = text(node)
        if types.get(name, '').split('.')[-1] in ('boolean', 'Boolean') and env.get(name, U) is U:
            env[name] = truth
            return True
        return False
    if node.type != 'binary_expression':
        return False
    op = text(node.child_by_field_name('operator'))
    left, right = unparenthesized(node.child_by_field_name('left')), unparenthesized(node.child_by_field_name('right'))
    if op in ('&&', '||'):
        if (op == '&&' and truth) or (op == '||' and not truth):
            a = assume(left, env, truth, types, symbol)
            b = assume(right, env, truth, types, symbol)
            return a or b
        return False
    if op not in INVERSE:
        return False
    value = literal(right)
    if left is None or left.type != 'identifier' or value is U:
        value = literal(left)
        left, right, op = right, left, REVERSE[op]
    if left is None or left.type != 'identifier' or value is U:
        return False
    name, current = text(left), env.get(text(left), U)
    typ = types.get(name, '').split('.')[-1]
    constant_node = unparenthesized(right)
    while constant_node and constant_node.type == 'unary_expression':
        constant_node = constant_node.named_children[-1]
    # Java can round integral operands during floating-point promotion. Keep
    # mixed domains and inexact literal conversions outside this small domain.
    if scalar(value) and (text(right).rstrip().endswith(('f', 'F'))
            or typ in INTEGERS and constant_node.type == 'decimal_floating_point_literal'
            or typ in ('float', 'Float') and isinstance(value, int) and abs(value) > 2**24
            or typ in ('double', 'Double') and isinstance(value, int) and abs(value) > 2**53):
        return False
    # NaN makes all ordered comparisons false. Their negation is not a numeric
    # complement unless finiteness has independently been established.
    if typ in NUMBERS - INTEGERS and not truth:
        return False
    op = op if truth else INVERSE[op]
    if current is not U and not isinstance(current, dict):
        if (scalar(current) and scalar(value)) or isinstance(current, type(value)):
            import operator
            operations = {'>': operator.gt, '>=': operator.ge, '<': operator.lt,
                          '<=': operator.le, '==': operator.eq, '!=': operator.ne}
            if not operations[op](current, value):
                raise InfeasiblePath('Conflicting concrete scalar predicates')
        return False
    if compare(current, op, value) is False:
        raise InfeasiblePath('Predicate contradicts the current scalar interval')
    if op == '==' and ((scalar(value) and typ in NUMBERS and (typ not in INTEGERS or value == math.floor(value)))
                       or isinstance(value, str) and typ == 'String'
                       or isinstance(value, bool) and typ in ('boolean', 'Boolean')):
        env[name] = value
        return True
    if typ not in NUMBERS or not scalar(value):
        return False
    abstract = deepcopy(current) if isinstance(current, dict) and '__symbol__' in current else {
        '__symbol__': symbol(), '__type__': typ, '__constraints__': ['path_condition']}
    bounds = abstract.setdefault('__interval__', {'low': None, 'high': None, 'excluded': []})
    if op in ('>', '>='):
        bound, closed = (math.floor(value) + 1, True) if typ in INTEGERS and op == '>' else (math.ceil(value), True) if typ in INTEGERS else (value, op == '>=')
        old = bounds['low']
        if old is None or bound > old:
            bounds.update(low=bound, low_closed=closed)
        elif old == bound:
            bounds['low_closed'] = bounds.get('low_closed', False) and closed
    elif op in ('<', '<='):
        bound, closed = (math.ceil(value) - 1, True) if typ in INTEGERS and op == '<' else (math.floor(value), True) if typ in INTEGERS else (value, op == '<=')
        old = bounds['high']
        if old is None or bound < old:
            bounds.update(high=bound, high_closed=closed)
        elif old == bound:
            bounds['high_closed'] = bounds.get('high_closed', False) and closed
    elif op == '!=':
        bounds['excluded'] = sorted(set(bounds['excluded']) | {value})
    low, high = bounds.get('low'), bounds.get('high')
    if low is not None and high is not None:
        if low > high or low == high and (not bounds.get('low_closed')
                or not bounds.get('high_closed') or low in bounds['excluded']):
            raise InfeasiblePath('Empty scalar interval')
    env[name] = abstract
    return True
