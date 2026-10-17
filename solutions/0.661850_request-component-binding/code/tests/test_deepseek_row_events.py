"""Row/click source facts: accepted subset and conservative counterexamples."""

from analyzer.row_events import row_events


def _line(html, needle):
    return next(number for number, line in enumerate(html.splitlines(), 1) if needle in line)


def test_loop_click_returns_fields_literals_and_line():
    html = (
        '<table>\n'
        '  <tr v-for="(item,index) in myRows">\n'
        '    <button v-on:click="edit(item.id,item.name,7,\'x\')">go</button>\n'
        '  </tr>\n'
        '</table>\n'
    )
    assert row_events(html) == [
        {'collection': 'myRows', 'row': 'item', 'handler': 'edit',
         'arguments': [{'field': 'id'}, {'field': 'name'}, {'literal': 7}, {'literal': 'x'}],
         'source_line': _line(html, 'v-on:click')}]

    same_node = '<tr v-for="(row, i) in myRows" @click="open(row.id)"><td>x</td></tr>'
    assert row_events(same_node) == [
        {'collection': 'myRows', 'row': 'row', 'handler': 'open',
         'arguments': [{'field': 'id'}], 'source_line': 1}]


def test_independent_tables_nearest_binding_and_outside_sibling():
    html = (
        '<table>\n'
        '  <tr v-for="(item, i) in orders"><td><button @click="open(item.id)">a</button></td></tr>\n'
        '</table>\n'
        '<table>\n'
        '  <tr v-for="(item, i) in products"><td><button @click="pick(item.sku)">b</button></td></tr>\n'
        '</table>\n'
        '<div><button @click="open(item.id)">outside</button></div>\n'
    )
    first = row_events(html)
    assert [(f['collection'], f['row'], f['handler'], f['arguments']) for f in first] == [
        ('orders', 'item', 'open', [{'field': 'id'}]),
        ('products', 'item', 'pick', [{'field': 'sku'}])]
    assert row_events(html) == first


def test_nested_loops_outer_alias_and_shadowed_unsupported_loop():
    html = (
        '<div v-for="(group, gi) in groups">\n'
        '  <div v-for="(member, mi) in members">\n'
        '    <button @click="pick(member.id)">member</button>\n'
        '    <button @click="pick(group.id)">group</button>\n'
        '    <button @click="pick(group.id, member.id)">mixed</button>\n'
        '  </div>\n'
        '  <div v-for="item in item.children">\n'
        '    <button @click="pick(item.id)">shadowed</button>\n'
        '  </div>\n'
        '  <button @click="pick(group.id)">visible</button>\n'
        '</div>\n'
    )
    assert [(f['collection'], f['row'], f['handler']) for f in row_events(html)] == [
        ('members', 'member', 'pick'),
        ('groups', 'group', 'pick'),
        ('groups', 'group', 'pick')]


def test_computed_or_ambiguous_handlers_and_arguments_are_omitted():
    html = (
        '<div v-for="(item, i) in rows">\n'
        '  <button @click="pick(item.id + 1)">a</button>\n'
        '  <button @click="pick(item[\'id\'])">b</button>\n'
        '  <button @click="pick(item.address.city)">c</button>\n'
        '  <button @click="pick(index)">d</button>\n'
        '  <button @click="pick(other.id)">e</button>\n'
        '  <button @click="pick">f</button>\n'
        '  <button @click="store.pick(item.id)">g</button>\n'
        '  <button @click="pick(...item.tags)">h</button>\n'
        '  <button @click="pick(item.id">i</button>\n'
        '</div>\n'
        '<div v-for="(row, j) in rows.filter(visible)"><button @click="pick(row.id)">k</button></div>\n'
    )
    assert row_events(html) == []


def test_string_escapes_entities_and_non_finite_numbers():
    html = (
        '<div v-for="(item, i) in rows">\n'
        '  <button @click=\'mark(item.id,"a\\"b\\u0041")\'>a</button>\n'
        '  <button @click="mark(item.id, &quot;q&quot;, true, false, null, 2.5)">b</button>\n'
        '  <button @click="mark(item.id, \'\\z\')">c</button>\n'
        '  <button @click="mark(item.id, 1e999)">d</button>\n'
        '</div>\n'
    )
    assert [f['arguments'] for f in row_events(html)] == [
        [{'field': 'id'}, {'literal': 'a"bA'}],
        [{'field': 'id'}, {'literal': 'q'}, {'literal': True}, {'literal': False},
         {'literal': None}, {'literal': 2.5}]]


def test_void_tags_never_enter_scope_and_mismatched_end_tags_reject_all():
    okay = (
        '<div v-for="(item, i) in rows">\n'
        '  <input @click="pick(item.id)" />\n'
        '  <br>\n'
        '  <button @click="hit(item.code)">x</button>\n'
        '</div>\n'
    )
    assert [(f['handler'], f['arguments']) for f in row_events(okay)] == [
        ('pick', [{'field': 'id'}]), ('hit', [{'field': 'code'}])]

    stray = '<div v-for="(item, i) in rows"><button @click="pick(item.id)">x</button></div></span>'
    assert row_events(stray) == []

    crossed = ('<div v-for="(item, i) in rows"><span>'
               '<button @click="pick(item.id)">x</button></div></span>')
    assert row_events(crossed) == []
