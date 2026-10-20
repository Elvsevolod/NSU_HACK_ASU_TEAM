//! `semarch` CLI v0: given a project directory, discover Tier-A source
//! files, parse them with the frontends, and dump the semantic index as
//! JSON. Analysis and exporters live above this in later tasks.

#![deny(clippy::correctness)]
#![warn(clippy::suspicious, clippy::complexity, clippy::perf)]

use std::path::PathBuf;

use anyhow::Context as _;
use clap::{Parser as CliParser, Subcommand};
use semarch_frontend_java::JavaFrontend;
use semarch_frontend_python::PythonFrontend;
use semarch_tt::pipeline::AnalyzerConfig;
use semarch_core::{Error, Language, LanguageFrontend, ProjectDiscovery, SemanticIndex};

#[derive(Debug, CliParser)]
#[command(name = "semarch")]
#[command(about = "Lightweight semantic architecture/scenario analyzer (v0)")]
struct Args {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Debug, Subcommand)]
enum Cmd {
    /// Discover Tier-A source files and print the parse plan (no parse).
    Discover { root: PathBuf },
    /// Parse a project and dump the semantic index as JSON.
    Parse {
        root: PathBuf,
        /// Fail if any frontend diagnostics were produced.
        #[arg(long)]
        strict: bool,
    },
    /// Parse inline source with one frontend (fixture/debug helper).
    Snippet {
        /// Language name: java | python.
        language: String,
        /// Read source from stdin instead of a file argument.
        #[arg(long)]
        stdin: bool,
        /// Optional source file.
        #[arg(value_name = "FILE")]
        file: Option<PathBuf>,
    },
    /// Parse a project, build the function-level architecture graph, print
    /// stats and the may-closure summary (T12).
    Graph { root: PathBuf },
    /// Train Ticket contour: ground scenario steps and export `submission.json`.
    TtExport {
        /// Contest workspace root (contains `skeleton/`, `scenarios/`, `targets/`).
        challenge: PathBuf,
        /// Output file (defaults to stdout).
        #[arg(long)]
        out: Option<PathBuf>,
        /// Print per-step entry ranking instead of only writing the answer.
        #[arg(long)]
        explain: bool,
        /// Restrict to these scenario ids (comma separated).
        #[arg(long, value_delimiter = ',')]
        scenarios: Vec<String>,
        /// Entry near-tie ratio (keep candidates scoring ≥ ratio × best).
        #[arg(long, default_value_t = 0.95)]
        entry_ratio: f64,
        /// Hard cap on entry candidates per step.
        #[arg(long, default_value_t = 4)]
        max_candidates: usize,
        /// Ablation switches (all on by default): `dispatch`, `declarations`,
        /// `repositories`, `entities`, `callbacks`, `guards`, `static`.
        #[arg(long, value_delimiter = ',')]
        disable: Vec<String>,
        /// Fail instead of degrading when project sources are unreadable
        /// (optional-feature guards G6 would be unknown).
        #[arg(long)]
        require_sources: bool,
        /// Answer engine: `legacy` (call-graph flood, the submitted answer),
        /// `shadow` (legacy answer + a written diff against the semantic
        /// engine) or `semantic` (the scenario state engine's own answer).
        #[arg(long, default_value = "legacy")]
        mode: String,
        /// Where the shadow diff goes (defaults to `<out>.shadow.json`).
        #[arg(long)]
        shadow_out: Option<PathBuf>,
    },
    /// Audit trail: for every predicted edge, the skeleton fact behind it, and
    /// every call site the scenario's feature set kills.
    TtReport {
        /// Contest workspace root (contains `skeleton/`, `scenarios/`, `targets/`).
        challenge: PathBuf,
        /// Output file (defaults to stdout).
        #[arg(long)]
        out: Option<PathBuf>,
        /// Restrict to these scenario ids (comma separated).
        #[arg(long, value_delimiter = ',')]
        scenarios: Vec<String>,
        /// Entry near-tie ratio (keep candidates scoring ≥ ratio × best).
        #[arg(long, default_value_t = 0.95)]
        entry_ratio: f64,
        /// Hard cap on entry candidates per step.
        #[arg(long, default_value_t = 4)]
        max_candidates: usize,
        /// Ablation switches, identical to `tt-export`, so a report can describe
        /// the very run whose answer is being explained.
        #[arg(long, value_delimiter = ',')]
        disable: Vec<String>,
        /// Fail instead of degrading when project sources are unreadable.
        #[arg(long)]
        require_sources: bool,
    },
    /// Semantic audit trail per scenario: bound requests with their provenance,
    /// guard decisions, effects with their proofs, suppressed call sites with
    /// the reason, coverage counters and every remaining gap.
    TtSemantic {
        /// Contest workspace root (contains `skeleton/`, `scenarios/`, `targets/`).
        challenge: PathBuf,
        /// Output file (defaults to stdout).
        #[arg(long)]
        out: Option<PathBuf>,
        /// Restrict to these scenario ids (comma separated).
        #[arg(long, value_delimiter = ',')]
        scenarios: Vec<String>,
        /// Entry near-tie ratio (keep candidates scoring ≥ ratio × best).
        #[arg(long, default_value_t = 0.95)]
        entry_ratio: f64,
        /// Hard cap on entry candidates per step.
        #[arg(long, default_value_t = 4)]
        max_candidates: usize,
        /// Ablation switches, identical to `tt-export`.
        #[arg(long, value_delimiter = ',')]
        disable: Vec<String>,
        /// Fail instead of degrading when project sources are unreadable.
        #[arg(long)]
        require_sources: bool,
    },
}

