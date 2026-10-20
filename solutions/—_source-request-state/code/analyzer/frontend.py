"""Static extraction and symbolic evaluation of browser request contracts."""
from copy import deepcopy
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import json
import re
from urllib.parse import urlsplit, parse_qsl
from tree_sitter import Language, Parser
import tree_sitter_javascript
from baseline_nlp import front_files
from .project import text, walk
from .state import U, JS_UNDEFINED
from .jsflow import definitions_before, url_cases
from .nl_inputs import control_polarity
from .option_sources import option_sources
from .row_events import row_events


def pairs(node):
    return {text(c.child_by_field_name('key')).strip('\"\''): c.child_by_field_name('value')
            for c in node.named_children if c.type == 'pair'} if node and node.type == 'object' else {}


def literal(node):
    if node is None:
        return U
    raw = text(node)
    if node.type == 'string':
        try:
            return json.loads(raw) if raw.startswith('"') else raw[1:-1]
        except ValueError:
            return U
    try:
        return json.loads(raw)
    except ValueError:
        return U


def constant(node):
    if node is not None and node.type == 'object':
        return {key: constant(val) for key, val in pairs(node).items()}
    if node is not None and node.type == 'array':
        return [constant(child) for child in node.named_children]
    return literal(node)


def json_value(value):
    if isinstance(value, dict):
        return {key: json_value(val) for key, val in value.items() if val is not JS_UNDEFINED}
    if isinstance(value, list):
        return [None if val is JS_UNDEFINED else json_value(val) for val in value]
    return value


def truth(value):
    if value is U or isinstance(value, dict) and '__symbol__' in value:
        return U
    if value is JS_UNDEFINED or value is None:
        return False
    return True if isinstance(value, (list, dict)) else bool(value)


def request_guards(node, scope):
    guards = []
    current = node.parent
    while current is not None and current != scope:
        if current.type == 'if_statement':
            condition = text(current.child_by_field_name('condition'))
            alternative = current.child_by_field_name('alternative')
            guards.append('!(' + condition + ')' if alternative is not None and alternative.start_byte <= node.start_byte < alternative.end_byte else condition)
        current = current.parent
    return guards


def ancestor(node, kinds):
    while node and node.type not in kinds:
        node = node.parent
    return node


def unwrapped(node):
    while node is not None and node.type in ('expression_statement', 'parenthesized_expression'):
        node = node.named_children[0] if node.named_children else None
    return node


FUNCTIONS = ('function_expression', 'function_declaration', 'method_definition', 'arrow_function')


def substitute(expression, bindings):
    """Substitute reference identifiers, preserving string literals and property names."""
    parser = Parser(Language(tree_sitter_javascript.language()))
    source = ('(' + expression + ');').encode()
    tree = parser.parse(source)
    changes = []
    for node in walk(tree.root_node):
        if node.type == 'identifier' and text(node) in bindings:
            changes.append((node.start_byte, node.end_byte, '(' + bindings[text(node)] + ')'))
    for start, end, value in reversed(changes):
        source = source[:start] + value.encode() + source[end:]
    return source.decode()[1:-2]


def callee_parts(node):
    if node is None:
        return None, None
    if node.type == 'identifier':
        return None, text(node)
    if node.type == 'member_expression':
        obj, prop = node.child_by_field_name('object'), node.child_by_field_name('property')
        if obj is not None and prop is not None and prop.type == 'property_identifier':
            return text(obj), text(prop)
    return None, None


def wrapper_identity(scope):
    """Name and owning object literal of the wrapper defined at this scope."""
    if scope is None or scope.type == 'program':
        return None, None
    name = text(scope.child_by_field_name('name'))
    if scope.type == 'method_definition':
        return name or None, ancestor(scope.parent, ('object',))
    parent = scope.parent
    key = parent.child_by_field_name('key') if parent is not None and parent.type == 'pair' else None
    if (scope.type == 'function_expression' and key is not None and key.type == 'property_identifier'
            and parent.child_by_field_name('value') == scope):
        return name or text(key) or None, ancestor(parent.parent, ('object',))
    return name or None, None


def this_owner(call):
    """Object literal providing a stable `this` to the call, or None inside plain nested functions."""
    function = ancestor(call.parent, FUNCTIONS)
    while function is not None and function.type == 'arrow_function':
        function = ancestor(function.parent, FUNCTIONS)
    if function is None:
        return None
    if function.type == 'method_definition':
        return ancestor(function.parent, ('object',))
    parent = function.parent
    key = parent.child_by_field_name('key') if parent is not None and parent.type == 'pair' else None
    if (function.type == 'function_expression' and key is not None and key.type == 'property_identifier'
            and parent.child_by_field_name('value') == function):
        return ancestor(parent.parent, ('object',))
    return None


