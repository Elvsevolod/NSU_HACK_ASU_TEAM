from copy import deepcopy
import pytest
from analyzer.history_agreement import agree_completed
from analyzer.history_join import common_wire_bag
from analyzer.java_collections import JsonObject
from analyzer.paths import join_states,run_paths
from analyzer.state import ScenarioState,U
from builders import build


def row(value,complete=True,outcome='returned'):
    return {'result':value,'selected_objects':[],'outcome':outcome,'exploration':{'complete':complete}}


def test_same_typed_id_in_every_complete_alternative_is_agreement():
    result=agree_completed([row({'id':7,'kind':'Long'}),row({'id':7,'kind':'Long'})],lambda a:a['result'])
    assert result['value']=={'id':7,'kind':'Long'} and result['alternatives']==2


@pytest.mark.parametrize('other',[
    row({'id':8,'kind':'Long'}),row({'id':True,'kind':'Boolean'}),row({'id':7,'kind':'Integer'}),
    row({'id':7,'kind':'Long'},False),row({'id':7,'kind':'Long'},outcome='HTTP error response'),
    row({'id':U,'kind':'Long'}),row(None)])
def test_different_unknown_failed_or_incomplete_producer_is_not_agreement(other):
    assert agree_completed([row({'id':7,'kind':'Long'}),other],lambda a:a['result']) is None


def test_wire_multiset_keeps_rows_and_refuses_ordinal_order():
    a=JsonObject({'id':7,'status':'READY'},'Equipment');b=JsonObject({'id':9,'status':'WAITING'},'Equipment')
    bag=common_wire_bag([[a,b],[deepcopy(b),deepcopy(a)]])
    assert {item['id'] for item in bag}=={7,9} and bag.order_known is False
    assert all(item['status']==('READY' if item['id']==7 else 'WAITING') for item in bag)


def test_unknown_values_type_collision_or_internal_alias_prevent_bag_join():
    assert common_wire_bag([[{'id':1}],[{'id':True}]]) is None
    assert common_wire_bag([[{'id':U}],[{'id':U}]]) is None
    a=JsonObject({'id':1},'A');b=JsonObject({'id':1},'B')
    assert common_wire_bag([[a],[b]]) is None
    assert common_wire_bag([[a,a],[deepcopy(a),deepcopy(a)]]) is None


def test_joined_complete_history_rebuilds_refs_without_mixing_row_fields(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'class Api{int entry(){return 1;}}'})
    a=ScenarioState(db);b=ScenarioState(db)
    x=JsonObject({'id':7,'status':'READY'},'Equipment');y=JsonObject({'id':9,'status':'WAITING'},'Equipment')
    a.history=[{**row([x,y]),'response_refs':{'collections':[]}}]
    b.history=[{**row([deepcopy(y),deepcopy(x)]),'response_refs':{'collections':[]}}]
    joined=join_states([a,b]);item=joined.history[0]
    assert {obj['id'] for obj in item['result']}=={7,9} and item['result'].order_known is False
    assert 'response_refs' not in item


def test_coverage_flag_does_not_claim_a_budget_boundary_is_complete(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{Object entry(boolean x,boolean y,boolean z){if(x)return 1;if(y)return 2;if(z)return 3;return 4;}}'''})
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{'x':U,'y':U,'z':U},limit=1)
    assert paths and all(path['exploration']['complete'] is False for path in paths)
