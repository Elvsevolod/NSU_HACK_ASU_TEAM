//! T11 acceptance: interprocedural value propagation through project-local
//! callee summaries, evaluated on the Common IR only (no language AST).
//!
//! The scenario shape mirrors the real Train Ticket flow used in Gate B:
//! a callee returns `"http://" + serviceName`, and the caller builds the
//! verification-code URL from its result. Here the callee is a hand-built IR
//! function, which proves the mechanism is language-neutral (Gate C's
//! cross-language check is a separate test on real frontends).

use semarch_core::analysis::{Analyzer, Env, Frame, SimpleNameResolver};
use semarch_core::ids::{CallSiteId, FunctionId};
use semarch_core::ir::{BinaryOp, CallSite, Function, SymbolKind, ValueExpr};
use semarch_core::span::SourceSpan;
use semarch_core::value::AbstractValue;

fn span(file: u32, start: u32, end: u32) -> SourceSpan {
    SourceSpan {
        file: file.into(),
        start_byte: start,
        end_byte: end,
        start_row: 0,
        start_col: start,
        end_row: 0,
        end_col: end,
    }
}

/// `getServiceUrl(String serviceName) -> "http://" + serviceName`
fn get_service_url(id: u32) -> Function {
    Function {
        id: FunctionId(id),
        name: "getServiceUrl".into(),
        qualified: Some("TokenServiceImpl.getServiceUrl".into()),
        kind: SymbolKind::Method,
        span: span(1, 100, 200),
        params: vec![ValueExpr::Parameter { index: 0 }],
        param_names: vec!["serviceName".into()],
        returns: vec![ValueExpr::Binary {
            op: BinaryOp::Add,
            lhs: Box::new(ValueExpr::Str { value: "http://".into() }),
            rhs: Box::new(ValueExpr::Symbolic { name: "serviceName".into() }),
        }],
        is_decl_only: false,
    }
}

fn callsite_get_service_url(id: u32, arg: ValueExpr) -> CallSite {
    CallSite {
        id: CallSiteId(id),
        callee: "getServiceUrl".into(),
        receiver: None,
        args: vec![arg],
        span: span(1, 380, 420),
        name_span: None,
    }
}

#[test]
fn project_callee_return_substitutes_arguments() {
    // summary: callee registered via the trivial name resolver
    let callee = get_service_url(1);
    let functions = vec![callee];

    let cs = callsite_get_service_url(9, ValueExpr::Str { value: "ts-verification-code-service".into() });
    let callsites = vec![cs.clone()];

    let resolver = SimpleNameResolver { functions: &functions };
    let analyzer = Analyzer::new(Env::default(), &callsites).with_resolver(&resolver);

    let got = analyzer.eval(&ValueExpr::CallResult { callsite: cs.id });
    assert_eq!(
        got,
        AbstractValue::str_val("http://ts-verification-code-service"),
        "callee return must be evaluated with actual args bound by name"
    );
}

#[test]
fn callee_parameter_shadows_scenario_env() {
    // env says serviceName = "seed"; the actual argument wins (closest scope)
    let functions = vec![get_service_url(1)];
    let mut env = Env::default();
    env.insert("serviceName".into(), AbstractValue::str_val("seed"));

    let cs = callsite_get_service_url(10, ValueExpr::Str { value: "override".into() });
    let callsites = vec![cs.clone()];

    let resolver = SimpleNameResolver { functions: &functions };
    let analyzer = Analyzer::new(env, &callsites).with_resolver(&resolver);

    let got = analyzer.eval(&ValueExpr::CallResult { callsite: cs.id });
    assert_eq!(got, AbstractValue::str_val("http://override"));
}

#[test]
fn unresolvable_callee_is_unknown_never_false() {
    let cs = callsite_get_service_url(11, ValueExpr::Str { value: "x".into() });
    let callsites = vec![cs.clone()];
    // No resolver attached: only builtins can decide → Unknown.
    let analyzer = Analyzer::new(Env::default(), &callsites);
    let got = analyzer.eval(&ValueExpr::CallResult { callsite: cs.id });
    assert_eq!(got, AbstractValue::Unknown);
}

#[test]
fn ambiguous_simple_name_is_unknown_not_a_guess() {
    let duplicated = get_service_url(1);
    let tweak = Function {
        id: FunctionId(2),
        name: "getServiceUrl".into(),
        ..duplicated.clone()
    };
    let functions = vec![duplicated, tweak];

    let cs = callsite_get_service_url(12, ValueExpr::Str { value: "v".into() });
    let callsites = vec![cs.clone()];

    let resolver = SimpleNameResolver { functions: &functions };
    let analyzer = Analyzer::new(Env::default(), &callsites).with_resolver(&resolver);
    let got = analyzer.eval(&ValueExpr::CallResult { callsite: cs.id });
    assert_eq!(got, AbstractValue::Unknown);
}

#[test]
fn recursion_depth_is_capped_not_infinite() {
    // f(n) calls itself with an unchanged argument; summaring must terminate
    // via MAX_DEPTH and stay Unknown, never loop forever.
    let rec = Function {
        id: FunctionId(3),
        name: "recurse".into(),
        qualified: None,
        kind: SymbolKind::Function,
        span: span(2, 0, 50),
        params: vec![ValueExpr::Parameter { index: 0 }],
        param_names: vec!["n".into()],
        returns: vec![ValueExpr::CallResult { callsite: CallSiteId(20) }],
        is_decl_only: false,
    };
    let functions = vec![rec];
    let cs = CallSite {
        id: CallSiteId(20),
        callee: "recurse".into(),
        receiver: None,
        args: vec![ValueExpr::Int { value: 1 }],
        span: span(2, 10, 20),
        name_span: None,
    };
    let callsites = vec![cs.clone()];

    let resolver = SimpleNameResolver { functions: &functions };
    let analyzer = Analyzer::new(Env::default(), &callsites).with_resolver(&resolver);
    let got = analyzer.eval(&ValueExpr::CallResult { callsite: cs.id });
    assert_eq!(got, AbstractValue::Unknown);
}

#[test]
fn frame_is_public_api_for_downstream_framework_adapters() {
    // Frame/Env are part of the analyzer surface; each of them stays usable
    // constructible with defaults.
    let frame = Frame::default();
    assert!(frame.params.is_empty() && frame.names.is_empty());
    let env = Env::default();
    assert!(env.is_empty());
}
