//! Prepared / not compiled. Extends, does not replace, B38 basic-finally gates.
use semarch_core::{analyze_body,Allocator,Env,Language,LanguageFrontend,ParseContext};
use semarch_core::value::{AbstractValue,LanguageProfile};
use semarch_frontend_java::JavaFrontend;
fn result(src:&str)->Vec<AbstractValue>{
 let mut frontend=JavaFrontend::new().unwrap();let mut alloc=Allocator::default();let mut ds=vec![];
 let mut ctx=ParseContext::new(0u32.into(),Language::Java,&mut alloc,&mut ds);
 let p=frontend.parse(&mut ctx,src).unwrap();assert!(ds.is_empty(),"{ds:?}");
 let f=p.functions.iter().find(|f|f.name=="f").unwrap();let b=p.bodies.iter().find(|b|b.function==f.id).unwrap();
 analyze_body(b,Env::new(),&p.callsites,None,LanguageProfile::java()).returns.into_iter().map(|r|r.value).collect()
}
#[test]
fn normal_inner_try_does_not_run_an_outer_finally_early(){
 assert_eq!(result("class C { int f() { int x=0; try { try { x=1; } finally { x=x+1; } return x; } finally { x=9; } } }"),vec![AbstractValue::Int{value:2}]);
}
#[test]
fn a_normal_inner_try_without_its_own_finally_still_does_not_exit_outer_scope(){
 let values=result("class C { int f() { int x=0; try { try { x=1; } catch (RuntimeException e) { x=1; } return x; } finally { x=9; } } }");
 assert!(!values.is_empty(),"a return must be observed");
 assert!(values.iter().all(|v|*v==AbstractValue::Int{value:1}),"{values:?}");
}
