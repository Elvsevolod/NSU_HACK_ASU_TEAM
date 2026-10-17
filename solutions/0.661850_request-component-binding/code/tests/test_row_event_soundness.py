from analyzer.row_events import row_events


def test_multiple_statements_cannot_be_reduced_to_a_pure_first_call():
    html='<div v-for="row in rows"><button @click="pick(row.id)); evil(); (null">go</button></div>'
    assert row_events(html)==[]


def test_unclosed_markup_and_empty_inner_loop_do_not_leak_scope():
    assert row_events('<div v-for="row in rows"><button @click="pick(row.id)">go</button>')==[]
    for loop in ('v-for','v-for=""'):
        assert row_events('<div v-for="row in rows"><span '+loop+'><button @click="pick(row.id)">go</button></span></div>')==[]


def test_duplicate_attributes_and_unsafe_integer_are_not_proven():
    assert row_events('<div v-for="row in rows" v-for="row in others"><button @click="pick(row.id)">go</button></div>')==[]
    assert row_events('<div v-for="row in rows"><button @click="pick(row.id,0x20000000000001)">go</button></div>')==[]
