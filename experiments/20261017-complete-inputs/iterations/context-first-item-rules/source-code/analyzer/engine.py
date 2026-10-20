"""Bounded abstract interpretation of Java source, with explicit unknown values.

Only source text is interpreted. This module never loads JVM classes or contacts
the application's services. Unresolved branches retain both possible paths.
"""
from collections import defaultdict
from copy import deepcopy
import json
import operator
import math
import re
from urllib.parse import urlsplit, parse_qsl, unquote

from .project import text
from .state import U
from .models import construct, library, known, unwrap, wire, key_equal, http_entity, optional_value
from .constraints import assume, compare


def member(obj, key):
    if not isinstance(obj, dict):
        return U
    if key in obj:
        return obj[key]
    normalized = re.sub(r'[^a-z0-9]', '', key.lower())
    return next((v for k, v in obj.items() if re.sub(r'[^a-z0-9]', '', k.lower()) == normalized), U)


def merge(a, b):
    if a == b:
        return a
    if isinstance(a, dict) and isinstance(b, dict):
        return {key: merge(a.get(key, U), b.get(key, U)) for key in sorted(a.keys() | b.keys(), key=lambda k: (type(k).__name__, str(k)))}
    return U


class AlternativeRequired(Exception):
    def __init__(self, key, choices):
        self.key, self.choices = key, choices


class JavaThrow(Exception):
    def __init__(self, value):
        self.value = value


