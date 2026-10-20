//! N02 acceptance: a condition's *guarded body* is delimited structurally.
//!
//! The predicate is evaluated before the branch decision, the `else` branch
//! runs when the predicate does not hold, and a `do { … } while (…)` body runs
//! at least once. None of those three may be reported as the region the
//! condition protects. Assertions are byte-based: the frontend reports the
//! consequence block `{ … }`, which starts on the same *line* as the predicate,
//! so row comparison alone would be meaningless.
//!
//! Guards are indexed in source order, which the fixture makes explicit.

use semarch_core::{Allocator, GuardCondition, Language, LanguageFrontend, ParseContext, ParsedFile, SourceSpan};
use semarch_frontend_java::JavaFrontend;

const SRC: &str = r#"class G {
    void thenBranch(String flag) {
        if (!isEmpty(flag)) {
            work();
        }
    }

    void withElse(String flag) {
        if (!isEmpty(flag)) {
            left();
        } else {
            right();
        }
    }

    void predicateCall(String flag) {
        if (!isEmpty(check(flag))) {
            guarded();
        }
    }

    void doWhile(String flag) {
        do {
            once();
        } while (!isEmpty(flag));
    }
}
"#;

fn parse(src: &str) -> ParsedFile {
    let mut fe = JavaFrontend::new().expect("grammar ABI ok");
    let mut alloc = Allocator::default();
    let mut diags = Vec::new();
    let mut ctx = ParseContext::new(0u32.into(), Language::Java, &mut alloc, &mut diags);
    let parsed = fe.parse(&mut ctx, src).expect("parse succeeds");
    assert!(diags.is_empty(), "unexpected diagnostics: {diags:?}");
    parsed
}

fn slice(src: &str, span: SourceSpan) -> &str {
    &src[span.start_byte as usize..span.end_byte as usize]
}

/// The four constructs of `SRC`, in source order.
fn guards(pf: &ParsedFile) -> [&GuardCondition; 4] {
    let g = &pf.guard_conditions;
    assert_eq!(g.len(), 4, "one condition per construct");
    [&g[0], &g[1], &g[2], &g[3]]
}

fn contains(outer: SourceSpan, inner: SourceSpan) -> bool {
    outer.start_byte <= inner.start_byte && inner.end_byte <= outer.end_byte
}

#[test]
fn then_span_excludes_the_predicate() {
    let pf = parse(SRC);
    let [then_branch, ..] = guards(&pf);
    let then = then_branch.then_span.expect("if has a delimited body");

    let body = slice(SRC, then);
    assert!(body.contains("work()"), "then body: {body:?}");
    assert!(
        !body.contains("isEmpty") && !body.contains("if"),
        "the predicate must not be inside the guarded body: {body:?}"
    );
    // Byte-based exclusion: the condition ends before the body starts.
    assert!(
        then_branch.span.end_byte <= then.start_byte,
        "predicate [{}, {}) overlaps body [{}, {})",
        then_branch.span.start_byte,
        then_branch.span.end_byte,
        then.start_byte,
        then.end_byte
    );
    // Legacy whole-construct span still delimits the statement.
    assert!(slice(SRC, then_branch.body_span.unwrap()).contains("if (!isEmpty(flag))"));
    assert!(!then_branch.body_always_runs);
}

#[test]
fn else_branch_is_not_the_guarded_body() {
    let pf = parse(SRC);
    let [_, with_else, ..] = guards(&pf);
    let then_span = with_else.then_span.expect("then span");
    let alt_span = with_else.else_span.expect("else span");
    let then = slice(SRC, then_span);
    let alt = slice(SRC, alt_span);

    assert!(then.contains("left()") && !then.contains("right()"), "then={then:?}");
    assert!(alt.contains("right()") && !alt.contains("left()"), "else={alt:?}");
    // The two regions are disjoint, and neither contains the predicate.
    assert!(then_span.end_byte <= alt_span.start_byte);
    assert!(with_else.span.end_byte <= then_span.start_byte);
}

#[test]
fn a_call_inside_the_predicate_is_not_guarded() {
    let pf = parse(SRC);
    let [_, _, with_predicate_call, _] = guards(&pf);
    let then = with_predicate_call.then_span.expect("then span");

    let check = pf
        .callsites
        .iter()
        .find(|c| c.callee == "check")
        .expect("check callsite");
    assert!(
        !contains(then, check.span),
        "the predicate call must not fall inside the guarded body"
    );
    assert!(contains(with_predicate_call.span, check.span), "it is the predicate");
    assert!(slice(SRC, then).contains("guarded()"));
}

#[test]
fn do_while_body_is_never_guarded() {
    let pf = parse(SRC);
    let [_, _, _, do_while] = guards(&pf);

    assert!(do_while.body_always_runs, "do-while body runs at least once");
    assert_eq!(do_while.then_span, None, "nothing is protected by a do-while condition");
    let once = pf
        .callsites
        .iter()
        .find(|c| c.callee == "once")
        .expect("once callsite");
    // The body *is* inside the legacy whole-construct span — which is exactly
    // why that span must not be used for pruning.
    let whole = do_while.body_span.expect("whole construct");
    assert!(contains(whole, once.span));
}