fn main() -> anyhow::Result<()> {
    let args = Args::parse();
    match args.cmd {
        Cmd::Discover { root } => {
            let files = ProjectDiscovery::new(&root).discover()?;
            for f in files {
                println!("{}\t{}", f.language.name(), f.path.display());
            }
            Ok(())
        }
        Cmd::Parse { root, strict } => {
            let idx = parse_project(&root)?;
            let json = serde_json::to_string_pretty(&idx.parsed)?;
            println!("{json}");
            if strict && !idx.diagnostics.is_empty() {
                for d in &idx.diagnostics {
                    eprintln!("diagnostic: {d}");
                }
                anyhow::bail!("strict mode: {} diagnostics", idx.diagnostics.len());
            }
            Ok(())
        }
        Cmd::Snippet { language, stdin, file } => run_snippet(&language, stdin, file),
        Cmd::Graph { root } => run_graph(&root),
        Cmd::TtExport {
            challenge,
            out,
            explain,
            scenarios,
            entry_ratio,
            max_candidates,
            disable,
            require_sources,
            mode,
            shadow_out,
        } => run_tt_export(
            &challenge,
            out.as_ref(),
            explain,
            &scenarios,
            &analyzer_config(entry_ratio, max_candidates, &disable),
            require_sources,
            semarch_tt::SemanticMode::parse(&mode)
                .with_context(|| format!("unknown --mode {mode:?} (legacy|shadow|semantic)"))?,
            shadow_out.as_ref(),
        ),
        Cmd::TtReport {
            challenge,
            out,
            scenarios,
            entry_ratio,
            max_candidates,
            disable,
            require_sources,
        } => run_tt_report(
            &challenge,
            out.as_ref(),
            &scenarios,
            &analyzer_config(entry_ratio, max_candidates, &disable),
            require_sources,
        ),
        Cmd::TtSemantic {
            challenge,
            out,
            scenarios,
            entry_ratio,
            max_candidates,
            disable,
            require_sources,
        } => run_tt_semantic(
            &challenge,
            out.as_ref(),
            &scenarios,
            &analyzer_config(entry_ratio, max_candidates, &disable),
            require_sources,
        ),
    }
}

