//! Python fixtures with exact assertions (T06 acceptance), mirroring the
//! Java fixture tests for T07 parity.

use semarch_core::{
    Allocator, BinaryOp, Language, LanguageFrontend, ParseContext, ParsedFile,
    SymbolKind, UnaryOp, ValueExpr,
};
use semarch_frontend_python::PythonFrontend;

fn parse(src: &str) -> (ParsedFile, Vec<semarch_core::FrontendError>) {
    let mut fe = PythonFrontend::new().expect("grammar ABI ok");
    let mut alloc = Allocator::default();
    let mut diags = Vec::new();
    let mut ctx = ParseContext::new(0u32.into(), Language::Python, &mut alloc, &mut diags);
    let parsed = fe.parse(&mut ctx, src).expect("parse succeeds");
    (parsed, diags)
}

const FIXTURE: &str = r#"
import requests as rq
from os.path import join

class Client:
    def call(self, url):
        if url == "":
            return join("a", "b")
        if not rq.get(url).ok:
            return None
        return rq.get(url).text

@app.route("/login")
def login(name):
    return name
"#;

#[test]
fn imports_normalized() {
    let (pf, _) = parse(FIXTURE);
    let shapes: Vec<(String, Option<String>)> =
        pf.imports.iter().map(|i| (i.path.clone(), i.alias.clone())).collect();
    assert_eq!(
        shapes,
        vec![
            ("requests".into(), Some("rq".into())),
            ("os.path.join".into(), None),
        ]
    );
}

#[test]
fn methods_qualified_names_arities() {
    let (pf, _) = parse(FIXTURE);
    assert_eq!(pf.functions.len(), 2);

    let call = &pf.functions[0];
    assert_eq!(call.name, "call");
    assert_eq!(call.qualified.as_deref(), Some("Client"));
    assert_eq!(call.kind, SymbolKind::Method);
    assert_eq!(call.params.len(), 2);

    let login = &pf.functions[1];
    assert_eq!(login.name, "login");
    assert_eq!(login.kind, SymbolKind::Function);
    assert_eq!(login.params.len(), 1);
}

#[test]
fn decorator_captured_with_args() {
    let (pf, _) = parse(FIXTURE);
    let names: Vec<&str> = pf.annotations.iter().map(|a| a.name.as_str()).collect();
    assert_eq!(names, ["app.route"]);
    // Raw argument text between the parentheses, as written.
    assert_eq!(pf.annotations[0].args.as_deref(), Some("\"/login\""));
}

#[test]
fn callsites_with_receivers_and_args() {
    let (pf, _) = parse(FIXTURE);
    let shapes: Vec<(&str, Option<ValueExpr>, usize)> = pf
        .callsites
        .iter()
        .map(|c| (c.callee.as_str(), c.receiver.clone(), c.args.len()))
        .collect();
    assert_eq!(
        shapes,
        vec![
            // join("a", "b")
            ("join", None, 2),
            // rq.get(url) — guard condition, registered once
            ("get", Some(ValueExpr::Symbolic { name: "rq".into() }), 1),
            // rq.get(url) — return expression
            ("get", Some(ValueExpr::Symbolic { name: "rq".into() }), 1),
        ]
    );
    // First condition is `url == ""` (not a call).
    match &pf.guard_conditions[0].condition {
        ValueExpr::Binary { op: BinaryOp::Eq, .. } => {}
        other => panic!("expected Eq guard, got {other:?}"),
    }
    // Second condition is `not rq.get(url).ok`.
    match &pf.guard_conditions[1].condition {
        ValueExpr::Unary { op: UnaryOp::Not, .. } => {}
        other => panic!("expected Not guard, got {other:?}"),
    }
}

#[test]
fn verification_code_shape_string_guard() {
    let (pf, _) = parse(
        "def stub(verify_code, remote):\n    if verify_code == '':\n        return None\n    return client.verify_code(verify_code, remote)\n",
    );
    let verify = pf
        .callsites
        .iter()
        .find(|c| c.callee == "verify_code")
        .expect("verify_code callsite");
    assert_eq!(
        verify.receiver,
        Some(ValueExpr::Symbolic { name: "client".into() })
    );
    assert_eq!(
        verify.args,
        vec![
            ValueExpr::Symbolic { name: "verify_code".into() },
            ValueExpr::Symbolic { name: "remote".into() }
        ]
    );
    // Empty-string literal guard proves false for the `true`-arm.
    match &pf.guard_conditions[0].condition {
        ValueExpr::Binary {
            op: BinaryOp::Eq,
            lhs,
            rhs,
        } => {
            assert_eq!(**lhs, ValueExpr::Symbolic { name: "verify_code".into() });
            assert_eq!(**rhs, ValueExpr::Str { value: String::new() });
        }
        other => panic!("expected Eq guard, got {other:?}"),
    }
}

#[test]
fn malformed_source_does_not_panic() {
    let (pf, _) = parse("def f(:\nreturn");
    // The semantic guarantee: a flat syntax error never panics the frontend
    // and never fabricates facts; whatever normalized facts the grammar
    // still yields are reported, the rest is `unknown`.
    assert_eq!(pf.language, Language::Python);
    assert_eq!(pf.functions.len(), 1);
    assert_eq!(pf.callsites.len(), 0);
}
