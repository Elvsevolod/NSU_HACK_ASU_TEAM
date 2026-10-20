"""A narrowly proven consumer equivalence: omitted/null/empty String input.

Only default-null bean properties observed through Spring StringUtils.isEmpty
are covered. Other observations retain a distinct wire-value constraint.
"""
from .project import walk,text


def empty_equivalent(engine, entry, field):
    p=engine.p;meta=p.methods[entry]
    parameters=[item for item in p.http_parameters(entry) if item['kind']=='RequestBody']
    if len(parameters)!=1:return False
    owner=p.resolve_type(parameters[0]['type'],meta['module'],meta['file'])
    info=p.type_fields.get(owner,{}).get(field)
    if not info or info['type'] not in ('String','java.lang.String') or info['has_initializer']:return False
    if any(m['owner']==owner and m['name']=='<init>' for m in p.methods.values()):return False
    getter='get'+field[:1].upper()+field[1:]
    getters=p.inherited_methods(owner,getter,0)
    source_getters=[p.ast[mid] for mid in getters if p.ast.get(mid) is not None]
    if source_getters:
        if len(source_getters)!=1:return False
        body=source_getters[0].child_by_field_name('body')
        statements=body.named_children if body is not None else []
        if len(statements)!=1 or statements[0].type!='return_statement':return False
        expression=statements[0].named_children
        if len(expression)!=1 or text(expression[0]) not in (field,'this.'+field):return False
    else:
        from .bean_properties import generated_accessor
        accessor=generated_accessor(p,owner,getter,0,engine.standard_type)
        if accessor is None or accessor['member']!=field:return False
    found=False
    def empty_call(node,names,context):
        if node is None:return False
        if node.type=='parenthesized_expression' and len(node.named_children)==1:return empty_call(node.named_children[0],names,context)
        if node.type!='method_invocation' or text(node.child_by_field_name('name'))!='isEmpty':return False
        args=node.child_by_field_name('arguments')
        return (len(args.named_children)==1 and text(args.named_children[0]) in names and
                engine.standard_type(text(node.child_by_field_name('object')),'org.springframework.util.StringUtils',context))
    for mid in p.ix.closure({entry})[0]:
        method=p.methods[mid];body=p.ast.get(mid)
        if body is None:continue
        receivers={name for name,typ in p.parameters(mid) if p.resolve_type(typ,method['module'],method['file'])==owner}
        if not receivers:continue
        for use in (n for n in walk(body) if n.type=='identifier' and text(n) in receivers):
            parent=use.parent
            if parent.type=='formal_parameter' and parent.child_by_field_name('name')==use:continue
            if parent.type=='method_invocation' and parent.child_by_field_name('object')==use:
                name=text(parent.child_by_field_name('name'));args=parent.child_by_field_name('arguments')
                if args.named_children or not name.startswith('get'):return False
                member=name[3:4].lower()+name[4:]
                candidates=p.inherited_methods(owner,name,0)
                source=[p.ast[target] for target in candidates if p.ast.get(target) is not None]
                if source:
                    statements=source[0].child_by_field_name('body')
                    statements=statements.named_children if statements else []
                    if len(source)!=1 or len(statements)!=1 or statements[0].type!='return_statement' or len(statements[0].named_children)!=1 or text(statements[0].named_children[0]) not in (member,'this.'+member):return False
                else:
                    from .bean_properties import generated_accessor
                    if generated_accessor(p,owner,name,0,engine.standard_type) is None:return False
                continue
            if parent.type=='argument_list' and parent.parent.type=='method_invocation':
                call=parent.parent;index=parent.named_children.index(use)
                sites=p.by_line.get((mid,call.start_point.row+1,text(call.child_by_field_name('name'))),())
                targets={target for site in sites for target in p.edges.get(site,{}).get('calls',())}
                if targets and all(len(p.parameters(target))>index and p.resolve_type(p.parameters(target)[index][1],
                        p.methods[target]['module'],p.methods[target]['file'])==owner and p.ast.get(target) is not None for target in targets):continue
            # No equivalence claim after a DTO alias, field capture, return,
            # cast, unknown call or any other unproved observation/escape.
            return False
        reads=[n for n in walk(body) if n.type=='method_invocation' and text(n.child_by_field_name('object')) in receivers
               and text(n.child_by_field_name('name'))==getter and not n.child_by_field_name('arguments').named_children]
        if any(n.type=='field_access' and text(n.child_by_field_name('object')) in receivers and
               text(n.child_by_field_name('field'))==field for n in walk(body)):return False
        for read in reads:
            names={text(read)};local=None
            if read.parent.type=='variable_declarator' and read.parent.child_by_field_name('value')==read:
                local=text(read.parent.child_by_field_name('name'));names.add(local)
            occurrences=[n for n in walk(body) if n.type=='identifier' and text(n)==local and
                not (n.parent.type=='variable_declarator' and n.parent.child_by_field_name('name')==n)] if local else [read]
            for node in occurrences:
                call=node.parent.parent if node.parent.type=='argument_list' else None
                if empty_call(call,names,method):found=True;continue
                ancestor=node.parent;guarded=False
                while ancestor is not None and ancestor!=body:
                    if ancestor.type=='if_statement':
                        condition=ancestor.child_by_field_name('condition')
                        while condition.type=='parenthesized_expression':condition=condition.named_children[0]
                        if condition.type=='unary_expression' and text(condition.child_by_field_name('operator'))=='!' and empty_call(condition.child_by_field_name('operand'),names,method):
                            consequence=ancestor.child_by_field_name('consequence')
                            guarded=consequence.start_byte<=node.start_byte<consequence.end_byte
                            if guarded:break
                    ancestor=ancestor.parent
                if not guarded:return False
    return found
