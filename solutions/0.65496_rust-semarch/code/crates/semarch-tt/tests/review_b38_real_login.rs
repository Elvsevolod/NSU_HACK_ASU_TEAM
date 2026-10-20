//! Missing N06 gate: REAL TokenServiceImpl contains `new` and `catch`.
//! These are expected regression tests, not assertions that native tests passed.
use std::path::{Path,PathBuf};
use semarch_scenario::scenario::{Scenario,Step};
use semarch_tt::pipeline::{AnalyzerConfig,LoadOptions,TtAnalyzer};
fn root()->PathBuf { Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..").join("tt-challenge") }
fn run(action:&str)->semarch_tt::engine::ScenarioOutcome {
 let r=root(); assert!(r.join("context/README.md").is_file(),"real contest fixture required");
 let a=TtAnalyzer::load_with(&r,&LoadOptions{require_sources:true}).expect("real sources");
 let s=Scenario{project:"trainticket".into(),id:"Review-real-login".into(),title:String::new(),description:String::new(),input:"text".into(),steps:vec![Step{n:1,action:action.into()}]};
 a.semantic_run(&s,&AnalyzerConfig::default()).expect("semantic pipeline")
}
fn verify_present(o:&semarch_tt::engine::ScenarioOutcome)->bool {
 o.prediction.remote.iter().any(|(_,t)|t.contains("VerifyCodeController#verifyCode"))
}
#[test]
fn real_empty_login_excludes_verify_despite_later_new_and_catch(){
 let o=run("Log in with an empty verification code");
 assert!(o.steps[0].bindings.iter().flat_map(|b|&b.fields).any(|f|f.name=="verificationCode" && f.value==semarch_tt::request::BoundValue::Empty),"binding precondition");
 assert!(!verify_present(&o),"a proven-empty request must not regain a remote via a whole-method fallback");
}
#[test]
fn real_absent_login_excludes_verify_when_dto_and_context_prove_empty(){
 let o=run("Log in without a verification code");
 assert!(!verify_present(&o));
}
#[test]
fn real_stated_code_still_keeps_verify(){
 let o=run("Log in with username admin and verification code 4578");
 assert!(verify_present(&o),"a negative-only fix must not erase the positive case");
}
#[test]
fn real_context_is_an_input_not_ignored_prose(){
 // Generic unmentioned fields stay Unknown. This particular package EXPLICITLY
 // states no verification code at login. Consume that fact with provenance.
 let context=std::fs::read_to_string(root().join("context/README.md")).unwrap();
 assert!(context.to_lowercase().contains("verification"),"fixture assumption");
 let o=run("Log in with username and password");
 assert!(!verify_present(&o),"read the default context instead of interpreting silence in isolation");
}
