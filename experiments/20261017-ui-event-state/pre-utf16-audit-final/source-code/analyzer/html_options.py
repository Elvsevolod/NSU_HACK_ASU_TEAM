"""Option labels from a known HTML fragment in its source container context."""
import html5lib

HTML = '{http://www.w3.org/1999/xhtml}'


def fragment_options(source, container):
    parser = html5lib.HTMLParser(tree=html5lib.getTreeBuilder('etree'),strict=False)
    root = parser.parseFragment(source,container=container,scripting=True)
    options, ids, diagnostics = [], {}, []
    for node in root.iter():
        if node.attrib.get('id'):
            ids[node.attrib['id']] = ids.get(node.attrib['id'],0)+1
    def visible(node):
        if node.tag == HTML+'template' or any(key.startswith(('v-',':','@')) for key in node.attrib):
            return
        yield node
        for child in node:
            yield from visible(child)
    for select in (node for node in visible(root) if node.tag == HTML+'select'):
        control = select.attrib.get('id')
        if not control or ids.get(control) != 1:
            diagnostics.append('Ambiguous fragment select identity')
            continue
        for option in select.iter(HTML+'option'):
            if 'value' in option.attrib and not any(key.startswith(('v-',':','@')) for key in option.attrib):
                label = ''.join(option.itertext()).strip()
                options.append({'control':control,'value':option.attrib['value'],'label':label,'space':'dom'})
    diagnostics.extend('HTML fragment recovery: '+code for _,code,_ in parser.errors)
    return options, diagnostics
