//! Java fixtures with exact assertions (T05 acceptance). Spans stay
//! byte-anchored: assertions below re-verify source text at span offsets.

use semarch_core::{
    Allocator, BinaryOp, Language, LanguageFrontend, ModuleDecl, ParseContext, ParsedFile,
    SymbolKind, UnaryOp, ValueExpr,
};
use semarch_frontend_java::JavaFrontend;

fn parse(src: &str) -> ParsedFile {
    let mut fe = JavaFrontend::new().expect("grammar ABI ok");
    let mut alloc = Allocator::default();
    let mut diags = Vec::new();
    let mut ctx =
        ParseContext::new(0u32.into(), Language::Java, &mut alloc, &mut diags);
    let parsed = fe.parse(&mut ctx, src).expect("parse succeeds");
    assert!(diags.is_empty(), "unexpected diagnostics: {diags:?}");
    parsed
}

const FIXTURE: &str = r#"
package fallback.msproject;

import com.google.common.annotations.VisibleForTesting;
import static java.util.Objects.requireNonNull;

public class Fallback {
    @Deprecated
    public String concat(String lhs, String rhs) {
        if ("".equals(lhs)) {
            return rhs;
        }
        return lhs.concat(rhs);
    }

    public void wrap(String key) {
        requireNonNull(key, "key");
        if (key != null && !key.isEmpty()) {
            id(key);
        }
    }
}
"#;

#[test]
fn module_package_and_imports() {
    let pf = parse(FIXTURE);
    assert_eq!(
        pf.module,
        Some(ModuleDecl {
            id: 0u32.into(),
            path: "fallback.msproject".into(),
        })
    );
    let paths: Vec<(String, Option<String>)> =
        pf.imports.iter().map(|i| (i.path.clone(), i.alias.clone())).collect();
    assert_eq!(
        paths,
        vec![
            ("com.google.common.annotations.VisibleForTesting".into(), None),
            ("java.util.Objects.requireNonNull".into(), Some("static".into())),
        ]
    );
}

#[test]
fn methods_qualified_names_arities_and_beans() {
    let pf = parse(FIXTURE);
    assert_eq!(pf.functions.len(), 2);

    let concat = &pf.functions[0];
    assert_eq!(concat.name, "concat");
    assert_eq!(concat.qualified.as_deref(), Some("Fallback"));
    assert_eq!(concat.kind, SymbolKind::Method);
    assert_eq!(concat.params.len(), 2);
    assert!(!concat.is_decl_only);
    // span byte-integrity: slice of source at [start_byte, end_byte] covers
    // the whole method xor exactly it.
    let body = &FIXTURE[concat.span.start_byte as usize..concat.span.end_byte as usize];
    assert!(body.contains("public String concat"), "span drift: {body:?}");

    let wrap = &pf.functions[1];
    assert_eq!(wrap.name, "wrap");
    assert_eq!(wrap.params.len(), 1);
}

#[test]
fn annotation_captured() {
    let pf = parse(FIXTURE);
    let names: Vec<&str> = pf.annotations.iter().map(|a| a.name.as_str()).collect();
    assert_eq!(names, ["Deprecated"]);
}

#[test]
fn callsites_with_receivers_and_args() {
    let pf = parse(FIXTURE);
    let shapes: Vec<(String, Option<ValueExpr>, usize)> = pf
        .callsites
        .iter()
        .map(|c| (c.callee.clone(), c.receiver.clone(), c.args.len()))
        .collect();

    assert_eq!(
        shapes,
        vec![
            // if ("".equals(lhs)) — receiver is the empty string literal;
            // guard callsites are registered once (same policy as Python)
            (
                "equals".into(),
                Some(ValueExpr::Str { value: String::new() }),
                1
            ),
            // return lhs.concat(rhs)
            ("concat".into(), Some(ValueExpr::Symbolic { name: "lhs".into() }), 1),
            // requireNonNull(key, "key")
            ("requireNonNull".into(), None, 2),
            // guard `!key.isEmpty()` (traversal order: after requireNonNull)
            ("isEmpty".into(), Some(ValueExpr::Symbolic { name: "key".into() }), 0),
            // id(key)
            ("id".into(), None, 1),
        ]
    );
}

