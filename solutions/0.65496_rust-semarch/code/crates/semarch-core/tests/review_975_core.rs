//! Prepared against 975ab41 public APIs. NOT compiled in the audit environment.
//! These tests specify conservative safety, not full heap precision.
use semarch_core::{analyze_body, Env, SourceSpan};
use semarch_core::ids::{BlockId, CallSiteId, FunctionId, GuardId};
use semarch_core::ir::{BasicBlock,FunctionBody,Statement,Terminator,ValueExpr,GapReason,CallSite,UnaryOp};
use semarch_core::value::{AbstractValue,LanguageProfile};
use semarch_core::cfg::GuardVerdict;
fn b(n:u32)->BlockId{n.into()}
fn s()->SourceSpan{SourceSpan{file:0u32.into(),start_byte:0,end_byte:1,start_row:0,start_col:0,end_row:0,end_col:1}}
fn sym(name:&str)->ValueExpr{ValueExpr::Symbolic{name:name.into()}}
fn body(blocks:Vec<BasicBlock>)->FunctionBody{FunctionBody{function:FunctionId(0),entry:b(0),exits:blocks.iter().filter(|b|b.terminator.is_exit()).map(|b|b.id).collect(),blocks,guards:vec![],gaps:vec![]}}
#[test]
fn gap_incoming_to_a_previously_clean_join_is_not_forgotten(){
 for order in [vec![0,1,3,2,4,5],vec![0,2,3,1,4,5]] {
  let blocks=order.iter().map(|&id| BasicBlock{id:b(id),statements:vec![],span:Some(s()),terminator:match id{
   0=>Terminator::Branch{guard:GuardId(0),condition:ValueExpr::Unknown,then_block:b(1),else_block:b(2)},
   1=>Terminator::Goto{next:b(3)},
   2=>Terminator::Gap{reason:GapReason::UnsupportedStatement,detail:"may modify tracked x".into(),next:Some(b(3))},
   3=>Terminator::Branch{guard:GuardId(1),condition:sym("x"),then_block:b(4),else_block:b(5)},
   _=>Terminator::Return{value:None}
  }}).collect();
  let mut env=Env::new();env.insert("x".into(),AbstractValue::bool(true));
  let a=analyze_body(&body(blocks),env,&[],None,LanguageProfile::java());
  assert!(a.tainted_blocks.contains(&b(3)),"incoming proof-validity must join regardless of witness order {order:?}: {a:?}");
 }
}
fn after_write(statement:Statement)->GuardVerdict {
 let cs=CallSite{id:CallSiteId(0),callee:"getVerificationCode".into(),receiver:Some(sym("dto")),args:vec![],span:s(),name_span:None};
 let condition=ValueExpr::Unary{op:UnaryOp::Not,operand:Box::new(ValueExpr::CallResult{callsite:CallSiteId(1)})};
 let isempty=CallSite{id:CallSiteId(1),callee:"isEmpty".into(),receiver:Some(sym("StringUtils")),args:vec![ValueExpr::CallResult{callsite:cs.id}],span:s(),name_span:None};
 let blocks=vec![BasicBlock{id:b(0),statements:vec![statement],terminator:Terminator::Branch{guard:GuardId(0),condition,then_block:b(1),else_block:b(2)},span:Some(s())},BasicBlock{id:b(1),statements:vec![],terminator:Terminator::Return{value:None},span:Some(s())},BasicBlock{id:b(2),statements:vec![],terminator:Terminator::Return{value:None},span:Some(s())}];
 let mut env=Env::new();env.insert("dto.verificationCode".into(),AbstractValue::str_val(""));
 analyze_body(&body(blocks),env,&[cs,isempty],None,LanguageProfile::java()).decisions[0].verdict
}
#[test]
fn field_write_cannot_leave_the_old_bound_property_as_a_proof(){
 let v=after_write(Statement::Assign{target:ValueExpr::Field{base:Box::new(sym("dto")),name:"verificationCode".into()},value:ValueExpr::Str{value:"X".into()}});
 assert_ne!(v,GuardVerdict::ProvesFalse,"either model the write or invalidate the cached property");
}
#[test]
fn replacing_a_receiver_does_not_preserve_its_previous_object_properties(){
 let v=after_write(Statement::Assign{target:sym("dto"),value:ValueExpr::Unknown});
 assert_eq!(v,GuardVerdict::Unknown,"the replacement object does not inherit old dto.* facts");
}
