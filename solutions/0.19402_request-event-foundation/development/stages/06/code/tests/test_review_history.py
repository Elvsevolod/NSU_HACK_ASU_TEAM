from analyzer.history_refs import references
from analyzer.provenance import history_value
from analyzer.state import U
from builders import build
import json
from analyzer.project import Project


SOURCE = '''class Invoice { @Id String id; } class Api {
  @GetMapping("/invoices") java.util.List<Invoice> list(){return null;}
  @GetMapping("/invoices/{invoiceId}") String show(@PathVariable String invoiceId){return invoiceId;}
}'''


def test_singleton_is_the_latest_collection(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': SOURCE})
    history = [{'entry': ids['Api.list'], 'result': [{'__type__': 'Invoice', 'id': 'A'}, {'__type__': 'Invoice', 'id': 'B'}]},
               {'entry': ids['Api.list'], 'result': [{'__type__': 'Invoice', 'id': 'C'}]}]
    assert history_value(project, ids['Api.show'], 'invoiceId', 'Open first invoice', history)[1] == 'C'


def test_empty_collection_blocks_stale_ordinal(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': SOURCE})
    history = [{'entry': ids['Api.list'], 'result': [{'__type__': 'Invoice', 'id': 'A'}, {'__type__': 'Invoice', 'id': 'B'}]},
               {'entry': ids['Api.list'], 'result': []}]
    assert history_value(project, ids['Api.show'], 'invoiceId', 'Open first invoice', history) is None


def test_later_read_does_not_replace_collection_order(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': SOURCE})
    history = [{'result': [{'__type__': 'Invoice', 'id': 'B'}, {'__type__': 'Invoice', 'id': 'A'}]},
               {'result': {'__type__': 'Invoice', 'id': 'A'}}]
    ref = history_value(project, ids['Api.show'], 'invoiceId', 'Open first invoice', history)
    assert ref == ('history[0].result[0].id', 'B')


def test_empty_wrapper_records_producer_and_element_schema(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': SOURCE})
    item = {'entry': ids['Api.list'], 'step': 2, 'result': {'data': []}}
    ref = references(project, item, 1)['collections'][0]
    assert ref['element_types'] == ('Invoice',)
    assert ref['size'] == 0 and ref['complete'] is True
    assert ref['producer'] == '2:' + ids['Api.list']


def test_unknown_producer_and_result_after_path_join_do_not_reuse_old_collection(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': SOURCE})
    history = [{'result': [{'__type__': 'Invoice', 'id': 'A'}]},
               {'entry': U, 'result': U, 'action': U, 'step': 2}]
    assert references(project, history[-1], 1)['objects'] == []
    assert history_value(project, ids['Api.show'], 'invoiceId', 'Open first invoice', history) is None


def test_same_simple_type_and_id_in_two_deployments_remain_separate(tmp_path):
    nodes,edges,ids={},[],{}
    for module in ('billing','library'):
        project,_,local=build(tmp_path/module,{'Api.java':('package '+module+';\n'+SOURCE).replace('@Id String id;','@Id String id;public String title;')},module=module)
        for key,node in project.nodes.items():
            node=dict(node)
            if node.get('file'):node['file']=module+'/'+node['file']
            if node.get('kind')=='type':node['fqn']=module+'.'+node['fqn']
            nodes[key]=node
        edges.extend(project.skeleton['edges']);ids[module]=local
    path=tmp_path/'skeleton.json'
    path.write_text(json.dumps({'nodes':nodes,'edges':edges,'project':'two-services'}))
    project=Project(path,tmp_path)
    history=[{'entry':ids['billing']['Api.list'],'result':[{'__type__':'billing.Invoice','id':'1','title':'Bill'}]},
             {'entry':ids['library']['Api.list'],'result':[{'__type__':'library.Invoice','id':'2','title':'Book'}]}]
    assert history_value(project,ids['billing']['Api.show'],'invoiceId','Open first invoice',history)[1]=='1'
    assert history_value(project,ids['library']['Api.show'],'invoiceId','Open first invoice',history)[1]=='2'
    history[1]['result']=[]
    assert history_value(project,ids['billing']['Api.show'],'invoiceId','Open first invoice',history)[1]=='1'
    assert history_value(project,ids['library']['Api.show'],'invoiceId','Open first invoice',history) is None


def test_nested_empty_child_collection_does_not_erase_parent_order(tmp_path):
    source=SOURCE.replace('@Id String id;','@Id String id;java.util.List<Child> children;')+'class Child{@Id String id;}'
    project,_,ids=build(tmp_path,{'Api.java':source})
    history=[{'entry':ids['Api.list'],'result':[{'__type__':'Invoice','id':'A','children':[]},{'__type__':'Invoice','id':'B','children':[]}]}]
    assert history_value(project,ids['Api.show'],'invoiceId','Open first invoice',history)[1]=='A'
    groups=references(project,history[0],0)['collections']
    assert groups[1]['element_types']==('Child',)
