from analyzer.engine import Engine
from analyzer.paths import run_paths,join_states
from analyzer.state import ScenarioState,U
from builders import build


def test_mutable_literal_is_not_project_constant_and_local_shadows(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{static int count=2;
      int entry(){int count=8;Api.count++;return count+Api.count;}
      int read(){return count;}}'''})
    state=ScenarioState(db);e=Engine(p,state)
    assert e.run(ids['Api.entry'],{})==11
    assert Engine(p,state).run(ids['Api.read'],{})==3
    assert Engine(p,ScenarioState(db)).run(ids['Api.read'],{})==2
    assert state.static_fields['type:service:Api'].kinds['count']=='Integer'


def test_dependency_source_order_once_and_alias(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Material{static List<String> names=new ArrayList<>();static{names.add("once");}
      static int first=4;static int next=first+3;}
      class Api{Object entry(){List<String> alias=Material.names;alias.add("twice");
      return Arrays.asList(Material.next,Material.names.size(),alias==Material.names);}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==[7,2,True]
    assert not e.approximate
    assert all(not part.startswith('source-context:') for edge in e.edges for part in edge)


def test_type_and_class_literal_do_not_initialize_other_type(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Material{static int counter=1;}
      class Api{Object entry(){Material other=null;return Material.class;}}'''})
    state=ScenarioState(db);Engine(p,state).run(ids['Api.entry'],{})
    assert not state.class_initialization and not state.static_fields


def test_declaring_owner_inherited_static_and_hiding(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Base{static int shared=2;}
      class Child extends Base{} class Hides extends Base{static int shared=7;}
      class Api{int entry(){Child.shared=4;return Base.shared+Hides.shared;}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==11
    assert 'shared' not in e.state.static_fields.get('type:service:Child',{})


def test_static_import_and_null_qualifier(tmp_path):
    p,db,ids=build(tmp_path,{'Material.java':'class Material{static int count=3;}',
      'Api.java':'import static Material.count;class Api{int entry(){Material m=null;m.count=4;return count;}}'})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==4


def test_branch_writes_and_aliases_remain_scenario_owned(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{static List<Integer> values=new ArrayList<>();
      Object entry(boolean flag){List<Integer> alias=values;if(flag){values.add(1);}else{values.add(2);}return alias;}
      int read(){return values.size();}}'''})
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{'flag':U},limit=4)
    assert {tuple(row['result']) for row in paths}=={(1,),(2,)}
    assert all(Engine(p,row['state']).run(ids['Api.read'],{})==1 for row in paths)
    assert not ScenarioState(db).static_fields


def test_failed_initializer_keeps_prefix_and_never_runs_body(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Material{static int prefix=1;static{prefix=2;throw new IllegalStateException();}
      static int read(){return 9;}}
      class Api{int entry(){return Material.read();}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='uncaught application exception'
    assert e.state.static_fields['type:service:Material']['prefix']==2
    assert ('','executes',ids['Material.read']) not in e.edges
    again=Engine(p,e.state);assert again.run(ids['Api.entry'],{}) is U
    assert any('NoClassDefFoundError' in warning for warning in again.warnings)


def test_initializer_error_is_not_wrapped_in_exception_in_initializer_error(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Material{static{throw new Error();}static int read(){return 9;}}
      class Api{int entry(){try{return Material.read();}catch(ExceptionInInitializerError ex){return 1;}catch(Error ex){return 2;}}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==2
    assert ('','executes',ids['Material.read']) not in e.edges


def test_cross_class_cycle_is_explicit_boundary(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class A{static int x=B.y;}class B{static int y=A.x;}
      class Api{int entry(){return A.x;}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='unsupported_semantics boundary' and any('cyclic static' in warning for warning in e.warnings)


def test_initializer_callback_does_not_report_unentered_callee(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Material{static int value=prefix();
      static{throw new IllegalStateException();}static int prefix(){return 1;}static int read(){return 9;}}
      class Api{int entry(){return Material.read();}}'''})
    e=Engine(p,ScenarioState(db));e.run(ids['Api.entry'],{})
    assert ('','executes',ids['Material.prefix']) in e.edges
    assert ('','executes',ids['Material.read']) not in e.edges
    assert not any(relation=='calls' and target==ids['Material.read'] for _,relation,target in e.edges)


def test_unresolved_handler_initialization_does_not_emit_a_remote_entry(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;
      class Receiver{static int marker=1;@GetMapping("/value")String read(){return "value";}}
      class Caller{RestTemplate rest;String entry(){return rest.getForObject("http://service/value",String.class);}}'''})
    state=ScenarioState(db);state.class_initialization['type:service:Receiver']=U
    e=Engine(p,state);assert e.run(ids['Caller.entry'],{}) is U
    assert ('','executes',ids['Receiver.read']) not in e.edges
    assert not any(relation=='remote' and target==ids['Receiver.read'] for _,relation,target in e.edges)


def test_null_final_string_is_not_a_compile_time_constant(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Material{static final String value=null;
      static{throw new IllegalStateException();}}class Api{String entry(){return Material.value;}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='uncaught application exception'


def test_literal_constant_does_not_initialize_but_unproved_expression_stops(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Material{static final int literal=3;static final int computed=1+2;
      static{throw new IllegalStateException();}}class Api{int entry(){return Material.literal;}int other(){return Material.computed;}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==3
    assert not e.state.class_initialization
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.other'],{}) is U
    assert e.outcome=='unsupported_semantics boundary' and not e.state.class_initialization
