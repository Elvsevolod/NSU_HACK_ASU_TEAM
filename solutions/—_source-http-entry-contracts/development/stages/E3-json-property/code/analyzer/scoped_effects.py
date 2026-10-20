"""One stop-only summary: a native unknown foreach with a read-only residual.

No continuation is resumed and no return value is supplied. The proof merely
avoids invalidating data after a stopped, local scalar projection. The domain
is {proven_read_only, unproved}; join is unproved unless both prove read-only.
There is no cache, fixed point, scheduler or exception/transaction shortcut.
"""
import hashlib
from .project import text,walk
from .native_storage import JavaList


def stop_summary(engine,boundary):
    if not engine.state.context.get('scoped_effect_summary',True):return None
    frames=engine.boundary_frames
    if not frames or engine.boundary_had_transaction or engine.state.transactions or engine.state.unscoped_state_assumptions:return None
    mids={mid for mid,_,_ in frames}
    if len(mids)!=1:return None
    mid=next(iter(mids));meta=engine.p.methods[mid]
    leaf=frames[-1][1];env=frames[-1][2]
    if leaf is None or leaf.type!='enhanced_for_statement' or 'unknown collection membership' not in str(boundary):return None
    value_node=leaf.child_by_field_name('value')
    if value_node is None or value_node.type!='identifier':return None
    carrier=env.get(text(value_node))
    if not isinstance(carrier,JavaList) or carrier.flavor not in ('ArrayList','LinkedList','Arrays.ArrayList','HashSet') or not carrier.opaque:return None
    # Start with the entire unvisited loop body. Add all later statements in
    # active blocks, every possible catch/finally, and reject repeated loops.
    residual=[leaf.child_by_field_name('body')]
    normal_exit=True
    for index in range(len(frames)-2,-1,-1):
        _,node,_=frames[index]
        child=frames[index+1][1]
        if node.type in ('block','constructor_body'):
            statements=list(node.named_children)
            if child not in statements:return None
            if normal_exit:
                for statement in statements[statements.index(child)+1:]:
                    residual.append(statement)
                    if statement.type in ('return_statement','throw_statement'):
                        normal_exit=False;break
        elif node.type in ('while_statement','do_statement','for_statement','enhanced_for_statement'):return None
        elif node.type in ('try_statement','try_with_resources_statement'):
            if node.type=='try_with_resources_statement':return None
            residual.extend(c for c in node.named_children if c.type in ('catch_clause','finally_clause'))
            if any(c.type=='catch_clause' for c in node.named_children):normal_exit=True
        elif node.type not in ('if_statement',):return None
    locals_={name for name,_ in engine.p.parameters(mid)}
    source=engine.p.ast.get(mid)
    for node in walk(source):
        if node.type=='variable_declarator':locals_.add(text(node.child_by_field_name('name')))
        elif node.type=='enhanced_for_statement':locals_.add(text(node.child_by_field_name('name')))
    active=set()
    def readonly(node,owner_mid=mid,names=locals_):
        if node is None:return True
        kind=node.type
        if kind in ('object_creation_expression','array_creation_expression','synchronized_statement','method_reference','lambda_expression','class_declaration','try_with_resources_statement'):return False
        if kind in ('assignment_expression','update_expression'):
            left=node.child_by_field_name('left') if kind=='assignment_expression' else next(iter(node.named_children),None)
            if left is None or left.type!='identifier' or text(left) not in names:return False
        if kind=='field_access':return False  # lazy/active class reads need another contract
        if kind=='identifier':
            owner=engine.p.methods[owner_mid]
            if (text(node) in engine.p.type_fields.get(owner['owner'],{}) or
                    engine.p.static_field_declaration(owner['owner'],text(node)) or
                    engine.p.imported_static_field(owner['file'],owner['module'],text(node))):return False
        if kind=='method_invocation':
            site=engine.p.site(owner_mid,node)
            targets=engine.p.targets(owner_mid,site) if site else engine.p.source_targets(owner_mid,node)
            if not targets:return False
            for target in targets:
                body=engine.p.ast.get(target)
                if target in active or body is None or engine.p.methods[target].get('abstract'):return False
                from .static_storage import items
                owner=engine.p.methods[target]['owner']
                status=engine.state.class_initialization.get(owner,{})
                if items(engine.p,owner) and (not isinstance(status,dict) or status.get('status')!='initialized'):return False
                nested_names={name for name,_ in engine.p.parameters(target)}
                nested_names.update(text(n.child_by_field_name('name')) for n in walk(body) if n.type=='variable_declarator')
                active.add(target)
                try:
                    if not readonly(body,target,nested_names):return False
                finally:active.remove(target)
        return all(readonly(child,owner_mid,names) for child in node.named_children)
    if not all(readonly(node) for node in residual):return None
    roots=[{'file':meta['file'],'start_line':n.start_point.row+1,'end_line':n.end_point.row+1} for n in residual if n is not None]
    return {'model_version':'readonly-native-foreach-stop/1','operation':'stopped scalar projection',
        'source_sha256':hashlib.sha256(engine.p.sources[meta['file']]).hexdigest(),
        'method':mid,'source_spans':roots,'preconditions':{
            'single_active_source_frame':True,'native_collection':carrier.flavor,'membership':'unknown',
            'no_transaction':True,'no_unscoped_effect':True,'residual_source_readonly':True},
        'return':'not supplied','throw':'not supplied','completion':'analysis boundary retained',
        'read_footprint':'source scalar locals only',
        'write_footprint':[],'alias_assumptions':'all reachable aliases retained; no residual heap stores',
        'guards':list(engine.boundary_guards),'prefix_effect_count':len(engine.data_operations),
        'effects_order':'executed prefix unchanged; suffix remains unexecuted',
        'reuse':'none; source and preconditions checked on every occurrence'}
