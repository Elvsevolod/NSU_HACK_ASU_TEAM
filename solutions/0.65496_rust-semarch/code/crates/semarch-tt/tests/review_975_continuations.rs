//! Prepared against 975ab41. Source-only two-service pipeline tests, NOT native-run here.
//! Uses seed remote wiring, not a live HTTP service. A separate contract fixture tests real exchange bindings.
use std::path::{Path,PathBuf};
use std::sync::atomic::{AtomicU64,Ordering};
use semarch_scenario::scenario::{Scenario,Step};
use semarch_tt::pipeline::{AnalyzerConfig,LoadOptions,TtAnalyzer};
use semarch_tt::engine::{ScenarioOutcome,Relation};
use serde_json::{json,Value};
const FILE:&str="caller/src/main/java/a/Ctl.java";
const DTO:&str="caller/src/main/java/a/Dto.java";
const RF:&str="remote/src/main/java/a/Verifier.java";
const ENTRY:&str="method:caller:a.Ctl#login(a.Dto)";
const HELPER:&str="method:caller:a.Ctl#helper(java.lang.String)";
const REMOTE:&str="method:remote:a.Verifier#verify()";
const SEND:&str="restTemplate.exchange(\"http://remote/verify\", HttpMethod.GET, null, Boolean.class);";
static SEQ:AtomicU64=AtomicU64::new(0);
struct Fixture{root:PathBuf}
impl Drop for Fixture{fn drop(&mut self){let _=std::fs::remove_dir_all(&self.root);}}
fn write(root:&Path,p:&str,s:&str){let f=root.join(p);std::fs::create_dir_all(f.parent().unwrap()).unwrap();std::fs::write(f,s).unwrap();}
fn pos(s:&str,i:usize)->(u32,u32){let t=&s[..i];((t.bytes().filter(|&x|x==b'\n').count()+1)as u32,(t.rfind('\n').map_or(i+1,|n|i-n))as u32)}
fn method(name:&str,desc:&str,file:&str,line:u32,module:&str,owner:&str)->Value{json!({"kind":"method","owner":owner,"name":name,"descriptor":desc,"module":module,"file":file,"line":line})}
fn fixture(main:&str,helper:&str)->Fixture{
 let root=std::env::temp_dir().join(format!("semarch-review975-{}-{}",std::process::id(),SEQ.fetch_add(1,Ordering::SeqCst)));assert!(!root.exists());
 let main=main.replace("SEND",SEND);let helper=helper.replace("SEND",SEND);
 let src=format!("package a;\nimport org.springframework.util.StringUtils;\nimport org.springframework.web.bind.annotation.PostMapping;\nimport org.springframework.web.client.RestTemplate;\nimport org.springframework.http.HttpMethod;\npublic class Ctl {{\n RestTemplate restTemplate;\n @PostMapping(path=\"/login\")\n public void login(Dto dto) {{\n {main}\n }}\n {helper}\n}}\n");
 write(&root,&format!("targets/probe/{FILE}"),&src);
 write(&root,&format!("targets/probe/{DTO}"),"package a;\npublic class Dto {\n public String verificationCode;\n public String getVerificationCode(){return verificationCode;}\n}\n");
 write(&root,&format!("targets/probe/{RF}"),"package a;\npublic class Verifier {\n public boolean verify(){return true;}\n}\n");
 write(&root,"targets/probe/probe-ui/client.js","$.ajax({url:'/login',type:'POST'});\n");
 let mut n=serde_json::Map::new();let mut es=vec![];
 for (id,fqn,module) in [("type:caller:a.Ctl","a.Ctl","caller"),("type:caller:a.Dto","a.Dto","caller"),("type:remote:a.Verifier","a.Verifier","remote")]{n.insert(id.into(),json!({"kind":"type","fqn":fqn,"type_kind":"class","module":module}));}
 n.insert("field:caller:a.Dto.verificationCode".into(),json!({"kind":"field","owner":"type:caller:a.Dto","name":"verificationCode","type_raw":"String","type":"java.lang.String","module":"caller","file":DTO,"line":3}));
 let mut entry=method("login","a.Dto",FILE,9,"caller","type:caller:a.Ctl");entry["annotations"]=json!([{"name":"PostMapping","args":"(path=\"/login\")"}]);entry["params_as_written"]=json!(["Dto"]);n.insert(ENTRY.into(),entry);
 n.insert(REMOTE.into(),method("verify","",RF,3,"remote","type:remote:a.Verifier"));
 let hs=src.find("public boolean helper");if let Some(h)=hs{n.insert(HELPER.into(),method("helper","java.lang.String",FILE,pos(&src,h).0,"caller","type:caller:a.Ctl"));}
 for (needle,callee,target,relation,args) in [("exchange(\"http://remote/verify\"","exchange",REMOTE,"remote_call","(\"http://remote/verify\", HttpMethod.GET, null, Boolean.class)"),("helper(\"\")","helper",HELPER,"calls","(\"\")"),("helper(\"X\")","helper",HELPER,"calls","(\"X\")")]{
  for (offset,_) in src.match_indices(needle){let (line,col)=pos(&src,offset);let owner=if hs.is_some_and(|h|offset>h){HELPER}else{ENTRY};let id=format!("call:{owner}@{line}:{col}");
   n.insert(id.clone(),json!({"kind":"call_site","method":owner,"callee":callee,"receiver":if callee=="exchange"{Some("restTemplate")}else{None},"receiver_type":if callee=="exchange"{Some("org.springframework.web.client.RestTemplate")}else{None},"arg_count":if callee=="exchange"{4}else{1},"args_text":args,"module":"caller","file":FILE,"line":line,"col":col}));
   es.push(json!({"source":id,"type":relation,"target":target}));
  }
 }
 write(&root,"skeleton/probe.json",&serde_json::to_string_pretty(&json!({"project":"probe","schema":"review","nodes":n,"edges":es})).unwrap());
 write(&root,"scenarios/S1.json",r#"{"project":"probe","id":"S1","title":"login","description":"","input":"text","steps":[{"n":1,"action":"Log in"}]}"#);
 Fixture{root}
}
fn run(f:&Fixture,action:&str)->ScenarioOutcome{
 let a=TtAnalyzer::load_with(&f.root,&LoadOptions{require_sources:true}).unwrap();
 let s=Scenario{project:"probe".into(),id:"review975".into(),title:String::new(),description:String::new(),input:"text".into(),steps:vec![Step{n:1,action:action.into()}]};
 let o=a.semantic_run(&s,&AnalyzerConfig::default()).unwrap();assert_eq!(o.steps[0].entries,vec![ENTRY.to_owned()],"entry precondition, do not accept vacuous no-remote");o
}
fn remote(o:&ScenarioOutcome)->bool{o.prediction.remote.iter().any(|(_,t)|t==REMOTE)}
const PREDICATE:&str="public boolean helper(String code){ return !StringUtils.isEmpty(code); }";
#[test]
fn negative_local_return_prunes_the_callers_later_remote(){let f=fixture("boolean ok=helper(\"\"); if(!ok) return; SEND",PREDICATE);assert!(!remote(&run(&f,"Log in")),"callee result must resume caller before remote");}
#[test]
fn positive_local_return_keeps_the_callers_remote(){let f=fixture("boolean ok=helper(\"X\"); if(!ok) return; SEND",PREDICATE);assert!(remote(&run(&f,"Log in")));}
#[test]
fn no_normal_return_from_helper_stops_the_callers_normal_continuation(){let f=fixture("helper(\"\"); SEND","public boolean helper(String code){throw new IllegalStateException();}");assert!(!remote(&run(&f,"Log in")),"throw-only is not Unknown-normal-return");}
#[test]
fn unknown_helper_result_keeps_a_possible_continuation(){let f=fixture("if(helper(\"\")) { SEND }","public boolean helper(String code){return external();}");assert!(remote(&run(&f,"Log in")),"unknown must not be converted into a false result");}
#[test]
fn possible_caller_cannot_make_the_callees_remote_unconditionally_confirmed(){let f=fixture("if(external()) helper(\"X\");","public boolean helper(String code){SEND return true;}");let o=run(&f,"Log in");let remote_events=o.steps[0].effects.iter().filter(|e|e.relation==Relation::Remote).collect::<Vec<_>>();assert!(!remote_events.is_empty());assert!(remote_events.iter().all(|e|e.status!="confirmed"),"caller certainty must cross call boundaries: {remote_events:#?}");}
#[test]
fn an_explicit_field_write_cannot_be_pruned_using_the_old_input(){let f=fixture("dto.verificationCode=\"X\"; if(!StringUtils.isEmpty(dto.getVerificationCode())) { SEND }","");assert!(remote(&run(&f,"Log in with an empty verification code")),"model field write or invalidate old binding before a certificate");}