#[test]
fn guard_conditions_expressions() {
    let pf = parse(FIXTURE);
    assert_eq!(pf.guard_conditions.len(), 2);

    // "".equals(lhs) → CallResult of the `equals` call site
    match &pf.guard_conditions[0].condition {
        ValueExpr::CallResult { callsite } => {
            let id = *callsite;
            let cs = pf
                .callsites
                .iter()
                .find(|c| c.id == id)
                .expect("callsite exists");
            assert_eq!(cs.callee, "equals");
        }
        other => panic!("expected CallResult guard, got {other:?}"),
    }

    // key != null && !key.isEmpty()
    match &pf.guard_conditions[1].condition {
        ValueExpr::Binary { op, lhs, rhs } => {
            assert_eq!(*op, BinaryOp::And);
            assert_eq!(
                **lhs,
                ValueExpr::Binary {
                    op: BinaryOp::Ne,
                    lhs: Box::new(ValueExpr::Symbolic { name: "key".into() }),
                    rhs: Box::new(ValueExpr::Null),
                }
            );
            match &**rhs {
                ValueExpr::Unary { op: UnaryOp::Not, operand } => {
                    assert_eq!(**operand, ValueExpr::CallResult { callsite: callsite_of(&pf, "isEmpty") });
                }
                other => panic!("expected Not(..), got {other:?}"),
            }
        }
        other => panic!("expected binary guard, got {other:?}"),
    }
}

fn callsite_of(pf: &ParsedFile, callee: &str) -> semarch_core::ids::CallSiteId {
    pf.callsites
        .iter()
        .find(|c| c.callee == callee)
        .map(|c| c.id)
        .unwrap_or_else(|| panic!("no callsite {callee}"))
}

/// Train Ticket verification-code *shape*: `verifyCodeService.verifyCode(
/// verifyCode, remote)` behind `!StringUtils.isEmpty(verifyCode)`.
const VERIFY_SHAPE: &str = r#"
public class Resp {
    String stub(String verifyCode, String remote) {
        if (!StringUtils.isEmpty(verifyCode)) {
            return verifyCodeService.verifyCode(verifyCode, remote);
        }
        return null;
    }
}
"#;

#[test]
fn verification_code_call_shape() {
    let pf = parse(VERIFY_SHAPE);
    assert_eq!(pf.functions.len(), 1);
    assert_eq!(pf.callsites.len(), 2);

    let verify = pf
        .callsites
        .iter()
        .find(|c| c.callee == "verifyCode")
        .expect("verifyCode callsite");
    assert_eq!(
        verify.receiver,
        Some(ValueExpr::Symbolic { name: "verifyCodeService".into() })
    );
    assert_eq!(
        verify.args,
        vec![
            ValueExpr::Symbolic { name: "verifyCode".into() },
            ValueExpr::Symbolic { name: "remote".into() }
        ]
    );

    let cond = &pf.guard_conditions[0].condition;
    match cond {
        ValueExpr::Unary { op: UnaryOp::Not, .. } => {}
        other => panic!("expected Not guard, got {other:?}"),
    }
}

#[test]
fn capability_matrix_is_the_emitted_subset() {
    use semarch_core::Capability::*;
    assert_eq!(
        semarch_frontend_java::CAPABILITIES,
        &[
            Declarations, Parameters, CallSites, Literals, MemberAccess, Assignments,
            IfElse, ReturnThrow, BasicLoops, AnnotationsDecorators, Imports, SourceSpans,
        ]
    );
}

#[test]
fn broken_source_produces_diagnostic_not_panic() {
    let mut fe = JavaFrontend::new().expect("grammar ok");
    let mut alloc = Allocator::default();
    let mut diags = Vec::new();
    let mut ctx = ParseContext::new(9u32.into(), Language::Java, &mut alloc, &mut diags);
    let parsed = fe.parse(&mut ctx, "class {{{").expect("no panic on bad source");
    // An ERROR node is a diagnostic, not a parse failure.
    assert!(diags.iter().any(|d| d.message.contains("ERROR")));
    assert_eq!(parsed.file, 9u32.into());
}
