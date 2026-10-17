"""Static extraction and symbolic evaluation of browser request contracts."""
from copy import deepcopy
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import json
import re
from urllib.parse import urlsplit, parse_qsl
from .symbolic_text import concat_text
from tree_sitter import Language, Parser
import tree_sitter_javascript
from baseline_nlp import front_files
from .project import text, walk
from .state import U, JS_UNDEFINED
from .jsflow import definitions_before, url_cases, UNKNOWN_EXPR, dom_access
from .nl_inputs import control_polarity
from .option_sources import option_sources
from .html_rows import analyze_html_rows
from .form_flow import vue_form_flows
from .html_options import fragment_options, document_options, document_texts
from .units import unit_name
from .response_arrays import summarize_array_copy


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


def primitive_equal(left, right, strict=False):
    """The primitive JS equality slice; opaque coercions stay unknown."""
    def category(value):
        if value is U:return 'unknown'
        if value is JS_UNDEFINED:return 'undefined'
        if value is None:return 'null'
        if type(value) is bool:return 'boolean'
        if type(value) in (int,float):return 'number'
        if isinstance(value,str) or isinstance(value,dict) and value.get('__type__') in ('String','java.lang.String') and '__symbol__' in value:return 'string'
        if isinstance(value,(dict,list)):return 'object'
        return 'unknown'
    a,b = category(left),category(right)
    if 'unknown' in (a,b):return U
    if a == b:
        if a == 'object':return left is right
        if a == 'string' and (not isinstance(left,str) or not isinstance(right,str)):
            if isinstance(left,dict) and isinstance(right,dict) and left['__symbol__'] == right['__symbol__']:return True
            lengths = [len(value.encode('utf-16-le',errors='surrogatepass'))//2 if isinstance(value,str) else value.get('__length__') for value in (left,right)]
            return False if all(type(n) is int for n in lengths) and lengths[0] != lengths[1] else U
        return left == right
    if strict:return False
    if {a,b} <= {'null','undefined'}:return True
    if a in ('null','undefined') or b in ('null','undefined'):return False
    if a == 'boolean':return primitive_equal(int(left),right)
    if b == 'boolean':return primitive_equal(left,int(right))
    if {a,b} == {'number','string'}:
        number,string = (left,right) if a == 'number' else (right,left)
        if not isinstance(string,str):return U
        string = string.strip()
        if not string:return number == 0
        if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',string):return U
        return number == float(string)
    return U


def dom_string(value):
    if value is None:return ''
    if isinstance(value,str):return value
    if type(value) is bool:return str(value).lower()
    if type(value) is int and abs(value) <= 9007199254740991:return str(value)
    if type(value) is float and abs(value) <= 9007199254740991 and 'e' not in repr(value):
        return str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value,dict) and value.get('__type__') in ('String','java.lang.String') and '__symbol__' in value:return value
    return U


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


def fragment_effect(node, scope, containers):
    """A bounded jQuery HTML sink in the actual response callback, outside loops."""
    fn = text(node.child_by_field_name('function'))
    match = re.fullmatch(r'''\$\((["'])(#[\w-]+)\1\)(?:\.find\((["'])(\w+)\3\))?\.(append|html)''',fn)
    args = node.child_by_field_name('arguments')
    if match is None or args is None or len(args.named_children) != 1:
        return None
    selector = match[2] + (' '+match[4] if match[4] else '')
    if selector not in containers or ancestor(node.parent,FUNCTIONS) != scope:
        return None
    parent = node.parent
    while parent is not None and parent != scope:
        if parent.type in ('for_statement','for_in_statement','while_statement','do_statement','try_statement'):
            return None
        parent = parent.parent
    expression = text(args.named_children[0])
    if match[5] == 'append' and '<select' not in expression.lower():
        return None
    definitions,_ = definitions_before(scope,node)
    return {'space':'options','key':selector,'container':containers[selector],
            'mode':match[5],'expr':expression,'definitions':definitions,'line':node.start_point.row+1}


