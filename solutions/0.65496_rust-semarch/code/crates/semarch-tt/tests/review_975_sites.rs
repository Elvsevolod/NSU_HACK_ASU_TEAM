//! Prepared / not compiled. Anchors must name the invocation, not text in arguments.
use std::sync::Arc;
use semarch_core::{CallSite,Language,SourceSpan,ValueExpr};
use semarch_core::ids::CallSiteId;
use semarch_tt::bodies::FileUnit;
fn outer(text:&str)->Option<u32>{
 let s=SourceSpan{file:0u32.into(),start_byte:0,end_byte:text.len() as u32,start_row:0,start_col:0,end_row:0,end_col:text.len() as u32};
 let cs=CallSite{id:CallSiteId(0),callee:"f".into(),receiver:None,args:vec![ValueExpr::Unknown],span:s,name_span:None};
 let u=FileUnit{file:"C.java".into(),language:Language::Java,source:Arc::from(text),callsites:vec![],functions:vec![]};u.anchor_col(&cs)
}
#[test]
fn nested_same_name_invocation_keeps_its_outer_anchor(){assert_eq!(outer("f(f(1))"),Some(0));}
#[test]
fn callee_like_text_in_a_string_is_not_a_call_anchor(){assert_eq!(outer("f(\"f(0)\")"),Some(0));}
#[test]
fn callee_like_text_in_a_comment_is_not_a_call_anchor(){assert_eq!(outer("f(/* f( */ 1)"),Some(0));}
