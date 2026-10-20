"""A source-only independent workflow; expected edges are checker-owned.

Read HTTP list -> Class<T> array -> choose row -> partial DTO -> persist ->
remote rejection -> fallback -> reread. Explicit HTTP and NL are separate.
"""
import json
from pathlib import Path
from analyzer.project import Project
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState
from analyzer.request import Request
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex,ContractGrounder
from builders import build


PORTAL='''import java.util.*;import org.springframework.web.client.RestTemplate;
 import org.springframework.http.*;import com.fasterxml.jackson.databind.ObjectMapper;
 class DocumentView{public String id;public int revision;public boolean approved;}
 class Approval{public String id;public int revision;public boolean approved;}
 class PortalGateway{RestTemplate rest;
  <T>T decode(String text,Class<T> type){return new ObjectMapper().readValue(text,type);}
  @GetMapping("/library") List<DocumentView> listDocuments(){
   String text=rest.getForObject("http://docs/documents",String.class);
   return Arrays.asList(decode(text,DocumentView[].class));}
  @PostMapping("/library/approve") DocumentView approveDocument(@RequestBody Approval input){
   return rest.postForObject("http://docs/documents/"+input.id+"/approve",input,DocumentView.class);}
 }'''
DOCS='''import java.util.*;import org.springframework.web.client.*;import org.springframework.http.*;
 import org.springframework.data.jpa.repository.JpaRepository;
 @Entity @Table(name="documents")class Document{@Id public String id;public int revision;public boolean approved;}
 class Approval{public String id;public int revision;public boolean approved;}
 interface Store extends JpaRepository<Document,String>{List<Document> findAll();Document findById(String id);Document save(Document value);}
 class DocumentController{Store store;RestTemplate rest;
  @GetMapping("/documents") List<Document> listDocuments(){return store.findAll();}
  @PostMapping("/documents/{id}/approve") ResponseEntity<Document> approveDocument(@PathVariable String id,@RequestBody Approval input){
   Document value=store.findById(id);if(value.revision!=input.revision){return new ResponseEntity<Document>(null,HttpStatus.CONFLICT);}
   value.approved=input.approved;value.revision++;store.save(value);
   try{rest.postForObject("http://audit/events",id,String.class);}catch(HttpServerErrorException failure){fallback();}
   return ResponseEntity.ok(value);}
  void fallback(){}
 }'''
AUDIT='''import org.springframework.http.*;class AuditController{
 @PostMapping("/events") ResponseEntity<String> accept(@RequestBody String id){return new ResponseEntity<String>(null,HttpStatus.SERVICE_UNAVAILABLE);}}'''


def fixture(root):
    merged={'project':'documents','nodes':{},'edges':[]};ids={};database=None
    for module,source in [('portal',PORTAL),('docs',DOCS),('audit',AUDIT)]:
        project,db,local=build(root/module,{'Api.java':source},module=module,
             rows={'documents':[{'id':'D7','revision':7,'approved':0}]} if module=='docs' else {})
        for node in project.skeleton['nodes'].values():
            if node.get('file'):node['file']=module+'/'+node['file']
            for origin in node.get('origin',[]):origin['file']=module+'/'+origin['file']
        merged['nodes'].update(project.skeleton['nodes']);merged['edges'].extend(project.skeleton['edges'])
        ids.update({module+'.'+key:value for key,value in local.items()})
        if module=='docs':database=db
    (root/'skeleton.json').write_text(json.dumps(merged))
    (root/'portal/ui.js').write_text('''new Vue({data:{documents:[]},methods:{
      listDocuments(){var vm=this;$.ajax({url:"/library",type:"GET",success:function(data){vm.documents=data;}});},
      approveDocument(item){var input={id:item.id,revision:item.revision,approved:true};
       $.ajax({url:"/library/approve",type:"POST",contentType:"application/json",data:JSON.stringify(input)});}
      }});''')
    (root/'portal/page.html').write_text('''<script src="ui.js"></script><button @click="listDocuments">List documents</button>
      <table><tr v-for="item in documents"><td>{{item.id}}</td><td><button @click="approveDocument(item)">Approve document</button></td></tr></table>''')
    return Project(root/'skeleton.json',root),database,ids


