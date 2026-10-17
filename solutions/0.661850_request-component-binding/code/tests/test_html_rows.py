from analyzer.html_rows import analyze_html_rows


def facts(source):
    return analyze_html_rows(source)['facts']


def test_html5_row_scope_uses_real_dom_foster_parenting():
    inside='<table><tr v-for="row in invoices"><td><button @click="open(row.id)">go</button></td></tr></table>'
    assert facts(inside)[0]['arguments']==[{'field':'id'}]
    outside=inside.replace('<td>','').replace('</td>','')
    got=analyze_html_rows(outside)
    assert got['facts']==[]
    assert any('outside row scope' in value for value in got['diagnostics'])


def test_unrelated_markup_and_identical_duplicate_do_not_erase_sound_source_facts():
    source='<div v-for="row in invoices"><button @click="open(row.id)" @click="open(row.id)">go</button></div></li>'
    got=analyze_html_rows(source)
    assert got['facts'][0]['handler']=='open'
    assert any('duplicate-attribute' in value for value in got['diagnostics'])
    different=source.replace('@click="open(row.id)" @click="open(row.id)"','@click="open(row.id)" @click="other(row.id)"')
    assert facts(different)==[]


def test_bad_element_does_not_drop_its_valid_sibling():
    source='''<div v-for="row in invoices">
      <button @click="wrong(row.id)" @click="other(row.id)">bad</button>
      <button @click="open(row.id)">good</button></div>'''
    assert [r['handler'] for r in facts(source)]==['open']


def test_index_deep_fields_and_nested_loop_shadowing():
    source='''<div v-for="(row,i) in invoices"><button @click="open(i,row.client.id,row)">go</button>
      <div v-for="row in external()"><button @click="bad(row.id)">bad</button></div>
      <div v-for="(other,j) in others"><button @click="bad(i,other.id)">bad</button></div>
      <button @click="again(row.id)">go</button></div>'''
    got=facts(source)
    assert [r['handler'] for r in got]==['open','again']
    assert got[0]['arguments']==[{'index':True},{'field':'client.id'},{'object':True}]


def test_multiline_start_tag_has_start_line_and_ambiguous_event_uses_loop_line():
    source='''<div v-for="row in invoices">
      <button
       @click="open(row.id)">go</button>
      <button @click="other(row.id)">go</button>
      <button @click="other(row.id)">go</button></div>'''
    got=facts(source)
    assert got[0]['source_line']==2
    assert got[1]['source_line']==1 and got[1]['source_line_kind']=='loop'
    assert len(got)==2


def test_duplicate_loops_and_empty_loop_never_get_guessed_sources():
    source='<div v-for="row in invoices"><button @click="open(row.id)">go</button></div>'
    assert facts(source+source)==[]
    for inner in ('v-for','v-for=""'):
        assert facts('<div v-for="row in invoices"><span '+inner+'><button @click="open(row.id)">bad</button></span></div>')==[]


def test_raw_text_and_foreign_content_are_not_row_events():
    source='''<script>var text='<div v-for="row in invoices"><button @click="open(row.id)">go</button></div>';</script>
      <textarea><div v-for="row in invoices"><button @click="open(row.id)">go</button></div></textarea>
      <svg v-for="row in invoices"><g @click="open(row.id)"></g></svg>'''
    assert facts(source)==[]


def test_optional_html_end_tags_use_browser_scope():
    source='''<ul><li v-for="row in invoices"><button @click="open(row.id)">go</button>
      <li><button @click="bad(row.id)">outside</button></ul>'''
    assert [r['handler'] for r in facts(source)]==['open']


def test_multistatement_or_computed_call_does_not_gain_a_row_scope():
    for event in ('open(row.id)); evil(); (null','open(row["id"])','open(row?.id)','open(row.id),evil()'):
        source="<div v-for='row in invoices'><button @click='"+event+"'>go</button></div>"
        assert facts(source)==[]
