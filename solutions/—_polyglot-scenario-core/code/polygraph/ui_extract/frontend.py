"""Static extraction and symbolic evaluation of browser request contracts."""
from copy import deepcopy
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlsplit, parse_qsl
from .symbolic_text import concat_text
from tree_sitter import Language, Parser
import tree_sitter_javascript
from .baseline import front_files
from .project import text, walk
from .state import U, JS_UNDEFINED, SymbolicValue, JSONObject
from .native import engine as native_engine, concrete, JavaScriptError, NativeUnavailable, OPERATORS, METHODS
from .json_values import stringify as json_stringify, parse as json_parse
from .jsflow import definitions_before, url_cases, UNKNOWN_EXPR, dom_access
from .nl_inputs import control_polarity
from .option_sources import option_sources
from .html_rows import analyze_html_rows
from .form_flow import vue_form_flows
from .html_options import fragment_options, document_options, document_texts
from .units import unit_name
from .response_arrays import summarize_array_copy
from .script_flow import ScriptFlow


def pairs(node):
    return {property_key(c.child_by_field_name('key')): c.child_by_field_name('value')
            for c in node.named_children if c.type == 'pair'} if node and node.type == 'object' else {}


def property_key(node):
    if node is not None and node.type == 'string':
        value=literal(node)
        return value if isinstance(value,str) else text(node)
    if node is not None and node.type == 'number':
        value=literal(node)
        return native_engine().run('String',value) if value is not U else text(node)
    return text(node)


def array_holes(node):
    expecting=True
    for child in node.children:
        if child.type in ('[',']','comment'):continue
        if child.type==',':
            if expecting:return True
            expecting=True
        else:expecting=False
    return False


def literal(node):
    if node is None:return U
    try:return native_engine().literal(text(node),node.type)
    except (JavaScriptError,NativeUnavailable):return U


def constant(node):
    if node is not None and node.type == 'object':
        if any(c.type not in ('pair','comment') or c.type=='pair' and c.child_by_field_name('key').type=='computed_property_name' for c in node.named_children) or '__proto__' in pairs(node):return U
        return JSONObject({key: constant(val) for key, val in pairs(node).items()})
    if node is not None and node.type == 'array':
        return U if array_holes(node) else [constant(child) for child in node.named_children if child.type!='comment']
    return literal(node)


def truth(value):
    if value is U or isinstance(value,SymbolicValue):return U
    try:return native_engine().run('truth',value)
    except NativeUnavailable:return U


def primitive_equal(left,right,strict=False):
    if left is U or right is U:return U
    if isinstance(left,SymbolicValue) or isinstance(right,SymbolicValue):
        if isinstance(left,SymbolicValue) and isinstance(right,SymbolicValue) and left.get('__symbol__')==right.get('__symbol__'):return True
        if (left is None or left is JS_UNDEFINED) and isinstance(right,SymbolicValue) and right.get('__nonnull__') is True:return False
        if (right is None or right is JS_UNDEFINED) and isinstance(left,SymbolicValue) and left.get('__nonnull__') is True:return False
        return U
    if isinstance(left,(dict,list)) and isinstance(right,(dict,list)):return left is right
    return native_engine().run('===' if strict else '==',left,right)


def dom_string(value,text_property=False):
    if value is None:return U if text_property else ''
    if isinstance(value,SymbolicValue):return value if value.get('__category__')=='string' and value.get('__nonnull__') is True else U
    return native_engine().run('String',value)


def object_property(value,key):
    if key in value:return value[key]
    inherited={'constructor','toString','toLocaleString','valueOf','hasOwnProperty','isPrototypeOf','propertyIsEnumerable',
               '__proto__','__defineGetter__','__defineSetter__','__lookupGetter__','__lookupSetter__'}
    # Complete own JSON keys do not prove the absence of Object.prototype.
    return JS_UNDEFINED if isinstance(value,JSONObject) and key not in inherited else U


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


