"""Checker-owned experiment key controls; the production scheduler is unchanged."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'checks'))
from residual_state_pilot import prepare,key_for
from analyzer.native_storage import JavaList


@pytest.mark.parametrize('change',[
    'actor','database_revision','clock','pending_write','completion','source',
    'remaining','native_kind','order','external_alias','bean_alias',
])
def test_semantic_inputs_cannot_share_residual_key(tmp_path,change):
    p,state,ids,digest=prepare(tmp_path)
    other=deepcopy(state);remaining=('L','M','R');completion='normal';other_digest=digest
    a_external=b_external=()
    cache=next(value for value in other.bean_instances.values() if getattr(value,'java_type',None)=='Cache')
    if change=='actor':other.browser['actor']='another-actor'
    if change=='database_revision':other.database.tables[('service','control')][0]['revision']=2
    if change=='clock':other.now+=timedelta(seconds=1)
    if change=='pending_write':other.transactions['unit']={'pending':[{'operation':'save'}]}
    if change=='completion':completion='throw'
    if change=='source':other_digest='other-source'
    if change=='remaining':remaining=('L','M')
    if change=='native_kind':cache['values'].kinds[0]='Long'
    if change=='order':cache['values'].order_known=True
    if change=='external_alias':
        original_cache=next(value for value in state.bean_instances.values() if getattr(value,'java_type',None)=='Cache')
        a_external=(original_cache['values'],)
        b_external=(JavaList(cache['values'],cache['values'].kinds),)
    if change=='bean_alias':
        original_cache=next(value for value in state.bean_instances.values() if getattr(value,'java_type',None)=='Cache')
        original_cache['alias']=original_cache['values']
        cache['alias']=deepcopy(cache['values'])
    a=key_for(state,('L','M','R'),digest,external_roots=a_external)
    b=key_for(other,remaining,other_digest,completion,external_roots=b_external)
    assert a is not None and b is not None and a!=b