def url_shape(expression):
    """URL segments from the AST; `{}` marks one dynamic path piece, query strings are dropped."""
    tree = Parser(Language(tree_sitter_javascript.language())).parse(('(' + expression + ');').encode())
    operands = []

    def collect(node):
        node = unwrapped(node)
        if node is not None and node.type == 'binary_expression' and text(node.child_by_field_name('operator')) == '+':
            collect(node.child_by_field_name('left'))
            collect(node.child_by_field_name('right'))
        else:
            operands.append(node)

    root = tree.root_node
    collect(unwrapped(root.named_children[0]) if root.named_children else None)
    marker = '\uffff'
    while any(isinstance(literal(node), str) and marker in literal(node) for node in operands):
        marker += '\uffff'
    buffer, query = '', False
    for operand in operands:
        if query:
            continue
        if operand is not None and operand.type == 'string':
            value = literal(operand)
            if not isinstance(value, str):
                buffer += marker
                continue
            if '?' in value:
                value, _, _ = value.partition('?')
                query = True
            buffer += value
        else:
            buffer += marker
    buffer = browser_url(buffer)
    if '://' in buffer:
        rest = buffer.split('://', 1)[1]
        buffer = rest[rest.find('/'):] if '/' in rest else ''
    return ['{}' if marker in part else part for part in buffer.split('/') if part]


def browser_url(value):
    # https://url.spec.whatwg.org/#concept-basic-url-parser, steps 1-3.
    return re.sub(r'[\t\n\r]', '', value.strip(''.join(chr(n) for n in range(33))))


def shape_match(shape, template):
    """Literal URLs need the full route; one dynamic piece fills exactly one template segment."""
    for index, segment in enumerate(shape):
        if index >= len(template):
            return False
        expected = template[index]
        if expected == '**':
            return True
        if expected.startswith('{') or expected == '*':
            continue
        if segment == '{}' or segment != expected:
            return False
    if len(shape) == len(template):
        return True
    return all(expected == '**' for expected in template[len(shape):])


def entire_object(node):
    for child in node.named_children:
        key = child.child_by_field_name('key') if child.type == 'pair' else None
        if key is None or key.type not in ('property_identifier', 'string', 'number'):
            return False
    return True


def scope_label(scope):
    name = text(scope.child_by_field_name('name'))
    parent = scope.parent
    if not name and parent is not None and parent.type == 'pair':
        key = parent.child_by_field_name('key')
        name = text(key) if key is not None and key.type == 'property_identifier' else ''
    if not name and parent is not None and parent.type == 'assignment_expression' and parent.child_by_field_name('right') == scope:
        lhs = parent.child_by_field_name('left')
        name = text(lhs.child_by_field_name('property')) if lhs.type == 'member_expression' else text(lhs)
    if not name and parent is not None and parent.type == 'variable_declarator':
        name = text(parent.child_by_field_name('name'))
    return name or text(parent)[:120]


def label_origin(scope):
    """Enclosing scope carrying a user-visible name, skipping anonymous callbacks."""
    while scope is not None and scope.type in ('arrow_function', 'function_expression'):
        parent = scope.parent
        if parent is not None and parent.type == 'pair' and parent.child_by_field_name('value') == scope:
            outer = ancestor(scope.parent, FUNCTIONS)
            if outer is not None and (text(outer.child_by_field_name('name')) or outer.type == 'method_definition'
                                      or outer.parent is not None and outer.parent.type in ('assignment_expression', 'variable_declarator')):
                scope = outer
                continue
            break
        if text(scope.child_by_field_name('name')):
            break
        if parent is not None and parent.type == 'assignment_expression':
            break
        scope = ancestor(scope.parent, (*FUNCTIONS, 'program'))
    return scope


def redeclares(scope, name, wrapper):
    """True when this scope declares `name` itself, shadowing an outer wrapper."""
    pars = scope.child_by_field_name('parameters') or scope.child_by_field_name('parameter')
    if pars is not None and any(n.type == 'identifier' and text(n) == name for n in walk(pars)):
        return True
    stack = [scope]
    while stack:
        for child in stack.pop().named_children:
            if child == wrapper:
                continue
            if child.type == 'function_declaration' and text(child.child_by_field_name('name')) == name:
                return True
            if child.type == 'variable_declarator' and text(child.child_by_field_name('name')) == name:
                return True
            if child.type not in FUNCTIONS:
                stack.append(child)
    return False


def shadowed(caller, wrapper, name):
    """True when a nested scope between the caller and the wrapper rebinds `name`."""
    scope = ancestor(caller.parent, (*FUNCTIONS, 'program'))
    while scope is not None and scope != wrapper:
        if redeclares(scope, name, wrapper):
            return True
        scope = ancestor(scope.parent, (*FUNCTIONS, 'program')) if scope.type != 'program' else None
    return False


