//! Entry-grounding audit: for every step of a scenario, show the query tokens,
//! the ranked candidates (with their UI-binding state) and the entry set the
//! selection policy actually chose. Development tool for tuning entry
//! grounding; it never runs in the answer path.
//!
//! ```text
//! cargo run --release --example entry_audit -p semarch-tt -- <challenge> [S1,S2]
//! ```

use semarch_scenario::scenario::Scenario;
use semarch_tt::pipeline::{AnalyzerConfig, TtAnalyzer};

fn main() {
    let mut args = std::env::args().skip(1);
    let root = args.next().expect("challenge root");
    let only: Vec<String> = args
        .next()
        .map(|s| s.split(',').map(str::to_owned).collect())
        .unwrap_or_default();
    let cfg = AnalyzerConfig::default();
    let an = TtAnalyzer::load(&root).expect("load");
    let dir = format!("{root}/scenarios");
    let mut files: Vec<_> = std::fs::read_dir(&dir)
        .expect("scenarios dir")
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|e| e == "json"))
        .collect();
    files.sort();
    for f in files {
        let text = std::fs::read_to_string(&f).expect("read scenario");
        let scn = Scenario::from_json(&text).expect("parse scenario");
        if !only.is_empty() && !only.contains(&scn.id) {
            continue;
        }
        let rankings = an.entries.rank_scenario(&scn);
        let short = |id: &str| id.split(':').nth(2).unwrap_or(id).to_owned();
        println!("===== {} ({})", scn.id, scn.title);
        let mut context: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
        for (i, r) in rankings.iter().enumerate() {
            let step = &scn.steps[i];
            context.extend(semarch_scenario::text::tokenize(&step.action));
            let query = an.entries.step_query(&scn, i);
            let sel = an
                .entries
                .select_step(r, &context, cfg.entry_ratio, cfg.max_candidates);
            let chosen = &sel.members;
            println!("  {}. {}", step.n, step.action);
            println!("     query: {}", query.join(" "));
            println!("     reason: {}", sel.reason.as_str());
            println!(
                "     -> {}",
                chosen
                    .iter()
                    .map(|&d| short(&an.entries.endpoints[d].method))
                    .collect::<Vec<_>>()
                    .join(" | ")
            );
            for c in r.ranked.iter().take(8) {
                let e = &an.entries.endpoints[c.doc];
                let sel = if chosen.contains(&c.doc) { "*" } else { " " };
                println!(
                    "     {sel} {:.3} {:<6} {:<8} {} {}",
                    c.score,
                    e.http,
                    if e.ui_bound { "ui" } else { "-" },
                    short(&e.method),
                    e.full_path
                );
            }
        }
    }
}
