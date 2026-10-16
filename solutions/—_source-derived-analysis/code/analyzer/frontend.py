"""Static extraction and symbolic evaluation of browser request contracts."""
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
import json
import re
from urllib.parse import urlsplit, parse_qsl
from tree_sitter import Language, Parser
import tree_sitter_javascript
from baseline_nlp import front_files, prefix_match
from baseline_closure import path_segs
from .project import text, walk
from .state import U


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


def ancestor(node, kinds):
    while node and node.type not in kinds:
        node = node.parent
    return node


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values, self.labels, self.scripts, self.options = {}, [], [], []
        self.option = None
        self.select = ''

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'script' and a.get('src'):
            self.scripts.append(a['src'])
        if tag == 'input' and a.get('id') and 'value' in a:
            self.values['#' + a['id']] = a['value']
        if tag == 'option' and 'value' in a:
            self.option = {'value': a['value'], 'label': '', 'control': self.select}
        if tag == 'select':
            self.select = a.get('id', a.get('name', a.get('v-model', '')))

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
        for path in files:
            if path.suffix != '.js':
                continue
            source = path.read_bytes()
            tree = self.parser.parse(source)
            self.trees[path] = tree
            defaults = {}
            for node in walk(tree.root_node):
                if node.type == 'pair' and text(node.child_by_field_name('key')) == 'data':
                    defaults.update({k: literal(v) for k, v in pairs(node.child_by_field_name('value')).items()})
            pages = [(p, page) for p, page in self.pages.items()
                     if any((p.parent / src).resolve() == path.resolve() for src in page.scripts if not src.startswith(('http', '//')))]
            for call in walk(tree.root_node):
                if call.type != 'call_expression':
                    continue
                function = text(call.child_by_field_name('function'))
                args = call.child_by_field_name('arguments')
                if not args or not args.named_children:
                    continue
                config = pairs(args.named_children[0])
                if not config.get('url') or not re.search(r'ajax$|\$http$', function):
                    continue
                raw_url = text(config['url'])
                strings = re.findall(r'[\"\']([^\"\']+)[\"\']', raw_url)
                prefix = next((s for s in strings if s.startswith(('/', 'http'))), '')
                verb = str(literal(config.get('type') or config.get('method'))).upper()
                if not prefix:
                    self.warnings.append(str(path.relative_to(project.root)) + ': unresolved request URL')
                    continue
                segs = path_segs(urlsplit(prefix).path)
                handlers = sorted({mid for mid, hv, template in project.ix.handlers
                                   if (verb == str(U).upper() or hv is None or hv == verb)
                                   and ((len(segs) == len(template) and prefix_match(segs, template))
                                        or (len(segs) < len(template) and prefix_match(segs, template)))})
                if not handlers:
                    continue
                scope = ancestor(call.parent, ('function_expression', 'function_declaration', 'method_definition', 'arrow_function', 'program'))
                definitions, fields = {}, {}
                for node in walk(scope):
                    if node.start_byte >= call.start_byte:
                        continue
                    if node.type == 'variable_declarator':
                        definitions[text(node.child_by_field_name('name'))] = text(node.child_by_field_name('value'))
                    if node.type == 'assignment_expression':
                        lhs = text(node.child_by_field_name('left'))
                        if '.' in lhs:
                            owner, key = lhs.rsplit('.', 1)
                            fields.setdefault(owner, {})[key] = text(node.child_by_field_name('right'))
                data = text(config.get('data'))
                seen = set()
                while data in definitions and data not in seen:
                    seen.add(data)
                    data = definitions[data]
                match = re.fullmatch(r'JSON\.stringify\((\w+)\)', data)
                if match:
                    data = match[1]
                body = fields.get(data, {})
                for owner, properties in fields.items():
                    if definitions.get(owner) in ('new Object()', '{}'):
                        definitions[owner] = '{' + ','.join(json.dumps(k) + ':' + v for k, v in properties.items()) + '}'
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
                self.sites[sid] = {'id': sid, 'file': path.relative_to(project.root).as_posix(),
                                   'page': pages[0][0].relative_to(project.root).as_posix() if pages else path.relative_to(project.root).as_posix(),
                                   'line': call.start_point.row + 1, 'handlers': handlers, 'verb': verb,
                                   'url': raw_url, 'prefix': prefix, 'body_fields': body,
                                   'definitions': definitions, 'defaults': defaults,
                                   'dom_defaults': {k: v for _, page in pages for k, v in page.values.items()},
                                   'options': [o for _, page in pages for o in page.options],
                                   'labels': ' '.join(label for _, page in pages for label in page.labels)[:1800],
                                   'source': text(scope)[:2800], 'effects': effects, 'response_name': response_name,
                                   'response_definitions': response_definitions}

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
            if kind in ('identifier', 'this'):
                if raw in env:
                    return env[raw]
                if raw in (definitions or {}) and raw not in active:
                    active.add(raw)
                    result = self.evaluate(definitions[raw], state, env, {k: v for k, v in definitions.items() if k != raw})
                    active.remove(raw)
                    return result
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
                left, right = value(node.child_by_field_name('left')), value(node.child_by_field_name('right'))
                op = text(node.child_by_field_name('operator'))
                if left is U or right is U:
                    return U
                if any(isinstance(value, dict) and '__symbol__' in value for value in (left, right)):
                    return U
                if op == '+':
                    return str(left) + str(right) if isinstance(left, str) or isinstance(right, str) else left + right
                if op in ('==', '===', '!=', '!=='):
                    equal = left == right or (op in ('==', '!=') and str(left) == str(right))
                    return not equal if '!' in op else equal
                if op in ('&&', '||'):
                    return left and right if op == '&&' else left or right
                return U
            if kind == 'unary_expression':
                arg = value(node.child_by_field_name('argument'))
                return not arg if raw.startswith('!') and isinstance(arg, bool) else U
            if kind == 'call_expression':
                fn = text(node.child_by_field_name('function'))
                args = node.child_by_field_name('arguments')
                vals = [value(c) for c in args.named_children] if args else []
                if fn in ('sessionStorage.getItem', 'localStorage.getItem') and vals and isinstance(vals[0], str):
                    return state.browser['storage'].get(vals[0], U)
                if fn == 'JSON.stringify' and vals:
                    return vals[0]
                if fn in ('parseInt', 'parseFloat') and vals:
                    try:
                        return int(vals[0]) if fn == 'parseInt' else float(vals[0])
                    except (ValueError, TypeError):
                        return U
                dom = re.fullmatch(r'\$\(([\"\'].*?[\"\'])\)\.(?:val|text)', fn)
                if dom:
                    return state.browser['dom'].get(dom[1][1:-1], U)
                return U
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
