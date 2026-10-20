//! Prepared regression tests; not compiled in the review environment.
//! Contract: an exit/decision is the join of ALL visits, not its first visit.
use semarch_core::analysis::analyze_body;
use semarch_core::ids::{BlockId, FunctionId, GuardId};
use semarch_core::ir::{BasicBlock, FunctionBody, Statement, Terminator, ValueExpr, BinaryOp};
use semarch_core::value::{AbstractValue, LanguageProfile};
use semarch_core::{Env, SourceSpan};
use semarch_core::cfg::GuardVerdict;
fn b(n:u32)->BlockId { BlockId::from_raw(n) }
fn x()->ValueExpr { ValueExpr::Symbolic{name:"x".into()} }
fn source()->SourceSpan { SourceSpan {file:0u32.into(),start_byte:0,end_byte:1,start_row:0,start_col:0,end_row:0,end_col:1} }
fn fixture(order:&[u32], exit_kind:&str)->FunctionBody {
 let blocks=order.iter().map(|&id|{
   let mut statements=Vec::new();
   let terminator=match id {
     0=>Terminator::Branch {guard:GuardId::from_raw(0),condition:ValueExpr::Unknown,then_block:b(1),else_block:b(2)},
     1|2=>{ statements.push(Statement::Assign{target:x(),value:ValueExpr::Int{value:id as i64}}); Terminator::Goto{next:b(3)} },
     3=>match exit_kind {
       "throw"=>Terminator::Throw{value:x()},
       "guard"=>Terminator::Branch {guard:GuardId::from_raw(1),condition:ValueExpr::Binary{op:BinaryOp::Eq,lhs:Box::new(x()),rhs:Box::new(ValueExpr::Int{value:1})},then_block:b(4),else_block:b(5)},
       _=>Terminator::Return{value:Some(x())},
     },
     _=>Terminator::Return{value:None},
   };
   BasicBlock{id:b(id),statements,terminator,span:Some(source())}
 }).collect::<Vec<_>>();
 FunctionBody{function:FunctionId::from_raw(0),entry:b(0),exits:blocks.iter().filter(|n|n.terminator.is_exit()).map(|n|n.id).collect(),blocks,guards:Vec::new(),gaps:Vec::new()}
}
#[test]
fn return_value_is_joined_after_late_predecessor() {
 for order in [vec![0,1,3,2],vec![0,1,2,3]] {
  let a=analyze_body(&fixture(&order,"return"),Env::new(),&[],None,LanguageProfile::java());
  let site=a.returns.iter().find(|r|r.block==b(3)).expect("merge return");
  assert_eq!(site.value,AbstractValue::Unknown,"block storage order {order:?}: {a:?}");
 }
}
#[test]
fn throw_value_is_joined_after_late_predecessor() {
 // Raw IR transfer test: values are markers, not a source-level Java throw-int.
 let a=analyze_body(&fixture(&[0,1,3,2],"throw"),Env::new(),&[],None,LanguageProfile::java());
 assert_eq!(a.throws.iter().find(|r|r.block==b(3)).unwrap().value,AbstractValue::Unknown);
}
#[test]
fn branch_certificate_cannot_keep_its_first_provisional_truth() {
 let a=analyze_body(&fixture(&[0,1,3,2,4,5],"guard"),Env::new(),&[],None,LanguageProfile::java());
 let d=a.decisions.iter().find(|d|d.block==b(3)).unwrap();
 assert_eq!(d.verdict,GuardVerdict::Unknown,"both incoming x values reach this decision");
}
#[test]
fn reordering_storage_not_edges_does_not_change_return_summary() {
 let a=analyze_body(&fixture(&[0,1,3,2],"return"),Env::new(),&[],None,LanguageProfile::java());
 let z=analyze_body(&fixture(&[0,1,2,3],"return"),Env::new(),&[],None,LanguageProfile::java());
 let vals=|r:&semarch_core::analysis::BodyAnalysis|r.returns.iter().map(|s|(s.block,s.value.clone())).collect::<Vec<_>>();
 assert_eq!(vals(&a),vals(&z));
}
