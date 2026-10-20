"""Option labels from a known HTML fragment in its source container context."""
import html5lib

HTML = '{http://www.w3.org/1999/xhtml}'


def html_text(node):
    """Element textContent excludes comment contents, but includes their tails."""
    parts = [node.text or '']
    for child in node:
        if isinstance(child.tag,str):
            parts.append(html_text(child))
        parts.append(child.tail or '')
    return ''.join(parts)


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
                raw = html_text(option)
                options.append({'control':control,'value':option.attrib['value'],'label':raw.strip(),
                                'raw_text':raw,'space':'dom'})
    diagnostics.extend('HTML fragment recovery: '+code for _,code,_ in parser.errors)
    return options, diagnostics


def document_options(source):
    """Literal single-select options; raw text belongs to the HTML5 tree."""
    parser = html5lib.HTMLParser(tree=html5lib.getTreeBuilder('etree'),strict=False)
    root = parser.parse(source,scripting=True)
    ids, output, diagnostics = {}, [], []
    for node in root.iter():
        if node.attrib.get('id'):
            ids[node.attrib['id']] = ids.get(node.attrib['id'],0)+1

    def visible(node, inert=False):
        inert = inert or node.tag in (HTML+'template',HTML+'noscript') or 'v-for' in node.attrib
        if inert or not isinstance(node.tag,str) or not node.tag.startswith(HTML):
            return
        if node.tag == HTML+'select':
            control = node.attrib.get('id')
            if (not control or ids.get(control) != 1 or 'multiple' in node.attrib
                    or 'disabled' in node.attrib or any(k.startswith(('v-',':','@')) for k in node.attrib)):
                if control:
                    diagnostics.append('Unsupported or ambiguous native select: #'+control)
                return
            for option in node.iter(HTML+'option'):
                if ('value' not in option.attrib or 'disabled' in option.attrib
                        or any(k.startswith(('v-',':','@')) for k in option.attrib)):
                    continue
                parent_disabled = any('disabled' in group.attrib and option in group.iter()
                                      for group in node.iter(HTML+'optgroup'))
                if parent_disabled:
                    continue
                raw = html_text(option)
                output.append({'control':control,'value':option.attrib['value'],'label':raw.strip(),
                               'raw_text':raw,'space':'dom'})
            return
        for child in node:
            visible(child,inert)
    visible(root)
    return output, diagnostics


def document_texts(source):
    """Initial textContent for unique static elements, excluding dynamic subtrees."""
    parser = html5lib.HTMLParser(tree=html5lib.getTreeBuilder('etree'),strict=False)
    root = parser.parse(source,scripting=True)
    ids, output = {}, {}
    for node in root.iter():
        if node.attrib.get('id'):
            ids[node.attrib['id']] = ids.get(node.attrib['id'],0)+1
    def dynamic(node):
        return (node.tag in (HTML+'template',HTML+'noscript',HTML+'script',HTML+'style')
                or 'contenteditable' in node.attrib
                or any(k.startswith(('v-',':','@')) for k in node.attrib))
    def visit(node, uncertain=False):
        if not isinstance(node.tag,str) or not node.tag.startswith(HTML):
            return
        uncertain = uncertain or dynamic(node)
        control = node.attrib.get('id')
        if control and ids[control] == 1 and not uncertain and '{{' not in html_text(node) and not any(dynamic(child) for child in node.iter()):
            output['#'+control] = html_text(node)
        for child in node:
            visit(child,uncertain)
    visit(root)
    return output
