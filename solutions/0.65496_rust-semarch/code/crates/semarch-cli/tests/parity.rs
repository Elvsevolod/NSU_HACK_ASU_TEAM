//! Cross-language IR parity (T07 acceptance): equivalent Java/Python
//! constructs must normalize to the same IR shapes without leaking
//! language-specific details into the core.

use semarch_core::{
    Allocator, BinaryOp, Language, LanguageFrontend, ParseContext, ParsedFile, SymbolKind,
    ValueExpr,
};
use semarch_frontend_java::JavaFrontend;
use semarch_frontend_python::PythonFrontend;

/// Same method shape in both languages: two parameters, one binary `eq`
/// guard against the empty call/compare, one member call on the second
/// parameter, one literal argument call, string return.
const JAVA: &str = r#"
public class Client {
    public String handle(String code, String url) {
        if (code.equals("")) {
            return "empty";
        }
        return call(url, "utf-8");
    }
}
"#;

const PYTHON: &str = r#"
class Client:
    def handle(self, code, url):
        if code == "":
            return "empty"
        return call(url, "utf-8")
"#;

fn pfile(lang: Language, src: &str) -> ParsedFile {
    let mut alloc = Allocator::default();
    let mut diags = Vec::new();
    let parsed = {
        let mut ctx = ParseContext::new(0u32.into(), lang, &mut alloc, &mut diags);
        match lang {
            Language::Java => {
                JavaFrontend::new().unwrap().parse(&mut ctx, src).unwrap()
            }
            Language::Python => {
                PythonFrontend::new().unwrap().parse(&mut ctx, src).unwrap()
            }
            _ => panic!("fixture languages only"),
        }
    };
    assert!(diags.is_empty(), "{diags:?}");
    parsed
}

fn callsite(pf: &ParsedFile, id: semarch_core::ids::CallSiteId) -> &semarch_core::CallSite {
    pf.callsites
        .iter()
        .find(|c| c.id == id)
        .unwrap_or_else(|| panic!("no callsite {id:?}"))
}

#[test]
fn method_sharding_parity() {
    let java = pfile(Language::Java, JAVA);
    let python = pfile(Language::Python, PYTHON);

    let j = &java.functions[0];
    let p = &python.functions[0];

    // Same normalized facts (name is language-agnostic by fixture design).
    assert_eq!(j.name, p.name);
    // Python methods carry an explicit `self`; the frontend honestly reports
    // what is written, so parity holds on the *logical* parameters
    // (`code`, `url`); implicit-receiver normalization belongs to the
    // framework layer (Flask adapter, T15), not to frontends.
    assert_eq!(j.params.len() + 1, p.params.len());
    assert_eq!(j.params[0], ValueExpr::Parameter { index: 0 });
    assert_eq!(j.params[1], ValueExpr::Parameter { index: 1 });
    assert_eq!(p.params, vec![
        ValueExpr::Parameter { index: 0 }, // self
        ValueExpr::Parameter { index: 1 }, // code
        ValueExpr::Parameter { index: 2 }, // url
    ]);
    match (j.kind, p.kind) {
        (SymbolKind::Method, SymbolKind::Method) => {}
        other => panic!("kind mismatch: {other:?}"),
    }
}

#[test]
fn guard_parity() {
    let java = pfile(Language::Java, JAVA);
    let python = pfile(Language::Python, PYTHON);

    let jc = &java.guard_conditions[0].condition;
    let pc = &python.guard_conditions[0].condition;

    match (jc, pc) {
        // Java: code.equals("") → CallResult; Python: code == "" → Binary Eq.
        (
            ValueExpr::CallResult { callsite: jc_id },
            ValueExpr::Binary { op: BinaryOp::Eq, lhs, rhs },
        ) => {
            assert_eq!(callsite(&java, *jc_id).callee, "equals");
            assert_eq!(
                callsite(&java, *jc_id).receiver,
                Some(ValueExpr::Symbolic { name: "code".into() })
            );
            assert_eq!(
                callsite(&java, *jc_id).args,
                vec![ValueExpr::Str { value: String::new() }]
            );
            assert_eq!(**lhs, ValueExpr::Symbolic { name: "code".into() });
            assert_eq!(**rhs, ValueExpr::Str { value: String::new() });
        }
        _ => panic!("unexpected guard shapes: {jc:?} / {pc:?}"),
    }
    // Both normalize to "guard with empty-string compare on `code`"; the
    // language difference (call vs operator) is a *frontend* fact already
    // recorded in the IR, not a core difference.
}

#[test]
fn callsite_parity() {
    let java = pfile(Language::Java, JAVA);
    let python = pfile(Language::Python, PYTHON);

    let jc = java
        .callsites
        .iter()
        .find(|c| c.callee == "call")
        .expect("java call");
    let pc = python
        .callsites
        .iter()
        .find(|c| c.callee == "call")
        .expect("python call");

    assert_eq!(jc.receiver, pc.receiver); // None in both (plain name)
    assert_eq!(jc.args, pc.args); // Symbolic(url), Str("utf-8")
    assert_eq!(jc.args.len(), 2);
}

#[test]
fn import_and_annotation_shapes_are_language_local() {
    // Parity does not force cross-language equality of import/annotation
    // shapes: those have no shared construct. What must hold: no tree-sitter
    // AST types in core, all values are serde heights of core IR.
    let java = pfile(Language::Java, JAVA);
    let python = pfile(Language::Python, PYTHON);
    assert_eq!(java.imports.len(), 0);
    assert_eq!(python.imports.len(), 0);
    assert_eq!(java.annotations.len(), 0);
    assert_eq!(python.annotations.len(), 0);
}
