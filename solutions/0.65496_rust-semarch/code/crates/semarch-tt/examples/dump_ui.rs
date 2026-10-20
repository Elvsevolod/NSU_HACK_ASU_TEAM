//! Diagnostic: print every UI request call site (the binding oracle).
//!
//! ```text
//! cargo run --release -p semarch-tt --example dump_ui -- <challenge> [url-substring]
//! ```

use semarch_tt::ui;

fn main() {
    let mut args = std::env::args().skip(1);
    let root = args.next().expect("challenge root");
    let needle = args.next().unwrap_or_default();
    let roots = ui::extract(&root).expect("load ui");
    let mut facts: Vec<&ui::UiFact> = roots.iter().collect();
    facts.sort_by(|a, b| a.file.cmp(&b.file).then(a.url.cmp(&b.url)));
    for f in facts {
        if !needle.is_empty() && !f.url.contains(&needle) {
            continue;
        }
        let mut acts = f.action_tokens.clone();
        acts.dedup();
        let file = f.file.rsplit('/').next().unwrap_or(&f.file);
        println!(
            "{:<6} {:<26} {:<34} {:<22} {}",
            f.http.as_deref().unwrap_or("-"),
            f.url,
            acts.join(" "),
            format!("{:?}", f.trigger),
            file
        );
    }
}
