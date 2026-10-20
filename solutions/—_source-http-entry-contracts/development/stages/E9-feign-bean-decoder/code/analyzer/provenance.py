"""Resolve response references by declared entity and explicit selection language."""
import re
from decimal import Decimal, InvalidOperation
from baseline_nlp import ntoks
from .state import U
from .project import text
from .models import date_value
from .java_collections import JavaMap,JavaRecord,JavaEnumValue,JsonObject,JsonText,schema_type,semantic_view


def source_string(project, value):
    """Evaluate only source-proven pure toString/getter expressions for composite IDs."""
    active = set()

    def invoke(obj, tid, name):
        signature = (tid, name)
        if tid is None or signature in active:
            return U
        methods = [m for m in project.methods_of(tid, name) if not project.parameters(m)]
        if not methods:
            if name == 'name' and tid in project.enum_members and isinstance(obj, dict):
                return obj.enum_name if isinstance(obj,JavaEnumValue) else U
            return U
        if len(methods) != 1:
            return U
        node = project.ast.get(methods[0])
        body = node.child_by_field_name('body') if node else None
        statements = [s for s in body.named_children if s.type not in ('line_comment', 'block_comment')] if body else []
        if len(statements) != 1 or statements[0].type != 'return_statement':
            return U
        active.add(signature)
        result = expression(statements[0].named_children[0], obj, tid)
        active.remove(signature)
        return result

    def expression(node, obj, tid):
        kind = node.type
        if kind == 'this':
            return obj
        if kind == 'identifier':
            return obj.get(text(node), U)
        if kind == 'field_access' and text(node.child_by_field_name('object')) == 'this':
            return obj.get(text(node.child_by_field_name('field')), U)
        if kind == 'string_literal':
            import json
            try:
                return json.loads(text(node))
            except ValueError:
                return U
        if kind == 'binary_expression' and text(node.child_by_field_name('operator')) == '+':
            left, right = expression(node.child_by_field_name('left'), obj, tid), expression(node.child_by_field_name('right'), obj, tid)
            if left is U or right is U or not isinstance(left, (str, int)) or not isinstance(right, (str, int)):
                return U
            return str(left) + str(right) if isinstance(left, str) or isinstance(right, str) else left + right
        if kind == 'method_invocation':
            args = node.child_by_field_name('arguments')
            if args and args.named_children:
                return U
            receiver = node.child_by_field_name('object')
            receiver_value = obj if receiver is None else expression(receiver, obj, tid)
            target = tid
            if receiver is not None and receiver.type == 'identifier':
                field = project.type_fields.get(tid, {}).get(text(receiver), {})
                target = project.resolve_type(field.get('type', ''), project.nodes[tid].get('module'), project.nodes[tid].get('file'))
            if not isinstance(receiver_value, dict):
                return U
            return invoke(receiver_value, target, text(node.child_by_field_name('name')))
        return U

    if not isinstance(value, dict):
        return U
    tid = project.resolve_type(schema_type(value) or '', '')
    result = invoke(value, tid, 'toString')
    return result if isinstance(result, str) else U


def contains_unknown(value,active=None):
    if value is U:
        return True
    if not isinstance(value,(dict,list,tuple)):return False
    active=set() if active is None else active
    if id(value) in active:return True
    active.add(id(value))
    try:
        if isinstance(value,JsonText):return contains_unknown(value.payload,active)
        if isinstance(value,JavaMap):
            return value.mapping is U or any(contains_unknown(entry['key'],active) or contains_unknown(entry['value'],active) for entry in value.entries())
        if isinstance(value,JavaRecord):
            return any(key not in value or contains_unknown(value[key],active) for key in value.wire_fields)
        if isinstance(value,(JsonObject,JavaEnumValue)):return any(contains_unknown(child,active) for child in value.values())
        if isinstance(value,dict):
            return any(contains_unknown(v,active) for k,v in value.items() if not str(k).startswith('__') or k in ('__json__','__map__'))
        return any(contains_unknown(child,active) for child in value)
    finally:
        active.remove(id(value))


def entity_words(value):
    value = re.sub(r'(Controller|Service|Impl|Request|Response|Dto|Info|Entity|Input|View)$', '', value.split('.')[-1], flags=re.I)
    return set(ntoks(value)) - {'get', 'find', 'query', 'lookup', 'read', 'create', 'new', 'id', 'key'}


