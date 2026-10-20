from copy import deepcopy
import json
from analyzer.engine import Engine
from analyzer.project import Project
from analyzer.state import ScenarioState
from analyzer.native_storage import JavaList,ReadOnlyList
from builders import build


def test_unmodifiable_list_is_a_view_and_rejects_source_mutations(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{
      int entry(){List<Integer> original=new ArrayList<>();List<Integer> view=Collections.unmodifiableList(original);
        original.add(7);try{view.set(0,8);}catch(UnsupportedOperationException e){return view.get(0);}return -1;}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==7
    backing=JavaList([1]);view=ReadOnlyList(backing)
    cloned=deepcopy({'backing':backing,'view':view})
    cloned['backing'].append(2)
    assert list(cloned['view'])==[1,2] and list(view)==[1]


def test_opaque_client_contract_is_not_a_server_route(tmp_path):
    project,_,ids=build(tmp_path,{'Api.java':'''@FeignClient(name="remote") interface Client{
      @PostMapping("/items") void create(String value);}
      class Api{@GetMapping("/items") String list(){return "ok";}}'''})
    assert {mid for mid,_,_ in project.ix.handlers}=={ids['Api.list']}
    assert {mid for mid,_,_ in project.client_routes}=={ids['Client.create']}


def test_lazy_collection_loads_on_use_and_keeps_repository_origin(tmp_path):
    source='''import java.util.*;class Api{Store store;
      Object read(){return store.findById("x").get().flags;}
      int entry(){List<String> values=(List<String>)read();return values.size();}}
      @Entity @Table(name="items") class Item{@Id String id;
        @ElementCollection @CollectionTable(name="flags",joinColumns=@JoinColumn(name="item_id"))
        @Column(name="flag") List<String> flags;}
      interface Store extends JpaRepository<Item,String>{}'''
    project,db,ids=build(tmp_path,{'Api.java':source},rows={'items':[{'id':'x'}],'flags':[{'item_id':'x','flag':'enabled'}]})
    skeleton=project.skeleton
    rid='res:table:service.flags'
    skeleton['nodes'][rid]={'kind':'data_resource','resource_kind':'table','schema':'service','name':'flags',
        'collection_of':'type:service:Item','origin':[{'file':'Api.java','line':5}]}
    path=tmp_path/'skeleton.json';path.write_text(json.dumps(skeleton));project=Project(path,tmp_path)
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.read'],{})
    assert not any(event['resource']==rid for event in engine.data_operations)
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Api.entry'],{})==1
    collection=[event for event in engine.data_operations if event['resource']==rid]
    assert len(collection)==1 and collection[0]['method']==ids['Api.read']


def test_more_than_four_commuting_getters_do_not_widen_unrelated_fields(tmp_path):
    source='''import java.util.*;import org.springframework.beans.support.*;
      class Api{@GetMapping("/items") Item entry(){return new Item();}}
      class Item{String a="A";String b="B";String c="C";String d="D";Set<String> values;
      public String getA(){return a;}public String getB(){return b;}public String getC(){return c;}public String getD(){return d;}
      Set<String> internal(){if(values==null){values=new HashSet<>();}return values;}
      public List<String> getValues(){List<String> result=new ArrayList<>(internal());
        PropertyComparator.sort(result,new MutableSortDefinition("name",true,true));return Collections.unmodifiableList(result);}}'''
    project,db,ids=build(tmp_path,{'Api.java':source})
    result=Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})
    assert result=={'a':'A','b':'B','c':'C','d':'D','values':[]}