/// Write the semantic audit trail: one entry per scenario, with the bound
/// request fields and their provenance, the guard decisions, the effects and
/// their proofs, the suppressed call sites and the coverage counters.
fn run_tt_semantic(
    challenge: &PathBuf,
    out: Option<&PathBuf>,
    only: &[String],
    cfg: &AnalyzerConfig,
    require_sources: bool,
) -> anyhow::Result<()> {
    use semarch_tt::pipeline::{LoadOptions, TtAnalyzer};

    let analyzer = TtAnalyzer::load_with(challenge, &LoadOptions { require_sources })?;
    report_diagnostics(&analyzer);

    let mut all = analyzer.analyze_all(cfg)?;
    if !only.is_empty() {
        all.retain(|(id, _, _)| only.iter().any(|s| s == id));
        anyhow::ensure!(!all.is_empty(), "no scenario matched {only:?}");
    }

    let mut scenarios = serde_json::Map::new();
    for (id, _, scn) in &all {
        let outcome = analyzer.semantic_run(scn, cfg)?;
        for step in &outcome.steps {
            eprintln!(
                "{id} step {}: entries={} bound_requests={} decisions={} effects={} suppressed={} sites(resolved={}, ambiguous={}, missing={}, no_body={}, kept={:?})",
                step.step,
                step.entries.len(),
                step.bindings.len(),
                step.decisions.len(),
                step.effects.len(),
                step.suppressed.len(),
                step.sites.resolved_exact,
                step.sites.resolved_ambiguous,
                step.sites.resolved_missing,
                step.sites.methods_without_body,
                step.sites.kept,
            );
        }
        scenarios.insert(id.clone(), serde_json::to_value(outcome)?);
    }
    let doc = serde_json::json!({
        "schema": "semarch.tt.semantic-audit/1",
        "project": analyzer.skeleton.project,
        "scenarios": scenarios,
    });
    let json = serde_json::to_string_pretty(&doc)?;
    match out {
        Some(path) => std::fs::write(path, json)?,
        None => println!("{json}"),
    }
    Ok(())
}

/// The one configuration both commands build, so an answer and the report that
/// explains it can never disagree about the switches.
fn analyzer_config(entry_ratio: f64, max_candidates: usize, disable: &[String]) -> AnalyzerConfig {
    let mut resolution = semarch_tt::ResolutionConfig::default();
    let mut use_context = true;
    for flag in disable {
        match flag.as_str() {
            "dispatch" => resolution.dispatch = false,
            "declarations" => resolution.drop_declarations = false,
            "repositories" => resolution.drop_repository_proxies = false,
            "entities" => resolution.materialize_entities = false,
            "callbacks" => resolution.framework_callbacks = false,
            "guards" => resolution.feature_guards = false,
            "static" | "static-receiver" => resolution.static_receiver = false,
            "context" => use_context = false,
            other => eprintln!("warning: unknown ablation flag {other}"),
        }
    }
    AnalyzerConfig {
        resolution,
        entry_ratio,
        max_candidates,
        use_context,
    }
}

/// Report every load-time degradation on stderr so it can never look like a
/// clean run.
fn report_diagnostics(analyzer: &semarch_tt::TtAnalyzer) {
    for d in &analyzer.diagnostics {
        eprintln!("diagnostic [{}] {}: {}", severity_word(d), d.id, d.message);
    }
}

fn severity_word(d: &semarch_tt::Diagnostic) -> &'static str {
    match d.severity {
        semarch_tt::Severity::Degraded => "degraded",
        semarch_tt::Severity::Info => "info",
    }
}

