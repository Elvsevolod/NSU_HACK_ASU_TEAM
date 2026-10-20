//! Temporary diagnostic: dump an endpoint's retrieval document (identity,
//! page and action vocabulary) so ranking decisions can be inspected by hand.
//!
//! ```text
//! cargo run --release --example dump_entry -p semarch-tt -- <challenge> <path-substring>
//! ```

use semarch_tt::pipeline::TtAnalyzer;

fn main() {
    let mut args = std::env::args().skip(1);
    let root = args.next().expect("challenge root");
    let needle = args.next().expect("path substring");
    let an = TtAnalyzer::load(&root).expect("load");
    for e in &an.entries.endpoints {
        if e.full_path.contains(&needle) {
            let mut counts = std::collections::BTreeMap::new();
            for t in &e.tokens {
                *counts.entry(t.clone()).or_insert(0usize) += 1;
            }
            let mut acts: Vec<String> = e.ui_action.clone();
            acts.sort();
            acts.dedup();
            println!(
                "\n{} [{}] {} {} bound={}",
                e.method, e.http, e.class, e.full_path, e.ui_bound
            );
            println!("  pages: {:?}", e.ui_page);
            println!("  action vocab: {}", acts.join(" "));
            println!("  doc len {} tokens", e.tokens.len());
            let mut by_count: Vec<(usize, String)> = counts.into_iter().map(|(t, c)| (c, t)).collect();
            by_count.sort_by(|a, b| b.0.cmp(&a.0).then(a.1.cmp(&b.1)));
            println!(
                "  tokens: {}",
                by_count
                    .iter()
                    .map(|(c, t)| if *c > 1 { format!("{t}×{c}") } else { t.clone() })
                    .collect::<Vec<_>>()
                    .join(" ")
            );
            println!(
                "  contract: {}",
                {
                    let mut c = e.contract.clone();
                    c.sort();
                    c.dedup();
                    c.join(" ")
                }
            );
        }
    }
}
