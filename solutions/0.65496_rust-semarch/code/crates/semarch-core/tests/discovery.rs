//! Discovery fixtures (T03 acceptance): `.gitignore`-aware walk, exact
//! language classification, deterministic order.

use std::fs;
use std::path::PathBuf;

use semarch_core::{Language, ProjectDiscovery};

fn tempdir(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("semarch-disc-{tag}-{}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).unwrap();
    dir
}

#[test]
fn walks_gitignore_and_classifies_by_extension() {
    let root = tempdir("main");
    let src = root.join("src");
    fs::create_dir_all(&src).unwrap();
    fs::create_dir_all(root.join("target")).unwrap();
    fs::write(src.join("Main.java"), "class Main {}").unwrap();
    fs::write(src.join("app.py"), "print(1)").unwrap();
    fs::write(src.join("notes.txt"), "not source").unwrap();
    fs::write(src.join("gen.java"), "class Gen {}").unwrap();
    fs::write(root.join("target").join("x.java"), "class X {}").unwrap();
    // .gitignore excludes `target/` and `gen.java`
    fs::write(root.join(".gitignore"), "target/\nsrc/gen.java\n").unwrap();

    let files = ProjectDiscovery::new(&root).discover().expect("walk ok");
    // The walker canonicalizes the root, so compare against the same.
    let root = root.canonicalize().unwrap();
    let rel: Vec<(String, Language)> = files
        .iter()
        .map(|f| {
            let rel = f.path.strip_prefix(&root).unwrap().to_string_lossy().into_owned();
            (rel, f.language)
        })
        .collect();

    assert_eq!(
        rel,
        vec![
            ("src/Main.java".into(), Language::Java),
            ("src/app.py".into(), Language::Python),
        ]
    );

    let _ = fs::remove_dir_all(&root);
}

#[test]
fn missing_root_errors() {
    let missing = tempdir("missing").join("nope");
    assert!(ProjectDiscovery::new(&missing).discover().is_err());
}

#[test]
fn unknown_extensions_are_skipped() {
    let root = tempdir("ext");
    fs::create_dir_all(&root).unwrap();
    fs::write(root.join("a.rs"), "fn main() {}").unwrap(); // not Tier-A v0
    fs::write(root.join("b.java"), "class B {}").unwrap();
    let files = ProjectDiscovery::new(&root).discover().unwrap();
    assert_eq!(files.len(), 1);
    assert_eq!(files[0].language, Language::Java);
    let _ = fs::remove_dir_all(&root);
}