def expected(ids,write=False):
    get=lambda name:ids[name]
    if not write:
        portal=get('portal.PortalGateway.listDocuments');server=get('docs.DocumentController.listDocuments');decode=get('portal.PortalGateway.decode')
        return {('', 'executes',mid) for mid in [portal,server,decode]} | {
          (portal,'calls',decode),(portal,'remote',server),(server,'data','res:table:docs.documents')}
    portal=get('portal.PortalGateway.approveDocument');server=get('docs.DocumentController.approveDocument')
    fallback=get('docs.DocumentController.fallback');audit=get('audit.AuditController.accept')
    return {('', 'executes',mid) for mid in [portal,server,fallback,audit]} | {
       (server,'calls',fallback),(portal,'remote',server),(server,'remote',audit),
       (server,'data','res:table:docs.documents')}


def test_explicit_http_array_selection_and_state_continuity(tmp_path):
    project,db,ids=fixture(tmp_path);state=ScenarioState(db)
    first=Engine(project,state);rows=first.run(ids['portal.PortalGateway.listDocuments'],Request.http('portal','GET','/library'))
    assert rows==[{'id':'D7','revision':7,'approved':False}]
    assert first.edges==expected(ids)
    body={'id':rows[0]['id'],'revision':rows[0]['revision'],'approved':True}
    second=Engine(project,first.state)
    result=second.run(ids['portal.PortalGateway.approveDocument'],Request.http('portal','POST','/library/approve',body=body))
    assert result=={'id':'D7','revision':8,'approved':True}
    assert second.edges==expected(ids,True)
    bound=second.request_events[0]['bound_arguments'][0]['value']
    assert (bound['id'],bound['revision'],bound['approved'])==('D7',7,True)
    assert [row['operation'] for row in second.data_operations]==['findById','save']
    assert [row['status'] for row in second.http_responses if not row.get('entered',False)]==[]
    third=Engine(project,second.state)
    assert third.run(ids['portal.PortalGateway.listDocuments'],Request.http('portal','GET','/library'))==[result]
    assert third.edges==expected(ids)
    assert not third.state.database.unknown_tables


def test_natural_language_selects_actual_array_result_in_next_request(tmp_path):
    project,db,ids=fixture(tmp_path);frontend=Frontend(project)
    grounder=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{},'choice_rules':[]})
    from analyzer.__main__ import analyze
    scenario={'id':'independent-documents','steps':[{'n':1,'action':'List documents'},
        {'n':2,'action':'Approve the first document'},{'n':3,'action':'List documents'}]}
    _,trace=analyze(project,frontend,ContractIndex(project,frontend),None,db,
        {'facts':{},'unresolved':[],'choice_rules':[]},scenario,path_limit=4,grounder_type=ContractGrounder)
    steps=trace['steps']
    assert len(steps[1]['alternatives'])==1
    selected=steps[1]['alternatives'][0]
    assert selected['entry']==ids['portal.PortalGateway.approveDocument']
    assert selected['request']['body']=={'id':'D7','revision':7,'approved':True}
    assert selected['result']=={'id':'D7','revision':8,'approved':True}
    assert steps[2]['alternatives'][0]['result']==[selected['result']]


def test_stale_revision_rejects_before_write_and_remote(tmp_path):
    project,db,ids=fixture(tmp_path);engine=Engine(project,ScenarioState(db))
    engine.run(ids['portal.PortalGateway.approveDocument'],Request.http('portal','POST','/library/approve',
        body={'id':'D7','revision':6,'approved':True}))
    assert [event['operation'] for event in engine.data_operations]==['findById']
    assert ids['audit.AuditController.accept'] not in {t for _,k,t in engine.edges if k=='executes'}
    assert engine.state.database.tables[('docs','documents')]==[{'id':'D7','revision':7,'approved':False}]