def request_contexts(root, call, depth=0, visited=()):
    """Inline wrappers: unshadowed bare names, this.name only within the same object literal."""
    scope = ancestor(call.parent, (*FUNCTIONS, 'program'))
    name, owner = wrapper_identity(scope)
    pars = scope.child_by_field_name('parameters')
    parameters = [text(n) for n in pars.named_children] if pars else []
    if not name or not parameters:
        return [(scope, None, {})]
    if depth >= 3 or name in visited:
        return []
    contexts = []
    for caller in walk(root):
        if caller.type != 'call_expression':
            continue
        receiver, callee = callee_parts(caller.child_by_field_name('function'))
        if callee != name:
            continue
        if receiver is None:
            if owner is not None or shadowed(caller, scope, name):
                continue
        elif receiver != 'this' or owner is None or this_owner(caller) != owner:
            continue
        args = caller.child_by_field_name('arguments')
        values = args.named_children if args else []
        if len(values) != len(parameters):
            continue
        for outer, trigger, bindings in request_contexts(root, caller, depth + 1, (*visited, name)):
            contexts.append((outer, trigger if trigger is not None else caller,
                             {key: substitute(text(value), bindings) for key, value in zip(parameters, values)}))
    return contexts or [(scope, None, {})]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values, self.labels, self.scripts, self.options = {}, [], [], []
        self.option = None
        self.select = ''
        self.select_model = ''

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'script' and a.get('src'):
            self.scripts.append(a['src'])
        if tag == 'input' and a.get('id') and 'value' in a:
            self.values['#' + a['id']] = a['value']
        if tag == 'option' and ('value' in a or 'v-bind:value' in a):
            self.option = {'value': a.get('value'), 'label': '', 'control': self.select}
            if 'v-for' in a and 'v-bind:value' in a:
                self.option.update(collection=a['v-for'].split(' in ')[-1].strip(),
                                   value_field=a['v-bind:value'].split('.')[-1], model=self.select_model)
        if tag == 'select':
            self.select = a.get('id', a.get('name', a.get('v-model', '')))
            self.select_model = a.get('v-model', '')

    def handle_data(self, data):
        value = data.strip()
        if value:
            self.labels.append(value)
            if self.option is not None:
                self.option['label'] += value

    def handle_endtag(self, tag):
        if tag == 'option' and self.option is not None:
            self.options.append(self.option)
            self.option = None
        if tag == 'select':
            self.select = ''
            self.select_model = ''


