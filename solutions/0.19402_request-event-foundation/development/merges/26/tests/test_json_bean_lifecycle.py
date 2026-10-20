"""Source JavaBeans callbacks affect JSON values, edges and failure boundaries."""
import pytest
from analyzer.engine import Engine
from analyzer.java_collections import JsonText
from analyzer.state import ScenarioState,U
from builders import build


def run(tmp_path,body,bean):
    p,db,ids=build(tmp_path,{'Api.java':'import com.fasterxml.jackson.databind.ObjectMapper;'
        'class Api{Object entry(){'+body+'}void after(){}}'+bean})
    e=Engine(p,ScenarioState(db));result=e.run(ids['Api.entry'],{})
    return result,e,ids


def called(e,ids,name):return any(k=='calls' and t==ids[name] for _,k,t in e.edges)


def executed(e,ids,name):return any(k=='executes' and t==ids[name] for _,k,t in e.edges)


def test_serialization_uses_a_computed_getter_without_a_matching_field(tmp_path):
    result,e,ids=run(tmp_path,'return new ObjectMapper().writeValueAsString(new Item());',
        'class Item{public String getLabel(){return "computed";}}')
    assert isinstance(result,JsonText) and result.payload=={'label':'computed'}
    assert not executed(e,ids,'Item.getLabel') and not called(e,ids,'Item.getLabel') and not e.approximate


def test_serialization_getter_takes_precedence_over_the_public_field(tmp_path):
    result,e,ids=run(tmp_path,'return new ObjectMapper().writeValueAsString(new Item());',
        'class Item{public int count=1;public int getCount(){return count+1;}}')
    assert isinstance(result,JsonText) and result.payload=={'count':2}
    assert not executed(e,ids,'Item.getCount') and not called(e,ids,'Item.getCount') and not e.approximate


def test_private_unexposed_field_is_not_leaked_by_serialization(tmp_path):
    result,e,_=run(tmp_path,'return new ObjectMapper().writeValueAsString(new Item());',
        'class Item{private String secret="hidden";public String name="shown";}')
    assert isinstance(result,JsonText) and result.payload=={'name':'shown'} and not e.approximate


def test_deserialization_invokes_the_source_setter_before_returning(tmp_path):
    result,e,ids=run(tmp_path,'Item item=new ObjectMapper().readValue("{\\"name\\":\\"alpha\\"}",Item.class);return item.getName();',
        'class Item{private String name;public void setName(String input){name=input.toUpperCase();}public String getName(){return name;}}')
    assert result=='ALPHA' and executed(e,ids,'Item.setName') and not e.approximate


def test_default_constructor_runs_before_a_setter_and_preserves_other_fields(tmp_path):
    result,e,ids=run(tmp_path,'Item item=new ObjectMapper().readValue("{\\"name\\":\\"input\\"}",Item.class);return item.getName();',
        'class Item{private String prefix="initial";private String name;public Item(){prefix="ctor:";}'
        'public void setName(String value){name=prefix+value;}public String getName(){return name;}}')
    assert result=='ctor:input' and not executed(e,ids,'Item.<init>') and executed(e,ids,'Item.setName') and not e.approximate


@pytest.mark.parametrize('bean',[
    'class Item{public String name;public Item(){throw new IllegalStateException();}}',
    'class Item{private String name;public void setName(String value){throw new IllegalStateException();}public String getName(){return name;}}',
])
def test_constructor_or_setter_failure_prevents_success_continuation(tmp_path,bean):
    result,e,ids=run(tmp_path,'new ObjectMapper().readValue("{\\"name\\":\\"x\\"}",Item.class);after();return true;',bean)
    assert result is U and not called(e,ids,'Api.after') and e.outcome=='uncaught application exception'


def test_getter_failure_prevents_success_continuation(tmp_path):
    result,e,ids=run(tmp_path,'new ObjectMapper().writeValueAsString(new Item());after();return true;',
        'class Item{public String getName(){throw new IllegalStateException();}}')
    assert result is U and not executed(e,ids,'Item.getName') and not called(e,ids,'Api.after')
    assert e.outcome=='uncaught application exception'


