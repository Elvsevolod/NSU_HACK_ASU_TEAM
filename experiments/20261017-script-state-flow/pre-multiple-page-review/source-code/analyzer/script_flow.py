"""Page-owned classic-script state at observed HTTP response boundaries.

This closed slice accepts literal initialization and bare assignments in observed
success callbacks. Other writers, aliases and dynamic ownership stay unknown.
It does not infer invocation of arbitrary event handlers or module evaluation.
"""
from collections import Counter
from .project import text, walk
from .script_vars import ScriptVars, literal_initializer, parent_function
from .jsflow import UNKNOWN_EXPR
from .state import U


CLASSIC = ('', 'text/javascript', 'application/javascript')
MUTATIONS = ('assignment_expression', 'augmented_assignment_expression', 'update_expression')
CONTROL = ('return_statement', 'throw_statement', 'try_statement', 'switch_statement',
           'await_expression', 'yield_expression', 'break_statement', 'continue_statement',
           'labeled_statement', 'for_statement', 'for_in_statement', 'while_statement', 'do_statement')


def base(node):
    while node is not None and node.type in ('member_expression', 'subscript_expression', 'parenthesized_expression'):
        node = node.child_by_field_name('object') if node.type != 'parenthesized_expression' else node.named_children[0]
    return node