class Frontend:
    def __init__(self, project):
        self.project = project
        self.parser = Parser(Language(tree_sitter_javascript.language()))
        self.sites, self.pages, self.trees, self.warnings = {}, {}, {}, []
        files = sorted(Path(p) for p in front_files(str(project.root)))
        for path in files:
            if path.suffix not in ('.html', '.htm'):
                continue
            page = Page()
            page.feed(path.read_text(errors='replace'))
            self.pages[path] = page
            page.row_events = row_events(path.read_text())
        for path in files:
            if path.suffix != '.js':
                continue
            source = path.read_bytes()
            tree = self.parser.parse(source)
            self.trees[path] = tree
            script_options = self.dom_options(tree)
            defaults = {}
            for node in walk(tree.root_node):
                if node.type == 'pair' and text(node.child_by_field_name('key')) == 'data':
                    arguments = node.parent.parent if node.parent is not None else None
                    caller = arguments.parent if arguments is not None and arguments.type == 'arguments' else None
                    if caller is not None and caller.type == 'call_expression' and re.search(r'ajax$|\$http$', text(caller.child_by_field_name('function'))):
                        continue
                    defaults.update({k: constant(v) for k, v in pairs(node.child_by_field_name('value')).items()})
            pages = [(p, page) for p, page in self.pages.items()
                     if any((p.parent / src).resolve() == path.resolve() for src in page.scripts if not src.startswith(('http', '//')))]
            for call, caller_scope, entry_call, argument_bindings in [
                    (c, outer_scope, trigger, bindings) for c in walk(tree.root_node) if c.type == 'call_expression'
                    for outer_scope, trigger, bindings in request_contexts(tree.root_node, c)]:
                if call.type != 'call_expression':
                    continue
                function = text(call.child_by_field_name('function'))
                args = call.child_by_field_name('arguments')
                if not args or not args.named_children:
                    continue
                config = pairs(args.named_children[0])
                if not config.get('url') or not re.search(r'ajax$|\$http$', function):
                    continue
                raw_url = substitute(text(config['url']), argument_bindings)
                local_definitions, _ = definitions_before(caller_scope, entry_call or call)
                # Resolve aliases only when their definition is a single expression.
                for _ in range(4):
                    changed = substitute(raw_url, {k: v for k, v in local_definitions.items()
                                                  if v and re.search(r'[\"\'](?:/|http)', v)})
                    if changed == raw_url:
                        break
                    raw_url = changed
                def parse_expression(expression):
                    parsed = self.parser.parse(('(' + expression + ');').encode()).root_node
                    return unwrapped(parsed.named_children[0]) if parsed.named_children else None
                cases = []
                for expression, conditions in url_cases(parse_expression(raw_url), local_definitions, parse_expression):
                    shape = url_shape(expression)
                    cases.append({'url': expression, 'conditions': conditions, 'url_shape': shape})
                strings = [literal(n) for n in walk(parse_expression(raw_url)) if n.type == 'string']
                prefix = next((browser_url(s) for s in strings if isinstance(s, str) and browser_url(s).startswith(('/', 'http'))), '')
                verb = str(literal(config.get('type') or config.get('method'))).upper()
                if not prefix:
                    self.warnings.append(str(path.relative_to(project.root)) + ': unresolved request URL')
                    continue
                for case in cases:
                    matches = [(mid, hv, template) for mid, hv, template in project.ix.handlers
                               if (verb == str(U).upper() or hv is None or hv == verb)
                               and shape_match(case['url_shape'], template)]
                    case['handlers'] = sorted(project.ix.preferred_handlers(matches, None if verb == str(U).upper() else verb))
                shape = url_shape(raw_url)
                handlers = sorted({mid for case in cases for mid in case['handlers']})
                if not handlers:
                    continue
                scope = ancestor(call.parent, (*FUNCTIONS, 'program'))
                inlined = caller_scope != scope
                guards = request_guards(call, scope)
                if entry_call is not None:
                    guards += request_guards(entry_call, caller_scope)
                for case in cases:
                    case['conditions'] = list(dict.fromkeys(guards + case['conditions']))
                field_scopes = [(caller_scope, entry_call), (scope, call)] if inlined else [(scope, call)]
                definitions, fields = {}, {}
                for owner_scope, limit in field_scopes:
                    definitions, _ = definitions_before(owner_scope, limit, definitions)
                for lhs, expression in definitions.items():
                    if '.' in lhs:
                        owner, key = lhs.rsplit('.', 1)
                        fields.setdefault(owner, {})[key] = expression
                data = substitute(text(config.get('data')), argument_bindings)
                seen, stringified, body_owner = set(), False, None
                while data and data not in seen:
                    seen.add(data)
                    root = self.parser.parse(('(' + data + ');').encode()).root_node
                    node = unwrapped(root.named_children[0]) if root.named_children else None
                    if node is None:
                        break
                    if node.type == 'call_expression' and text(node.child_by_field_name('function')) == 'JSON.stringify':
                        args = node.child_by_field_name('arguments')
                        inner = unwrapped(args.named_children[0]) if args and len(args.named_children) == 1 else None
                        if inner is None:
                            break
                        data, stringified = text(inner), True
                        continue
                    raw = text(node)
                    if raw != data:
                        data = raw
                        continue
                    if node.type == 'identifier' and data in definitions:
                        body_owner = data
                        data = definitions[data]
                        continue
                    break
                body = fields.get(data, {})
                body_complete = False
                body_keys_complete = False
                root = self.parser.parse(('(' + data + ');').encode()).root_node if data else None
                body_node = unwrapped(root.named_children[0]) if root and root.named_children else None
                if body_node is not None and body_node.type == 'object':
                    body = {key: text(value) for key, value in pairs(body_node).items()}
                    body_complete = entire_object(body_node)
                    body_keys_complete = body_complete
                elif config.get('data') is not None and not body and literal(body_node) is U:
                    self.warnings.append(str(path.relative_to(project.root)) + ': unresolved request body: ' + data[:160])
                conditional_body = {key: expression for key, expression in body.items()
                                    if any(n.type == 'ternary_expression' for n in walk(parse_expression(expression)))}
                if conditional_body:
                    body_complete = False
                    body = {key: expression for key, expression in body.items() if key not in conditional_body}
                success = config.get('success')
                effects = []
                response_definitions = {}
                response_name = 'response'
                if success:
                    pars = success.child_by_field_name('parameters')
                    if pars and pars.named_children:
                        response_name = text(pars.named_children[0])
                    for node in walk(success):
                        if node.type == 'variable_declarator':
                            response_definitions[text(node.child_by_field_name('name'))] = text(node.child_by_field_name('value'))
                        condition = []
                        parent = node.parent
                        while parent and parent != success:
                            if parent.type == 'if_statement':
                                cond = text(parent.child_by_field_name('condition'))
                                alternative = parent.child_by_field_name('alternative')
                                condition.append('!(' + cond + ')' if alternative and alternative.start_byte <= node.start_byte < alternative.end_byte else cond)
                            parent = parent.parent
                        if node.type == 'call_expression':
                            fn = text(node.child_by_field_name('function'))
                            arguments = node.child_by_field_name('arguments')
                            values = arguments.named_children if arguments else []
                            storage = re.fullmatch(r'(?:sessionStorage|localStorage)\.setItem', fn)
                            dom = re.fullmatch(r'\$\(([\"\'])([^\"\']*)\1\)\.(val|text|html)', fn)
                            if storage and len(values) >= 2 and isinstance(literal(values[0]), str):
                                effects.append({'space': 'storage', 'key': literal(values[0]), 'expr': text(values[1]), 'conditions': condition})
                            elif dom and values:
                                effects.append({'space': 'dom', 'key': dom[2], 'expr': text(values[0]), 'conditions': condition})
                        elif node.type == 'assignment_expression':
                            lhs = text(node.child_by_field_name('left'))
                            if lhs.startswith(('this.', 'that.')):
                                effects.append({'space': 'form', 'key': lhs.split('.', 1)[1], 'expr': text(node.child_by_field_name('right')), 'conditions': condition})
                            elif lhs in ('location.href', 'window.location.href'):
                                effects.append({'space': 'navigation', 'key': 'href', 'expr': text(node.child_by_field_name('right')), 'conditions': condition})
                sid = path.relative_to(project.root).as_posix() + ':' + str(call.start_point.row + 1)
                if argument_bindings:
                    sid += '@' + str(caller_scope.start_point.row + 1) + ':' + str(len(self.sites))
                label_scope = label_origin(caller_scope if inlined else scope)
                event_parameters = label_scope.child_by_field_name('parameters') if label_scope is not None else None
                event_names = [text(child) for child in event_parameters.named_children] if event_parameters else []
                methods_owner = ancestor(label_scope.parent, ('object',)) if label_scope is not None else None
                owner_pair = methods_owner.parent if methods_owner is not None else None
                vue = ancestor(methods_owner, ('new_expression',)) if methods_owner is not None else None
                vue_method = (owner_pair is not None and owner_pair.type == 'pair'
                              and text(owner_pair.child_by_field_name('key')) == 'methods'
                              and vue is not None and text(vue.child_by_field_name('constructor')) == 'Vue')
                row_bindings = [dict(fact, parameters=event_names, page=str(page_path.relative_to(project.root)))
                                for page_path, page in pages for fact in page.row_events
                                if vue_method and fact['handler'] == scope_label(label_scope) and len(event_names) == len(fact['arguments'])
                                and not set(event_names) & definitions.keys()]
                options = deepcopy(script_options)
                for _, page in pages:
                    for option in page.options:
                        if option.get('collection'):
                            values = defaults.get(option['collection'])
                            label_field = re.fullmatch(r'\{\{\s*\w+\.(\w+)\s*\}\}', option['label'])
                            for value in values if isinstance(values, list) and label_field else []:
                                if isinstance(value, dict):
                                    options.append({'control': option['model'], 'space': 'form',
                                                    'value': value.get(option['value_field'], U),
                                                    'label': value.get(label_field[1], '')})
                        else:
                            options.append(option)
                self.sites[sid] = {'id': sid, 'file': path.relative_to(project.root).as_posix(),
                                   'page': pages[0][0].relative_to(project.root).as_posix() if pages else path.relative_to(project.root).as_posix(),
                                   'line': call.start_point.row + 1, 'handlers': handlers, 'verb': verb,
                                   'url': raw_url, 'prefix': prefix, 'url_shape': shape,
                                   'url_cases': cases,
                                   'body_fields': body, 'body_complete': body_complete, 'stringified': stringified,
                                   'body_keys_complete': body_keys_complete,
                                   'conditional_fields': conditional_body, 'body_owner': body_owner,
                                   'definitions': definitions, 'defaults': defaults,
                                   'dom_defaults': {k: v for _, page in pages for k, v in page.values.items()},
                                   'options': options,
                                   'row_bindings': row_bindings,
                                   'labels': ' '.join(label for _, page in pages for label in page.labels)[:1800],
                                   'source': text(label_scope)[:2800],
                                   'helper_source': text(scope)[:2800] if inlined else None,
                                   'action_label': scope_label(label_scope),
                                   'effects': effects, 'response_name': response_name,
                                   'option_sources': option_sources(success, response_name),
                                   'response_definitions': response_definitions}
        for site in self.sites.values():
            if not site['row_bindings']:
                continue
            page_path = project.root / site['page']
            page = self.pages.get(page_path)
            paths = {(page_path.parent / src).resolve() for src in page.scripts if not src.startswith(('http', '//'))} if page else set()
            vue_count = sum(node.type == 'new_expression' and text(node.child_by_field_name('constructor')) == 'Vue'
                            for path, tree in self.trees.items() if path.resolve() in paths for node in walk(tree.root_node))
            if vue_count != 1:
                site['row_bindings'] = []
                self.warnings.append(site['id'] + ': ambiguous Vue component ownership for row event')

    def event_values(self, site, action, state):
        """Bind a click's arguments only to one selected, observed typed row."""
        from .provenance import history_value, entity_words, source_string, contains_unknown
        bindings = site.get('row_bindings', [])
        if len(bindings) != 1:
            return {}, None
        fact = bindings[0]
        rows = state.browser['form'].get(fact['collection'], U)
        if not isinstance(rows, list) or not rows:
            return {}, None
        matches = []
        for row in rows:
            if not isinstance(row, dict) or not row.get('__type__'):
                continue
            tid = self.project.resolve_type(row['__type__'], '')
            for key, info in self.project.type_fields.get(tid, {}).items():
                if not info.get('id'):
                    continue
                identity = row.get(key, U)
                rendered = source_string(self.project, identity) if isinstance(identity, dict) else identity
                selected = history_value(self.project, site['handlers'][0], key, action, state.history,
                                         entity_words(row['__type__']))
                if selected and rendered is not U and selected[1] == rendered and not contains_unknown(rendered):
                    matches.append((row, selected[0]))
        if len(matches) != 1:
            return {}, None
        row, reference = matches[0]
        return ({name: deepcopy(row.get(arg['field'], U) if 'field' in arg else arg['literal'])
                 for name, arg in zip(fact['parameters'], fact['arguments'])},
                fact['page'] + ':' + str(fact['source_line']) + ';' + reference)

    def input_controls(self, expression, definitions):
        """Literal DOM selectors and direct form properties, not substring matches."""
        expanded, seen = expression, set()
        for _ in range(8):
            tree = self.parser.parse(('(' + expanded + ');').encode())
            names = {text(node) for node in walk(tree.root_node) if node.type == 'identifier'}
            bindings = {name: definitions[name] for name in names - seen
                        if name in definitions and definitions[name]}
            if not bindings:
                break
            seen.update(bindings)
            expanded = substitute(expanded, bindings)
        tree = self.parser.parse(('(' + expanded + ');').encode())
        dom, form = set(), set()
        for node in walk(tree.root_node):
            if node.type == 'call_expression' and text(node.child_by_field_name('function')) in ('$', 'jQuery'):
                args = node.child_by_field_name('arguments')
                selector = literal(args.named_children[0]) if args is not None and len(args.named_children) == 1 else U
                if isinstance(selector, str) and selector.startswith('#'):
                    dom.add(selector[1:])
            elif node.type == 'member_expression' and text(node.child_by_field_name('object')) in ('this', 'that', '$scope'):
                form.add(text(node.child_by_field_name('property')))
        return {'dom': dom, 'form': form}

    def option_producers(self, site, field):
        """Only AJAX producers of the actual control read by this request field."""
        expression = {**site['body_fields'], **site.get('conditional_fields', {})}.get(field, '')
        controls = self.input_controls(expression, site['definitions'])['dom']
        return [(producer, fact) for producer in self.sites.values() if producer['page'] == site['page']
                for fact in producer.get('option_sources', []) if fact['control'] in controls]

    def dom_options(self, tree):
        """Constant option elements assembled through the standard DOM API."""
        def expression_node(expression):
            parsed = self.parser.parse(('(' + expression + ');').encode())
            return unwrapped(parsed.root_node.named_children[0]) if parsed.root_node.named_children else None

        output = []
        for call in walk(tree.root_node):
            if call.type != 'call_expression':
                continue
            receiver, method = callee_parts(call.child_by_field_name('function'))
            args = call.child_by_field_name('arguments')
            if method != 'appendChild' or args is None or len(args.named_children) != 1:
                continue
            argument = args.named_children[0]
            if argument.type != 'identifier':
                continue
            scope = ancestor(call.parent, FUNCTIONS) or tree.root_node
            definitions, _ = definitions_before(scope, call)
            option = text(argument)
            if not re.fullmatch(r'document\.createElement\(\s*(["\'])option\1\s*\)', text(expression_node(definitions.get(option, '')))):
                continue
            control = re.fullmatch(r'document\.getElementById\(\s*(["\'])(.*?)\1\s*\)', text(expression_node(definitions.get(receiver, ''))))
            if not control:
                continue
            values = {}
            for key in ('value', 'innerText', 'textContent'):
                expression = definitions.get(option + '.' + key, '')
                values[key] = constant(expression_node(expression))
            label = values['innerText'] if isinstance(values['innerText'], str) else values['textContent']
            if isinstance(label, str) and isinstance(values['value'], (str, int, float)):
                output.append({'control': control[2], 'value': str(values['value']), 'label': label,
                               'source_line': call.start_point.row + 1})
        return output

    def apply_absence(self, site, fields, action, state):
        """An explicit negative choice may take a source-proven empty-control branch."""
        expressions = [*site['body_fields'].values(), *site.get('conditional_fields', {}).values()]
        for expression in expressions:
            tree = self.parser.parse(('(' + expression + ');').encode())
            for node in walk(tree.root_node):
                if node.type != 'binary_expression' or text(node.child_by_field_name('operator')) not in ('!=', '!=='):
                    continue
                left, right = node.child_by_field_name('left'), node.child_by_field_name('right')
                for control_node, empty_node in ((left, right), (right, left)):
                    if literal(empty_node) not in ('', None):
                        continue
                    control = re.fullmatch(r'\$\(\s*(["\'])(.*?)\1\s*\)\.text\(\s*\)', text(control_node))
                    if not control:
                        continue
                    normalized = re.sub(r'[^a-z0-9]', '', control[2].lower())
                    matches = [key for key in fields if normalized.endswith(re.sub(r'[^a-z0-9]', '', key.lower()))]
                    if matches and any(control_polarity(action, re.sub(r'(?:Type|Mode)$', '', key)) is False for key in matches):
                        state.browser['dom'][control[2].strip()] = ''

    def evaluate(self, expression, state, extra=None, definitions=None):
        if not expression:
            return U
        tree = self.parser.parse(('(' + expression + ');').encode())
        active = set()
        env = {'this': state.browser['form'], 'that': state.browser['form'], **(extra or {})}

        def value(node):
            if node is None:
                return U
            kind, raw = node.type, text(node)
            if kind in ('string', 'number', 'true', 'false', 'null'):
                return literal(node)
            if kind in ('parenthesized_expression', 'expression_statement'):
                return value(node.named_children[0]) if node.named_children else U
            if kind in ('identifier', 'this', 'undefined'):
                if raw in env:
                    return env[raw]
                if raw in (definitions or {}) and raw not in active:
                    active.add(raw)
                    result = self.evaluate(definitions[raw], state, env, {k: v for k, v in definitions.items() if k != raw})
                    active.remove(raw)
                    return result
                if raw == 'undefined':
                    return JS_UNDEFINED
                return U
            if kind == 'member_expression':
                obj = value(node.child_by_field_name('object'))
                key = text(node.child_by_field_name('property'))
                return obj.get(key, U) if isinstance(obj, dict) else len(obj) if key == 'length' and isinstance(obj, (str, list)) else U
            if kind == 'subscript_expression':
                obj, key = value(node.child_by_field_name('object')), value(node.child_by_field_name('index'))
                if isinstance(obj, dict):
                    return obj.get(key, U)
                return obj[key] if isinstance(obj, (list, str)) and isinstance(key, int) and 0 <= key < len(obj) else U
            if kind == 'binary_expression':
                left = value(node.child_by_field_name('left'))
                op = text(node.child_by_field_name('operator'))
                if op in ('&&', '||'):
                    condition = truth(left)
                    if condition is U:
                        return U
                    if (op == '&&' and not condition) or (op == '||' and condition):
                        return left
                    return value(node.child_by_field_name('right'))
                right = value(node.child_by_field_name('right'))
                if left is U or right is U or left is JS_UNDEFINED or right is JS_UNDEFINED:
                    return U
                if any(isinstance(value, dict) and '__symbol__' in value for value in (left, right)):
                    return U
                if op == '+':
                    return str(left) + str(right) if isinstance(left, str) or isinstance(right, str) else left + right
                if op in ('==', '===', '!=', '!=='):
                    equal = left == right or (op in ('==', '!=') and str(left) == str(right))
                    return not equal if '!' in op else equal
                if op in ('<', '<=', '>', '>=') and isinstance(left, (str, int, float)) and isinstance(right, type(left)):
                    return {'<': lambda: left < right, '<=': lambda: left <= right,
                            '>': lambda: left > right, '>=': lambda: left >= right}[op]()
                return U
            if kind == 'ternary_expression':
                condition = truth(value(node.child_by_field_name('condition')))
                if condition is U:
                    left, right = value(node.child_by_field_name('consequence')), value(node.child_by_field_name('alternative'))
                    return left if left is not U and left == right else U
                return value(node.child_by_field_name('consequence' if condition else 'alternative'))
            if kind == 'unary_expression':
                arg = value(node.child_by_field_name('argument'))
                condition = truth(arg)
                return not condition if raw.startswith('!') and condition is not U else U
            if kind == 'call_expression':
                fn = text(node.child_by_field_name('function'))
                args = node.child_by_field_name('arguments')
                vals = [value(c) for c in args.named_children] if args else []
                if fn in ('sessionStorage.getItem', 'localStorage.getItem') and vals and isinstance(vals[0], str):
                    return state.browser['storage'].get(vals[0], U)
                if fn == 'JSON.stringify' and vals:
                    return vals[0]
                if fn == 'JSON.parse' and vals and isinstance(vals[0], str):
                    try:
                        return json.loads(vals[0])
                    except ValueError:
                        return U
                function_node = node.child_by_field_name('function')
                if function_node is not None and function_node.type == 'member_expression':
                    receiver = value(function_node.child_by_field_name('object'))
                    method = text(function_node.child_by_field_name('property'))
                    if isinstance(receiver, datetime) and not vals:
                        date_fields = {'getFullYear': receiver.year, 'getMonth': receiver.month - 1,
                                       'getDate': receiver.day, 'getHours': receiver.hour,
                                       'getMinutes': receiver.minute, 'getSeconds': receiver.second}
                        if method in date_fields:
                            return date_fields[method]
                    if isinstance(receiver, str):
                        if method == 'charAt' and len(vals) == 1 and isinstance(vals[0], int):
                            return receiver[vals[0]] if 0 <= vals[0] < len(receiver) else ''
                        if method == 'split' and len(vals) == 1 and isinstance(vals[0], str) and vals[0]:
                            return receiver.split(vals[0])
                        if method == 'replace' and len(vals) == 2 and all(isinstance(v, str) for v in vals):
                            return receiver.replace(vals[0], vals[1], 1)
                        if method == 'indexOf' and len(vals) == 1 and isinstance(vals[0], str):
                            return receiver.find(vals[0])
                    if isinstance(receiver, list) and method == 'concat' and all(isinstance(v, list) for v in vals):
                        return receiver + [item for val in vals for item in val]
                selected = re.fullmatch(r"\$\(\s*([\"'])(.*?)\1\s*\)\.find\(\s*([\"'])option:selected\3\s*\)\.val", fn)
                if selected:
                    return state.browser['dom'].get(selected[2].strip(), U)
                if fn in ('parseInt', 'parseFloat') and vals:
                    try:
                        return int(vals[0]) if fn == 'parseInt' else float(vals[0])
                    except (ValueError, TypeError):
                        return U
                dom = re.fullmatch(r'\$\(([\"\'].*?[\"\'])\)\.(?:val|text)', fn)
                if dom:
                    return state.browser['dom'].get(dom[1][1:-1].strip(), U)
                checked = re.fullmatch(r'\$\(([\"\'].*?[\"\'])\)\.is', fn)
                if checked and vals == [':checked']:
                    return state.browser['dom'].get(checked[1][1:-1].strip() + ':checked', U)
                return U
            if kind == 'new_expression' and text(node.child_by_field_name('constructor')) == 'Date':
                args = node.child_by_field_name('arguments')
                return state.now if args is not None and not args.named_children and isinstance(state.now, datetime) else U
            if kind == 'object':
                return {key: value(val) for key, val in pairs(node).items()}
            if kind == 'array':
                return [value(c) for c in node.named_children]
            return U

        try:
            return value(tree.root_node.named_children[0])
        except (TypeError, ValueError, IndexError, KeyError, AttributeError):
            state.limitations.append('unsupported JavaScript value operation: ' + expression[:160])
            return U

    def update_input(self, expression, value, state):
        """Reflect a grounded value in the source form control used by URL guards."""
        tree = self.parser.parse(('(' + expression + ');').encode())
        node = unwrapped(tree.root_node.named_children[0]) if tree.root_node.named_children else None
        if node is None:
            return
        raw = text(node)
        if node.type == 'member_expression' and text(node.child_by_field_name('object')) in ('this', 'that'):
            state.browser['form'][text(node.child_by_field_name('property'))] = deepcopy(value)
        elif node.type == 'call_expression':
            fn = text(node.child_by_field_name('function'))
            dom = re.fullmatch(r'\$\(([\"\'])(.*?)\1\)\.(val|text)', fn)
            if dom:
                stored = str(value).lower() if isinstance(value, bool) else str(value) if isinstance(value, (int, float)) else deepcopy(value)
                state.browser['dom'][dom[2].strip()] = stored

    def enter(self, site, state):
        page = site['page']
        active = state.browser.get('active_page')
        if page != active:
            if isinstance(active, str):
                state.browser.setdefault('pages', {})[active] = {'form': state.browser['form'], 'dom': state.browser['dom']}
            previous = state.browser.setdefault('pages', {}).get(page, {})
            if not isinstance(previous, dict):
                previous = {'form': {key: U for key in site['defaults']},
                            'dom': {key: U for key in site['dom_defaults']}}
                state.limitations.append('unknown prior browser page state: ' + page)
            state.browser['form'] = deepcopy(previous.get('form', {}))
            state.browser['dom'] = deepcopy(previous.get('dom', {}))
            state.browser['active_page'] = page
        for name, default in site['defaults'].items():
            state.browser['form'].setdefault(name, deepcopy(default))
        for name, default in site['dom_defaults'].items():
            state.browser['dom'].setdefault(name, default)

    def apply_response(self, site, result, state):
        env = {site['response_name']: result}
        for effect in site['effects']:
            conditions = [self.evaluate(c, state, env, site['response_definitions']) for c in effect['conditions']]
            if False in conditions:
                continue
            val = self.evaluate(effect['expr'], state, env, site['response_definitions'])
            if any(c is U for c in conditions):
                val = U
                state.limitations.append('unknown browser response guard: ' + site['id'])
            if effect['space'] == 'navigation':
                if isinstance(val, str):
                    state.browser['url'] = dict(parse_qsl(urlsplit(val).query))
                else:
                    state.browser['url'] = {key: U for key in state.browser['url']}
                    state.limitations.append('unknown browser navigation target: ' + site['id'])
            else:
                key = effect['key']
                if not isinstance(key, str):
                    state.browser[effect['space']] = {key: U for key in state.browser[effect['space']] if isinstance(key, str)}
                    state.limitations.append('unknown browser response key: ' + site['id'])
                else:
                    state.browser[effect['space']][key] = val
