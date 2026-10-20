//! Compile-spike: load every Tier-A grammar with the pinned `tree-sitter`
//! runtime and parse one fixture per language. Acceptance: no panic, no
//! ERROR root nodes. Result recorded in `docs/adr/0002-grammar-pin.md`.
use tree_sitter::Parser;
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut parser = Parser::new();
    macro_rules! spike {
        ($lang:literal, $language:expr, $src:literal) => {{
            parser
                .set_language(&$language.into())
                .map_err(|e| format!("{}: ABI mismatch: {e}", $lang))?;
            let tree = parser.parse($src, None).ok_or_else(|| format!("{}: no tree", $lang))?;
            let root = tree.root_node();
            if root.has_error() {
                return Err(format!("{}: parsed tree has ERROR nodes", $lang).into());
            }
            println!("{}: ok ({} bytes)", $lang, root.end_byte());
        }};
    }
    spike!("java", tree_sitter_java::LANGUAGE, "class A { void f() {} }");
    spike!("python", tree_sitter_python::LANGUAGE, "def f():\n    pass\n");
    spike!("go", tree_sitter_go::LANGUAGE, "package a\n\nfunc f() {}\n");
    spike!("javascript", tree_sitter_javascript::LANGUAGE, "function f() {}\n");
    spike!("typescript", tree_sitter_typescript::LANGUAGE_TYPESCRIPT, "function f(): void {}\n");
    spike!("tsx", tree_sitter_typescript::LANGUAGE_TSX, "const a = <b>x</b>;\n");
    spike!("c-sharp", tree_sitter_c_sharp::LANGUAGE, "class A { void F() {} }");
    println!("SPIKE OK");
    Ok(())
}
