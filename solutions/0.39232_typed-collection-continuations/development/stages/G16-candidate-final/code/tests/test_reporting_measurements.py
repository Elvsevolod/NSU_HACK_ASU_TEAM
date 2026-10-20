import json
import pytest
from analyzer.measurements import peak_rss
from analyzer.reporting import finite_report


@pytest.mark.parametrize('system,unit,expected',[
    ('darwin','bytes',120),('linux','KiB',122880),('linux2','KiB',122880),('unknown',None,None)])
def test_peak_memory_units(system,unit,expected):
    assert peak_rss(120,system)=={'peak_rss_raw':120,'peak_rss_raw_unit':unit,'peak_rss_bytes':expected}


def test_report_cycle_is_finite_without_changing_source_heap():
    parent={'id':1};child={'id':2,'parent':parent};parent['children']=[child]
    report={'arguments':[parent],'result':{'id':1}}
    value=finite_report(report)
    assert json.loads(json.dumps(value))['arguments'][0]['children'][0]['parent']=={'$cycle_ref':'$/arguments/0'}
    assert child['parent'] is parent and parent['children'][0] is child
    assert value['result'] is report['result']


def test_dag_alias_is_not_mislabeled_as_cycle():
    child={'id':2};report={'left':child,'right':child}
    assert finite_report(report) is report
    assert json.loads(json.dumps(finite_report(report)))=={'left':{'id':2},'right':{'id':2}}
