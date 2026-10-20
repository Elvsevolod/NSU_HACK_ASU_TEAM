//! The binder must not replace a literal by a lowercased search token.
use semarch_tt::request::{bind,BoundValue,FieldDecl};
fn bound(text:&str,field:&str,ty:&str)->BoundValue {
 let d=FieldDecl{name:field.into(),type_raw:Some(ty.into())};
 let r=bind(1,text,"method:probe:a.Ctl#login(a.Dto)","/login",&[d],&[]);
 assert_eq!(r.fields.len(),1); r.fields[0].value.clone()
}
#[test]
fn literal_preserves_case_and_hyphen(){
 assert_eq!(bound("Log in with verification code AbC-4578","verificationCode","String"),BoundValue::Literal("AbC-4578".into()));
}
#[test]
fn literal_preserves_negative_fraction(){
 assert_eq!(bound("Pay with price -12.50","price","double"),BoundValue::Literal("-12.50".into()));
}
#[test]
fn literal_preserves_underscore(){
 assert_eq!(bound("Log in with username FDSE_microservice","username","String"),BoundValue::Literal("FDSE_microservice".into()));
}
#[test]
fn explicit_empty_is_not_a_missing_field(){
 assert_eq!(bound("Log in with an empty verification code","verificationCode","String"),BoundValue::Empty);
}
#[test]
fn omission_needs_deserialization_evidence_before_it_becomes_null(){
 // Existing API only knows a type; it knows neither initializer nor constructor.
 // Proposed corrected contract: the type alone is insufficient to infer null.
 assert!(BoundValue::Absent.abstract_value(Some("String")).is_none());
}