/// Print a per-scenario audit trail: evidence per edge, and pruned call sites.
fn run_tt_report(
    challenge: &PathBuf,
    out: Option<&PathBuf>,
    only: &[String],
    cfg: &AnalyzerConfig,
    require_sources: bool,
) -> anyhow::Result<()> {
    use semarch_tt::pipeline::{LoadOptions, TtAnalyzer};
    use semarch_tt::report;

    let analyzer = TtAnalyzer::load_with(challenge, &LoadOptions { require_sources })?;
    report_diagnostics(&analyzer);

    let mut all = analyzer.analyze_all(cfg)?;
    if !only.is_empty() {
        all.retain(|(id, _, _)| only.iter().any(|s| s == id));
        anyhow::ensure!(!all.is_empty(), "no scenario matched {only:?}");
    }

    let report = report::build(&analyzer, &all, cfg);
    for (id, rep) in &report.scenarios {
        let n = |k: &str| rep.counts.get(k).copied().unwrap_or(0);
        eprintln!(
            "{id}: {} edges ({} without a project call site, {} with an ambiguous witness), {} executes explained, {} call sites pruned by feature guards, {} unknown ids",
            n("edges"),
            n("edges_without_call_site"),
            n("edges_with_ambiguous_witness"),
            rep.executes.len(),
            n("pruned_call_sites"),
            rep.unknown_ids.len(),
        );
    }
    let json = serde_json::to_string_pretty(&report)?;
    match out {
        Some(path) => std::fs::write(path, json)?,
        None => println!("{json}"),
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)] // one flat CLI call site, not an API
fn run_tt_export(
    challenge: &PathBuf,
    out: Option<&PathBuf>,
    explain: bool,
    only: &[String],
    cfg: &AnalyzerConfig,
    require_sources: bool,
    mode: semarch_tt::SemanticMode,
    shadow_out: Option<&PathBuf>,
) -> anyhow::Result<()> {
    use semarch_tt::export;
    use semarch_tt::pipeline::{LoadOptions, TtAnalyzer};

    let analyzer = TtAnalyzer::load_with(challenge, &LoadOptions { require_sources })?;
    report_diagnostics(&analyzer);
    let stats = analyzer.graph.stats();
    eprintln!(
        "skeleton: {} methods, {} call sites, {} repository types ({} methods), {} callbacks ({} filters), {} tables; {} UI facts; {} endpoints; {} feature guards",
        stats.methods,
        stats.call_sites,
        stats.repository_types,
        stats.repository_methods,
        stats.callbacks,
        stats.filters,
        analyzer.graph.table_ids.len(),
        analyzer.ui_facts,
        analyzer.entries.len(),
        analyzer.graph.guard_count(),
    );

    let mut all = analyzer.analyze_all(cfg)?;
    if !only.is_empty() {
        all.retain(|(id, _, _)| only.iter().any(|s| s == id));
        anyhow::ensure!(!all.is_empty(), "no scenario matched {only:?}");
    }

    if explain {
        for (id, pred, scn) in &all {
            println!("=== {id} ===");
            print!("{}", analyzer.explain(scn, cfg));
            println!(
                "  -> executes={} calls={} remote={} data={}",
                pred.executes.len(),
                pred.calls.len(),
                pred.remote.len(),
                pred.data.len()
            );
        }
    }

    let mut predictions: Vec<(String, semarch_tt::Prediction)> = Vec::new();
    for (id, legacy, scn) in &all {
        match mode {
            // Shadow keeps the legacy answer: the diff is the artifact, not the
            // answer, so a shadow run can never change the submission.
            semarch_tt::SemanticMode::Legacy | semarch_tt::SemanticMode::Shadow => {
                predictions.push((id.clone(), legacy.clone()));
            }
            semarch_tt::SemanticMode::Semantic => {
                let pred = analyzer.semantic_predict(scn, cfg)?;
                eprintln!(
                    "{id}: semantic engine -> executes={} calls={} remote={} data={}",
                    pred.executes.len(),
                    pred.calls.len(),
                    pred.remote.len(),
                    pred.data.len()
                );
                predictions.push((id.clone(), pred));
            }
        }
    }
    if mode == semarch_tt::SemanticMode::Shadow {
        let mut diffs = Vec::new();
        for (_, _, scn) in &all {
            let diff = analyzer.shadow_run(scn, cfg)?;
            eprintln!(
                "shadow {}: legacy(calls={} remote={} data={}) semantic(calls={} remote={} data={}) agreed={} only_legacy={} only_semantic={}",
                diff.scenario,
                diff.legacy.calls,
                diff.legacy.remote,
                diff.legacy.data,
                diff.semantic.calls,
                diff.semantic.remote,
                diff.semantic.data,
                diff.agreed,
                diff.only_legacy.len(),
                diff.only_semantic.len(),
            );
            diffs.push(diff);
        }
        let json = serde_json::to_string_pretty(&diffs)?;
        match shadow_out.or(out) {
            Some(path) => {
                let path = if shadow_out.is_some() {
                    path.clone()
                } else {
                    let mut p = path.clone();
                    let stem = p
                        .file_stem()
                        .map_or_else(String::new, |n| n.to_string_lossy().into_owned());
                    p.set_file_name(format!("{stem}.shadow.json"));
                    p
                };
                std::fs::write(&path, json)?;
                eprintln!("shadow diff written to {}", path.display());
            }
            None => println!("{json}"),
        }
    }
    let (submission, reports) = export::build(
        &analyzer.skeleton.project,
        &predictions,
        &analyzer.graph.method_ids,
        &analyzer.graph.table_ids,
    );
    for (id, rep) in &reports {
        if !rep.rejected.is_empty() {
            eprintln!(
                "warning: {id}: {} edge(s) dropped with non-whitelisted ids",
                rep.rejected.len()
            );
            for r in rep.rejected.iter().take(5) {
                eprintln!("    {r}");
            }
        }
        eprintln!("{id}: {} edges emitted", rep.emitted);
    }

    let json = export::to_json(&submission)?;
    match out {
        Some(path) => std::fs::write(path, json)?,
        None => println!("{json}"),
    }
    Ok(())
}

