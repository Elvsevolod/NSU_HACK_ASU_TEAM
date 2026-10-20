//! Source -> Tree-sitter lowering -> core analysis. Prepared, NOT compiled here.
use semarch_core::analysis::analyze_body;
use semarch_core::{Allocator, Env, Language, LanguageFrontend, ParseContext};
use semarch_core::value::{AbstractValue, LanguageProfile};
use semarch_frontend_java::JavaFrontend;
fn check(source:&str, expected:i64) {
 let mut frontend=JavaFrontend::new().expect("grammar ABI");
 let mut ids=Allocator::default(); let mut diagnostics=Vec::new();
 let mut ctx=ParseContext::new(0u32.into(),Language::Java,&mut ids,&mut diagnostics);
 let unit=frontend.parse(&mut ctx,source).expect("source parsing");
 assert!(diagnostics.is_empty(),"{diagnostics:?}");
 let f=unit.functions.iter().find(|f|f.name=="f").expect("function f");
 let body=unit.bodies.iter().find(|b|b.function==f.id).expect("lowered f");
 let a=analyze_body(body,Env::new(),&unit.callsites,None,LanguageProfile::java());
 assert_eq!(a.returns.len(),1,"{a:?}");
 assert_eq!(a.returns[0].value,AbstractValue::Int{value:expected},"{a:?}");
}

#[test]
fn return_is_evaluated_before_finally() { check(r#"class Example { int f() { int x=1; try { return x; } finally { x=2; } } }"#, 1); }

#[test]
fn return_in_finally_overrides_pending_return() { check(r#"class Example { int f() { try { return 1; } finally { return 2; } } }"#, 2); }

#[test]
fn nested_ternary_uses_actual_branch_exits() { check(r#"class Example { int f() { return true ? (false ? 1 : 2) : 3; } }"#, 2); }