def test_private_field_without_any_visible_property_is_unknown_to_default_mapper(tmp_path):
    result,e,ids=run(tmp_path,'new ObjectMapper().readValue("{\\"name\\":\\"x\\"}",Item.class);after();return true;',
        'class Item{private String name;}')
    assert result is U and not called(e,ids,'Api.after') and e.outcome=='uncaught application exception'


def test_nonvoid_source_setter_is_still_a_json_mutator(tmp_path):
    result,e,ids=run(tmp_path,'Item item=new ObjectMapper().readValue("{\\"name\\":\\"x\\"}",Item.class);return item.getName();',
        'class Item{private String name;public Item setName(String value){name=value+"!";return this;}public String getName(){return name;}}')
    assert result=='x!' and executed(e,ids,'Item.setName') and not e.approximate


def test_static_getter_does_not_become_an_instance_property(tmp_path):
    result,e,ids=run(tmp_path,'return new ObjectMapper().writeValueAsString(new Item());',
        'class Item{public String name="visible";public static String getSecret(){return "hidden";}}')
    assert isinstance(result,JsonText) and result.payload=={'name':'visible'}
    assert not called(e,ids,'Item.getSecret') and not e.approximate


def test_boolean_is_getter_is_discovered_without_a_same_named_field(tmp_path):
    result,e,ids=run(tmp_path,'return new ObjectMapper().writeValueAsString(new Item());',
        'class Item{public boolean isReady(){return true;}}')
    assert isinstance(result,JsonText) and result.payload=={'ready':True}
    assert not executed(e,ids,'Item.isReady') and not called(e,ids,'Item.isReady') and not e.approximate


def test_scenario_http_body_uses_the_same_setter_contract(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{
      @PostMapping("/items") String entry(@RequestBody Item input){return input.getName();}}
      class Item{private String name;public void setName(String value){name=value.toUpperCase();}
      public String getName(){return name;}}'''})
    e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{'name':'alpha'})=='ALPHA'
    assert executed(e,ids,'Item.setName') and executed(e,ids,'Item.getName')


def test_scenario_http_response_carries_computed_wire_properties(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{
      @GetMapping("/items") Item entry(){return new Item();}}
      class Item{public String getLabel(){return "computed";}}'''})
    e=Engine(p,ScenarioState(db));result=e.run(ids['Api.entry'],{})
    assert result=={'label':'computed'} and not executed(e,ids,'Item.getLabel')


def test_http_response_getter_runs_exactly_once(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{
      @GetMapping("/items") Item entry(){return new Item();}}
      class Item{private int count;public int getCount(){return ++count;}}'''})
    e=Engine(p,ScenarioState(db));result=e.run(ids['Api.entry'],{})
    assert result=={'count':1}


def test_source_invoked_getter_and_constructor_remain_in_the_graph(tmp_path):
    result,e,ids=run(tmp_path,'return new Item().getName();',
        'class Item{private String name;public Item(){name="direct";}public String getName(){return name;}}')
    assert result=='direct'
    assert executed(e,ids,'Item.<init>') and called(e,ids,'Item.<init>')
    assert executed(e,ids,'Item.getName') and called(e,ids,'Item.getName')


def test_json_property_write_order_is_preserved_when_callbacks_interact(tmp_path):
    result,e,_=run(tmp_path,'return new ObjectMapper().readValue("{\\"b\\":\\"x\\",\\"a\\":\\"y\\"}",Item.class).getValue();',
        'class Item{private String value="";public void setA(String input){value+="A";}'
        'public void setB(String input){value+="B";}public String getValue(){return value;}}')
    assert result=='BA' and not e.approximate


def test_duplicate_json_properties_invoke_the_setter_per_occurrence(tmp_path):
    result,e,_=run(tmp_path,'return new ObjectMapper().readValue("{\\"name\\":\\"first\\",\\"name\\":\\"last\\"}",Item.class).getValue();',
        'class Item{private String value="";public void setName(String input){value+=input+",";}'
        'public String getValue(){return value;}}')
    assert result=='first,last,' and not e.approximate


def test_filter_context_does_not_change_the_controllers_body_contract(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{
      @PostMapping("/items") String entry(@RequestBody Item input){return input.getName();}}
      class Item{private String name;public void setName(String value){name=value.toUpperCase();}
      public String getName(){return name;}}
      class Gate extends OncePerRequestFilter{
      void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain){chain.doFilter(req,res);}}'''})
    e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{'name':'alpha'})=='ALPHA'
    assert executed(e,ids,'Item.setName') and executed(e,ids,'Api.entry')