def objects(value, path):
    value=semantic_view(value)
    if isinstance(value,JavaMap):
        if isinstance(value.mapping,dict):
            for entry in value.entries():yield from objects(entry['value'],path+'['+repr(entry['key'])+']')
        return
    if isinstance(value, dict):
        if isinstance(schema_type(value), str) and schema_type(value):
            yield path, value
        for key, child in value.items():
            if isinstance(value,JsonObject) or isinstance(value,JavaRecord) and key in value.wire_fields or not str(key).startswith('__'):
                yield from objects(child, path + '.' + str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from objects(child, path + '[' + str(index) + ']')


def ordinal_for(action, requested):
    for candidate in re.finditer(r'\b(first|second|third|fourth)\b(?!-)', action, re.I):
        following = re.split(r'[,;()]|\b(?:for|with|without|on|of)\b', action[candidate.end():], 1, flags=re.I)[0]
        if requested & set(ntoks(following)[:4]):
            return candidate
    return None


def new_for(action, requested):
    for candidate in re.finditer(r'\b(?:(?:newly|just|recently)\s+(?:created|added|registered|booked)|new|latest)\b', action, re.I):
        following = re.split(r'[,;()]|\b(?:for|with|without|on|of)\b', action[candidate.end():], 1, flags=re.I)[0]
        if requested & set(ntoks(following)[:4]):
            return candidate
    return None


def cheapest_reference(action, history, by_step, observations):
    """Use the matching search and require a unique minimum in every price field."""
    if not re.search(r'\bcheapest\b', action, re.I):
        return None
    scopes = [index for index in by_step if re.search(r'\bcheapest\b', history[index].get('action', ''), re.I)]
    if not scopes:
        return None
    index = max(scopes)
    rows = [observations[index, identity] for identity in by_step[index]]
    if len(rows) == 1:
        return rows[0][:2]
    vectors = []
    for _, _, obj in rows:
        prices = {key: value for key, value in obj.items() if set(ntoks(key)) & {'price', 'cost'}}
        if not prices or any(isinstance(value, bool) or value is U or contains_unknown(value) for value in prices.values()):
            return None
        try:
            vector = {key: Decimal(str(value)) for key, value in prices.items()}
        except InvalidOperation:
            return None
        if not all(value.is_finite() for value in vector.values()):
            return None
        vectors.append(vector)
    if any(vector.keys() != vectors[0].keys() for vector in vectors):
        return None
    winners = [position for position, vector in enumerate(vectors)
               if all(all(vector[key] <= other[key] for key in vector) for other in vectors)]
    return rows[winners[0]][:2] if len(winners) == 1 else None


def request_entity(project,mid,field):
    requested=entity_words(field)
    if requested:return requested
    names={field,*(p['wire_name'] for p in project.http_parameters(mid) if p['name']==field)}
    owners={tuple(sorted(entity_words(route[i-1]))) for handler,_,route in project.ix.handlers if handler==mid
            for i,segment in enumerate(route) if i>0 and segment.strip('{}').split(':',1)[0] in names and not route[i-1].startswith('{')}
    return set(next(iter(owners))) if len(owners)==1 else entity_words(project.nodes[project.methods[mid]['owner']]['fqn'])


def enum_descriptors(project,tid,action):
    # The leading action verb is not an observed state adjective.
    description=re.sub(r'^\s*\w+\b','',action,count=1)
    words=set(ntoks(description));result=[]
    for name,info in project.type_fields.get(tid,{}).items():
        meta=project.nodes[tid];target=project.resolve_type(info['type'],meta['module'],info['file'])
        matches=[key.rsplit('.',1)[-1] for key in project.enum_members.get(target,[]) if set(ntoks(key.rsplit('.',1)[-1]))<=words]
        if len(matches)>1:return None
        if matches:result.append((name,matches[0]))
    if result and re.search(r'\b(?:not|without|non)\b',description,re.I):return None
    if len({expected for _,expected in result})!=len(result):return None
    return result


def related_selection_value(project,mid,field,action,history,ui_scope=None):
    if not re.search(r'\b(?:its|their|associated)\b',action,re.I):return None
    requested=request_entity(project,mid,field)
    if not requested:return None
    expected=dict(project.parameters(mid)).get(field)
    for index in range(len(history)-1,-1,-1):
        if ui_scope and history[index].get('ui_scope') and history[index]['ui_scope']!=ui_scope:continue
        candidates=[]
        for position,item in enumerate(history[index].get('selected_objects',[])):
            obj=item.get('object',{});tid=project.resolve_type(schema_type(obj),project.methods[mid]['module'])
            for name,info in project.type_fields.get(tid,{}).items():
                if not name.lower().endswith('id') or entity_words(name)!=requested:continue
                value=obj.get(name,U)
                source_base=info['type'].rsplit('.',1)[-1];target_base=(expected or '').rsplit('.',1)[-1]
                if value is U or value is None or contains_unknown(value) or source_base!=target_base:continue
                candidates.append(('history['+str(index)+'].selected_objects['+str(position)+'].object.'+name,value))
        unique={(type(value).__name__,repr(value)) for _,value in candidates}
        if candidates:return candidates[0] if len(unique)==1 else None
    return None


def history_value(project, mid, field, action, history, requested_entity=None, use_selection=True,ui_scope=None):
    """Only typed matching owners qualify. Multiple objects remain ambiguous."""
    norm = lambda value: re.sub(r'[^a-z0-9]', '', value.lower())
    requested = set(requested_entity) if requested_entity else entity_words(field[:-4] if field.endswith('Name') else field)
    if not requested:
        route_entities = set()
        names = {field, *(p['wire_name'] for p in project.http_parameters(mid) if p['name'] == field)}
        for handler, _, route in project.ix.handlers:
            if handler != mid:
                continue
            for index, segment in enumerate(route):
                if segment.strip('{}').split(':', 1)[0] in names and index > 0:
                    previous = route[index - 1]
                    if not previous.startswith('{'):
                        route_entities.add(tuple(sorted(entity_words(previous))))
        requested = set(next(iter(route_entities))) if len(route_entities) == 1 else entity_words(project.nodes[project.methods[mid]['owner']]['fqn'])
    candidates, by_step, creations, confirmed_creations, observations, first_seen = {}, {}, {}, {}, {}, {}
    collections = []
    for index, item in enumerate(history):
        if ui_scope and item.get('ui_scope') and item['ui_scope']!=ui_scope:continue
        from .history_refs import references,compatible_scope,object_scope
        saved_refs = item.get('response_refs')
        response_refs = saved_refs if isinstance(saved_refs,dict) and isinstance(saved_refs.get('collections'),list) else references(project, item, index)
        if item.get('result') is U and collections:
            entry=item.get('entry')
            meta=project.methods.get(entry,{}) if isinstance(entry,str) else {}
            declared=[entity_words(name) for name in re.findall(r'[\w.$]+',meta.get('return_raw',''))
                      if project.resolve_type(name,meta.get('module',''),meta.get('file')) in project.type_fields]
            if not meta or not declared or any(requested & owner for owner in declared):collections.append((index, []))
        observed = [*objects(item.get('result', U), 'history[' + str(index) + '].result'),
                    *objects(item.get('created_objects', []), 'history[' + str(index) + '].created_objects')]
        for path, obj in observed:
            owner = entity_words(schema_type(obj))
            deployment,fqn,tid = object_scope(project,item,obj)
            declared = project.type_fields.get(tid, {})
            ids = [k for k, meta in declared.items() if meta.get('id')]
            keys = [k for k in obj if norm(k) == norm(field)]
            named_reference = norm(field).endswith('id') and norm(field) != 'id' and any(k in declared for k in keys)
            if not named_reference and not compatible_scope(project,mid,requested,item,obj):continue
            if not named_reference and (not requested or not owner or not requested & owner):
                continue
            if norm(field) in ('key', 'id') and owner != requested:
                continue
            if not keys and owner == requested and (norm(field).endswith('id') or norm(field) in ('key', 'id')):
                keys = ids
            if not keys and owner == requested and field.endswith('Name') and 'name' in declared:
                from .nl_inputs import field_role, intermediate_field
                if field_role(field) is None and field != intermediate_field(project.request_fields(mid)):
                    keys = ['name']
            for key in keys:
                value = obj.get(key, U)
                if contains_unknown(value) or value is None:
                    continue
                rendered = source_string(project, value) if isinstance(value, dict) and '__symbol__' not in value else value
                canonical = rendered if rendered is not U else value
                identity = (deployment,fqn,repr(canonical))
                first_seen.setdefault(identity, index)
                candidates[identity] = (path + '.' + key, value, index)
                observations[index, identity] = (path + '.' + key, value, obj)
                by_step.setdefault(index, [])
                if identity not in by_step[index]:
                    by_step[index].append(identity)
                entry = item.get('entry')
                # A DTO value introduced by a create POST can flow without an
                # ORM resource. Managed records need the actual write journal.
                value_creation = (tid not in project.entities.values() and entry in project.methods
                                  and first_seen[identity] == index
                                  and isinstance(item.get('action', ''), str)
                                  and re.match(r'^(?:create|add|register|book|reserve|insert)\b', item.get('action', ''), re.I)
                                  and any(handler == entry and verb == 'POST' for handler, verb, _ in project.ix.handlers)
                                  and any(project.resolve_type(parameter['type'], project.methods[entry]['module'], project.methods[entry]['file']) == tid
                                          for parameter in project.http_parameters(entry) if parameter['kind'] == 'RequestBody'))
                if owner == requested and ('.created_objects' in path or value_creation):
                    creations.setdefault(identity, index)
                if owner == requested and '.created_objects' in path:
                    confirmed_creations[identity] = index
        for group in response_refs['collections']:
            if not isinstance(group,dict):continue
            if group.get('element_types') and not any(compatible_scope(project,mid,requested,item,declared_type=typ) for typ in group['element_types']):continue
            if group['element_types'] and not any(requested & entity_words(typ) for typ in group['element_types']):continue
            slots=[None]*group['size']
            for path,obj in observed:
                if path not in group['object_paths']:continue
                if not compatible_scope(project,mid,requested,item,obj):continue
                owner=entity_words(schema_type(obj))
                if not requested & owner:continue
                _,_,tid=object_scope(project,item,obj)
                declared=project.type_fields.get(tid,{})
                keys=[key for key in obj if norm(key)==norm(field)]
                if not keys and owner==requested:keys=[key for key,info in declared.items() if info.get('id')]
                position=re.fullmatch(r'\[(\d+)\]',path[len(group['response_path']):])
                if position and len(keys)==1:
                    key=keys[0];value=obj.get(key,U)
                    if value is not None and not contains_unknown(value):slots[int(position[1])]=(path+'.'+key,value)
            if group['element_types'] or any(slot is not None for slot in slots) or not group['size']:
                collections.append((index,[] if group.get('order_known') is False and group['size']>1 else slots))
    identities = list(candidates)
    described=False
    filtered=[]
    for identity in identities:
        latest=max(i for i,key in observations if key==identity)
        _,_,obj=observations[latest,identity]
        _,_,tid=object_scope(project,history[latest],obj)
        predicates=enum_descriptors(project,tid,action)
        if predicates is None:return None
        if predicates:
            described=True
            if any(name not in obj or contains_unknown(obj[name]) for name,_ in predicates):return None
            if all((obj.get(name).enum_name if isinstance(obj.get(name),JavaEnumValue) else obj.get(name))==expected for name,expected in predicates):filtered.append(identity)
    if described:identities=filtered
    ordinal = ordinal_for(action, requested)
    wants_new = new_for(action, requested)
    cheapest = cheapest_reference(action, history, by_step, observations) if not ordinal and not wants_new else None
    if cheapest:
        return cheapest
    if use_selection and not described and not ordinal and not wants_new and (norm(field).endswith('id') or norm(field) in ('key', 'id')):
        definite = any(requested <= set(ntoks(re.split(r'[,;()]|\b(?:for|with|without|on)\b', action[match.end():], 1, flags=re.I)[0])[:4])
                       for match in re.finditer(r'\b(?:the|this|same)\b', action, re.I))
        latest_creation = max(confirmed_creations.values(), default=-1) if definite else -1
        for index in range(len(history) - 1, -1, -1):
            if ui_scope and history[index].get('ui_scope') and history[index]['ui_scope']!=ui_scope:continue
            if index < latest_creation:
                break
            selected = history[index].get('selected_objects', [])
            for position, item in enumerate(selected if isinstance(selected, list) else []):
                if item.get('qualified_type') and not compatible_scope(project,mid,requested,
                    {'entry':item.get('producer_entry')},declared_type=item['qualified_type']):continue
                if item.get('entity') == sorted(requested) and item.get('value', U) is not U and not contains_unknown(item['value']):
                    return 'history[' + str(index) + '].selected_objects[' + str(position) + '].value', item['value']
        if definite and confirmed_creations:
            latest = max(confirmed_creations.values())
            created = [identity for identity, index in confirmed_creations.items() if index == latest]
            if len(created) == 1:
                return candidates[created[0]][:2]
    if wants_new:
        created = [key for key in identities if key in creations]
        if not created:
            return None
        newest = max(creations[key] for key in created)
        identities = sorted(created, key=lambda key: creations[key]) if ordinal else [key for key in created if creations[key] == newest]
    elif ordinal:
        # Use the latest collection's actual order, even after later single-object reads.
        if collections:
            latest, identities = collections[-1]
            if not identities:
                return None
            values = identities
            position = ('first', 'second', 'third', 'fourth').index(ordinal[1].lower())
            return values[position] if position < len(values) else None
    values = [candidates[key] for key in identities]
    if ordinal and values:
        ordered = values
        position = ('first', 'second', 'third', 'fourth').index(ordinal[1].lower())
        return ordered[position][:2] if position < len(ordered) else None
    if len(values) == 1:
        return values[0][:2]
    return None


def selected_field(project, field, params, history, mid=None,ui_scope=None):
    """A value from a selected object needs a matching identifier in this request."""
    owners = set()
    if mid is not None:
        meta = project.methods[mid]
        for parameter in project.http_parameters(mid):
            if parameter['kind'] != 'RequestBody':
                continue
            tid = project.resolve_type(parameter['type'], meta['module'], meta['file'])
            if field in project.type_fields.get(tid, {}):
                owners.add(tuple(sorted(entity_words(project.nodes[tid]['fqn']))))
    for index in range(len(history) - 1, -1, -1):
        if ui_scope and history[index].get('ui_scope') and history[index]['ui_scope']!=ui_scope:continue
        selected = history[index].get('selected_objects', [])
        for position, item in enumerate(selected if isinstance(selected, list) else []):
            obj = item.get('object', {})
            entity = set(item.get('entity', []))
            if mid is not None:
                from .history_refs import compatible_scope
                if not compatible_scope(project,mid,entity,{'entry':item.get('producer_entry')},obj):continue
            if mid is not None and not (tuple(sorted(entity)) in owners or entity and entity <= entity_words(field)):
                continue
            tid = project.resolve_type(schema_type(obj) or '', '') if isinstance(obj, dict) else None
            if field not in project.type_fields.get(tid, {}):
                continue
            linked = any(entity_words(key) == set(item.get('entity', [])) and value == item.get('value') for key, value in params.items())
            value = obj.get(field, U)
            if linked and value is not U and not contains_unknown(value):
                return 'history[' + str(index) + '].selected_objects[' + str(position) + '].object.' + field, value
    return None


def history_role_value(project, field, params, history):
    """Carry role values only from an object whose declared ID matches this request."""
    from .nl_inputs import field_role
    role = field_role(field)
    if role not in ('origin', 'destination', 'via') and field.lower() != 'date':
        return None
    identifiers = {key: value for key, value in params.items()
                   if key.lower().endswith('id') and value is not U and value is not None}
    if not identifiers:
        return None
    for index in range(len(history) - 1, -1, -1):
        previous = history[index].get('parameters', {})
        shared = identifiers.keys() & previous.keys()
        if shared and all(previous[key] == identifiers[key] for key in shared):
            values = [(key, value) for key, value in previous.items() if field_role(key) == role
                      and value is not None and value is not U and not contains_unknown(value)
                      and (field.lower() != 'date' or date_value(value) is not U)]
            if len({repr(value) for _, value in values}) == 1:
                return 'history[' + str(index) + '].parameters.' + values[0][0], values[0][1]
        matches = []
        for path, obj in objects(history[index].get('result', U), 'history[' + str(index) + '].result'):
            tid = project.resolve_type(schema_type(obj), '')
            declared = project.type_fields.get(tid, {})
            linked = False
            for key, expected in identifiers.items():
                keys = [key] if key in declared else [name for name, info in declared.items() if info.get('id')]
                if key not in declared and entity_words(key) != entity_words(schema_type(obj)):
                    keys = []
                value = obj.get(keys[0], U) if len(keys) == 1 else U
                if isinstance(value, dict) and '__symbol__' not in value:
                    value = source_string(project, value)
                if value is not U and value == expected:
                    linked = True
            if not linked:
                continue
            if field.lower() == 'date':
                filters = [(key, value) for key, value in previous.items() if field_role(key) == 'date'
                           and value is not None and value is not U and not contains_unknown(value) and date_value(value) is not U]
                if len({repr(value) for _, value in filters}) == 1:
                    return 'history[' + str(index) + '].parameters.' + filters[0][0], filters[0][1]
            for key in declared:
                value = obj.get(key, U)
                if field_role(key) == role and value is not U and value is not None and not contains_unknown(value):
                    matches.append((path + '.' + key, value))
        if matches:
            return matches[0] if len({repr(value) for _, value in matches}) == 1 else None
    return None