class ScriptFlow:
    def __init__(self, trees):
        self.models = {path:ScriptVars(tree.root_node) for path,tree in trees.items()}

    def add(self, path, tree):
        self.models[path] = ScriptVars(tree.root_node)

    def install(self, frontend, anchors, constant):
        resolved = {source.resolve():m for source,m in self.models.items()}
        identifiers = {source:{text(n) for n in walk(model.root) if n.type == 'identifier'} for source,model in resolved.items()}
        opaque_calls = {source:next((text(n.child_by_field_name('function')) for n in walk(model.root)
                         if n.type == 'call_expression' and text(n.child_by_field_name('function')) not in
                         ('$.ajax','jQuery.ajax','$http','JSON.stringify')),None) for source,model in resolved.items()}
        dynamic_this = {source:any(n.type == 'this' for n in walk(model.root)) for source,model in resolved.items()}
        callbacks = {}
        requests = {}
        for path,call,success in anchors.values():
            requests.setdefault(path,[]).append(call)
            if success is not None:
                callbacks.setdefault(path, set()).add((success.start_byte, success.end_byte))
        unsafe = {}
        for path,model in self.models.items():
            problems = {name:[] for name in model.bindings}
            for node in walk(model.root):
                if node.type in MUTATIONS:
                    target = node.child_by_field_name('left') or node.child_by_field_name('argument')
                    root = base(target)
                    name = model.resolve(root)
                    if name:
                        owner = parent_function(node)
                        observed = owner is not None and (owner.start_byte,owner.end_byte) in callbacks.get(path,set())
                        if model.write(node) != name or not observed:
                            problems[name].append('unobserved or non-bare script writer at line '+str(node.start_point.row+1))
                if node.type in ('variable_declarator','assignment_expression'):
                    source = base(node.child_by_field_name('value') if node.type == 'variable_declarator' else node.child_by_field_name('right'))
                    source_name = model.resolve(source)
                    if source_name:
                        problems[source_name].append('script value may acquire a mutable alias at line '+str(node.start_point.row+1))
                if node.type in ('member_expression','subscript_expression') and text(node.child_by_field_name('object')) in ('window','globalThis','self'):
                    key = text(node.child_by_field_name('property')) if node.type == 'member_expression' else None
                    for name,messages in problems.items():
                        if key is None or key == name:
                            messages.append('script binding accessed through global object at line '+str(node.start_point.row+1))
                if node.type == 'identifier' and model.resolve(node):
                    name = text(node)
                    parent = node.parent
                    owner = parent_function(node)
                    in_callback = owner is not None and (owner.start_byte,owner.end_byte) in callbacks.get(path,set())
                    in_request = any(call.start_byte <= node.start_byte < call.end_byte for call in requests.get(path,[]))
                    declaration = parent is not None and parent.type == 'variable_declarator' and parent.child_by_field_name('name') == node
                    if not (declaration or in_callback or in_request):
                        problems[name].append('script reference outside observed request slice at line '+str(node.start_point.row+1))
                    # An alias may be mutated by code outside this closed slice.
                    if parent is not None and parent.type == 'variable_declarator' and parent.child_by_field_name('value') == node:
                        problems[name].append('script object alias at line '+str(node.start_point.row+1))
                    current = node
                    while current.parent is not None and current.parent.type in ('member_expression','subscript_expression','parenthesized_expression'):
                        current = current.parent
                    owner = current.parent
                    if owner is not None and owner.type == 'call_expression' and owner.child_by_field_name('function') == current:
                        problems[name].append('script object method call at line '+str(node.start_point.row+1))
                    if owner is not None and owner.type == 'arguments':
                        call = owner.parent
                        if text(call.child_by_field_name('function')) != 'JSON.stringify':
                            problems[name].append('script value escapes to a call at line '+str(node.start_point.row+1))
                if node.type in MUTATIONS:
                    target = node.child_by_field_name('left') or node.child_by_field_name('argument')
                    root = base(target)
                    if root is not None and text(root) in ('window','globalThis','self'):
                        for messages in problems.values():
                            messages.append('explicit global-object write at line '+str(node.start_point.row+1))
            unsafe[path] = problems
        for sid,(path,call,success) in anchors.items():
            site,model = frontend.sites[sid],self.models[path]
            expression_names = set()
            for expression in [site['url'],*site['body_fields'].values(),*site.get('conditional_fields',{}).values(),
                               *site['definitions'].values(),*site.get('conditions',[])]:
                parsed = frontend.parser.parse(expression.encode()).root_node
                expression_names.update(text(n) for n in walk(parsed) if n.type == 'identifier')
            if not model.bindings:
                site['script_diagnostics'] = list(model.diagnostics) if expression_names & model.program_names else []
                frontend.warnings.extend(sid+': '+message for message in model.diagnostics)
                continue
            # Resolve at ORIGINAL AST anchors, never at newly parsed expressions.
            shadowed = model.function_shadow_names(call)
            request_names = {name for name in expression_names if model.resolve(call,name) and name not in shadowed}
            callback_names = {text(node) for node in walk(success) if node.type == 'identifier' and model.resolve(node)
                              and not (node.parent.type == 'assignment_expression' and node.parent.child_by_field_name('left') == node)} if success is not None else set()
            demanded = request_names | callback_names | {effect['key'] for effect in site['effects'] if effect['space'] == 'script'}
            page = frontend.pages.get(frontend.project.root/site['page'])
            issues = list(model.diagnostics)
            disabled = not page
            if page:
                page_path = frontend.project.root/site['page']
                includes = [(page_path.parent/src).resolve() for src in page.scripts if not src.startswith(('http','//'))]
                counts = Counter(name for include in includes if include in resolved for name in resolved[include].program_names)
                disabled = (len(includes) != len(page.scripts) or any(include not in resolved for include in includes)
                            or includes.count(path.resolve()) != 1
                            or any(kind not in CLASSIC for kind in page.script_kinds.values())
                            or any(script['kind'] in CLASSIC or script['kind']=='module' for script in page.inline_scripts))
            else:
                counts = Counter()
            if disabled:
                issues.append('classic-script page ownership or evaluation order is unresolved')
            defaults = {}
            for name,record in model.bindings.items():
                if name not in demanded:
                    continue
                messages = list(unsafe[path][name])
                if opaque_calls[path.resolve()] is not None:
                    messages.append('unmodeled script call may mutate shared bindings: '+opaque_calls[path.resolve()])
                if dynamic_this[path.resolve()]:
                    messages.append('dynamic this may alias the global object')
                if counts[name] > 1:
                    messages.append('colliding script declarations on the page')
                if page and any(other != path.resolve() and name in identifiers[other]
                                for other in includes if other in resolved):
                    messages.append('script binding is referenced by another included script')
                if page and any(other != path.resolve() and (opaque_calls[other] is not None or dynamic_this[other] or resolved[other].diagnostics)
                                for other in includes if other in resolved):
                    messages.append('another included script has unsupported effects or scope')
                if name in ('undefined','NaN','Infinity','window','globalThis','self','document','location','localStorage','sessionStorage'):
                    messages.append('host or immutable global binding')
                # Inline events can write bindings without an observed request.
                if page and any(name in handler for handler in page.inline_handlers):
                    messages.append('inline event may access or mutate script binding')
                issues.extend(name+': '+message for message in messages)
                valid = not disabled and not messages
                defaults[name] = U
                if valid and record['initializer_safe']:
                    declarator = next(n for n in model.root.named_children if n.type == 'variable_declaration'
                                      and any(text(c.child_by_field_name('name')) == name for c in n.named_children))
                    initializer = next(c.child_by_field_name('value') for c in declarator.named_children
                                       if text(c.child_by_field_name('name')) == name)
                    defaults[name] = constant(initializer)
                for effect in site['effects']:
                    if effect['space'] == 'script' and effect['key'] == name and not valid:
                        effect['expr'] = UNKNOWN_EXPR
            if any(effect.get('script_unsupported') for effect in site['effects']):
                issues.append('script response write has unsupported control flow or object mutation')
            site.update(script_defaults=defaults,script_reads=sorted(request_names),
                        script_callback_reads=sorted(callback_names),script_diagnostics=sorted(set(issues)) if demanded else [])
            frontend.warnings.extend(sid+': '+message for message in site['script_diagnostics'])

    def effect(self, path, node, success, condition):
        model = self.models[path]
        name = model.write(node)
        if name is None:
            return None
        unsupported = any(n.type in CONTROL and n.start_byte < node.start_byte for n in walk(success))
        unsupported |= any(n.type == 'call_expression' for n in walk(success))
        for prefix in walk(success):
            if prefix.start_byte >= node.start_byte:
                continue
            if prefix.type == 'expression_statement' and prefix.named_children and model.write(prefix.named_children[0]) is None:
                unsupported = True
            if prefix.type == 'variable_declarator':
                initializer = prefix.child_by_field_name('value')
                if initializer is not None and initializer.type != 'identifier' and not literal_initializer(initializer):
                    unsupported = True
            if prefix.type == 'if_statement' and prefix.end_byte <= node.start_byte:
                unsupported = True
        parameters = success.child_by_field_name('parameters') or success.child_by_field_name('parameter')
        response_names = {text(n) for n in walk(parameters) if n.type == 'identifier'} if parameters is not None else set()
        unsupported |= any(n.type in MUTATIONS and text(n.child_by_field_name('left') or n.child_by_field_name('argument')) in response_names
                           for n in walk(success))
        # Mutation of a response alias after capture cannot be replayed as a stale snapshot.
        unsupported |= any(n.type in MUTATIONS and (target := n.child_by_field_name('left') or n.child_by_field_name('argument')) is not None
                           and target.type in ('member_expression','subscript_expression') for n in walk(success))
        return {'space':'script','key':name,'expr':UNKNOWN_EXPR if unsupported else text(node.child_by_field_name('right')),
                'conditions':condition,'script_unsupported':unsupported}
