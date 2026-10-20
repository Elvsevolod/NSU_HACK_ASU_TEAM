//! Gate B: the Train Ticket verification-code contract, end to end on the
//! REAL source (not a fixture):
//!
//! `TokenServiceImpl#getToken` guards its remote verification call with
//! `!StringUtils.isEmpty(verifyCode)`. Scenario S0 logs in with an empty
//! verification code, so the guard proves false on that path and the remote
//! effect must be recorded as **excluded** with evidence — gold S0 has
//! exactly 0 remote edges. A non-empty code keeps the effect possible; an
//! *unknown* code must keep it possible too (`unknown != false`).
//!
//! The framework mapping `restTemplate.exchange(..)` → HttpCall is the
//! generic-HTTP-adapter contract (T15+); here the test provides the
//! adapter's declared output so the gate isolates the *guard mechanism*.

use std::collections::BTreeMap;

use semarch_core::value::AbstractValue;
use semarch_core::{
    Allocator, Analyzer, Evidence, EvidenceStatus, Effect, GuardVerdict, Language,
    LanguageFrontend, ParseContext, ParsedFile, UnaryOp, ValueExpr, apply_verdict,
};
use semarch_frontend_java::JavaFrontend;

const TOKEN_SERVICE: &str =
    "tt-challenge/targets/trainticket/ts-auth-service/src/main/java/auth/service/impl/TokenServiceImpl.java";

fn parse_real_file() -> ParsedFile {
    let path = std::format!(
        "{}/../../../{}",
        env!("CARGO_MANIFEST_DIR"),
        TOKEN_SERVICE
    );
    let source = std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("gate B needs the Train Ticket tree ({e}): {path}"));
    let mut fe = JavaFrontend::new().expect("grammar ABI ok");
    let mut alloc = Allocator::default();
    let mut diags = Vec::new();
    let mut ctx = ParseContext::new(0u32.into(), Language::Java, &mut alloc, &mut diags);
    fe.parse(&mut ctx, &source).expect("parse succeeds")
}

/// The `!StringUtils.isEmpty(verifyCode)` guard condition: strictly a
/// `Not(CallResult)` whose call is the `isEmpty` builtin.
fn find_guard(pf: &ParsedFile) -> ValueExpr {
    pf.guard_conditions
        .iter()
        .find(|g| {
            matches!(
                &g.condition,
                ValueExpr::Unary {
                    op: UnaryOp::Not,
                    operand,
                } if matches!(
                    &**operand,
                    ValueExpr::CallResult { callsite }
                        if pf
                            .callsites
                            .iter()
                            .any(|c| c.id == *callsite && c.callee == "isEmpty")
                )
            )
        })
        .map(|g| g.condition.clone())
        .expect("the `!StringUtils.isEmpty(..)` guard must be extracted")
}

/// The adapter declares the remote effect as `possible`; the guard
/// mechanism (not the adapter) decides the final status.
fn adapter_effect() -> (Effect, Evidence) {
    (
        Effect::HttpCall {
            url: "http://ts-verification-code-service/api/v1/verifycode/verify/{verifyCode}"
                .into(),
        },
        Evidence::possible("generic_http_adapter:restTemplate.exchange"),
    )
}

fn is_http(e: &Effect) -> bool {
    matches!(e, Effect::HttpCall { .. })
}

#[test]
fn empty_verify_code_excludes_remote_effect_with_evidence() {
    let pf = parse_real_file();
    let guard = find_guard(&pf);

    let mut effects = vec![adapter_effect()];
    assert_eq!(effects[0].1.status, EvidenceStatus::Possible);

    // S0 initial state: the user submits an *empty* verification code.
    let env = BTreeMap::from([(
        "verifyCode".to_string(),
        AbstractValue::str_val(""),
    )]);
    let analyzer = Analyzer::new(env, &pf.callsites);
    let verdict = analyzer.eval_condition(&guard);
    assert_eq!(
        verdict,
        GuardVerdict::ProvesFalse,
        "an empty code must prove the guard false, not merely unknown"
    );
    apply_verdict(
        &mut effects,
        is_http,
        verdict,
        "guard_proves_false:StringUtils.isEmpty(verifyCode)==true",
    );
    assert_eq!(effects[0].1.status, EvidenceStatus::Excluded);
    assert!(effects[0].1.reason.contains("guard_proves_false"));
}

#[test]
fn nonempty_verify_code_keeps_remote_effect_possible() {
    let pf = parse_real_file();
    let guard = find_guard(&pf);

    let mut effects = vec![adapter_effect()];
    let env = BTreeMap::from([(
        "verifyCode".to_string(),
        AbstractValue::str_val("abcd"),
    )]);
    let analyzer = Analyzer::new(env, &pf.callsites);
    let verdict = analyzer.eval_condition(&guard);
    assert_eq!(verdict, GuardVerdict::ProvesTrue);
    apply_verdict(&mut effects, is_http, verdict, "guard_proves_true");
    // The remote call really happens on this path: still possible (v0 has
    // no "confirmed" upgrade for framework mappings).
    assert_eq!(effects[0].1.status, EvidenceStatus::Possible);
}

#[test]
fn unknown_verify_code_stays_possible_never_false() {
    let pf = parse_real_file();
    let guard = find_guard(&pf);

    let mut effects = vec![adapter_effect()];

    // No binding for verifyCode at all: the scenario provides nothing.
    let analyzer = Analyzer::new(BTreeMap::new(), &pf.callsites);
    let verdict = analyzer.eval_condition(&guard);
    assert_eq!(
        verdict,
        GuardVerdict::Unknown,
        "unknown != false: no binding means no decision"
    );
    apply_verdict(&mut effects, is_http, verdict, "no_decision");
    assert_eq!(effects[0].1.status, EvidenceStatus::Possible);
}
