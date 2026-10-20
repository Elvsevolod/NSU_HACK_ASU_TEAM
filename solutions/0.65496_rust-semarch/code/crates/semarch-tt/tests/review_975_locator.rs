//! The call-site locator has to name the *invocation*, on the token's own row,
//! with a column that is a UTF-8 byte column. These gates exercise the
//! frontend-provided name span directly, the fallback lexer (hand-built IR) and
//! the same-line/unicode cases the review asked for.

use std::sync::Arc;

use semarch_core::{Allocator, Language, LanguageFrontend, ParseContext, ValueExpr};
use semarch_core::ids::CallSiteId;
use semarch_core::ir::CallSite;
use semarch_frontend_java::JavaFrontend;
use semarch_tt::bodies::FileUnit;

/// Parse one Java source and pair it with the `FileUnit` the engine would use,
/// so the call sites carry the frontend's own `name_span`.
fn unit(src: &str) -> (FileUnit, Vec<CallSite>) {
    let mut frontend = JavaFrontend::new().unwrap();
    let mut alloc = Allocator::default();
    let mut diagnostics = Vec::new();
    let mut ctx = ParseContext::new(0u32.into(), Language::Java, &mut alloc, &mut diagnostics);
    let parsed = frontend.parse(&mut ctx, src).unwrap();
    assert!(diagnostics.is_empty(), "{diagnostics:?}");
    let unit = FileUnit {
        file: "C.java".into(),
        language: Language::Java,
        source: Arc::from(src),
        callsites: parsed.callsites.clone(),
        functions: parsed.functions.clone(),
    };
    (unit, parsed.callsites)
}

fn call<'a>(sites: &'a [CallSite], callee: &str) -> &'a CallSite {
    sites
        .iter()
        .find(|c| c.callee == callee)
        .unwrap_or_else(|| panic!("no call to {callee}"))
}

/// `(line index in source, byte column of the first `needle` on it)`.
fn expected(src: &str, needle: &str) -> (u32, u32) {
    for (row, line) in src.lines().enumerate() {
        if let Some(col) = line.find(needle) {
            return (row as u32, col as u32);
        }
    }
    panic!("`{needle}` not found");
}

#[test]
fn a_multiline_receiver_keeps_the_name_on_its_own_row() {
    let src = "class C {\n  void m(RestTemplate restTemplate) {\n    restTemplate\n      .exchange(\"u\", HttpMethod.GET, null, 1);\n  }\n}\n";
    let (unit, sites) = unit(src);
    let cs = call(&sites, "exchange");
    let (row, col) = unit.anchor(cs).expect("name token located");
    let (want_row, want_col) = expected(src, "exchange");
    assert_eq!((row, col), (want_row, want_col), "{cs:?}");
    // The skeleton keys a call-site fact by the *name*'s line, not the
    // receiver's first line.
    assert_eq!(unit.site_line(cs), want_row + 1);
}

#[test]
fn a_unicode_literal_before_the_name_does_not_shift_the_column() {
    let src = "class C {\n  void m() { String s = \"привет\"; helper(1); }\n}\n";
    let (unit, sites) = unit(src);
    let cs = call(&sites, "helper");
    let (row, col) = unit.anchor(cs).expect("name token located");
    let (want_row, want_col) = expected(src, "helper");
    assert_eq!((row, col), (want_row, want_col), "{cs:?}");
    // The column is a byte column: everything before the name on the line,
    // Cyrillic included, counts in bytes.
    assert_eq!(usize::try_from(col).unwrap(), src.lines().nth(1).unwrap().find("helper").unwrap());
}

#[test]
fn same_line_invocations_get_distinct_anchors() {
    let src = "class C {\n  void m() { a.helper(1); b.helper(2); }\n}\n";
    let (unit, sites) = unit(src);
    let found: Vec<CallSite> = sites.iter().filter(|c| c.callee == "helper").cloned().collect();
    assert_eq!(found.len(), 2, "{sites:?}");
    let a = unit.anchor(&found[0]).expect("first anchor");
    let b = unit.anchor(&found[1]).expect("second anchor");
    assert_ne!(a, b);
    assert_eq!(a.0, b.0, "same line");
    let line = src.lines().nth(1).unwrap();
    assert_eq!(a.1, line.find("a.helper").unwrap() as u32 + 2, "{a:?}");
    assert_eq!(b.1, line.find("b.helper").unwrap() as u32 + 2, "{b:?}");
}

#[test]
fn the_fallback_lexer_names_the_outer_invocation_not_the_first_lookalike() {
    // No frontend name span: `f(x).f(1)` must anchor on the *second* `f`
    // (the invocation's own name), not on the receiver's `f(x)`.
    let text = "f(x).f(1)";
    let span = semarch_core::SourceSpan {
        file: 0u32.into(),
        start_byte: 0,
        end_byte: text.len() as u32,
        start_row: 0,
        start_col: 0,
        end_row: 0,
        end_col: text.len() as u32,
    };
    let cs = CallSite {
        id: CallSiteId(0),
        callee: "f".into(),
        receiver: Some(ValueExpr::Symbolic { name: "x".into() }),
        args: vec![ValueExpr::Int { value: 1 }],
        span,
        name_span: None,
    };
    let unit = FileUnit {
        file: "C.java".into(),
        language: Language::Java,
        source: Arc::from(text),
        callsites: Vec::new(),
        functions: Vec::new(),
    };
    assert_eq!(unit.anchor_col(&cs), Some(5));
}
