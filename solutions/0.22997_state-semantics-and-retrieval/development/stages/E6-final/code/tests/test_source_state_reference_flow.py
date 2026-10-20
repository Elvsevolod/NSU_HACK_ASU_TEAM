from analyzer.provenance import history_value,related_selection_value
from analyzer.selection import selected_objects
from analyzer.java_collections import JsonObject
from analyzer.native_storage import JavaList
from analyzer.state import U
from builders import build


def profile(tmp_path):
    return build(tmp_path,{'Api.java':'''enum Phase{READY,ARCHIVED,LOANED}
      record ItemResponse(Long id,Long groupId,Phase phase){}
      class ItemController{@PatchMapping("/items/{id}/archive") ItemResponse archive(@PathVariable Long id){return null;}}
      class GroupController{@GetMapping("/groups/{id}")String get(@PathVariable Long id){return "ok";}}'''})


def item(i,phase='READY',group=90):return JsonObject({'id':i,'groupId':group,'phase':phase},'ItemResponse')


def test_state_descriptor_is_source_enum_and_verb_is_not_a_state(tmp_path):
    p,_,ids=profile(tmp_path);h=[{'entry':ids['ItemController.archive'],'result':[item(4),item(8,'LOANED')]}]
    assert history_value(p,ids['ItemController.archive'],'id','Archive the ready item',h)==('history[0].result[0].id',4)
    assert history_value(p,ids['ItemController.archive'],'id','Archive the item',h) is None
    assert history_value(p,ids['ItemController.archive'],'id','Archive the not ready item',h) is None


def test_unknown_or_duplicate_state_match_does_not_prove_a_unique_object(tmp_path):
    p,_,ids=profile(tmp_path)
    for rows in ([item(4),item(8)],[item(4),item(8,U)]):
        h=[{'entry':ids['ItemController.archive'],'result':rows}]
        assert history_value(p,ids['ItemController.archive'],'id','Archive the ready item',h) is None


def test_latest_observation_cancels_stale_state_and_same_keeps_typed_focus(tmp_path):
    p,_,ids=profile(tmp_path);entry=ids['ItemController.archive']
    h=[{'entry':entry,'result':[item(4),item(8,'LOANED')]},{'entry':entry,'result':item(4,'ARCHIVED')}]
    assert history_value(p,entry,'id','Archive the ready item',h) is None
    selected=selected_objects(p,entry,'Archive the ready item',h,{'id':4})
    assert len(selected)==1 and selected[0]['object']['phase']=='ARCHIVED'
    h[-1]['selected_objects']=selected
    assert history_value(p,entry,'id','Archive the same item again',h)[1]==4
    assert related_selection_value(p,ids['GroupController.get'],'id','Read its group',h)[1]==90


def test_related_value_requires_selected_owner_and_declared_property(tmp_path):
    p,_,ids=profile(tmp_path);entry=ids['ItemController.archive']
    h=[{'entry':entry,'result':item(4)}]
    assert related_selection_value(p,ids['GroupController.get'],'id','Read its group',h) is None


def test_unspecified_collection_order_cannot_supply_first(tmp_path):
    p,_,ids=profile(tmp_path);rows=JavaList([item(4),item(8)]);rows.order_known=False
    h=[{'entry':ids['ItemController.archive'],'result':rows}]
    assert history_value(p,ids['ItemController.archive'],'id','Read the first item',h) is None