fn run_graph(root: &PathBuf) -> anyhow::Result<()> {
    let idx = parse_project(root)?;

    // Flat function list (ids are dense across files via the shared
    // allocator); per-file call-site slices for span-based ownership.
    let functions: Vec<semarch_core::Function> = idx
        .parsed
        .iter()
        .flat_map(|p| p.functions.iter().cloned())
        .collect();
    let callsites_by_file: Vec<Vec<semarch_core::CallSite>> =
        idx.parsed.iter().map(|p| p.callsites.clone()).collect();
    let slices: Vec<&[semarch_core::CallSite]> = callsites_by_file.iter().map(|v| v.as_slice()).collect();

    let (graph, stats) = semarch_core::ArchitectureGraph::build(&functions, &slices);
    let closure = graph.may_closure();

    println!("{}", serde_json::to_string_pretty(&stats)?);
    // Top reachable-by-closure functions (diagnostic summary only).
    let mut ranked: Vec<(usize, String)> = closure
        .iter()
        .map(|(id, reach)| (reach.len(), id.to_string()))
        .collect();
    ranked.sort_by(|a, b| b.0.cmp(&a.0).then(a.1.cmp(&b.1)));
    for (n, id) in ranked.iter().take(12) {
        println!("{id}\t{n}");
    }
    Ok(())
}

fn run_snippet(language: &str, stdin: bool, file: Option<PathBuf>) -> anyhow::Result<()> {
    let source = if stdin {
        std::io::read_to_string(std::io::stdin())?
    } else {
        let path = file.context("pass a file or --stdin")?;
        std::fs::read_to_string(path)?
    };
    let mut idx = SemanticIndex::new();
    match language {
        "java" => {
            parse_into("snippet.java", &mut JavaFrontend::new()?, &source, &mut idx)?;
        }
        "python" => {
            parse_into("snippet.py", &mut PythonFrontend::new()?, &source, &mut idx)?;
        }
        other => anyhow::bail!("unknown language {other} (tier-A v0: java, python)"),
    }
    println!("{}", serde_json::to_string_pretty(&idx.parsed)?);
    Ok(())
}

fn parse_project(root: &PathBuf) -> Result<SemanticIndex, Error> {
    let files = ProjectDiscovery::new(root).discover()?;
    let mut idx = SemanticIndex::new();
    for f in files {
        let title = f.path.display().to_string();
        let source = std::fs::read_to_string(&f.path).map_err(Error::Io)?;
        match f.language {
            Language::Java => {
                parse_into(&title, &mut JavaFrontend::new()?, &source, &mut idx)?;
            }
            Language::Python => {
                parse_into(&title, &mut PythonFrontend::new()?, &source, &mut idx)?;
            }
            Language::Go | Language::JavaScript | Language::TypeScript | Language::CSharp => {
                // Frontends for these are T22–T24; skip silently to keep the
                // discovery plan stable in v0.
            }
        }
    }
    Ok(idx)
}

fn parse_into(
    path: &str,
    frontend: &mut dyn LanguageFrontend,
    source: &str,
    idx: &mut SemanticIndex,
) -> Result<u32, Error> {
    let file_raw = idx.parse_with(frontend, source)?;
    idx.set_file_path(file_raw, path);
    Ok(file_raw)
}