def component_property(node,aliases):
    while node is not None and node.type in ('member_expression','subscript_expression'):
        base=node.child_by_field_name('object')
        if text(base) in aliases:
            prop=node.child_by_field_name('property')
            return text(prop) if prop is not None else None
        node=base
    return None


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
        self.form_flows = {}
        self.unsupported = []
        self.unit_cache = {}
        self.selector_cache = {}
        files = sorted(Path(p) for p in front_files(str(project.root)))
        for path in files:
            if path.suffix not in ('.js','.html','.htm'):
                self.unsupported.append('Unsupported frontend syntax '+path.suffix+': request extraction unavailable in '+str(path.relative_to(project.root)))
        for path in files:
            if path.suffix not in ('.html', '.htm'):
                continue
            page = Page()
            content = path.read_text(errors='replace')
            page.feed(content)
            self.pages[path] = page
            rows = analyze_html_rows(content)
            page.row_events = rows['facts']
            page.editable_models = rows['editable_models']
            page.containers = rows['containers']
            native_options, option_warnings = document_options(content)
            page.text_values = document_texts(content)
            page.options = [option for option in page.options if 'collection' in option] + native_options
            self.warnings.extend(str(path.relative_to(project.root))+': '+message for message in option_warnings)
            self.warnings.extend(str(path.relative_to(project.root)) + ': ' + message for message in rows['diagnostics'])
        for path in files:
            if path.suffix != '.js':
                continue
            source = path.read_bytes()
            tree = self.parser.parse(source)
            if tree.root_node.has_error:
                self.unsupported.append('Frontend JavaScript parse errors: '+str(path.relative_to(project.root)))
            for node in walk(tree.root_node):
                if node.type=='call_expression' and re.fullmatch(r'(?:(?:window|globalThis)\.)?fetch|axios(?:\.\w+)?',text(node.child_by_field_name('function'))):
                    self.unsupported.append('Unsupported frontend HTTP client '+text(node.child_by_field_name('function'))+': '+str(path.relative_to(project.root))+':'+str(node.start_point.row+1))
            self.trees[path] = tree
            self.form_flows[path] = vue_form_flows(tree.root_node)
            text_controls = {access[0].split('|',2)[2] for node in walk(tree.root_node)
                             if (access := dom_access(node)) and not access[1] and access[0].startswith('@dom|text|')}
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
                response_aliases, response_this = [],False
                if success:
                    component=this_owner(call)
                    component_pair=component.parent if component is not None else None
                    vue_owner=(component_pair is not None and component_pair.type=='pair'
                               and text(component_pair.child_by_field_name('key'))=='methods'
                               and text((ancestor(component,('new_expression',)) or call).child_by_field_name('constructor'))=='Vue')
                    response_aliases=[key for key,value in definitions.items() if value=='this' and '.' not in key
                                      and vue_owner and not redeclares(success,key,None)]
                    response_this=bool(vue_owner and (success.type=='arrow_function' or text(config.get('context')) in ['this',*response_aliases]))
                    aliases=set(response_aliases)|({'this'} if response_this else set())
                    response_definitions=dict(definitions)
                    pars = success.child_by_field_name('parameters')
                    if pars and pars.named_children:
                        response_name = text(pars.named_children[0])
                    loops=[node for node in walk(success) if node.type in ('for_statement','for_in_statement','while_statement','do_statement')]
                    copies={}
                    for loop in loops:
                        fact=summarize_array_copy(loop,success,definitions)
                        root=fact['target'].split('.')[0] if fact else None
                        if fact and root in aliases:
                            copies[loop.start_byte]=fact
                        else:
                            self.unsupported.append('Unsupported browser response loop: '+str(path.relative_to(project.root))+':'+str(loop.start_point.row+1))
                    for node in walk(success):
                        effect_start=len(effects)
                        enclosing=next((loop for loop in loops if loop.start_byte<node.start_byte<loop.end_byte),None)
                        if enclosing is not None and enclosing.start_byte in copies:
                            continue
                        if node.start_byte in copies:
                            fact=copies[node.start_byte]
                            effects.append({'space':'form','key':fact['key'],'expr':fact['expr'],'conditions':[],
                                            'definitions':definitions_before(success,node,definitions)[0],
                                            'copy_array':True})
                            continue
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
                                effects.append({'space': 'dom', 'mode':dom[3], 'key': dom[2], 'expr': text(values[0]), 'conditions': condition})
                            containers = {key:tag for _,page in pages for key,tag in page.containers.items()}
                            fragment = fragment_effect(node,success,containers)
                            if fragment is not None:
                                effects.append({**fragment,'conditions':condition})
                        elif node.type == 'assignment_expression':
                            lhs = text(node.child_by_field_name('left'))
                            target=component_property(node.child_by_field_name('left'),aliases)
                            if target is not None:
                                effects.append({'space': 'form', 'key':target,
                                                'expr': UNKNOWN_EXPR if enclosing is not None else text(node.child_by_field_name('right')),
                                                'conditions':condition})
                            elif enclosing is not None:
                                base=node.child_by_field_name('left')
                                while base is not None and base.type in ('member_expression','subscript_expression'):
                                    base=base.child_by_field_name('object')
                                if base is not None and base.type=='identifier':
                                    response_definitions[text(base)]=UNKNOWN_EXPR
                            elif lhs in ('location.href', 'window.location.href'):
                                effects.append({'space': 'navigation', 'key': 'href', 'expr': text(node.child_by_field_name('right')), 'conditions': condition})
                        for effect in effects[effect_start:]:
                            effect.setdefault('definitions',definitions_before(success,node,definitions)[0])
                            if enclosing is not None or ancestor(node.parent,FUNCTIONS)!=success:
                                effect['expr']=UNKNOWN_EXPR
                                self.unsupported.append('Unmodeled browser response iteration or nested callback: '+str(path.relative_to(project.root))+':'+str(node.start_point.row+1))
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
                                                    'source_collection':option['collection'],
                                                    'label': value.get(label_field[1], '')})
                        else:
                            options.append(option)
                self.sites[sid] = {'id': sid, 'file': path.relative_to(project.root).as_posix(),
                                   'page': pages[0][0].relative_to(project.root).as_posix() if pages else path.relative_to(project.root).as_posix(),
                                   'line': call.start_point.row + 1, 'handlers': handlers, 'verb': verb,
                                   'vue_component':vue_method,
                                   'url': raw_url, 'prefix': prefix, 'url_shape': shape,
                                   'url_cases': cases,
                                   'body_fields': body, 'body_complete': body_complete, 'stringified': stringified,
                                   'body_keys_complete': body_keys_complete,
                                   'conditional_fields': conditional_body, 'body_owner': body_owner,
                                   'definitions': definitions, 'defaults': defaults,
                                   'dom_defaults': {k: v for _, page in pages for k, v in page.values.items()},
                                   'dom_text_defaults': {k:v for _,page in pages for k,v in page.text_values.items() if k in text_controls},
                                   'options': options,
                                   'row_bindings': row_bindings,
                                   'labels': ' '.join(label for _, page in pages for label in page.labels)[:1800],
                                   'source': text(label_scope)[:2800],
                                   'helper_source': text(scope)[:2800] if inlined else None,
                                   'action_label': scope_label(label_scope),
                                   'action_scope':label_scope.start_byte,
                                   'effects': effects, 'response_name': response_name,
                                   'response_aliases':response_aliases,'response_this':response_this,
                                   'option_sources': option_sources(success, response_name),
                                   'dom_preparation': self.dom_before(call,path),
                                   'response_definitions': response_definitions}
        action_sites = {}
        for site in self.sites.values():
            action_sites.setdefault((site['file'],site['action_scope']),[]).append(site['id'])
        for site in self.sites.values():
            site['compound_request_sites'] = sorted(action_sites[(site['file'],site['action_scope'])])
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
        self.warnings.extend(self.unsupported)

    def dom_before(self, call, path):
        """Literal DOM property equations along the request's lexical windows.

        Callback invocation and arbitrary plugin effects are hypotheses, recorded
        by the binder. This does not bridge independent handlers or infer events.
        """
        if any(redeclares(self.trees[path].root_node,name,None) for name in ('$', 'jQuery')):
            self.warnings.append(str(path.relative_to(self.project.root))+': shadowed jQuery DOM preparation')
            return {}
        scope = ancestor(call.parent,FUNCTIONS)
        windows, limit = [], call
        while scope is not None:
            windows.append((scope,limit))
            limit, scope = scope, ancestor(scope.parent,FUNCTIONS)
        definitions, references, opaque = {}, [], []
        for scope,limit in reversed(windows):
            if any(redeclares(scope,name,None) for name in ('$', 'jQuery')):
                self.warnings.append(str(path.relative_to(self.project.root))+': shadowed jQuery DOM preparation')
                return {}
            # A callback captures lexical variables by reference. Its invocation
            # may follow further writes, unlike a preceding DOM setter's snapshot.
            definitions = {key:expr if key.startswith('@dom|text|') else UNKNOWN_EXPR
                           for key,expr in definitions.items()}
            parameters = scope.child_by_field_name('parameters')
            for parameter in parameters.named_children if parameters else []:
                if parameter.type == 'identifier':
                    definitions[text(parameter)] = UNKNOWN_EXPR
            for node in walk(scope):
                if node.start_byte >= limit.start_byte or ancestor(node.parent,FUNCTIONS) != scope:
                    continue
                access = dom_access(node)
                if access and access[1]:
                    references.append(str(path.relative_to(self.project.root))+':'+str(node.start_point.row+1))
                if node.type == 'call_expression':
                    _,name = callee_parts(node.child_by_field_name('function'))
                    args = node.child_by_field_name('arguments')
                    if args and (args.named_children or name in ('remove','empty')) and name in ('text','val','html','append','prepend','prop','attr','replaceWith','remove','empty') and access is None:
                        opaque.append(str(node.start_point.row+1))
                if node.type in ('assignment_expression','augmented_assignment_expression'):
                    lhs = node.child_by_field_name('left')
                    if lhs is not None and lhs.type == 'member_expression' and text(lhs.child_by_field_name('property')) in ('textContent','innerHTML','innerText','value'):
                        opaque.append(str(node.start_point.row+1))
            definitions,uncertain = definitions_before(scope,limit,definitions,track_dom=True)
            if '@dom-expression-budget' in uncertain:
                self.warnings.append(str(path.relative_to(self.project.root))+': Source DOM expression budget exceeded')
        properties = {key:expr for key,expr in definitions.items() if key.startswith('@dom|')}
        if not properties:
            return {}
        if opaque:
            properties = {key:UNKNOWN_EXPR for key in properties}
            self.warnings.append(str(path.relative_to(self.project.root))+': Unsupported DOM mutation before request: '+','.join(sorted(set(opaque))))
        return {'properties':properties,'definitions':definitions,'references':sorted(set(references))}

    def prepared_dom_values(self, site, state):
        summary = site.get('dom_preparation',{})
        if not summary:
            return {}
        expressions = [site['url'],*site['body_fields'].values(),*site.get('conditional_fields',{}).values()]
        needed = {'#'+control.strip() for expression in expressions
                  for control in self.input_controls(expression,site['definitions'])['dom']}
        output = {}
        reference = ';'.join(summary['references']) or site['id']
        for key,expression in summary['properties'].items():
            _,method,control = key.split('|',2)
            if control not in needed:
                continue
            value = self.evaluate(expression,state,site.get('event_values',{}),summary['definitions'])
            value = dom_string(value)
            output[(method,control)] = value,reference
        return output

    def source_selector_values(self, site, state, explicit):
        """A selected source branch may constrain a declared Vue select option."""
        if not site.get('vue_component') or len(site.get('url_cases',[])) != 1:
            return {}
        if len(self.form_flows.get(self.project.root/site['file'],[])) != 1:
            return {}
        if site['id'] not in self.selector_cache:
            self.selector_cache[site['id']] = self.source_selector_facts(site)
        return {control:(value,reference) for control,value,reference,collection in self.selector_cache[site['id']]
                if ('form',control) not in explicit and state.browser['form'].get(control,U) != value
                and (not collection or state.browser['form'].get(collection,U) == site['defaults'].get(collection,U))}

    def source_selector_facts(self, site):
        """Cache only source equations and static options, never browser values."""
        output = []
        for condition in site.get('conditions',[]):
            expression = condition
            for _ in range(8):
                changed = substitute(expression,site['definitions'])
                if changed == expression:break
                expression = changed
            tree = self.parser.parse(('('+expression+');').encode())
            node = unwrapped(tree.root_node.named_children[0]) if tree.root_node.named_children else None
            if node is None or node.type != 'binary_expression' or text(node.child_by_field_name('operator')) not in ('==','==='):
                continue
            left,right = (unwrapped(node.child_by_field_name(key)) for key in ('left','right'))
            for member,constant_node in ((left,right),(right,left)):
                if member is None or member.type != 'member_expression' or text(member.child_by_field_name('object')) != 'this':
                    continue
                control = text(member.child_by_field_name('property'))
                constant_value = literal(constant_node)
                if constant_value is U:continue
                strict = text(node.child_by_field_name('operator')) == '==='
                options = [o for o in site['options'] if o.get('space') == 'form' and o['control'] == control
                           and primitive_equal(o['value'],constant_value,strict) is True]
                if len(options) == 1:
                    output.append((control,options[0]['value'],site['id']+':'+condition,options[0].get('source_collection')))
        return output

    def unit_hints(self,site,field):
        key=site['id'],field
        if key in self.unit_cache:return self.unit_cache[key]
        expression={**site['body_fields'],**site.get('conditional_fields',{})}.get(field,'')
        controls=self.input_controls(expression,site['definitions'])['dom']
        tree=self.trees.get(self.project.root/site['file'])
        hints=[]
        if tree is None:
            self.unit_cache[key]=hints
            return hints
        for node in walk(tree.root_node):
            if node.type!='call_expression':continue
            function=text(node.child_by_field_name('function'))
            match=re.fullmatch(r'''\$\((["'])#([\w-]+)\1\)\.text''',function)
            args=node.child_by_field_name('arguments')
            if match is None or match[2] not in controls or args is None or not args.named_children:continue
            value=args.named_children[0]
            if value.type=='binary_expression' and text(value.child_by_field_name('operator'))=='+':
                suffix=unit_name(literal(value.child_by_field_name('right')))
                left=value.child_by_field_name('left')
                if suffix and left.type=='call_expression' and re.fullmatch(r'''\$\((["'])#[\w-]+\1\)\.val''',text(left.child_by_field_name('function'))):
                    hints.append((suffix,site['file']+':'+str(node.start_point.row+1)+':display-unit'))
                    continue
            self.unit_cache[key]=[]
            return [] # An unknown writer could change the physical interpretation.
        self.unit_cache[key]=hints
        return hints

    def row_values(self, fact, mid, action, state, anchors=None):
        """Project only a uniquely identified row from its own source collection."""
        from .provenance import history_value, entity_words, source_string, contains_unknown
        rows = state.browser['form'].get(fact['collection'], U)
        if not isinstance(rows, list) or not rows:
            return {}, None
        matches = {}
        for position, row in enumerate(rows):
            if not isinstance(row, dict) or not row.get('__type__'):
                continue
            owner = entity_words(row['__type__'])
            tid = self.project.resolve_type(row['__type__'], '')
            declared = self.project.type_fields.get(tid, {})
            keys = [key for key, info in declared.items() if info.get('id') or key in ('id', 'key')
                    or key.lower().endswith('id') and entity_words(key) == owner]
            for key in keys:
                identity = row.get(key, U)
                rendered = source_string(self.project, identity) if isinstance(identity, dict) and '__symbol__' not in identity else identity
                supplied = [(name, value) for name, value in (anchors or {}).items()
                            if entity_words(name) == owner and value not in ('', None, U) and not contains_unknown(value)]
                if len(supplied) > 1:
                    comparable = [source_string(self.project,value) if isinstance(value,dict) and '__symbol__' not in value else value
                                  for _,value in supplied]
                    if comparable[0] is U or any(value != comparable[0] for value in comparable[1:]):
                        return {}, None
                selected = (('request.' + supplied[0][0], supplied[0][1]) if supplied else
                            history_value(self.project, mid, key, action, state.history, owner))
                expected = source_string(self.project, selected[1]) if selected and isinstance(selected[1], dict) and '__symbol__' not in selected[1] else selected[1] if selected else U
                if selected and rendered is not U and rendered == expected and not contains_unknown(rendered):
                    matches[position] = row, selected[0]
        if len(matches) != 1:
            return {}, None
        position, (row, reference) = next(iter(matches.items()))
        arguments = []
        for argument in fact['arguments']:
            if 'field' in argument:
                value = row
                for part in argument['field'].split('.'):
                    value = value.get(part, U) if isinstance(value, dict) else U
            elif argument.get('index'):
                value = position
            elif argument.get('object'):
                value = row
            else:
                value = argument['literal']
            arguments.append(deepcopy(value))
        location = fact['page'] + ':' + str(fact['source_line'])
        if fact.get('source_line_kind'):
            location += '(' + fact['source_line_kind'] + ')'
        return dict(zip(fact['parameters'], arguments)), location + ';' + reference

    def event_values(self, site, action, state):
        """Bind a click's arguments only to one selected, observed typed row."""
        bindings = site.get('row_bindings', [])
        if len(bindings) != 1:
            return {}, None
        return self.row_values(bindings[0], site['handlers'][0], action, state)

    def projected_form_values(self, site, mid, action, state, anchors=None, excluded=()):
        """Read a unique source row-to-form equation, without inventing an event.

        The caller records the inferred preparation as a hypothesis. Only safe
        selectors of the same unique Vue component can supply a missing value.
        """
        from .provenance import contains_unknown
        file = self.project.root / site['file']
        page_path = self.project.root / site['page']
        page = self.pages.get(page_path)
        flows = self.form_flows.get(file, [])
        if page is None or len(flows) != 1:
            return {}
        paths = {(page_path.parent / src).resolve() for src in page.scripts if not src.startswith(('http', '//'))}
        components = sum(node.type == 'new_expression' and text(node.child_by_field_name('constructor')) == 'Vue'
                         for path, tree in self.trees.items() if path.resolve() in paths for node in walk(tree.root_node))
        if components != 1:
            return {}
        flow = flows[0]
        expressions = [site['url'], *site['body_fields'].values(), *site.get('conditional_fields', {}).values()]
        needed = set().union(*(self.input_controls(expr, site['definitions'])['form'] for expr in expressions)) - set(excluded)
        candidates = {}
        for selector in flow['projectors']:
            fields = needed & selector['fields'].keys()
            fields = {field for field in fields
                      if set(flow['writers'].get(field, [])) == {selector['handler']} and '*' not in flow['writers']}
            if not fields:
                continue
            facts = [fact for fact in page.row_events if fact['handler'] == selector['handler']
                     and len(fact['arguments']) == len(selector['parameters'])]
            if len(facts) != 1:
                continue
            fact = {**facts[0], 'parameters':selector['parameters'], 'page':site['page']}
            values, reference = self.row_values(fact, mid, action, state, anchors)
            if reference is None:
                continue
            active, failed = set(), []
            calls = {}
            def helper(name, arguments):
                if name in active:
                    failed.append(name);return U
                meta = flow['helpers'][name]
                if len(arguments) != len(meta['parameters']):
                    failed.append(name);return U
                active.add(name)
                result = self.evaluate(meta['expression'], state, dict(zip(meta['parameters'],arguments)), meta['definitions'], calls)
                active.remove(name)
                if result is U or result is JS_UNDEFINED:
                    failed.append(name)
                return result
            for name in flow['helpers']:
                for alias in selector['aliases']:
                    calls[alias + '.' + name] = lambda arguments, name=name: helper(name,arguments)
            projected = {field:self.evaluate(expression,state,values,selector['fields'] | selector.get('definitions',{}),calls)
                         for field,expression in selector['fields'].items()}
            if failed or any(contains_unknown(value) or value is JS_UNDEFINED for value in projected.values()):
                continue
            for field in fields:
                candidates.setdefault(field,[]).append((projected[field],reference + ';' + site['file'] + ':' + str(selector['source_line'])))
        output = {}
        for field, values in candidates.items():
            if values and all(value == values[0][0] for value,_ in values):
                output[field] = values[0]
        return output

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
            elif node.type == 'member_expression' and text(unwrapped(node.child_by_field_name('object'))) in ('this', 'that', '$scope'):
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
        """A negative intent cannot prove that a display control was cleared."""
        problems = []
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
                        problems.append('Negative UI choice does not prove an empty display control: '+control[2].strip())
        return sorted(set(problems))

    def evaluate(self, expression, state, extra=None, definitions=None, local_calls=None):
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
                    result = self.evaluate(definitions[raw], state, env, {k: v for k, v in definitions.items() if k != raw}, local_calls)
                    active.remove(raw)
                    return result
                if raw == 'undefined':
                    return JS_UNDEFINED
                return U
            if kind == 'member_expression':
                obj = value(node.child_by_field_name('object'))
                key = text(node.child_by_field_name('property'))
                if key.startswith('__'):
                    state.limitations.append('Abstract metadata is not a browser data property: ' + raw)
                    return U
                if key=='length' and isinstance(obj,dict) and obj.get('__type__') in ('String','java.lang.String') and '__symbol__' in obj:
                    return obj.get('__length__',U)
                if key == 'length' and isinstance(obj,str):
                    return len(obj.encode('utf-16-le',errors='surrogatepass'))//2
                return obj.get(key, U) if isinstance(obj, dict) else len(obj) if key == 'length' and isinstance(obj, list) else U
            if kind == 'subscript_expression':
                obj, key = value(node.child_by_field_name('object')), value(node.child_by_field_name('index'))
                if isinstance(key, str) and key.startswith('__'):
                    state.limitations.append('Abstract metadata is not a browser data property: ' + raw)
                    return U
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
                if op in ('==','===','!=','!=='):
                    equal = primitive_equal(left,right,len(op) == 3)
                    if equal is U:
                        state.limitations.append('Unknown JavaScript equality/coercion: '+raw)
                        return U
                    return not equal if '!' in op else equal
                if left is U or right is U or left is JS_UNDEFINED or right is JS_UNDEFINED:
                    return U
                if op=='+' and any(isinstance(v,dict) and '__symbol__' in v and
                                   v.get('__type__') in ('String','java.lang.String') for v in (left,right)):
                    def string_part(item):
                        if item is None:return 'null'
                        if type(item) is bool:return str(item).lower()
                        if type(item) is int and abs(item)<=9007199254740991:return str(item)
                        return item
                    return concat_text(string_part(left),string_part(right))
                if any(isinstance(value, dict) and '__symbol__' in value for value in (left, right)):
                    return U
                if op == '+':
                    if isinstance(left, str) or isinstance(right, str):
                        def scalar(item):
                            if item is None: return 'null'
                            if isinstance(item, bool): return 'true' if item else 'false'
                            if isinstance(item, str): return item
                            if type(item) is int and abs(item) <= 9007199254740991: return str(item)
                            if type(item) is float and abs(item) <= 9007199254740991:
                                if item.is_integer(): return str(int(item))
                                if 'e' not in repr(item): return repr(item)
                            return U
                        a, b = scalar(left), scalar(right)
                        if a is U or b is U:
                            state.limitations.append('Unsupported JavaScript ToPrimitive in concatenation: ' + raw)
                            return U
                        return a + b
                    return left + right
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
                if raw[:1] in ('+','-') and type(arg) in (int,float):
                    return -arg if raw.startswith('-') else arg
                return not condition if raw.startswith('!') and condition is not U else U
            if kind == 'call_expression':
                fn = text(node.child_by_field_name('function'))
                args = node.child_by_field_name('arguments')
                vals = [value(c) for c in args.named_children] if args else []
                if fn in (local_calls or {}):
                    return local_calls[fn](vals)
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
                            if len(receiver.encode('utf-16-le',errors='surrogatepass'))//2 != len(receiver):
                                state.limitations.append('Unsupported JavaScript UTF16 charAt: '+raw)
                                return U
                            return receiver[vals[0]] if 0 <= vals[0] < len(receiver) else ''
                        if method == 'split' and len(vals) == 1 and isinstance(vals[0], str) and vals[0]:
                            return receiver.split(vals[0])
                        if method == 'replace' and len(vals) == 2 and all(isinstance(v, str) for v in vals):
                            return receiver.replace(vals[0], vals[1], 1)
                        if method == 'indexOf' and len(vals) == 1 and isinstance(vals[0], str):
                            index = receiver.find(vals[0])
                            return -1 if index < 0 else len(receiver[:index].encode('utf-16-le',errors='surrogatepass'))//2
                        if method in ('substr','substring') and 1 <= len(vals) <= 2 and all(type(v) is int for v in vals):
                            if len(receiver.encode('utf-16-le',errors='surrogatepass'))//2 != len(receiver):
                                state.limitations.append('Unsupported JavaScript UTF16 substring: '+raw)
                                return U
                            if method == 'substr':
                                start = min(max(vals[0],0),len(receiver)) if vals[0] >= 0 else max(len(receiver)+vals[0],0)
                                end = min(start+max(vals[1],0),len(receiver)) if len(vals) == 2 else len(receiver)
                            else:
                                start,end = sorted((min(max(vals[0],0),len(receiver)),min(max(vals[1],0),len(receiver)) if len(vals) == 2 else len(receiver)))
                            return receiver[start:end]
                    if isinstance(receiver, list) and method == 'concat' and all(isinstance(v, list) for v in vals):
                        return receiver + [item for val in vals for item in val]
                selected = re.fullmatch(r"\$\(\s*([\"'])(.*?)\1\s*\)\.find\(\s*([\"'])option:selected\3\s*\)\.(val|text)", fn)
                if selected:
                    if vals:
                        state.limitations.append('Unsupported selected-option setter return value: '+raw)
                        return U
                    chosen = state.browser['dom'].get(selected[2].strip(), U)
                    if selected[4] == 'val':
                        return chosen
                    if chosen is U:
                        return U
                    options = state.browser.get('source_options',[])+[
                        option for group in state.browser.get('options',{}).values() if isinstance(group,list)
                        for option in group]
                    matching = [option for option in options if '#'+option['control'].lstrip('#') == selected[2].strip()
                                and option['value'] == chosen]
                    if len(matching) == 1 and 'raw_text' in matching[0]:
                        return matching[0]['raw_text']
                    state.limitations.append('Unknown or ambiguous native selected option text: '+selected[2].strip())
                    return U
                if fn in ('parseInt', 'parseFloat') and vals:
                    try:
                        return int(vals[0]) if fn == 'parseInt' else float(vals[0])
                    except (ValueError, TypeError):
                        return U
                dom = re.fullmatch(r'\$\(([\"\'].*?[\"\'])\)\.(?:val|text)', fn)
                if dom:
                    if vals:
                        state.limitations.append('Unsupported DOM setter return value: '+raw)
                        return U
                    control = dom[1][1:-1].strip()
                    if fn.endswith('.text'):
                        return state.browser.get('dom_text',{}).get(control,U)
                    return state.browser['dom'].get(control, U)
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
                stored = dom_string(value)
                if dom[3] == 'text':
                    state.browser.setdefault('dom_text',{})[dom[2].strip()] = deepcopy(stored)
                else:
                    state.browser['dom'][dom[2].strip()] = stored

    def enter(self, site, state):
        page = site['page']
        active = state.browser.get('active_page')
        if page != active:
            if isinstance(active, str):
                state.browser.setdefault('pages', {})[active] = {'form': state.browser['form'], 'dom': state.browser['dom'],
                                                               'dom_text':state.browser.get('dom_text',{}),
                                                               'options':state.browser.get('options',{})}
            previous = state.browser.setdefault('pages', {}).get(page, {})
            if not isinstance(previous, dict):
                previous = {'form': {key: U for key in site['defaults']},
                            'dom': {key: U for key in site['dom_defaults']},
                            'dom_text': {key:U for key in site.get('dom_text_defaults',{})}}
                state.limitations.append('unknown prior browser page state: ' + page)
            state.browser['form'] = deepcopy(previous.get('form', {}))
            state.browser['dom'] = deepcopy(previous.get('dom', {}))
            state.browser['dom_text'] = deepcopy(previous.get('dom_text',{}))
            state.browser['options'] = deepcopy(previous.get('options',{}))
            state.browser['active_page'] = page
        for name, default in site['defaults'].items():
            state.browser['form'].setdefault(name, deepcopy(default))
        for name, default in site['dom_defaults'].items():
            state.browser['dom'].setdefault(name, default)
        for name,default in site.get('dom_text_defaults',{}).items():
            state.browser.setdefault('dom_text',{}).setdefault(name,default)
        state.browser['source_options'] = [option for option in site.get('options',[]) if option.get('space') == 'dom']

    def apply_response(self, site, result, state):
        env = {**site.get('event_values',{}),site['response_name']: result}
        if 'response_this' in site:
            env['this']=state.browser['form'] if site['response_this'] else U
            env.setdefault('that',U)
            env.update({alias:state.browser['form'] for alias in site['response_aliases']})
        for effect in site['effects']:
            definitions = effect.get('definitions',site['response_definitions'])
            conditions = [truth(self.evaluate(c, state, env, definitions)) for c in effect['conditions']]
            if False in conditions:
                continue
            val = self.evaluate(effect['expr'], state, env, definitions)
            if effect.get('copy_array') and not isinstance(val,list):
                val=U
                state.limitations.append('Unknown source array in browser copy: '+site['id'])
            if effect.get('copy_array'):val=deepcopy(val)
            if any(c is U for c in conditions):
                val = U
                state.limitations.append('unknown browser response guard: ' + site['id'])
            if effect['space'] == 'options':
                target = state.browser.setdefault('options',{})
                if not isinstance(val,str):
                    target[effect['key']] = U
                    state.limitations.append('Unknown rendered HTML options: '+site['id'])
                    continue
                options, warnings = fragment_options(val,effect['container'])
                state.limitations.extend(site['id']+': '+warning for warning in warnings)
                reference = site['file']+':'+str(effect['line'])+':HTML-fragment'
                options = [dict(option,reference=reference) for option in options]
                prior = target.get(effect['key'],[])
                target[effect['key']] = options if effect['mode'] == 'html' else prior+options if isinstance(prior,list) else U
            elif effect['space'] == 'navigation':
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
                    if effect['space'] == 'dom':
                        if effect.get('mode') == 'text':
                            if val is JS_UNDEFINED:continue
                            val = dom_string(val)
                            state.browser.setdefault('dom_text',{})[key] = deepcopy(val)
                        elif effect.get('mode') == 'html':
                            state.browser.setdefault('dom_text',{})[key] = U
                            state.limitations.append('HTML replacement text requires DOM construction: '+site['id'])
                        else:
                            state.browser['dom'][key] = '' if val is JS_UNDEFINED else dom_string(val)
                    else:
                        state.browser[effect['space']][key] = val
