//! Lowering census over a real Java checkout (N03/N04 measurement).
//!
//! It parses every Java file the project discovery reports, lowers each
//! function body into the ordered IR, validates the result and prints a table
//! of the constructs it could not model. Nothing is executed; the output is the
//! measured basis for the bounded support matrix in the documentation.
//!
//! ```text
//! cargo run --release --example lowering_census --manifest-path semarch/Cargo.toml -p semarch-tt -- <project-root>
//! ```

use std::collections::BTreeMap;

use semarch_core::ir::GapReason;
use semarch_core::{Allocator, Language, LanguageFrontend, ParseContext, ProjectDiscovery};
use semarch_core::lowering::{validate, BodyCheck};
use semarch_frontend_java::JavaFrontend;

fn main() {
    let root = std::env::args().nth(1).unwrap_or_else(|| {
        eprintln!("usage: lowering_census <project-root>");
        std::process::exit(2);
    });
    let root = std::path::Path::new(&root)
        .canonicalize()
        .expect("project root exists");
    let files = ProjectDiscovery::new(&root).discover().expect("discovery");

    let mut frontend = JavaFrontend::new().expect("grammar ABI ok");
    let mut parsed_files = 0usize;
    let mut failed_files = 0usize;
    let mut bodies = 0usize;
    let mut blocks = 0usize;
    let mut statements = 0usize;
    let mut guards = 0usize;
    let mut exits = 0usize;
    let mut invalid: Vec<(String, String, Vec<String>)> = Vec::new();
    let mut by_reason: BTreeMap<GapReason, usize> = BTreeMap::new();
    let mut by_detail: BTreeMap<String, usize> = BTreeMap::new();
    let mut empty_bodies = 0usize;

    for file in files {
        if file.language != Language::Java {
            continue;
        }
        let rel = file
            .path
            .strip_prefix(&root)
            .map_or_else(|_| file.path.clone(), |p| p.to_path_buf());
        let rel = rel.to_string_lossy().replace('\\', "/");
        let source = match std::fs::read_to_string(&file.path) {
            Ok(s) => s,
            Err(_) => {
                failed_files += 1;
                continue;
            }
        };
        let mut alloc = Allocator::default();
        let mut diagnostics = Vec::new();
        let mut ctx = ParseContext::new(
            semarch_core::ids::FileId::from_raw(0),
            Language::Java,
            &mut alloc,
            &mut diagnostics,
        );
        let parsed = match frontend.parse(&mut ctx, &source) {
            Ok(p) => p,
            Err(_) => {
                failed_files += 1;
                continue;
            }
        };
        parsed_files += 1;
        for body in &parsed.bodies {
            bodies += 1;
            blocks += body.blocks.len();
            guards += body.guards.len();
            exits += body.exits.len();
            for block in &body.blocks {
                statements += block.statements.len();
            }
            if body.blocks.is_empty() {
                empty_bodies += 1;
            }
            for gap in &body.gaps {
                *by_reason.entry(gap.reason).or_default() += 1;
                // The detail text is the audit vocabulary; keep the head so
                // variants of the same construct group together.
                let head: String = gap.detail.chars().take(64).collect();
                *by_detail.entry(head).or_default() += 1;
            }
            if let BodyCheck::Invalid { problems } = validate(body) {
                let function = parsed
                    .functions
                    .iter()
                    .find(|f| f.id == body.function)
                    .map_or_else(|| format!("{:?}", body.function), |f| f.name.clone());
                invalid.push((rel.clone(), function, problems));
            }
        }
    }

    println!("files parsed:      {parsed_files} (failed: {failed_files})");
    println!("function bodies:   {bodies} (empty: {empty_bodies})");
    println!("basic blocks:      {blocks}");
    println!("statements:        {statements}");
    println!("guards:            {guards}");
    println!("exit blocks:       {exits}");
    println!("invalid bodies:    {}", invalid.len());
    for (file, function, problems) in invalid.iter().take(10) {
        println!("  INVALID {file} :: {function}: {problems:?}");
    }

    let total_gaps: usize = by_reason.values().sum();
    println!("\ngaps: {total_gaps}");
    for (reason, count) in &by_reason {
        println!("  {reason:?}: {count}");
    }
    println!("\ntop gap details:");
    let mut details: Vec<(&String, &usize)> = by_detail.iter().collect();
    details.sort_by(|a, b| b.1.cmp(a.1).then_with(|| a.0.cmp(b.0)));
    for (detail, count) in details.into_iter().take(25) {
        println!("  {count:>6}  {detail}");
    }
}