def completion_checks(scope, stop=None, modeled=(), base=None):
    """Ordered completion checks; parser facts only, never executing a script."""
    checks = []
    for node in walk(scope):
        if stop is not None and node.end_byte > stop.start_byte:
            continue
        owner = ancestor(node.parent, FUNCTIONS) or ancestor(node.parent, ('program',))
        if owner != scope or node.start_byte in modeled:
            continue
        if node.type == 'variable_declarator':
            expression, completion = node.child_by_field_name('value'), 'evaluate'
        elif node.type in ('return_statement', 'throw_statement', 'expression_statement'):
            expression = node.named_children[0] if node.named_children else None
            completion = {'return_statement':'return', 'throw_statement':'throw'}.get(node.type, 'evaluate')
        else:
            continue
        if expression is None and completion == 'evaluate':
            continue
        if expression is not None and expression.start_byte in modeled:
            continue
        receiver = None
        if expression is not None and expression.type == 'assignment_expression' and text(expression.child_by_field_name('operator')) in ('','='):
            target = expression.child_by_field_name('left')
            if target is not None and target.type == 'member_expression' and text(target.child_by_field_name('property')) != '__proto__':
                receiver = text(target.child_by_field_name('object'))
                expression = expression.child_by_field_name('right')
        parent, unsupported = node.parent, False
        while parent is not None and parent != scope:
            unsupported |= parent.type in ('try_statement', 'switch_statement', 'for_statement', 'for_in_statement', 'while_statement', 'do_statement')
            parent = parent.parent
        checks.append({'space':'completion', 'completion':completion, 'key':'',
                       'expr':text(expression) if expression is not None else 'undefined',
                       'offset':node.start_byte, 'conditions':request_guards(node, scope),
                       'receiver':receiver,
                       'definitions':definitions_before(scope, node, base)[0], 'unsupported_control':unsupported})
    return checks


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
        self.script_kinds, self.inline_scripts, self.inline_handlers = {}, [], []
        self.current_script = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.inline_handlers.extend(value for key,value in attrs if key.startswith('on') and value)
        if tag == 'script':
            self.current_script = {'src':a.get('src'),'kind':a.get('type','').strip().lower(),'text':''}
            if a.get('src'):
                self.scripts.append(a['src'])
                self.script_kinds[a['src']] = self.current_script['kind']
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
        if self.current_script is not None:
            self.current_script['text'] += data
        value = data.strip()
        if value:
            self.labels.append(value)
            if self.option is not None:
                self.option['label'] += value

    def handle_endtag(self, tag):
        if tag == 'script' and self.current_script is not None:
            if not self.current_script['src'] and self.current_script['text'].strip():
                self.inline_scripts.append(self.current_script)
            self.current_script = None
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
        self.ajax_hooks = []
        self.unit_cache = {}
        self.selector_cache = {}
        self.script_flow, script_anchors = ScriptFlow({}), {}
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
            if page.inline_scripts:
                self.unsupported.append('Inline JavaScript is not lowered: '+str(path.relative_to(project.root)))
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
                if node.type=='call_expression' and text(node.child_by_field_name('function')) in ('$.ajaxSetup','jQuery.ajaxSetup','$.ajaxPrefilter','jQuery.ajaxPrefilter','$.ajaxTransport','jQuery.ajaxTransport'):
                    self.ajax_hooks.append(str(path.relative_to(project.root))+':'+str(node.start_point.row+1))
                if node.type=='call_expression' and re.fullmatch(r'(?:(?:window|globalThis)\.)?fetch|axios(?:\.\w+)?',text(node.child_by_field_name('function'))):
                    self.unsupported.append('Unsupported frontend HTTP client '+text(node.child_by_field_name('function'))+': '+str(path.relative_to(project.root))+':'+str(node.start_point.row+1))
            self.trees[path] = tree
            self.script_flow.add(path,tree)
            self.form_flows[path] = vue_form_flows(tree.root_node)
            self.warnings.extend(str(path.relative_to(project.root))+': '+message
                                 for flow in self.form_flows[path] for message in flow.get('diagnostics',[]))
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
                if not config.get('url') or function not in ('$.ajax','jQuery.ajax','$http'):
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
                verb = str(literal(config.get('type') or config.get('method'))).upper() if 'type' in config or 'method' in config else 'GET'
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
                    self.warnings.append(str(path.relative_to(project.root))+': no handler matches the source method/URL')
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
                data_input = data
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
                callback_chain, chained = [], call
                while chained.parent is not None and chained.parent.type == 'member_expression' and chained.parent.child_by_field_name('object') == chained:
                    member = chained.parent
                    outer = member.parent
                    if outer is None or outer.type != 'call_expression':break
                    callback_chain.append(text(member.child_by_field_name('property')))
                    chained = outer
                if callback_chain:
                    self.unsupported.append('Response callback chain not lowered: '+str(path.relative_to(project.root))+':'+str(call.start_point.row+1))
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
                            storage = re.fullmatch(r'(sessionStorage|localStorage)\.setItem', fn)
                            dom = re.fullmatch(r'\$\(([\"\'])([^\"\']*)\1\)\.(val|text|html)', fn)
                            if storage and len(values) >= 2 and isinstance(literal(values[0]), str):
                                effects.append({'space': 'storage', 'storage_kind':storage[1], 'key': literal(values[0]), 'expr': text(values[1]), 'conditions': condition})
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
                            script_effect = self.script_flow.effect(path,node,success,condition)
                            if script_effect is not None:
                                effects.append(script_effect)
                        for effect in effects[effect_start:]:
                            effect['offset'] = node.start_byte
                            effect.setdefault('definitions',definitions_before(success,node,definitions)[0])
                            if enclosing is not None or ancestor(node.parent,FUNCTIONS)!=success:
                                effect['expr']=UNKNOWN_EXPR
                                if effect['space'] == 'script':
                                    effect['script_unsupported'] = True
                                self.unsupported.append('Unmodeled browser response iteration or nested callback: '+str(path.relative_to(project.root))+':'+str(node.start_point.row+1))
                    checks = completion_checks(success, modeled={effect['offset'] for effect in effects if 'offset' in effect}, base=definitions)
                    effects = sorted(effects + checks, key=lambda effect:effect.get('offset',0))
                sid = path.relative_to(project.root).as_posix() + ':' + str(call.start_point.row + 1) + ':' + str(call.start_point.column + 1)
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
                xhr_fields = constant(config.get('xhrFields'))
                xhr_supported = isinstance(xhr_fields,dict) and set(xhr_fields) <= {'withCredentials'} and all(type(value) is bool for value in xhr_fields.values())
                unsupported_options = set(config)&{'beforeSend','converters','dataFilter','xhr','jsonp','jsonpCallback','transformRequest','transformResponse','paramSerializer'}
                if 'xhrFields' in config and not xhr_supported:
                    unsupported_options.add('xhrFields')
                self.sites[sid] = {'id': sid, 'file': path.relative_to(project.root).as_posix(),
                                   'page': pages[0][0].relative_to(project.root).as_posix() if pages else path.relative_to(project.root).as_posix(),
                                   'line': call.start_point.row + 1, 'handlers': handlers, 'verb': verb,
                                   'start_byte':call.start_byte,'column':call.start_point.column+1,
                                   'headers_expression':substitute(text(config.get('headers')),argument_bindings),
                                   'client':'angular-http' if function == '$http' else 'jquery',
                                   'content_type':literal(config.get('contentType')),
                                   'content_type_present':config.get('contentType') is not None,
                                   'process_data':literal(config['processData']) if 'processData' in config else True,
                                   'unsupported_ajax_options':sorted(unsupported_options),
                                   'with_credentials':xhr_fields.get('withCredentials',False) if isinstance(xhr_fields,dict) else literal(config.get('withCredentials')),
                                   'params_expression':substitute(text(config.get('params')),argument_bindings),
                                   'response_data_type':literal(config.get('dataType')),
                                   'data_expression':data_input,
                                   'data_present':config.get('data') is not None,
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
                                   'unmodeled_callback_chain':callback_chain,
                                   'request_checks': completion_checks(scope, call),
                                   'response_aliases':response_aliases,'response_this':response_this,
                                   'option_sources': option_sources(success, response_name),
                                   'dom_preparation': self.dom_before(call,path),
                                   'response_definitions': response_definitions}
                script_anchors[sid] = (path,call,success)
        self.script_flow.install(self,script_anchors,constant)
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
            value = dom_string(value,method == 'text')
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
        if getattr(state,'angular_scope',False):env['$scope']=state.browser['form']

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
                if obj is None or obj is JS_UNDEFINED:raise JavaScriptError('TypeError','Property read on null/undefined')
                if isinstance(obj,SymbolicValue) and key.startswith('__'):
                    state.limitations.append('Abstract metadata is not a browser data property: ' + raw)
                    return U
                if key=='length' and isinstance(obj,SymbolicValue) and obj.get('__type__') in ('String','java.lang.String'):
                    return obj.get('__length__',U)
                if key == 'length' and isinstance(obj,str):
                    return len(obj.encode('utf-16-le',errors='surrogatepass'))//2
                return object_property(obj,key) if isinstance(obj, dict) else len(obj) if key == 'length' and isinstance(obj, list) else U
            if kind == 'subscript_expression':
                obj, key = value(node.child_by_field_name('object')), value(node.child_by_field_name('index'))
                if obj is None or obj is JS_UNDEFINED:raise JavaScriptError('TypeError','Indexed read on null/undefined')
                if isinstance(obj,SymbolicValue) and isinstance(key, str) and key.startswith('__'):
                    state.limitations.append('Abstract metadata is not a browser data property: ' + raw)
                    return U
                if isinstance(obj, dict):
                    key=native_engine().run('String',key) if concrete(key) else U
                    return object_property(obj,key) if key is not U else U
                if isinstance(obj,(list,str)):
                    if key=='length':return len(obj) if isinstance(obj,list) else len(obj.encode('utf-16-le',errors='surrogatepass'))//2
                    if type(key) is str and re.fullmatch(r'0|[1-9]\d*',key):key=int(key)
                    if type(key) in (int,float) and not isinstance(key,bool) and key>=0 and key==int(key):
                        key=int(key)
                        length=len(obj) if isinstance(obj,list) else len(obj.encode('utf-16-le',errors='surrogatepass'))//2
                        return JS_UNDEFINED if key>=length else obj[key] if isinstance(obj,list) else native_engine().run('charAt',obj,key)
                    return U
                return U
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
                if op=='+' and any(isinstance(v,SymbolicValue) and v.get('__category__')=='string' for v in (left,right)):
                    def string_part(item):
                        if item is None:return 'null'
                        if type(item) is bool:return str(item).lower()
                        if type(item) is int and abs(item)<=9007199254740991:return str(item)
                        return item
                    return concat_text(string_part(left),string_part(right))
                if any(isinstance(value,SymbolicValue) for value in (left,right)):
                    return U
                if op in OPERATORS:
                    return native_engine().run(op,left,right)
                return U
            if kind == 'ternary_expression':
                condition = truth(value(node.child_by_field_name('condition')))
                if condition is U:
                    left, right = value(node.child_by_field_name('consequence')), value(node.child_by_field_name('alternative'))
                    return left if left is not U and left == right else U
                return value(node.child_by_field_name('consequence' if condition else 'alternative'))
            if kind == 'unary_expression':
                arg = value(node.child_by_field_name('argument'))
                return native_engine().run('u'+raw[0] if raw[0] in '+-' else raw[0],arg) if arg is not U else U
            if kind == 'call_expression':
                fn = text(node.child_by_field_name('function'))
                if fn.split('.')[0] in getattr(state,'blocked_natives',()):
                    state.limitations.append('Shadowed native operation: '+fn)
                    return U
                args = node.child_by_field_name('arguments')
                vals = [value(c) for c in args.named_children] if args else []
                if fn == '__unresolved_jquery_text_null__':
                    state.limitations.append('jQuery version is not resolved for text(null)')
                    return U
                if fn in (local_calls or {}):
                    return local_calls[fn](vals)
                if fn in ('sessionStorage.getItem', 'localStorage.getItem') and vals and isinstance(vals[0], str):
                    kind=fn.split('.')[0]
                    return state.browser['storage'].setdefault(kind,{}).get(vals[0], None if state.browser.get('storage_complete',{}).get(kind) else U)
                if fn == 'JSON.stringify' and vals:
                    return json_stringify(vals[0])
                if fn == 'JSON.parse' and vals:
                    return json_parse(vals[0])
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
                    if isinstance(receiver,str) and method in METHODS:
                        return native_engine().run(method,receiver,*vals)
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
                if fn in ('parseInt','parseFloat') and vals:
                    return native_engine().run(fn,*vals)
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
            if kind == 'new_expression' and text(node.child_by_field_name('constructor')) == 'Object' and 'Object' not in getattr(state,'blocked_natives',()):
                args=node.child_by_field_name('arguments')
                return JSONObject({}) if args is not None and not args.named_children else U
            if kind == 'object':
                if any(c.type not in ('pair','comment') or c.type=='pair' and c.child_by_field_name('key').type=='computed_property_name' for c in node.named_children) or '__proto__' in pairs(node):
                    state.limitations.append('Unsupported object keys/spread/prototype: '+raw)
                    return U
                return JSONObject({key: value(val) for key, val in pairs(node).items()})
            if kind == 'array':
                if array_holes(node):
                    state.limitations.append('Array holes require unsupported iteration semantics: '+raw)
                    return U
                return [value(c) for c in node.named_children if c.type!='comment']
            return U

        try:
            return value(tree.root_node.named_children[0])
        except NativeUnavailable as exc:
            state.limitations.append('Native JavaScript operation unavailable: '+str(exc))
            return U
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
        if node.type == 'member_expression' and text(node.child_by_field_name('object')) in (('this','that','$scope') if getattr(state,'angular_scope',False) else ('this','that')):
            state.browser['form'][text(node.child_by_field_name('property'))] = deepcopy(value)
        elif node.type == 'call_expression':
            fn = text(node.child_by_field_name('function'))
            dom = re.fullmatch(r'\$\(([\"\'])(.*?)\1\)\.(val|text)', fn)
            if dom:
                stored = dom_string(value,dom[3] == 'text')
                if value is None and dom[3] == 'text':
                    state.limitations.append('jQuery version is not resolved for text(null)')
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
                                                               'script':state.browser.get('script',{}),
                                                               'script_unknown':state.browser.get('script_unknown',False),
                                                               'options':state.browser.get('options',{})}
            previous = state.browser.setdefault('pages', {}).get(page, {})
            if not isinstance(previous, dict):
                previous = {'form': {key: U for key in site['defaults']},
                            'dom': {key: U for key in site['dom_defaults']},
                            'script': {key:U for key in site.get('script_defaults',{})},
                            'script_unknown':True,
                            'dom_text': {key:U for key in site.get('dom_text_defaults',{})}}
                state.limitations.append('unknown prior browser page state: ' + page)
            state.browser['form'] = deepcopy(previous.get('form', {}))
            state.browser['dom'] = deepcopy(previous.get('dom', {}))
            state.browser['dom_text'] = deepcopy(previous.get('dom_text',{}))
            state.browser['script'] = deepcopy(previous.get('script',{}))
            state.browser['script_unknown'] = previous.get('script_unknown',False)
            state.browser['options'] = deepcopy(previous.get('options',{}))
            state.browser['active_page'] = page
        for name, default in site['defaults'].items():
            state.browser['form'].setdefault(name, deepcopy(default))
        for name, default in site['dom_defaults'].items():
            state.browser['dom'].setdefault(name, default)
        for name,default in site.get('dom_text_defaults',{}).items():
            state.browser.setdefault('dom_text',{}).setdefault(name,default)
        for name,default in site.get('script_defaults',{}).items():
            state.browser.setdefault('script',{}).setdefault(name,U if state.browser.get('script_unknown',False) is not False else deepcopy(default))
        state.browser['source_options'] = [option for option in site.get('options',[]) if option.get('space') == 'dom']


    def script_values(self, site, state, callback=False):
        state.limitations.extend(site.get('script_diagnostics',[]))
        names = site.get('script_callback_reads' if callback else 'script_reads',[])
        values = {name:state.browser.get('script',{}).get(name,U) for name in names}
        for name,value in values.items():
            if value is U:
                state.limitations.append('Unknown script binding state: '+name+' at '+site['id'])
        return values


    def apply_response(self, site, result, state):
        event_values = {key:value for key,value in site.get('event_values',{}).items() if key not in site.get('script_reads',[])}
        env = {**self.script_values(site,state,callback=True),**event_values,site['response_name']: deepcopy(result)}
        if 'response_this' in site:
            env['this']=state.browser['form'] if site['response_this'] else U
            env.setdefault('that',U)
            env.update({alias:state.browser['form'] for alias in site['response_aliases']})
        completion_unknown = False
        for effect in site['effects']:
            definitions = effect.get('definitions',site['response_definitions'])
            conditions = [truth(self.evaluate(c, state, env, definitions)) for c in effect['conditions']]
            if False in conditions:
                continue
            uncertain = any(c is U for c in conditions) or effect.get('unsupported_control',False)
            try:
                val = U if completion_unknown or effect.get('unsupported_control') else self.check_completion(effect,state,env,definitions)
            except JavaScriptError:
                if not uncertain and not completion_unknown:
                    raise
                val = U
            if effect['space'] == 'completion':
                if uncertain or val is U:
                    completion_unknown = True
                    state.limitations.append('Unknown browser callback completion before later effects: '+site['id'])
                elif effect['completion'] == 'return':
                    break
                elif effect['completion'] == 'throw':
                    raise JavaScriptError('ThrownValue','Source callback throws')
                continue
            if val is U:
                completion_unknown = True
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
                            if val is None:
                                state.limitations.append('jQuery version is not resolved for text(null)')
                            val = dom_string(val,True)
                            state.browser.setdefault('dom_text',{})[key] = deepcopy(val)
                        elif effect.get('mode') == 'html':
                            state.browser.setdefault('dom_text',{})[key] = U
                            state.limitations.append('HTML replacement text requires DOM construction: '+site['id'])
                        else:
                            state.browser['dom'][key] = '' if val is JS_UNDEFINED else dom_string(val)
                    else:
                        if effect['space']=='storage' and val is not U and not isinstance(val,SymbolicValue):
                            val=native_engine().run('String',val)
                        if effect['space']=='storage':
                            state.browser['storage'].setdefault(effect['storage_kind'],{})[key]=val
                        else:
                            state.browser[effect['space']][key] = val
                        if effect['space'] == 'script':
                            env[key] = val

    def check_completion(self, effect, state, env, definitions):
        if effect.get('receiver'):
            receiver=self.evaluate(effect['receiver'],state,env,definitions)
            if receiver is None or receiver is JS_UNDEFINED:
                raise JavaScriptError('TypeError','Property assignment on null/undefined')
            if not isinstance(receiver,dict) or isinstance(receiver,SymbolicValue):
                return U
        return self.evaluate(effect['expr'],state,env,definitions)

