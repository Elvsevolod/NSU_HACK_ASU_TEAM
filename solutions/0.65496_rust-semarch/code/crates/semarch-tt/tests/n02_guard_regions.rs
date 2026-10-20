//! N02 acceptance at the resolution level: which call sites a feature guard may
//! kill, and which it must leave alone.
//!
//! The fixture is built from the four shapes that the earlier line-range logic
//! got wrong (predicate, `else`, `do…while`) plus the ordinary positive case.
//! Line numbers are derived from the source text, so the test cannot drift.

use std::collections::HashSet;

use semarch_tt::guards::GuardIndex;

const SRC: &str = r#"class G {
    void thenBranch(String flag) {
        if (!StringUtils.isEmpty(flag)) {
            work();
        }
    }

    void withElse(String flag) {
        if (!StringUtils.isEmpty(flag)) {
            left();
        } else {
            right();
        }
    }

    void predicateCall(String flag) {
        if (!StringUtils.isEmpty(predicate(flag))) {
            guarded();
        }
    }

    void doWhile(String flag) {
        do {
            once();
        } while (!StringUtils.isEmpty(flag));
    }
}
"#;

fn temp_root(tag: &str) -> std::path::PathBuf {
    let root = std::env::temp_dir().join(format!(
        "semarch-n02-{tag}-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.subsec_nanos())
            .unwrap_or(0)
    ));
    let _ = std::fs::remove_dir_all(&root);
    std::fs::create_dir_all(&root).expect("create temp root");
    root
}

/// 1-based line of the unique source line containing `needle`.
fn line_of(needle: &str) -> u32 {
    let hits: Vec<usize> = SRC
        .lines()
        .enumerate()
        .filter(|(_, l)| l.contains(needle))
        .map(|(i, _)| i + 1)
        .collect();
    assert_eq!(hits.len(), 1, "`{needle}` must be unambiguous: {hits:?}");
    hits[0] as u32
}

#[test]
fn only_the_then_body_is_a_guarded_region() {
    let root = temp_root("regions");
    std::fs::write(root.join("G.java"), SRC).expect("write fixture");

    let index = GuardIndex::build(&root).expect("builds");
    let file = "G.java";
    let absent: HashSet<String> = HashSet::new();

    // The ordinary positive case: the body of a feature test is guarded.
    assert!(index.blocks(file, line_of("work();"), &absent));
    assert!(index.blocks(file, line_of("left();"), &absent));

    // The predicate is evaluated before the branch: never guarded.
    assert!(!index.blocks(file, line_of("predicate(flag)"), &absent));
    // The `else` branch runs when the condition does not hold: not "feature
    // absent", so it is left alone.
    assert!(!index.blocks(file, line_of("right();"), &absent));
    // A do-while body runs at least once.
    assert!(!index.blocks(file, line_of("once();"), &absent));
    // A predicate that tests a *call result* names no feature on its own.
    assert!(!index.blocks(file, line_of("guarded();"), &absent));

    // Engaging the feature revives the guarded body.
    let engaged: HashSet<String> = ["flag".to_owned()].into_iter().collect();
    assert!(!index.blocks(file, line_of("work();"), &engaged));
    assert!(!index.blocks(file, line_of("left();"), &engaged));

    // Only the two real feature tests produce guards.
    assert_eq!(index.len(), 2, "then-branch and if/else only");

    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn the_predicate_row_is_not_part_of_the_region() {
    let root = temp_root("rows");
    std::fs::write(root.join("G.java"), SRC).expect("write fixture");
    let index = GuardIndex::build(&root).expect("builds");

    // The predicate's own line must not be inside the guarded range: it is the
    // line directly above the body in this fixture.
    let work_line = line_of("work();");
    let predicate_line = work_line - 1;
    assert!(!index.blocks("G.java", predicate_line, &HashSet::new()));

    let _ = std::fs::remove_dir_all(&root);
}
