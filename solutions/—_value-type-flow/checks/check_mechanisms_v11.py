"""Source-only relation measurements by mechanism, independent of Train Ticket.

Small component fixtures, not a representative real-project portability corpus.
References are manually specified from source and fixed before Engine execution.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

p=argparse.ArgumentParser()
p.add_argument('--code',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--work',type=Path,required=True)
args=p.parse_args()
assert not args.work.exists() and not args.output.exists()
args.work.mkdir(parents=True)
sys.path[:0]=[str(args.code.resolve()),str(args.code.resolve()/'tests')]
from builders import build
from analyzer.paths import run_paths
from analyzer.state import ScenarioState
from analyzer.project import Project
from analyzer.__main__ import serial,analyze
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex,ContractGrounder


def edges(ids,entry,methods=(),calls=(),remote=(),data=()):
    return {('', 'executes',ids[name]) for name in (entry,*methods)} | {
        (ids[a],'calls',ids[b]) for a,b in calls} | {
        (ids[a],'remote',ids[b]) for a,b in remote} | {
        (ids[a],'data','res:table:service.'+table) for a,table in data}


cases=[]
cases.append({'name':'concrete_receiver','family':'local_dispatch','entry':'Start.entry','sources':{
 'Api.java':'''interface Worker {String run();}
 class PremiumWorker implements Worker {public String run(){return "premium";}}
 class BasicWorker implements Worker {public String run(){return "basic";}}
 class Start {String entry(){Worker worker=new PremiumWorker();return worker.run();}}'''},
 'methods':['PremiumWorker.run'],'calls':[('Start.entry','PremiumWorker.run')]})

cases.append({'name':'verb_and_remote_unit','family':'remote_http','entry':'Client.entry','sources':{
 'Client.java':'''import org.springframework.web.client.RestTemplate;class Client {RestTemplate rest;String entry(){
   return rest.postForObject("http://stock/records","payload",String.class);}}''',
 'Stock.java':'''class Api {@GetMapping("/records") String read(){return "get";}
   @PostMapping("/records") String write(@RequestBody String body){return accepted();}
   String accepted(){return "post";}}'''},
 'remote_units':True,'methods':['Api.write','Api.accepted'],
 'calls':[('Api.write','Api.accepted')],'remote':[('Client.entry','Api.write')]})

for label,value,fails in [('invalid','broken',True),('out_of_range','2147483648',True),('valid','12',False)]:
    called='Api.invalid' if fails else 'Api.after'
    cases.append({'name':'parse_int_'+label,'family':'guaranteed_library_failure','entry':'Api.entry','sources':{
      'Api.java':'''class Api {String entry(){try{Integer.parseInt("'''+value+'''");return after();}
        catch(NumberFormatException failure){return invalid();}}
        String after(){return "after";}String invalid(){return "invalid";}}'''},
      'methods':[called],'calls':[('Api.entry',called)]})

for operator in ('=','>'):
    cases.append({'name':'native_predicate_'+('equals' if operator=='=' else 'greater'),'family':'orm_predicates','entry':'Api.entry','sources':{
      'Api.java':'''class Api {@Autowired Store store;String entry(){
        if(store.visible(1).isEmpty()){return none();}return found();}
        String found(){return "found";}String none(){return "none";}}
        @Entity @Table(name="parts") class Part {@Id String id;int quantity;}
        interface Store extends JpaRepository<Part,String>{
          @Query(value="SELECT * FROM parts WHERE quantity '''+operator+''' ?1",nativeQuery=true)
          List<Part> visible(int threshold);}'''},'rows':{'parts':[{'id':'a','quantity':1},{'id':'b','quantity':2}]},
      'methods':['Api.found'],'calls':[('Api.entry','Api.found')],'data':[('Api.entry','parts')]})

cases.append({'name':'shallow_copy_mappings','family':'java_collections','entry':'Api.entry','sources':{
 'Api.java':'''import java.util.*;class Api {String entry(){
   Map original=new HashMap();original.put("mode","ready");Map copied=new HashMap(original);
   if("ready".equals(copied.get("mode"))){return ready();}return lost();}
   String ready(){return "ready";}String lost(){return "lost";}}'''},
 'methods':['Api.ready'],'calls':[('Api.entry','Api.ready')]})

cases.extend([
 {'name':'boxed_scalar_keys','family':'java_collections','entry':'Api.entry','sources':{
  'Api.java':"""import java.util.*;class Api {String entry(){Map m=new HashMap();
    m.put(7,"integer");m.put("7","string");
    if("integer".equals(m.get(7))){return correct();}return wrong();}
    String correct(){return "correct";}String wrong(){return "wrong";}}"""},
  'methods':['Api.correct'],'calls':[('Api.entry','Api.correct')]},
 {'name':'distinct_map_references','family':'reference_identity','entry':'Api.entry','sources':{
  'Api.java':"""import java.util.*;class Api {String entry(){Map left=new HashMap();Map right=new HashMap();
    if(left==right){return same();}return different();}
    String same(){return "same";}String different(){return "different";}}"""},
  'methods':['Api.different'],'calls':[('Api.entry','Api.different')]},
 {'name':'json_map_to_script_to_request','family':'frontend_response_binding','entry':'Api.load','sources':{
  'Api.java':"""import java.util.*;class Api {
    @GetMapping("/settings") Map load(){Map flags=new HashMap();flags.put("mode","ready");return flags;}
    @PostMapping("/publish") String publish(@RequestBody Input input){
      if("ready".equals(input.mode)){return accepted();}return rejected();}
    String accepted(){return "accepted";}String rejected(){return "rejected";}}
    class Input {public String mode;}"""},'journey':True,
  'methods':['Api.publish','Api.accepted'],'calls':[('Api.publish','Api.accepted')]}
])


# References remain hand-written and are committed to work/reference.json before execution.
cases.extend([
 {'name':'native_map_initializer','family':'java_collections','entry':'Api.entry','sources':{
  'Api.java':"""import java.util.*;class Api {String entry(){String value="ready";
    Map map=new HashMap(){{put("mode",value);}};
    if("ready".equals(map.get("mode"))){return accepted();}return rejected();}
    String accepted(){return "accepted";}String rejected(){return "rejected";}}"""},
  'methods':['Api.accepted'],'calls':[('Api.entry','Api.accepted')]},
 {'name':'foreign_rest_template_namesake','family':'http_client_type_binding','entry':'Client.entry','sources':{
  'Api.java':"""import external.library.RestTemplate;
    class Api {@GetMapping("/items") String list(){return "wrong";}}
    class Client {RestTemplate rest;Object entry(){return rest.getForObject("http://service/items",Object.class);}}"""}},
 {'name':'http_request_map_ownership','family':'http_request_binding','entry':'Client.entry','sources':{
  'Client.java':"""import java.util.*;import org.springframework.web.client.RestTemplate;
    class Client {RestTemplate rest;String entry(){Map input=new HashMap();input.put("mode","original");
      rest.postForObject("http://stock/update",input,String.class);
      if("original".equals(input.get("mode"))){return accepted();}return rejected();}
      String accepted(){return "accepted";}String rejected(){return "rejected";}}""",
  'Stock.java':"""import java.util.*;class Api {
    @PostMapping("/update") String update(@RequestBody Map<String,String> input){input.put("mode","changed");return "ok";}}"""},
  'remote_units':True,'methods':['Api.update','Client.accepted'],
  'calls':[('Client.entry','Client.accepted')],'remote':[('Client.entry','Api.update')]}
])


cases.append({'name':'generic_http_response_binding','family':'generic_json_types','entry':'Client.entry','sources':{
 'Client.java':"""import java.util.*;import org.springframework.web.client.RestTemplate;
  import org.springframework.core.ParameterizedTypeReference;import org.springframework.http.HttpMethod;
  class Client {RestTemplate rest;String entry(){Box<Map<String,String>> value=rest.exchange(
    "http://stock/item",HttpMethod.GET,null,new ParameterizedTypeReference<Box<Map<String,String>>>(){}).getBody();
    if("known".equals(value.payload.get("id"))){return accepted();}return rejected();}
    String accepted(){return "accepted";}String rejected(){return "rejected";}}""",
 'Stock.java':"""class Item {public String id="known";}class Box<T> {public T payload;}
  class Api {@GetMapping("/item") Box item(){Box result=new Box();result.payload=new Item();return result;}}"""},
 'remote_units':True,'methods':['Api.item','Client.accepted'],
 'calls':[('Client.entry','Client.accepted')],'remote':[('Client.entry','Api.item')]})


cases.append({'name':'uncaught_server_failure_boundary','family':'http_failure_boundary','entry':'Client.entry','sources':{
 'Client.java':"""import org.springframework.web.client.RestTemplate;
  import org.springframework.web.client.HttpServerErrorException;
  class Client {RestTemplate rest;String entry(){try{
    rest.getForObject("http://stock/fail",String.class);return after();}
    catch(IllegalArgumentException failure){return wrong();}
    catch(HttpServerErrorException failure){return rejected();}}
    String after(){return "after";}String wrong(){return "wrong";}String rejected(){return "rejected";}}""",
 'Stock.java':"""class Api {@GetMapping("/fail") String fail(){throw new IllegalArgumentException();}}"""},
 'remote_units':True,'methods':['Api.fail','Client.rejected'],
 'calls':[('Client.entry','Client.rejected')],'remote':[('Client.entry','Api.fail')]})


cases.append({'name':'query_driven_table_selection','family':'data_dependent_table_selection','entry':'Api.entry','sources':{
 'Api.java':"""class Api {Store store;AuditStore audits;String entry(){
   if(store.above(1).isEmpty()){audits.findAll();return none();}return ready();}
   String none(){return "none";}String ready(){return "ready";}}
   @Entity @Table(name="parts") class Part {@Id String id;int quantity;}
   @Entity @Table(name="audits") class Audit {@Id String id;}
   interface Store extends JpaRepository<Part,String>{
    @Query(value="SELECT * FROM parts WHERE quantity > ?1",nativeQuery=true) List<Part> above(int threshold);}
   interface AuditStore extends JpaRepository<Audit,String>{List<Audit> findAll();}"""},
 'rows':{'parts':[{'id':'one','quantity':2}],'audits':[]},'methods':['Api.ready'],
 'calls':[('Api.entry','Api.ready')],'data':[('Api.entry','parts')]})

# New references isolate expression typing before each relation measurement.
cases.extend([
 {'name':'expression_key_table_selection','family':'expression_key_data','entry':'Api.entry','sources':{
 'Api.java':'''import java.util.*;class Api {Store stock;AuditStore audit;String entry(){
  Map map=new HashMap();map.put("key"+7,"ready");
  if("ready".equals(map.get("key7"))){stock.findAll();return accepted();}
  audit.findAll();return rejected();}String accepted(){return "ok";}String rejected(){return "bad";}}
  @Entity @Table(name="items") class Item {@Id String id;}
  @Entity @Table(name="events") class Event {@Id String id;}
  interface Store extends JpaRepository<Item,String>{List<Item> findAll();}
  interface AuditStore extends JpaRepository<Event,String>{List<Event> findAll();}'''},
 'rows':{'items':[],'events':[]},'methods':['Api.accepted'],'calls':[('Api.entry','Api.accepted')],
 'data':[('Api.entry','items')]},
 {'name':'boolean_expression_key','family':'expression_key_boolean','entry':'Api.entry','sources':{
 'Api.java':'''import java.util.*;class Api {String entry(){Map map=new HashMap();map.put(2>1,"ready");
  if("ready".equals(map.get(true))){return accepted();}return rejected();}
  String accepted(){return "ok";}String rejected(){return "bad";}}'''},
 'methods':['Api.accepted'],'calls':[('Api.entry','Api.accepted')]},
 {'name':'numeric_conditional_boxing','family':'expression_key_numeric','entry':'Api.entry','sources':{
 'Api.java':'''import java.util.*;class Api {String entry(){Map map=new HashMap();map.put(true?1:2L,"ready");
  if("ready".equals(map.get(1L)) && map.get(1)==null){return accepted();}return rejected();}
  String accepted(){return "ok";}String rejected(){return "bad";}}'''},
 'methods':['Api.accepted'],'calls':[('Api.entry','Api.accepted')]},
 {'name':'char_numeric_promotion','family':'expression_char_promotion','entry':'Api.entry','sources':{
 'Api.java':'''class Api {String entry(){if('A'+1==66){return accepted();}return rejected();}
  String accepted(){return "ok";}String rejected(){return "bad";}}'''},
 'methods':['Api.accepted'],'calls':[('Api.entry','Api.accepted')]},
 {'name':'string_return_key_remote_selection','family':'expression_key_remote','entry':'Client.entry','sources':{
 'Client.java':'''import java.util.*;import org.springframework.web.client.RestTemplate;
 class Client {RestTemplate rest;String entry(){String part="mode-tail";Map map=new HashMap();
  map.put(part.substring(0,4),"ready");
  if("ready".equals(map.get("mode"))){return rest.getForObject("http://stock/alive",String.class);}
  return rest.getForObject("http://stock/wrong",String.class);}}''',
 'Stock.java':'''class Api {@GetMapping("/alive") String alive(){return "ok";}
  @GetMapping("/wrong") String wrong(){return "bad";}}'''},
 'remote_units':True,'methods':['Api.alive'],'remote':[('Client.entry','Api.alive')]}
])

cases.extend([
 {'name':'foreach_source_element_type','family':'loop_element_types','entry':'Api.entry','sources':{
 'Api.java':'''import java.util.*;class Item{String getKey(){return "known";}}
 class Api{String entry(){Map map=new HashMap();for(Item item:Arrays.asList(new Item())){
  map.put(item.getKey(),"ready");}if("ready".equals(map.get("known"))){return accepted();}return rejected();}
  String accepted(){return "ok";}String rejected(){return "bad";}}'''},
 'methods':['Item.getKey','Api.accepted'],'calls':[('Api.entry','Item.getKey'),('Api.entry','Api.accepted')]},
 {'name':'inferred_stream_callback_type','family':'stream_parameter_types','entry':'Api.entry','sources':{
 'Api.java':'''import java.util.*;import java.util.stream.Collectors;class Api{String entry(){Map map=new HashMap();
  List<String> values=Arrays.asList("known");values.stream().map(key->{map.put(key,"ready");return key;})
  .collect(Collectors.toList());if("ready".equals(map.get("known"))){return accepted();}return rejected();}
  String accepted(){return "ok";}String rejected(){return "bad";}}'''},
 'methods':['Api.accepted'],'calls':[('Api.entry','Api.accepted')]},
 {'name':'block_binding_lifetime','family':'lexical_binding_scope','entry':'Start.entry','sources':{
 'Api.java':'''import java.util.*;class Api{String key="outer";String inspect(){if(true){int key=1;}
  Map map=new HashMap();map.put(key,"ready");if("ready".equals(map.get("outer"))){return accepted();}return rejected();}
  String accepted(){return "ok";}String rejected(){return "bad";}}
  class Start{String entry(){return new Api().inspect();}}'''},
 'methods':['Api.inspect','Api.accepted'],'calls':[('Start.entry','Api.inspect'),('Api.inspect','Api.accepted')]}
])

cases.append({'name':'null_unboxing_before_later_argument','family':'null_unboxing_failure','entry':'Api.entry','sources':{
 'Api.java':'''class Api{String entry(){try{Integer value=null;consume(value,side());return after();}
  catch(NullPointerException failure){return failed();}}void consume(int value,int later){}
  int side(){return 1;}String after(){return "wrong";}String failed(){return "caught";}}'''},
 'methods':['Api.failed'],'calls':[('Api.entry','Api.failed')]})

# A declared limitation is measured too: correct uncertainty is not exact generic binding.
cases.append({'name':'generic_shadowing_conservative','family':'generic_type_variable_binding','entry':'Api.entry','sources':{
 'Api.java':'''import java.util.*;class Box<String>{String value;String getValue(){return value;}}
 class Api{String entry(){Box box=new Box();box.value='x';Map map=new HashMap();map.put(box.getValue(),"found");
 if("found".equals(map.get("x"))){return wrong();}return correct();}
 String correct(){return "ok";}String wrong(){return "bad";}}'''},
 'methods':['Box.getValue','Api.correct'],'calls':[('Api.entry','Box.getValue'),('Api.entry','Api.correct')]})

results=[]
for case in cases:
    work=args.work/case['name']
    project,db,ids=build(work,case['sources'],rows=case.get('rows'))
    if case.get('remote_units'):
        skeleton=project.skeleton
        for unit in ('client','stock'):
            skeleton['nodes']['module:'+unit]={'kind':'module','name':unit,'deployment_units':[unit]}
        for node in skeleton['nodes'].values():
            if node.get('file') in ('Client.java','Stock.java'):
                node['module']='client' if node['file']=='Client.java' else 'stock'
        (work/'skeleton.json').write_text(json.dumps(skeleton))
        project=Project(work/'skeleton.json',work)
    if case.get('journey'):
        (work/'page.html').write_text('<button onclick="loadSettings()">Load settings</button><button onclick="publishSettings()">Publish settings</button><script src="ui.js"></script>')
        (work/'ui.js').write_text("""var mode=null;
          function loadSettings(){$.ajax({url:'/settings',type:'GET',success:function(reply){mode=reply.mode;}});}
          function publishSettings(){$.ajax({url:'/publish',type:'POST',data:{mode:mode}});}""")
    reference=edges(ids,case['entry'],case.get('methods',()),case.get('calls',()),case.get('remote',()),case.get('data',()))
    reference_path=work/'reference.json'
    reference_path.write_text(json.dumps(sorted(reference),indent=2)+'\n')
    reference_hash=hashlib.sha256(reference_path.read_bytes()).hexdigest()
    if case.get('journey'):
        frontend=Frontend(project)
        block,detail=analyze(project,frontend,ContractIndex(project,frontend),None,db,{'facts':{},'unresolved':[]},
          {'id':'independent-settings','steps':[{'n':1,'action':'Load settings'},{'n':2,'action':'Publish settings'}]},grounder_type=ContractGrounder)
        actual={('' if edge['relation']=='executes' else edge['source'],edge['relation'],edge['target']) for edge in block['edges']}
        class Observation:
            edges=actual
            warnings=detail['unresolved']
        outcomes=[{'engine':Observation(),'result':[a['result'] for s in detail['steps'] for a in s['alternatives']],
                   'approximate':detail['analysis_status']!='complete_in_supported_model'}]
    else:
        outcomes=run_paths(project,ScenarioState(db),ids[case['entry']],{})
        actual=set.union(*(outcome['engine'].edges for outcome in outcomes)) if outcomes else set()
    by_relation={}
    for relation in ('executes','calls','remote','data'):
        wanted={edge for edge in reference if edge[1]==relation}
        got={edge for edge in actual if edge[1]==relation}
        by_relation[relation]={'tp':len(wanted&got),'fp':len(got-wanted),'fn':len(wanted-got),
            'nonempty':bool(wanted|got),'iou':len(wanted&got)/len(wanted|got) if wanted|got else None}
    assert hashlib.sha256(reference_path.read_bytes()).hexdigest()==reference_hash
    results.append({'name':case['name'],'family':case['family'],'relations':by_relation,
        'missing':sorted(reference-actual),'extra':sorted(actual-reference),
        'warnings':sorted(set().union(*(outcome['engine'].warnings for outcome in outcomes))),
        'outcomes':[{'result':o['result'],'approximate':o['approximate']} for o in outcomes],
        'source_sha256':{name:hashlib.sha256(source.encode()).hexdigest() for name,source in case['sources'].items()},
        'reference_sha256':reference_hash,'reference_fixed_before_prediction':True})
families={}
for family in sorted({result['family'] for result in results}):
    groups=[result for result in results if result['family']==family]
    summary={}
    for relation in ('executes','calls','remote','data'):
        counts={key:sum(result['relations'][relation][key] for result in groups) for key in ('tp','fp','fn')}
        total=sum(counts.values())
        summary[relation]={**counts,'iou':counts['tp']/total if total else None,'tested_nonempty':bool(total)}
    families[family]={'cases':len(groups),'relations':summary,
                      'cases_with_warnings':sum(bool(result['warnings']) for result in groups)}
report={'analyzer_code':str(args.code.resolve()),'application_started':False,'reference_source':'manual source-based component fixtures',
 'limits':['Small synthetic components, not representative project performance',
           'Fixed entry methods isolate execution; one frontend journey includes source-derived natural-language request choice',
           'Empty relation sets are untested, never counted as quality1',
           'Union of possible execution alternatives compared against deterministic source reference'],
 'families':families,'cases':results}
args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=serial)+'\n')
print(json.dumps(families,ensure_ascii=False))