def test_source_proven_omission_does_not_become_an_artificial_setter_call(tmp_path):
    from analyzer.contracts import ContractGrounder,ContractIndex
    from analyzer.frontend import Frontend
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{
      @PostMapping("/items") Item create(@RequestBody Item input){return input;}}
      class Item{public String name="seed";private int touches;
      public void setName(String value){touches++;name=value;}public int getTouches(){return touches;}}'''})
    (tmp_path/'page.html').write_text('<script src="ui.js"></script>')
    (tmp_path/'ui.js').write_text('function create(){$.ajax({url:"/items",type:"POST",contentType:"application/json",data:JSON.stringify({})});}')
    frontend=Frontend(p);state=ScenarioState(db)
    proposal=ContractGrounder(p,frontend,ContractIndex(p,frontend),None,{'facts':{}}).step('Create item',state)[0][0]
    e=Engine(p,proposal['state']);result=e.run(proposal['entry'],proposal['params'])
    assert result=={'name':'seed','touches':0}
    assert not executed(e,ids,'Item.setName')


def test_unobserved_property_presence_retains_both_omission_and_callback_failure(tmp_path):
    from analyzer.paths import run_paths
    from analyzer.request_inputs import RequestInputs
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{
      @PostMapping("/items") String entry(@RequestBody Item input){after();return "ok";}void after(){}}
      class Item{private String name;public void setName(String value){throw new IllegalStateException();}}'''})
    params=RequestInputs({},flat_bodies=['input'],body_unknowns={'input':{'name':'unobserved'}})
    outcomes=run_paths(p,ScenarioState(db),ids['Api.entry'],params)
    assert len(outcomes)==2
    assert {o['engine'].outcome for o in outcomes}=={'returned','HTTP error response'}
    assert sorted(called(o['engine'],ids,'Api.after') for o in outcomes)==[False,True]
    bounded=run_paths(p,ScenarioState(db),ids['Api.entry'],params,limit=1)[0]['engine']
    assert bounded.approximate and called(bounded,ids,'Api.after')
    assert executed(bounded,ids,'Item.setName')
    assert any('property presence' in warning for warning in bounded.warnings)


def test_known_present_unknown_value_cannot_skip_a_guaranteed_setter_failure(tmp_path):
    from analyzer.request_inputs import RequestInputs
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{
      @PostMapping("/items") String entry(@RequestBody Item input){after();return "ok";}void after(){}}
      class Item{public void setName(String value){throw new IllegalStateException();}}'''})
    e=Engine(p,ScenarioState(db));params=RequestInputs({},flat_bodies=['input'],body_unknowns={'input':{'name':'present'}})
    assert e.run(ids['Api.entry'],params) is U and not called(e,ids,'Api.after')
    assert e.outcome=='HTTP error response'


def test_native_lombok_boolean_backing_field_survives_json_and_source_calls(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import lombok.Data;import com.fasterxml.jackson.databind.ObjectMapper;
      @Data class Item{private boolean isReady;}
      class Api{boolean entry(){Item item=new ObjectMapper().readValue("{\\"ready\\":true}",Item.class);
      if(!item.isReady()){wrong();}item.setReady(false);return item.isReady();}void wrong(){}}'''})
    e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{}) is False and not called(e,ids,'Api.wrong') and not e.approximate


