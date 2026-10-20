//! Source-only two-service fixtures: no target compilation or execution.
//! Native regression tests PREPARED in the audit, not compiled there.
use std::path::{Path,PathBuf};
use std::sync::atomic::{AtomicU64,Ordering};
use semarch_scenario::scenario::{Scenario,Step};
use semarch_tt::pipeline::{AnalyzerConfig,LoadOptions,TtAnalyzer};
use semarch_tt::engine::ScenarioOutcome;
use serde_json::{json,Value};
const FILE:&str="caller/src/main/java/a/Ctl.java";
const DTO:&str="caller/src/main/java/a/Dto.java";
const TARGET_FILE:&str="remote/src/main/java/a/Verifier.java";
const ENTRY:&str="method:caller:a.Ctl#login(a.Dto)";
const HELPER:&str="method:caller:a.Ctl#helper(java.lang.String)";
const REMOTE:&str="method:remote:a.Verifier#verify()";
static SEQ:AtomicU64=AtomicU64::new(0);
struct Fixture {root:PathBuf, first_send:Option<String>}
impl Drop for Fixture { fn drop(&mut self){let _=std::fs::remove_dir_all(&self.root);} }
fn write(root:&Path,rel:&str,text:&str){let p=root.join(rel);std::fs::create_dir_all(p.parent().unwrap()).unwrap();std::fs::write(p,text).unwrap();}
fn position(s:&str,start:usize)->(u32,u32){let prefix=&s[..start];let row=prefix.bytes().filter(|&b|b==b'\n').count()+1;let col=prefix.rfind('\n').map_or(start+1,|i|start-i);(row as u32,col as u32)}
fn method_node(name:&str,desc:&str,file:&str,line:u32,module:&str,owner:&str)->Value{json!({"kind":"method","owner":owner,"name":name,"descriptor":desc,"module":module,"file":file,"line":line})}
fn fixture(main:&str, helper:bool)->Fixture{
 let root=std::env::temp_dir().join(format!("semarch-b38-review-{}-{}",std::process::id(),SEQ.fetch_add(1,Ordering::SeqCst)));
 assert!(!root.exists(),"unexpected preexisting fixture");
 let tail=if helper {"    public void helper(String code) {\n        if (!StringUtils.isEmpty(code)) { send(); }\n    }\n"} else {""};
 let source=format!("package a;\nimport org.springframework.util.StringUtils;\nimport org.springframework.web.bind.annotation.PostMapping;\npublic class Ctl {{\n    @PostMapping(path = \"/login\")\n    public void login(Dto dto) {{\n{main}\n    }}\n{tail}}}\n");
 write(&root,&format!("targets/probe/{FILE}"),&source);
 write(&root,&format!("targets/probe/{DTO}"),"package a;\npublic class Dto {\n private String verificationCode;\n public String getVerificationCode(){return verificationCode;}\n}\n");
 write(&root,&format!("targets/probe/{TARGET_FILE}"),"package a;\npublic class Verifier {\n public void verify() {}\n}\n");
 write(&root,"targets/probe/probe-ui/client.js","$.ajax({url:'/login',type:'POST'});\n");
 let mut nodes=serde_json::Map::new();let mut edges=Vec::new();
 nodes.insert("type:caller:a.Ctl".into(),json!({"kind":"type","fqn":"a.Ctl","type_kind":"class","module":"caller"}));
 nodes.insert("type:caller:a.Dto".into(),json!({"kind":"type","fqn":"a.Dto","type_kind":"class","module":"caller"}));
 nodes.insert("field:caller:a.Dto.verificationCode".into(),json!({"kind":"field","owner":"type:caller:a.Dto","name":"verificationCode","type_raw":"String","type":"java.lang.String","module":"caller","file":DTO,"line":3}));
 nodes.insert("type:remote:a.Verifier".into(),json!({"kind":"type","fqn":"a.Verifier","type_kind":"class","module":"remote"}));
 let mut endpoint=method_node("login","a.Dto",FILE,6,"caller","type:caller:a.Ctl");
 endpoint["annotations"]=json!([{"name":"PostMapping","args":"(path = \"/login\")"}]);
 endpoint["params_as_written"]=json!(["Dto"]);nodes.insert(ENTRY.into(),endpoint);
 nodes.insert(REMOTE.into(),method_node("verify","",TARGET_FILE,3,"remote","type:remote:a.Verifier"));
 let helper_start=source.find("public void helper");
 if let Some(h)=helper_start {let mut n=method_node("helper","java.lang.String",FILE,position(&source,h).0,"caller","type:caller:a.Ctl");n["params_as_written"]=json!(["String"]);nodes.insert(HELPER.into(),n);}
 let mut first_send=None;
 for (needle,callee,target,relation) in [("send();","send",REMOTE,"remote_call"),("helper(\"\");","helper",HELPER,"calls"),("helper(\"X\");","helper",HELPER,"calls"),("helper(code);","helper",HELPER,"calls")] {
  for (offset,_) in source.match_indices(needle){
   let (line,col)=position(&source,offset);
   let owner=if helper_start.is_some_and(|h|offset>h){HELPER}else{ENTRY};
   let id=format!("call:{owner}@{line}:{col}");
   if callee=="send" && first_send.is_none(){first_send=Some(id.clone());}
   let argument=&needle[needle.find('(').unwrap()+1..needle.find(')').unwrap()];
   nodes.insert(id.clone(),json!({"kind":"call_site","method":owner,"callee":callee,"receiver":null,"arg_count":if argument.is_empty(){0}else{1},"args_text":if argument.is_empty(){Vec::<String>::new()}else{vec![argument.to_owned()]},"module":"caller","file":FILE,"line":line,"col":col}));
   edges.push(json!({"source":id,"type":relation,"target":target}));
  }
 }
 write(&root,"skeleton/probe.json",&serde_json::to_string_pretty(&json!({"project":"probe","schema":"review","nodes":nodes,"edges":edges})).unwrap());
 write(&root,"scenarios/S1.json",r#"{"project":"probe","id":"S1","title":"login","description":"","input":"text","steps":[{"n":1,"action":"Log in"}]}"#);
 Fixture{root,first_send}
}
fn run(f:&Fixture,action:&str)->ScenarioOutcome{
 let analyzer=TtAnalyzer::load_with(&f.root,&LoadOptions{require_sources:true}).expect("fixture sources load");
 let s=Scenario{project:"probe".into(),id:"Review".into(),title:String::new(),description:String::new(),input:"text".into(),steps:vec![Step{n:1,action:action.into()}]};
 let out=analyzer.semantic_run(&s,&AnalyzerConfig::default()).expect("semantic fixture");
 assert!(out.steps[0].entries.iter().any(|e|e==ENTRY),"grounding precondition: {:?}",out.steps[0].entries);
 out
}
fn verify(o:&ScenarioOutcome)->bool{o.prediction.remote.iter().any(|(_,t)|t==REMOTE)}
#[test]
fn unrelated_object_creation_does_not_revive_a_false_remote(){
 let f=fixture("        String code = dto.getVerificationCode();\n        if (!StringUtils.isEmpty(code)) { send(); }\n        Object unused = new Object();",false);
 let out=run(&f,"Log in with an empty verification code");
 assert!(!verify(&out),"do not discard the unrelated gap; scope its effects correctly");
}
#[test]
fn two_calls_with_distinct_values_are_not_one_method_visit(){
 let f=fixture("        helper(\"\");\n        helper(\"X\");",true);
 assert!(verify(&run(&f,"Log in")),"the SECOND input opens the remote branch");
}
#[test]
fn reversing_two_helper_calls_preserves_the_union_of_remote_effects(){
 let a=fixture("        helper(\"\");\n        helper(\"X\");",true);
 let b=fixture("        helper(\"X\");\n        helper(\"\");",true);
 let left=verify(&run(&a,"Log in"));let right=verify(&run(&b,"Log in"));
 assert!(left && right,"both independent inputs must be analyzed: {left} vs {right}");
}
#[test]
fn local_scalar_argument_is_read_at_its_actual_call_site(){
 let f=fixture("        String code = dto.getVerificationCode();\n        helper(code);",true);
 assert!(!verify(&run(&f,"Log in with an empty verification code")),"propagate the local scalar, not just dto.* or the entry environment");
}
#[test]
fn same_line_same_name_does_not_share_liveness(){
 let f=fixture("        if (false) send(); send();",false);
 let out=run(&f,"Log in");
 assert!(verify(&out),"the second call stays live");
 let first=f.first_send.as_ref().unwrap();
 assert!(!out.steps[0].effects.iter().any(|e|&e.call_site==first),"the first, false-guarded call must not inherit the second call's proof");
}
