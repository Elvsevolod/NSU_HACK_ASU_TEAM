import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from analyzer.models import wire,construct,library
from builders import build


def run_http(tmp_path,setup,conservative=False):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import org.springframework.web.client.RestTemplate;
      class Server{@GetMapping("/values") Collection<String> values(){'''+setup+'''return map.values();}}
      class Client{RestTemplate rest;Object entry(){List data=rest.getForObject("http://service/values",List.class);
      return data.size()==0?"empty":data.get(0);}}'''})
    engine=Engine(project,ScenarioState(db),conservative=conservative);return engine.run(ids['Client.entry'],{}),engine


@pytest.mark.parametrize('setup,expected',[
 ('Map map=new HashMap();','empty'),
 ('Map map=new HashMap();map.put("key","value");','value'),
 ('Map map=new LinkedHashMap();map.put("first","left");map.put("second","right");','left'),
])
def test_http_view_is_a_json_array_with_only_proven_order(tmp_path,setup,expected):
    result,engine=run_http(tmp_path,setup)
    assert result==expected


def test_http_unordered_view_does_not_choose_a_python_first_element(tmp_path):
    result,engine=run_http(tmp_path,'Map map=new HashMap();map.put("first","left");map.put("second","right");',conservative=True)
    assert result is U and engine.approximate
    assert any('Map view element order' in warning for warning in engine.warnings)


def test_map_entry_json_shape_is_unknown_without_codec_version_evidence():
    _,mapping=construct('HashMap',[],U);library('put',mapping,['key','value'],'map',U)
    _,view=library('entrySet',mapping,[],'map',U)
    _,iterator=library('iterator',view,[],'view',U)
    _,entry=library('next',iterator,[],'iterator',U)
    warnings=[]
    assert wire(entry,warnings.append) is U
    assert warnings and 'codec and version' in warnings[0]


def test_a_view_cycle_is_detected_at_json_conversion():
    _,mapping=construct('HashMap',[],U)
    _,view=library('values',mapping,[],'map',U)
    library('put',mapping,['self',view],'map',U)
    from analyzer.java_exceptions import JavaThrow
    with pytest.raises(JavaThrow):wire(view)