def test_skeleton_generated_members_do_not_poison_or_enter_the_json_graph(tmp_path):
    import json
    from analyzer.project import Project
    p,db,ids=build(tmp_path,{'Api.java':'''import lombok.Data;import com.fasterxml.jackson.databind.ObjectMapper;
      @Data class Item{private boolean isReady;}
      class Api{boolean entry(){Item item=new ObjectMapper().readValue("{\\"ready\\":true}",Item.class);
        return item.isReady();}}'''})
    generated=[]
    for name,pars,ret in [('isReady',[],'boolean'),('setReady',['boolean'],'void'),('<init>',[],'')]:
        mid='method:service:Item#'+name+'('+','.join(pars)+')';generated.append(mid)
        p.skeleton['nodes'][mid]={**p.methods[ids['Api.entry']],'owner':'type:service:Item','name':name,
                                 'params_as_written':pars,'return_raw':ret}
    (tmp_path/'skeleton.json').write_text(json.dumps(p.skeleton));p=Project(tmp_path/'skeleton.json',tmp_path)
    e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{}) is True and not e.approximate
    assert not set(generated)&{target for _,kind,target in e.edges if kind in ('calls','executes')}


def test_setter_return_can_fail_and_does_not_prove_commuting_property_order(tmp_path):
    from analyzer.paths import run_paths
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import com.fasterxml.jackson.databind.ObjectMapper;
      class Item{private int a;private int b;public int setA(int input){a=input;return 1/0;}
        public void setB(int input){b=input;}}
      class Api{void entry(){Map input=new HashMap();input.put("a",1);input.put("b",2);
        new ObjectMapper().convertValue(input,Item.class);after();}void after(){}}'''})
    outcomes=run_paths(p,ScenarioState(db),ids['Api.entry'],{})
    assert len(outcomes)==2 and all(o['engine'].outcome=='uncaught application exception' for o in outcomes)
    assert sorted(executed(o['engine'],ids,'Item.setB') for o in outcomes)==[False,True]
    assert not any(called(o['engine'],ids,'Api.after') for o in outcomes)


def test_ignored_getter_is_not_invoked_or_exported(tmp_path):
    result,e,ids=run(tmp_path,'return new ObjectMapper().writeValueAsString(new Item());',
        'class Item{public String visible="yes";@com.fasterxml.jackson.annotation.JsonIgnore '
        'public String getSecret(){throw new IllegalStateException();}}')
    assert isinstance(result,JsonText) and result.payload=={'visible':'yes'} and not e.approximate
    assert not executed(e,ids,'Item.getSecret')


@pytest.mark.parametrize('wire',['"{\\"name\\":\\"incoming\\"}"',
    'new ObjectMapper().writeValueAsString(new java.util.HashMap<String,String>(){{put("name","incoming");}})'])
def test_ignored_property_is_skipped_without_invoking_the_source_setter(tmp_path,wire):
    result,e,ids=run(tmp_path,'Item item=new ObjectMapper().readValue('+wire+',Item.class);return item.raw();',
        'class Item{private String name="seed";@com.fasterxml.jackson.annotation.JsonIgnore '
        'public void setName(String value){throw new IllegalStateException();}public String getName(){return name;}String raw(){return name;}}')
    assert result=='seed' and not executed(e,ids,'Item.setName') and not e.approximate


def test_disabled_ignore_marker_preserves_the_ordinary_property(tmp_path):
    result,e,_=run(tmp_path,'return new ObjectMapper().writeValueAsString(new Item());',
        'class Item{@com.fasterxml.jackson.annotation.JsonIgnore(false) public String name="shown";}')
    assert isinstance(result,JsonText) and result.payload=={'name':'shown'} and not e.approximate


@pytest.mark.parametrize('wire',['"{\\"name\\":\\"incoming\\"}"',
    'new ObjectMapper().writeValueAsString(new java.util.HashMap<String,String>(){{put("name","incoming");}})'])
def test_ignored_property_can_be_rejected_by_an_observed_mapper_feature(tmp_path,wire):
    result,e,ids=run(tmp_path,'ObjectMapper mapper=new ObjectMapper();mapper.enable(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_IGNORED_PROPERTIES);'
        'mapper.readValue('+wire+',Item.class);after();return true;',
        'class Item{@com.fasterxml.jackson.annotation.JsonIgnore public String name;}')
    assert result is U and not called(e,ids,'Api.after') and e.outcome=='uncaught application exception'


def test_chosen_getter_order_stays_correlated_with_the_emitted_document_order(tmp_path):
    from analyzer.paths import run_paths
    p,db,ids=build(tmp_path,{'Api.java':'''import com.fasterxml.jackson.databind.ObjectMapper;
      class Source{private int n;public int getA(){return ++n;}public int getB(){return ++n;}}
      class Target{private int n;public void setA(int v){n=n*10+v;}public void setB(int v){n=n*10+v;}int value(){return n;}}
      class Api{int entry(){return new ObjectMapper().convertValue(new Source(),Target.class).value();}}'''})
    outcomes=run_paths(p,ScenarioState(db),ids['Api.entry'],{})
    assert len(outcomes)==2 and {o['result'] for o in outcomes}=={12}


def test_linked_map_emits_a_document_in_its_known_insertion_order(tmp_path):
    result,e,_=run(tmp_path,'java.util.Map input=new java.util.LinkedHashMap();input.put("b","x");input.put("a","y");'
        'return new ObjectMapper().readValue(new ObjectMapper().writeValueAsString(input),Item.class).raw();',
        'class Item{private String text="";public void setA(String value){text+="A";}public void setB(String value){text+="B";}String raw(){return text;}}')
    assert result=='BA' and not e.approximate


def test_commuting_setters_compare_qualified_types_in_their_declaration_namespaces(tmp_path):
    result,e,_=run(tmp_path,'java.util.Map input=new java.util.HashMap();input.put("a","x");input.put("b","y");'
        'return new ObjectMapper().readValue(new ObjectMapper().writeValueAsString(input),Item.class).raw();',
        'class Item{private String a;private String b;public void setA(java.lang.String value){a=value;}'
        'public void setB(String value){b=value;}String raw(){return a+":"+b;}}')
    assert result=='x:y' and not e.approximate


@pytest.mark.parametrize('bean,body,expected',[
    ('import lombok.Data;@Data class Item{private boolean isReady;}','{ready:true}',True),
    ('class Item{private String text;public void setName(String value){text=value.toUpperCase();}public String getName(){return text;}}','{name:"alpha"}','ALPHA'),
])
def test_ui_wire_properties_use_a_structured_body_when_java_field_names_differ(tmp_path,bean,body,expected):
    from analyzer.contracts import ContractGrounder,ContractIndex
    from analyzer.frontend import Frontend
    imports='import lombok.Data;' if bean.startswith('import') else ''
    bean=bean.removeprefix(imports)
    read='isReady()' if expected is True else 'getName()'
    typ='boolean' if expected is True else 'String'
    p,db,ids=build(tmp_path,{'Api.java':imports+bean+'class Api{@PostMapping("/items") '+typ+' create(@RequestBody Item input){return input.'+read+';}}'})
    (tmp_path/'page.html').write_text('<script src="ui.js"></script>')
    (tmp_path/'ui.js').write_text('function create(){$.ajax({url:"/items",type:"POST",data:JSON.stringify('+body+')});}')
    f=Frontend(p);proposal=ContractGrounder(p,f,ContractIndex(p,f),None,{'facts':{}}).step('Create item',ScenarioState(db))[0][0]
    assert 'input' in proposal['params'] and not proposal['unresolved']
    e=Engine(p,proposal['state'])
    assert e.run(proposal['entry'],proposal['params'])==expected and not e.approximate


def test_unobserved_changed_property_layout_cannot_confirm_the_java_default_branch(tmp_path):
    from analyzer.contracts import ContractGrounder,ContractIndex
    from analyzer.frontend import Frontend
    from analyzer.paths import run_paths
    p,db,ids=build(tmp_path,{'Api.java':'''import lombok.Data;import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
      @Data @JsonIgnoreProperties(ignoreUnknown=true) class Item{private boolean isReady;}
      class Api{@PostMapping("/items") String create(@RequestBody Item input){
        if(input.isReady()){return yes();}return no();}String yes(){return "yes";}String no(){return "no";}}'''})
    f=Frontend(p);proposal=ContractGrounder(p,f,ContractIndex(p,f),None,{'facts':{}}).step('Create item',ScenarioState(db))[0][0]
    assert any('JSON property layout' in issue for issue in proposal['unresolved'])
    outcomes=run_paths(p,proposal['state'],proposal['entry'],proposal['params'])
    assert {o['result'] for o in outcomes}=={'yes','no'}