class Engine:
    def __init__(self, project, state, decisions=None, conservative=False, constraints=True):
        self.p, self.state = project, state
        self.edges = set()
        self.evidence = defaultdict(set)
        self.conditions, self.warnings = [], set()
        self.data_operations = []
        self.created_objects = []
        self.active = set()
        self.calls = 0
        self.method = None
        self.params = {}
        self.uncertain = 0
        self.decisions = decisions or {}
        self.conservative = conservative
        self.branch_index = 0
        self.approximate = False
        self.outcome = 'returned' 
        self.use_constraints = constraints
        self.variable_types = {}
        self.constraint_sequence = 0

    def constraint_symbol(self):
        self.constraint_sequence += 1
        return 'path-scalar-' + str(self.constraint_sequence)

    def choose(self, label, choices):
        self.branch_index += 1
        key = str(self.branch_index) + ':' + label
        if key in self.decisions:
            return self.decisions[key]
        if not self.conservative:
            raise AlternativeRequired(key, choices)
        self.approximate = True
        self.warnings.add('path budget: alternatives conservatively retained at ' + label)
        return None

    def add(self, source, relation, target, reason):
        self.edges.add((source, relation, target))
        self.evidence[(source, relation, target)].add(reason)

    def executed(self, mid, reason):
        self.add('', 'executes', mid, reason)

    def run(self, entry, params):
        self.params = params
        self.entry = entry
        try:
            for mid in self.p.by_name.get('doFilterInternal', []):
                if (self.p.ix.unit_of(mid) == self.p.ix.unit_of(entry)
                        and 'OncePerRequestFilter' in (self.p.root / self.p.methods[mid]['file']).read_text()):
                    self.invoke(mid, [], reason='project request filter')
            args = [self.input_value(name, typ, params) for name, typ in self.p.parameters(entry)]
            result = self.invoke(entry, args, reason='scenario request')
        except JavaThrow:
            self.outcome = 'uncaught application exception'
            return U
        return unwrap(result)

    def input_value(self, name, typ, params):
        if name.lower() in ('headers', 'httpheaders'):
            return {'__type__': 'HttpHeaders'}
        if name in params:
            if isinstance(params[name], dict) and '__json__' in params[name] and any(
                    p['name'] == name and p['kind'] == 'RequestBody' and p['type'].split('.')[-1] == 'String'
                    for p in self.p.http_parameters(self.method or getattr(self, 'entry', ''))):
                return deepcopy(params[name])
            return self.coerce(params[name], typ)
        if typ.split('.')[-1] in ('String', 'UUID', 'int', 'double', 'boolean', 'Date', 'Long'):
            return U
        value = {'__type__': typ, **deepcopy(params)}
        method = self.method or getattr(self, 'entry', '')
        meta = self.p.methods.get(method, {})
        tid = self.p.resolve_type(typ, meta.get('module'), meta.get('file'))
        if tid in self.p.type_fields and not typ.startswith('org.springframework.http.'):
            value['__http_entity__'] = False
        return value

    @staticmethod
    def coerce(value, typ):
        typ = typ.split('.')[-1]
        if value is U or value is None:
            return value
        if isinstance(value, dict) and '__symbol__' in value:
            aliases = {'Integer': 'int', 'Long': 'long', 'Boolean': 'boolean', 'Double': 'double', 'Float': 'float'}
            source_type = value['__type__'].split('.')[-1]
            return value if aliases.get(source_type, source_type) == aliases.get(typ, typ) else U
        if typ in ('boolean', 'Boolean'):
            return value if isinstance(value, bool) else value.lower() == 'true' if isinstance(value, str) and value.lower() in ('true', 'false') else U
        if typ in ('int', 'Integer', 'long', 'Long', 'short', 'Short', 'byte', 'Byte'):
            if isinstance(value, bool):
                return U
            try:
                return int(value) if isinstance(value, (str, int)) else U
            except ValueError:
                return U
        if typ in ('double', 'Double', 'float', 'Float'):
            try:
                return float(value) if not isinstance(value, bool) else U
            except (TypeError, ValueError):
                return U
        if typ == 'Date':
            from .models import date_value
            return date_value(value)
        if typ == 'String':
            return value if isinstance(value, str) else U
        if isinstance(value, str):
            try:
                if typ in ('int', 'Integer', 'long', 'Long'): return int(value)
                if typ in ('double', 'Double', 'float', 'Float'): return float(value)
                if typ in ('boolean', 'Boolean'): return value.lower() == 'true'
            except ValueError:
                return U
        return value

    def invoke(self, mid, args, receiver=None, reason='source call'):
        self.executed(mid, reason)
        if any(a['name'].split('.')[-1] == 'Transactional' for a in self.p.methods[mid].get('annotations', [])):
            self.approximate = True
            self.warnings.add('transaction dirty checking is not fully modeled: ' + mid)
        signature = (mid, json.dumps(args, sort_keys=True, default=str))
        if signature in self.active or self.calls >= 12000 or len(self.active) >= 64:
            self.warnings.add('recursion or context budget: conservative closure used')
            self.fallback(mid)
            return U
        node = self.p.ast.get(mid)
        if node is None:
            self.warnings.add('no source body: ' + mid)
            self.fallback(mid)
            return U
        self.calls += 1
        self.active.add(signature)
        previous = self.method
        previous_types = self.variable_types
        self.method = mid
        self.variable_types = dict(self.p.parameters(mid))
        env = {name: args[i] if i < len(args) else U for i, (name, _) in enumerate(self.p.parameters(mid))}
        env['this'] = receiver if isinstance(receiver, dict) else {}
        body = node.child_by_field_name('body')
        try:
            try:
                result, control = self.execute(body, env)
            except (TypeError, ValueError, IndexError, KeyError, AttributeError, ZeroDivisionError) as exc:
                self.approximate = True
                self.warnings.add('unsupported value operation in ' + mid + ': ' + type(exc).__name__)
                self.fallback(mid)
                result, control = U, None
        finally:
            self.method = previous
            self.variable_types = previous_types
            self.active.remove(signature)
        if control == 'throw':
            raise JavaThrow(result)
        return result

    def fallback(self, mid):
        self.approximate = True
        methods, calls, remote, data = self.p.ix.closure({mid})
        for method in methods:
            self.executed(method, 'unresolved source: may-call closure')
        for relation, pairs in [('calls', calls), ('remote', remote), ('data', data)]:
            for source, target in pairs:
                self.add(source, relation, target, 'unresolved source: may-call closure')
                if relation == 'data':
                    rows = self.state.database.rows(self.p.nodes[target])
                    if rows is not None:
                        self.state.database.invalidate(rows)

    def execute(self, node, env):
        if node is None:
            return U, None
        typ = node.type
        if typ in ('block', 'constructor_body'):
            for child in node.named_children:
                value, control = self.execute(child, env)
                if control:
                    return value, control
            return U, None
        if typ in ('return_statement', 'throw_statement'):
            value = self.value(node.named_children[0], env) if node.named_children else None
            return value, 'return' if typ == 'return_statement' else 'throw'
        if typ == 'if_statement':
            cond = self.value(node.child_by_field_name('condition'), env)
            self.conditions.append({'method': self.method, 'line': node.start_point.row + 1,
                                    'condition': text(node.child_by_field_name('condition')),
                                    'value': cond if isinstance(cond, bool) else 'unknown'})
            if isinstance(cond, bool):
                return self.execute(node.child_by_field_name('consequence' if cond else 'alternative'), env)
            decision = self.choose(self.method + ':' + str(node.start_point.row + 1), [True, False])
            if decision is not None:
                if self.use_constraints:
                    refined = assume(node.child_by_field_name('condition'), env, decision,
                                     self.variable_types, self.constraint_symbol)
                    self.conditions[-1]['refined'] = refined
                return self.execute(node.child_by_field_name('consequence' if decision else 'alternative'), env)
            before_state = deepcopy(self.state)
            left, right = deepcopy(env), deepcopy(env)
            self.uncertain += 1
            self.state = deepcopy(before_state)
            a, ac = self.execute(node.child_by_field_name('consequence'), left)
            left_state = self.state
            self.state = deepcopy(before_state)
            b, bc = self.execute(node.child_by_field_name('alternative'), right)
            right_state = self.state
            self.state = before_state
            # Changes on incompatible paths are not committed to a shared database.
            self.state.database.unknown_tables.update(left_state.database.unknown_tables | right_state.database.unknown_tables)
            for table in set(left_state.database.tables) | set(right_state.database.tables):
                if left_state.database.tables.get(table) != right_state.database.tables.get(table):
                    self.state.database.unknown_tables.add(table)
            self.uncertain -= 1
            env.update(merge(left, right))
            return (merge(a, b), ac) if ac == bc and ac else (U, None)
        if typ == 'enhanced_for_statement':
            values = self.value(node.child_by_field_name('value'), env)
            name = text(node.child_by_field_name('name'))
            items = values if isinstance(values, list) else [U]
            if len(items) > 64:
                self.approximate = True
                self.warnings.add('loop collection widened after 64 elements')
                items = items[:64] + [U]
            for item in items:
                env[name] = item
                result, control = self.execute(node.child_by_field_name('body'), env)
                if control in ('return', 'throw') and isinstance(values, list):
                    return result, control
                if control == 'break': break
            return U, None
        if typ in ('for_statement', 'while_statement', 'do_statement'):
            init = node.child_by_field_name('init')
            if init: self.execute(init, env)
            condnode = node.child_by_field_name('condition')
            for iteration in range(64):
                cond = self.value(condnode, env) if condnode else U
                if cond is False and not (typ == 'do_statement' and iteration == 0): break
                if cond is U:
                    decision = self.choose(self.method + ':loop:' + str(node.start_point.row + 1), [True, False])
                    if decision is False:
                        break
                    if decision is True:
                        cond = True
                    else:
                        self.uncertain += 1
                result, control = self.execute(node.child_by_field_name('body'), env)
                if cond is U: self.uncertain -= 1
                if control in ('return', 'throw') and cond is True: return result, control
                if control == 'break': break
                update = node.child_by_field_name('update')
                if update: self.value(update, env)
                if cond is not True:
                    self.warnings.add('unknown loop bounded to one pass: ' + self.method)
                    break
            else:
                self.approximate = True
                self.warnings.add('loop bounded after 64 passes: ' + self.method)
                self.fallback(self.method)
            return U, None
        if typ == 'try_statement' or typ == 'try_with_resources_statement':
            resources = node.child_by_field_name('resources')
            if resources:
                self.value(resources, env)
            try:
                result, control = self.execute(node.child_by_field_name('body'), env)
            except JavaThrow as exc:
                result, control = exc.value, 'throw'
            if control == 'throw':
                for child in node.named_children:
                    if child.type == 'catch_clause':
                        result, control = self.execute(child.child_by_field_name('body'), env)
                        break
            for child in node.named_children:
                if child.type == 'finally_clause':
                    final, fc = self.execute(child.named_children[-1], env)
                    if fc:
                        return final, fc
            return result, control
        if typ == 'local_variable_declaration':
            for child in node.named_children:
                if child.type == 'variable_declarator':
                    name = text(child.child_by_field_name('name'))
                    self.variable_types[name] = text(node.child_by_field_name('type'))
                    env[name] = self.value(child.child_by_field_name('value'), env)
            return U, None
        if typ in ('break_statement', 'continue_statement'):
            return U, 'break' if typ == 'break_statement' else 'continue'
        if typ in ('line_comment', 'block_comment'):
            return U, None
        return self.value(node, env), None

    def value(self, node, env):
        if node is None:
            return U
        typ, raw = node.type, text(node)
        if typ == 'identifier':
            return env.get(raw, member(env.get('this'), raw))
        if typ in ('true', 'false'):
            return typ == 'true'
        if typ == 'null_literal':
            return None
        if typ == 'character_literal':
            return raw[1:-1]
        if typ == 'string_literal':
            try:
                return json.loads(raw)
            except ValueError:
                return raw[1:-1]
        if typ in ('decimal_integer_literal', 'decimal_floating_point_literal'):
            try:
                return float(raw.rstrip('fFdD')) if '.' in raw else int(raw.rstrip('lL'))
            except ValueError:
                return U
        if typ == 'this':
            return env.get('this', U)
        if typ == 'parenthesized_expression':
            return self.value(node.named_children[-1], env)
        if typ == 'cast_expression':
            value = self.value(node.named_children[-1], env)
            target = text(node.child_by_field_name('type'))
            limits = {'byte': (-128, 127), 'short': (-32768, 32767),
                      'int': (-2147483648, 2147483647), 'long': (-9223372036854775808, 9223372036854775807)}
            if target in limits:
                if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
                    narrowed = int(value)
                    if limits[target][0] <= narrowed <= limits[target][1]:
                        return narrowed
                self.approximate = True
                self.warnings.add('unsupported numeric cast outside modeled finite range: ' + text(node))
                return U
            return value
        if typ == 'field_access':
            if raw in self.p.constants: return self.p.constants[raw]
            constants = {'Float.MAX_VALUE': 3.4028235e38, 'Double.MAX_VALUE': 1.7976931348623157e308,
                         'Long.MAX_VALUE': 9223372036854775807, 'Integer.MAX_VALUE': 2147483647}
            if raw in constants: return constants[raw]
            if raw.startswith(('HttpMethod.', 'HttpStatus.', 'Calendar.')):
                return raw.split('.')[-1]
            enum = self.p.enum_reference(raw, self.method)
            if enum:
                return deepcopy(self.p.enum_objects[enum])
            obj = self.value(node.child_by_field_name('object'), env)
            field = text(node.child_by_field_name('field'))
            return len(obj) if isinstance(obj, list) and field == 'length' else member(obj, field)
        if typ == 'unary_expression':
            arg = self.value(node.child_by_field_name('operand') or node.named_children[-1], env)
            if arg is U:
                return U
            if raw.startswith('!') and isinstance(arg, bool):
                return not arg
            if raw.startswith('-') and isinstance(arg, (int, float)):
                return -arg
            return U
        if typ == 'binary_expression':
            op = text(node.child_by_field_name('operator'))
            a = self.value(node.child_by_field_name('left'), env)
            if (op == '&&' and a is False) or (op == '||' and a is True):
                return a
            b = self.value(node.child_by_field_name('right'), env)
            if op == '&&' and b is False:
                return False
            if op == '||' and b is True:
                return True
            if a is U or b is U:
                return U
            if any(isinstance(v, dict) and '__symbol__' in v for v in (a, b)):
                if self.use_constraints:
                    constrained = compare(a, op, b)
                    if constrained is not U:
                        return constrained
                if op in ('==', '!=') and a == b:
                    return op == '=='
                return U
            ops = {'==': operator.eq, '!=': operator.ne, '<': operator.lt, '>': operator.gt,
                   '<=': operator.le, '>=': operator.ge, '+': operator.add, '-': operator.sub,
                   '*': operator.mul, '/': operator.truediv, '&&': lambda x, y: x and y,
                   '||': lambda x, y: x or y}
            if op == '+' and (isinstance(a, str) or isinstance(b, str)):
                return str(a) + str(b)
            try:
                if op in ('/', '%') and type(a) is int and type(b) is int:
                    quotient = (abs(a) // abs(b)) * (-1 if (a < 0) != (b < 0) else 1)
                    return quotient if op == '/' else a - quotient * b
                if op in ops:
                    return ops[op](a, b)
                self.approximate = True
                self.warnings.add('unsupported Java binary operator: ' + op)
                return U
            except (TypeError, ValueError, ZeroDivisionError):
                self.approximate = True
                self.warnings.add('unsupported or failing Java arithmetic: ' + raw)
                return U
        if typ == 'update_expression':
            child = node.named_children[0]
            old = self.value(child, env)
            new = old + (1 if '++' in raw else -1) if isinstance(old, (int, float)) else U
            if child.type == 'identifier': env[text(child)] = new
            return new if raw.startswith(('++', '--')) else old
        if typ == 'assignment_expression':
            lhs, rhs = node.child_by_field_name('left'), node.child_by_field_name('right')
            result = self.value(rhs, env)
            op = text(node.child_by_field_name('operator'))
            if op != '=':
                old = self.value(lhs, env)
                try: result = {'+=': operator.add, '-=': operator.sub}[op](old, result)
                except (KeyError, TypeError): result = U
            if lhs.type == 'identifier':
                env[text(lhs)] = result
            elif lhs.type == 'field_access':
                obj = self.value(lhs.child_by_field_name('object'), env)
                if isinstance(obj, dict):
                    obj[text(lhs.child_by_field_name('field'))] = result
            return result
        if typ == 'ternary_expression':
            c = self.value(node.child_by_field_name('condition'), env)
            if isinstance(c, bool):
                return self.value(node.child_by_field_name('consequence' if c else 'alternative'), env)
            decision = self.choose(self.method + ':ternary:' + str(node.start_point.row + 1), [True, False])
            if decision is not None:
                return self.value(node.child_by_field_name('consequence' if decision else 'alternative'), env)
            self.uncertain += 1
            self.approximate = True
            result = merge(self.value(node.child_by_field_name('consequence'), deepcopy(env)),
                         self.value(node.child_by_field_name('alternative'), deepcopy(env)))
            self.uncertain -= 1
            return result
        if typ in ('switch_expression', 'switch_statement'):
            selected = self.value(node.child_by_field_name('condition'), env)
            groups = node.child_by_field_name('body').named_children
            matched = False
            selected_group = None
            if selected is U:
                selected_group = self.choose(self.method + ':switch:' + str(node.start_point.row + 1), list(range(len(groups))))
            for group_index, group in enumerate(groups):
                label = group.named_children[0]
                cases = [self.value(c, env) for c in label.named_children]
                take = (selected is U and (selected_group is None or selected_group == group_index)) or selected in cases or (text(label) == 'default' and not matched)
                if not take: continue
                matched = True
                branch = deepcopy(env) if selected is U else env
                for stmt in group.named_children[1:]:
                    _, control = self.execute(stmt, branch)
                    if control: break
                if selected is U: env.update(merge(env, branch)); self.approximate = True
                else: break
            return U
        if typ == 'lambda_expression':
            return ('lambda', node, dict(env), self.method, dict(self.variable_types))
        if typ in ('method_invocation', 'object_creation_expression'):
            return self.call(node, env)
        if typ == 'array_initializer':
            return [self.value(child, env) for child in node.named_children]
        if typ == 'array_access':
            arr = self.value(node.child_by_field_name('array'), env)
            idx = self.value(node.child_by_field_name('index'), env)
            return arr[idx] if isinstance(arr, list) and isinstance(idx, int) and 0 <= idx < len(arr) else U
        if typ == 'expression_statement':
            return self.value(node.named_children[0], env)
        if typ in ('type_identifier', 'scoped_type_identifier', 'generic_type', 'class_literal', 'line_comment', 'block_comment'):
            return U
        for child in node.named_children:
            if child.type.endswith('statement') or child.type in ('block', 'local_variable_declaration'):
                self.execute(child, env)
            else:
                self.value(child, env)
        if typ in ('switch_expression', 'switch_statement'):
            self.warnings.add('switch alternatives conservatively retained: ' + self.method)
        return U

    def call(self, node, env):
        mid = self.method
        site = self.p.site(mid, node)
        cs = self.p.nodes.get(site, {})
        name = '<init>' if node.type == 'object_creation_expression' else text(node.child_by_field_name('name'))
        objnode = node.child_by_field_name('object')
        obj = self.value(objnode, env) if objnode else env.get('this', U)
        argnode = node.child_by_field_name('arguments')
        args = [self.value(child, env) for child in argnode.named_children
                if child.type not in ('line_comment', 'block_comment')] if argnode else []
        reason = site or f"{self.p.methods[mid]['file']}:{node.start_point.row + 1}"
        wiring = self.p.edges.get(site, {})
        targets = self.p.targets(mid, site) if site else self.p.source_targets(mid, node)
        receiver_type = cs.get('receiver_type')
        if not targets and name == 'builder' and receiver_type in self.p.builder_types:
            fields = self.p.builder_types[receiver_type]
            return {'__builder__': receiver_type, 'fields': {n: False if t == 'boolean' else 0 if t in ('int', 'long', 'double', 'float') else None for n, t in fields}}
        if not targets and isinstance(obj, dict) and '__builder__' in obj:
            if name == 'build': return {'__type__': obj['__builder__'], **deepcopy(obj['fields'])}
            if name in obj['fields'] and len(args) == 1:
                obj['fields'][name] = args[0]
                return obj
        if not targets and name == 'values' and not args:
            meta = self.p.methods[mid]
            tid = self.p.resolve_type(text(objnode), meta['module'], meta['file'])
            values = [deepcopy(self.p.enum_objects[key]) for key in self.p.enum_members.get(tid, [])]
            if values: return values
        if not targets and name == 'encode' and receiver_type and 'PasswordEncoder' in receiver_type and args and isinstance(args[0], str):
            # Abstract non-null encoding; no hashing or authentication is executed.
            return 'encoded:' + args[0]
        if not targets and isinstance(obj, dict) and (obj.get('__type__') or obj.get('__enum_type__')) and name != '<init>':
            runtime_type = self.p.nodes[obj['__enum_type__']]['fqn'] if obj.get('__enum_type__') else obj['__type__']
            targets = [m for m in self.p.by_name.get(name, [])
                       if (self.p.nodes[self.p.methods[m]['owner']]['fqn'] == runtime_type if '.' in runtime_type else self.p.nodes[self.p.methods[m]['owner']]['fqn'].split('.')[-1] == runtime_type)
                       and len(self.p.methods[m].get('params_as_written', [])) == len(args)
                       and not self.p.methods[m].get('abstract')
                       and self.p.ix.unit_of(mid) in self.p.ix.units.get(self.p.methods[m]['module'], ())]
        if name == '<init>':
            typ = text(node.child_by_field_name('type'))
            obj = {'__type__': typ}
            tid = self.p.resolve_type(typ, self.p.methods[mid]['module'], self.p.methods[mid]['file'])
            if tid:
                obj = {'__type__': self.p.nodes[tid]['fqn'], '__http_entity__': False}
            for field, info in self.p.type_fields.get(tid, {}).items():
                default = info['default']
                if default is U and not info['has_initializer']:
                    default = False if info['type'] == 'boolean' else 0 if info['type'] in ('int', 'long', 'double', 'float', 'short', 'byte') else None
                elif default is U:
                    self.approximate = True
                    self.warnings.add('unsupported instance initializer: ' + str(tid) + '.' + field)
                obj[field] = deepcopy(default)
            if typ.split('.')[-1] == 'UsernamePasswordAuthenticationToken':
                obj.update(principal=args[0] if args else U, credentials=args[1] if len(args) > 1 else U)
            if not tid and re.match(r'(ArrayList|LinkedList|List|HashSet|Set)', typ):
                obj = list(args[0]) if args and isinstance(args[0], list) else []
        if name == '<init>':
            handled, value = construct(typ, args, self.state.now) if not tid and not targets else (False, U)
            if handled: obj = value
            elif not targets and receiver_type in self.p.all_args_types:
                fields = self.p.all_args_types[receiver_type]
                if len(fields) == len(args): obj = {'__type__': receiver_type, **{n: v for (n, _), v in zip(fields, args)}}
        if len(targets) > 1:
            selected = self.choose(reason + ':dispatch', targets)
            if selected is not None:
                targets = [selected]
            else:
                self.uncertain += 1
        result = U
        for target_index, target in enumerate(targets):
            self.add(mid, 'calls', target, reason)
            value = self.invoke(target, args, obj, reason)
            result = value if target_index == 0 else merge(result, value)
        if wiring.get('data_access'):
            return self.repository(mid, cs, args, sorted(wiring['data_access']), reason)
        remote = sorted(wiring.get('remote_call', set()) | wiring.get('message_delivery', set()))
        if (not remote and name in ('exchange', 'getForEntity', 'postForEntity', 'getForObject', 'postForObject')
                and receiver_type and receiver_type.split('.')[-1] in ('RestTemplate', 'RestOperations')
                and args and isinstance(args[0], str) and args[0].startswith('http')):
            verb = args[1] if name == 'exchange' and len(args) > 1 and isinstance(args[1], str) else 'GET' if name.startswith('get') else 'POST'
            remote = sorted(self.p.ix.handlers_for(verb, urlsplit(args[0]).path, urlsplit(args[0]).hostname))
        if remote:
            url = args[0] if args and isinstance(args[0], str) else None
            if url and url.startswith('http'):
                verb = args[1] if len(args) > 1 and isinstance(args[1], str) else None
                matched = set(self.p.ix.handlers_for(verb, urlsplit(url).path, urlsplit(url).hostname))
                remote = sorted(matched)
                if not remote:
                    self.approximate = True
                    self.warnings.add('known HTTP URL has no matching source handler: ' + reason)
            else:
                self.approximate = True
                self.warnings.add('remote target is approximated from static wiring: ' + reason)
            results = []
            request = args[2] if name == 'exchange' and len(args) > 2 else args[1] if name.startswith('post') and len(args) > 1 else None
            body = unwrap(request) if http_entity(request) else request if name.startswith('post') else None if request is None else U
            if len(remote) > 1:
                selected = self.choose(reason + ':remote', remote)
                if selected is not None:
                    remote = [selected]
                else:
                    self.uncertain += 1
            for target in remote:
                self.add(mid, 'remote', target, reason)
                values = []
                route_values = self.path_parameters(target, url)
                for par, typ in self.p.parameters(target):
                    if par in route_values:
                        values.append(self.coerce(route_values[par], typ))
                    elif 'Header' in typ:
                        values.append({})
                    else:
                        values.append(body)
                results.append(wire(unwrap(self.invoke(target, values, reason=reason))))
            value = results[0] if len(results) == 1 else U
            return {'__type__': 'ResponseEntity', '__http_entity__': True, 'body': value} if name in ('exchange', 'getForEntity', 'postForEntity') else value
        if name == 'authenticate' and 'AuthenticationManager' in (cs.get('receiver_type') or ''):
            self.authentication(mid, args, reason)
        if name == '<init>':
            return obj
        if not targets:
            handled, value = self.stream_call(name, obj, args, text(objnode), reason, env)
            if handled:
                return value
        handled, value = library(name, obj, args, text(objnode), self.state.now) if not targets else (False, U)
        if handled: return value
        if targets:
            return result
        if name.startswith(('get', 'is')) and not args:
            prop = name[3:] if name.startswith('get') else name[2:]
            prop = prop[:1].lower() + prop[1:]
            if isinstance(obj, dict):
                value = member(obj, prop)
                if value is not U:
                    return value
        if name.startswith('set') and len(args) == 1 and isinstance(obj, dict):
            prop = name[3:4].lower() + name[4:]
            obj[prop] = args[0]
            return None
        if result is not U:
            return result
        if name == 'orElseThrow' and optional_value(obj):
            value = member(obj, 'optional')
            if value is not U and value is not None:
                return value
            for arg in args:
                if isinstance(arg, tuple) and arg[0] == 'lambda':
                    self.value(arg[1].child_by_field_name('body'), arg[2])
            return U
        if name == 'isPresent' and optional_value(obj):
            val = member(obj, 'optional')
            return val is not None if val is not U else U
        if name == 'get' and not args and optional_value(obj):
            return obj['optional']
        if name in ('isEmpty', 'isBlank'):
            value = args[0] if args else obj
            return value is None or value == '' or value == [] if value is not U else U
        if name in ('equals', 'equalsIgnoreCase') and args:
            return (obj == args[0] if name == 'equals' else str(obj).lower() == str(args[0]).lower()) if known(obj) and known(args[0]) else U
        if name == 'startsWith' and args and isinstance(obj, str) and isinstance(args[0], str):
            return obj.startswith(args[0])
        if name == 'toString':
            return str(obj) if isinstance(obj, (str, int, float)) else U
        if name in ('valueOf', 'fromString', 'parseInt', 'parseDouble', 'parseFloat') and args and args[0] is not U:
            try:
                return int(args[0]) if name == 'parseInt' else float(args[0]) if name in ('parseDouble', 'parseFloat') else args[0]
            except (ValueError, TypeError):
                return U
        if name == 'size' and isinstance(obj, list):
            return len(obj)
        if name == 'get' and isinstance(obj, list) and args and isinstance(args[0], int):
            return obj[args[0]] if 0 <= args[0] < len(obj) else U
        if name in ('add', 'addAll') and isinstance(obj, list) and args:
            obj.extend(args[0] if name == 'addAll' and isinstance(args[0], list) else [args[0]])
            return True
        if name == 'randomUUID':
            # Symbolic IDs are stable within a run and never refer to runtime data.
            self.state.symbol_sequence += 1
            return 'symbolic-' + str(self.state.symbol_sequence)
        if name not in ('debug', 'info', 'warn', 'error', 'trace', 'println', 'print'):
            self.approximate = True
            self.warnings.add('unsupported call: ' + reason + ' ' + name)
        return U

    def stream_call(self, name, obj, args, receiver, reason, env):
        """Sequential lazy filter/map pipelines over a known ordered collection."""
        if name == 'stream' and isinstance(obj, list) and not args:
            return True, {'__stream__': obj, 'operations': [], 'lifecycle': {'consumed': False}}
        if name == 'toList' and not args and receiver in ('Collectors', 'java.util.stream.Collectors'):
            meta = self.p.methods[self.method]
            source = text(self.p.trees[meta['file']].root_node)
            imported = bool(re.search(r'\bimport\s+java\.util\.stream\.(?:Collectors|\*)\s*;', source))
            shadowed = receiver in env or self.p.resolve_type(receiver, meta['module'], meta['file'])
            if not shadowed and (receiver.startswith('java.') or imported):
                return True, {'__collector__': 'java.util.stream.Collectors.toList'}
        if not isinstance(obj, dict) or '__stream__' not in obj:
            return False, U
        if obj['lifecycle']['consumed']:
            self.approximate = True
            self.warnings.add('stream reused after consumption: ' + reason)
            return True, U
        if name in ('filter', 'map') and len(args) == 1 and isinstance(args[0], tuple) and args[0][0] == 'lambda':
            return True, {**obj, 'operations': [*obj['operations'], (name, args[0])]}
        if name != 'collect' or args != [{'__collector__': 'java.util.stream.Collectors.toList'}]:
            self.approximate = True
            self.warnings.add('unsupported stream operation: ' + reason + ' ' + name)
            return True, U
        obj['lifecycle']['consumed'] = True
        if len(obj['__stream__']) > 10000:
            self.warnings.add('stream collection budget exceeded: ' + reason)
            self.fallback(self.method)
            return True, U
        output = []
        for item in obj['__stream__']:
            keep = True
            for operation, callback in obj['operations']:
                value = self.lambda_value(callback, item)
                if operation == 'map':
                    item = value
                    continue
                if type(value) is not bool:
                    value = self.choose(reason + ':stream-filter', [True, False])
                    if value is None:
                        self.warnings.add('unknown stream membership: ' + reason)
                        self.fallback(self.method)
                        return True, U
                if not value:
                    keep = False
                    break
            if keep:
                output.append(item)
        return True, output

    def lambda_value(self, callback, item):
        node, captured, owner, types = callback[1:]
        parameters = node.child_by_field_name('parameters')
        names = ([text(parameters)] if parameters is not None and parameters.type == 'identifier' else
                 [text(child.child_by_field_name('name') or child) for child in parameters.named_children]
                 if parameters is not None else [])
        if len(names) != 1:
            self.approximate = True
            self.warnings.add('unsupported stream callback parameters: ' + text(node))
            return U
        local = {**captured, names[0]: item}
        previous, previous_types = self.method, self.variable_types
        self.method, self.variable_types = owner, dict(types)
        try:
            body = node.child_by_field_name('body')
            if body.type != 'block':
                return self.value(body, local)
            value, control = self.execute(body, local)
            if control == 'throw':
                raise JavaThrow(value)
            return value if control == 'return' else U
        finally:
            self.method, self.variable_types = previous, previous_types

    def path_parameters(self, target, url):
        if not url:
            return {}
        segments = urlsplit(url).path.strip('/').split('/')
        for mid, _, template in self.p.ix.handlers:
            if mid == target and len(template) == len(segments) and all(
                    key.startswith('{') or key in ('*', '**') or key == val for key, val in zip(template, segments)):
                values = {key[1:-1].split(':', 1)[0]: unquote(value) for key, value in zip(template, segments) if key.startswith('{')}
                query = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
                for par in self.p.http_parameters(target):
                    source = values if par['kind'] == 'PathVariable' else query if par['kind'] == 'RequestParam' else {}
                    if par['wire_name'] in source:
                        values[par['name']] = source[par['wire_name']]
                    elif par['kind'] == 'RequestParam' and par['default'] is not U:
                        values[par['name']] = par['default']
                    elif par['kind'] == 'RequestParam' and not par['required']:
                        values[par['name']] = None
                return values
        return {}

    def authentication(self, mid, args, reason):
        module = self.p.methods[mid]['module']
        principal = member(args[0], 'principal') if args else U
        self.approximate = True
        self.warnings.add('authentication provider result is abstracted')
        for callback in self.p.by_name.get('loadUserByUsername', []):
            if self.p.methods[callback]['module'] == module and not self.p.methods[callback].get('abstract'):
                self.invoke(callback, [principal], reason='Spring authentication callback at ' + reason)
        for name in ('getPassword', 'getAuthorities', 'isAccountNonExpired', 'isAccountNonLocked', 'isCredentialsNonExpired', 'isEnabled'):
            for callback in self.p.by_name.get(name, []):
                meta = self.p.methods[callback]
                if meta['module'] == module and any(a.split('.')[-1] == 'UserDetails' for a in self.p.framework_types.get(meta['owner'], set())):
                    self.invoke(callback, [], reason='UserDetails authentication callback at ' + reason)

    def repository(self, mid, cs, args, resources, reason):
        result = U
        for rid in resources:
            self.add(mid, 'data', rid, reason)
            self.data_operations.append({'method': mid, 'resource': rid, 'operation': cs.get('callee'),
                                         'arguments': deepcopy(args), 'source_site': reason,
                                         'uncertain_write': bool(self.uncertain)})
            resource = self.p.nodes[rid]
            rows = self.state.database.rows(resource)
            if rows is None or resource.get('collection_of'):
                self.approximate = True
                self.warnings.add('ORM access is approximated from static mapping: ' + rid)
                continue
            name = cs.get('callee', '')
            entity = self.p.entities.get(rid)
            if name.startswith(('save', 'insert')) and args and isinstance(args[0], dict):
                record = deepcopy(args[0])
                if self.uncertain:
                    self.warnings.add('possible database write not committed: ' + reason)
                    self.state.database.invalidate(rows)
                else:
                    generated = self.p.generated_ids.get(rid)
                    if generated and record.get(generated, U) in (U, None):
                        self.state.symbol_sequence += 1
                        record[generated] = 'symbolic-' + str(self.state.symbol_sequence)
                        args[0][generated] = record[generated]
                    keys = self.p.id_fields.get(rid, [])
                    key = tuple(record.get(k, U) for k in keys) if keys else U
                    existing = next((r for r in rows if key is not U and U not in key and all(self.p.materialize(self.state.database, rid, r).get(k, U) == record.get(k, U) for k in keys)), None)
                    if existing is None:
                        rows.append(record)
                        self.created_objects.append({**deepcopy(record), '__resource__': rid,
                                                     '__type__': self.p.nodes[entity]['fqn'] if entity else record.get('__type__', '')})
                    else:
                        existing.update(record)
                result = record
                continue
            selected = [self.p.materialize(self.state.database, rid, r) for r in rows]
            find = re.search(r'(?:find|query|get|delete|exists).*?By(.+)', name)
            unknown_query = False
            query_key = (cs.get('receiver_type'), name)
            declared_query = query_key in self.p.repository_queries
            query = self.p.repository_queries.get(query_key)
            primary_keys = self.p.id_fields.get(rid, [])
            pairs = []
            if declared_query:
                if query is None or any(int(index) > len(args) or int(index) < 1 for _, _, index in query):
                    unknown_query = True
                else:
                    from .state import camel
                    pairs = [(camel(field) + ('In' if op.lower() == 'in' else ''), args[int(index)-1]) for field, op, index in query]
            elif name == 'findAllById' and args and isinstance(args[0], list):
                if len(primary_keys) == 1:
                    selected = [r for r in selected if r.get(primary_keys[0]) in args[0]]
                else:
                    unknown_query = True
            elif find:
                fields = re.split('And', find[1])
                pairs = [(field, value) for field, value in zip(fields, args)]
                if len(fields) != len(args):
                    unknown_query = True
                if name in ('findById', 'getById', 'getReferenceById', 'existsById', 'deleteById') and len(primary_keys) == 1 and args:
                    pairs = [(primary_keys[0], args[0])]
            elif name not in ('findAll', 'count'):
                unknown_query = True
            for field, value in pairs:
                in_query = field.endswith('In')
                field = field[:-2] if in_query else field
                prop = field[:1].lower() + field[1:]
                symbolic_query = isinstance(value, dict) and '__symbol__' in value
                if not known(value) and not symbolic_query:
                    unknown_query = True
                else:
                    def matches(row):
                        nonlocal unknown_query
                        stored = member(row, prop)
                        if symbolic_query or isinstance(stored, dict) and '__symbol__' in stored:
                            equal = key_equal(stored, value)
                            if equal is U:
                                unknown_query = True
                            return equal is not False
                        if not known(stored):
                            unknown_query = True
                            return True
                        if isinstance(stored, dict) and isinstance(value, dict):
                            equal = key_equal(stored, value)
                            if equal is U: unknown_query = True
                            return equal is not False
                        return stored in value if in_query and isinstance(value, list) else stored == value
                    selected = [r for r in selected if matches(r)]
            if unknown_query:
                self.approximate = True
                self.warnings.add('repository predicate is not fully modeled: ' + reason)
            if name.startswith('delete'):
                if not self.uncertain and not unknown_query:
                    if primary_keys:
                        removed = [tuple(row.get(key, U) for key in primary_keys) for row in selected]
                        rows[:] = [row for row in rows if tuple(self.p.materialize(self.state.database, rid, row).get(key, U)
                                                               for key in primary_keys) not in removed]
                    else:
                        self.approximate = True
                        self.warnings.add('deletion without an identifiable primary key: ' + reason)
                else:
                    self.warnings.add('possible deletion not committed: ' + reason)
                    self.state.database.invalidate(rows)
                result = None
                continue
            if name == 'count':
                result = len(rows); continue
            if name.startswith('exists'):
                result = U if unknown_query else bool(selected)
                continue
            materialized = []
            for row in selected:
                record = {'__type__': self.p.nodes[entity]['fqn'] if entity else '', **deepcopy(row)}
                if entity:
                    for ctor in self.p.methods_of(entity, '<init>'):
                        if not self.p.methods[ctor].get('params_as_written'):
                            # Constructor is reached through materialization, not a direct project call.
                            if any(self.p.targets(ctor, site) for site in self.p.sites.get(ctor, [])):
                                self.invoke(ctor, [], deepcopy(record), 'entity materialization with project calls at ' + reason)
                materialized.append(record)
            if unknown_query:
                result = U
                continue
            # Repository declarations are indexed even though their bodies are abstract.
            declared = [m.get('return_raw', '') for m in self.p.methods.values()
                        if m['name'] == name and self.p.nodes[m['owner']]['fqn'] == cs.get('receiver_type')]
            return_type = declared[0] if declared else ('Optional' if name == 'findById' else '')
            first = materialized[0] if materialized else None
            result = {'__optional__': True, 'optional': first} if 'Optional' in return_type else materialized if any(t in return_type for t in ('List', 'Set', 'Collection')) or name == 'findAll' else first
        return result
