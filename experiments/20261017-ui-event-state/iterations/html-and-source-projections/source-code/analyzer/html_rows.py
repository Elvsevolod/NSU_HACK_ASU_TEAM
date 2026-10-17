"""Row argument facts from HTML5 DOM structure, with separate source locations.

Only .html/.htm in-DOM Vue templates are supported. No scripts are evaluated.
The lexical pass locates source evidence; it never supplies the binding scope.
"""
from html.parser import HTMLParser
import json
import html5lib
from .row_events import _VFOR, _IDENTIFIER, _loop_scope, _KEYWORD_COLLECTIONS
from .row_arguments import decode_row_event


HTML = '{http://www.w3.org/1999/xhtml}'
VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
SEMANTIC = {'v-for','@click','v-on:click'}


def signature(tag, attrs):
    return tag, tuple(sorted(attrs.items()))


class Locations(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.records, self.frames = [], []
        self.by_signature = {}

    def handle_starttag(self, tag, attrs):
        first, duplicates, conflicts = {}, set(), set()
        for key, value in attrs:
            value = value if value is not None else ''
            if key in first:
                duplicates.add(key)
                if value != first[key]:
                    conflicts.add(key)
            else:
                first[key] = value
        uid = len(self.records)
        loops = tuple(i for _, i in self.frames if i is not None)
        if 'v-for' in first:
            loops += (uid,)
        record = {'uid':uid,'tag':tag,'attrs':first,'line':self.getpos()[0],
                  'loops':loops,'duplicates':duplicates,'conflicts':conflicts}
        self.records.append(record)
        self.by_signature.setdefault(signature(tag,first),[]).append(record)
        if tag not in VOID:
            self.frames.append((tag,uid if 'v-for' in first else None))

    def handle_endtag(self, tag):
        for position in range(len(self.frames)-1,-1,-1):
            if self.frames[position][0] == tag:
                del self.frames[position:]
                break


def analyze_html_rows(source):
    locations = Locations()
    locations.feed(source)
    locations.close()
    parser = html5lib.HTMLParser(tree=html5lib.getTreeBuilder('etree'),strict=False)
    root = parser.parse(source)
    diagnostics = ['HTML5 recovery at ' + str(position[0]) + ':' + str(position[1]) + ': ' + code
                   for position,code,_ in parser.errors if code != 'expected-doctype-but-got-start-tag']
    facts, seen, counter, editable = [], set(), 0, set()

    def visit(node, scopes, loop_records, guards, depth=0):
        nonlocal counter
        if depth > 256:
            diagnostics.append('HTML row scope depth budget exceeded')
            return
        if not isinstance(node.tag,str) or not node.tag.startswith(HTML):
            return
        tag, attrs = node.tag[len(HTML):], dict(node.attrib)
        if tag in ('input','textarea','select'):
            editable.update(value for key,value in attrs.items() if key == 'v-model' or key.startswith('v-model.'))
        if tag == 'template':
            if any('v-for' in n.attrib for n in node.iter()):
                diagnostics.append('Unsupported template-content row scope')
            return
        records = locations.by_signature.get(signature(tag,attrs),[])
        if 'v-for' in attrs:
            scopes = dict(scopes)
            matches = [record for record in records if 'v-for' in record['attrs']]
            proven = len(matches) == 1 and not matches[0]['conflicts'] & SEMANTIC
            if proven and loop_records and loop_records[-1]['uid'] not in matches[0]['loops']:
                proven = False
            shape = _VFOR.match(attrs['v-for'])
            if proven and shape:
                row, index = shape[1] or shape[3], shape[2]
                collection = shape[4]
                if (_IDENTIFIER.fullmatch(collection) and collection not in _KEYWORD_COLLECTIONS
                        and row != index):
                    counter += 1
                    binding = {'kind':'row','scope':counter,'collection':collection,'row':row}
                    scopes[row] = binding
                    if index:
                        scopes[index] = {**binding,'kind':'index'}
                else:
                    scopes.update({key:None for key in _loop_scope(attrs['v-for'])})
                loop_records = [*loop_records,matches[0]]
            else:
                aliases = _loop_scope(attrs['v-for'])
                scopes.update({key:None for key in aliases or scopes})
                diagnostics.append('Unproven or unsupported row loop source: ' + attrs['v-for'])
        if 'v-else' in attrs or 'v-else-if' in attrs:
            scopes = {key:None for key in scopes}
            diagnostics.append('Unsupported alternative Vue branch for row source')
        guards = [*guards,*(attrs[key] for key in ('v-if','v-show') if key in attrs)]
        clicks = [attrs[key] for key in ('@click','v-on:click') if key in attrs]
        if len(clicks) == 1:
            fact = decode_row_event(clicks[0],scopes)
            if fact is not None:
                candidates = [record for record in records if not record['conflicts'] & SEMANTIC
                              and loop_records and loop_records[-1]['uid'] in record['loops']]
                if not candidates:
                    diagnostics.append('DOM and lexical row scope disagree for ' + clicks[0])
                else:
                    fact = dict(fact)
                    if len(candidates) == 1:
                        fact['source_line'] = candidates[0]['line']
                    else:
                        fact['source_line'] = loop_records[-1]['line']
                        fact['source_line_kind'] = 'loop'
                        diagnostics.append('Ambiguous event line; using proven loop line for ' + clicks[0])
                    if guards:
                        fact['guards'] = guards
                    key = json.dumps(fact,sort_keys=True)
                    if key not in seen:
                        seen.add(key);facts.append(fact)
            elif scopes:
                diagnostics.append('Unsupported row event arguments or scope: ' + clicks[0])
            elif any(record['loops'] for record in records):
                diagnostics.append('Event moved outside row scope by HTML5 tree construction: ' + clicks[0])
        elif len(clicks) > 1 and scopes:
            diagnostics.append('Multiple Vue click directives on one element are unsupported')
        for child in node:
            visit(child,scopes,loop_records,guards,depth+1)

    visit(root,{},[],[])
    return {'facts':facts,'diagnostics':list(dict.fromkeys(diagnostics)), 'editable_models':sorted(editable)}
