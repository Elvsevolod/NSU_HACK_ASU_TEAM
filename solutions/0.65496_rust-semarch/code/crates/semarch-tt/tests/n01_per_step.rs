//! N01 acceptance (see `planning/BACKLOG.csv`): per-step entry decisions are
//! real (not a union mislabelled per step), a run manifest records the inputs
//! and configuration, and a missing project checkout is an *explicit*
//! degradation instead of a silent success without guards.
//!
//! The fixture is deliberately not Train Ticket: two mapped handlers on one
//! controller, both named by two steps of one scenario, and (in one variant) no
//! project checkout at all.

use std::path::{Path, PathBuf};

use semarch_scenario::scenario::Scenario;
use semarch_tt::pipeline::{AnalyzerConfig, LoadOptions, TtAnalyzer};
use semarch_tt::{Severity, report};

const ALPHA: &str = "method:svc:a.Letters#alpha";
const BETA: &str = "method:svc:a.Letters#beta";

fn temp_root(tag: &str) -> PathBuf {
    let root = std::env::temp_dir().join(format!(
        "semarch-n01-{tag}-{}-{}",
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

fn write(root: &Path, rel: &str, body: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, body).expect("write");
}

/// Skeleton with two `@GetMapping` handlers on one controller.
fn write_skeleton(root: &Path) {
    let sk = serde_json::json!({
        "project": "toy", "schema": "test",
        "nodes": {
            "type:svc:a.Letters": {
                "kind": "type", "fqn": "a.Letters", "type_kind": "class", "module": "svc",
                "annotations": [{"name": "RequestMapping", "args": "(\"/svc\")"}]
            },
            ALPHA: {
                "kind": "method", "owner": "type:svc:a.Letters", "name": "alpha",
                "descriptor": "", "module": "svc",
                "annotations": [{"name": "GetMapping", "args": "(path = \"/alpha\")"}]
            },
            BETA: {
                "kind": "method", "owner": "type:svc:a.Letters", "name": "beta",
                "descriptor": "", "module": "svc",
                "annotations": [{"name": "GetMapping", "args": "(path = \"/beta\")"}]
            }
        },
        "edges": []
    });
    write(
        root,
        "skeleton/toy.json",
        &serde_json::to_string_pretty(&sk).expect("skeleton json"),
    );
}

/// One scenario whose two steps name the two handlers (and share the class
/// token, which is what makes the union/per-step distinction observable).
fn write_scenario(root: &Path) {
    let scn = serde_json::json!({
        "project": "toy", "id": "S1", "title": "letters", "description": "",
        "input": "text",
        "steps": [
            {"n": 1, "action": "Run alpha in Letters"},
            {"n": 2, "action": "Run beta in Letters"}
        ]
    });
    write(
        root,
        "scenarios/S1.json",
        &serde_json::to_string_pretty(&scn).expect("scenario json"),
    );
}

/// UI client binding both routes to a control.
fn write_ui(root: &Path) {
    write(
        root,
        "targets/toy/svc-ui/static/client.js",
        "$(\"#go_alpha\").click(function () { $.ajax({ url: \"/svc/alpha\" }); });\n\
         $(\"#go_beta\").click(function () { $.ajax({ url: \"/svc/beta\" }); });\n",
    );
}

/// A minimal Java checkout so the G6 guard sources exist.
fn write_sources(root: &Path) {
    write(
        root,
        "targets/toy/svc/src/main/java/a/Letters.java",
        "package a;\npublic class Letters {}\n",
    );
}

fn load_scenario(root: &Path) -> Scenario {
    let text = std::fs::read_to_string(root.join("scenarios/S1.json")).expect("scenario");
    Scenario::from_json(&text).expect("parses")
}

fn alpha_has_step_lists(report: &report::ScenarioReport) -> (Vec<String>, Vec<String>) {
    (
        report.steps[0].selected_this_step.clone(),
        report.steps[1].selected_this_step.clone(),
    )
}

#[test]
fn per_step_selection_is_not_the_union() {
    let root = temp_root("steps");
    write_skeleton(&root);
    write_scenario(&root);
    write_ui(&root);
    write_sources(&root);

    let an = TtAnalyzer::load(&root).expect("loads");
    assert!(
        an.diagnostics.is_empty(),
        "a complete checkout must degrade nothing: {:?}",
        an.diagnostics
    );

    let scn = load_scenario(&root);
    let cfg = AnalyzerConfig::default();
    let pred = an.analyze(&scn, &cfg);
    let rep = report::build(
        &an,
        &[(scn.id.clone(), pred.clone(), scn.clone())],
        &cfg,
    );
    let rep = rep.scenarios.get("S1").expect("one scenario block");

    assert_eq!(rep.steps.len(), 2, "two steps in the fixture");
    let (step1, step2) = alpha_has_step_lists(rep);
    assert_eq!(step1, vec![ALPHA.to_owned()], "step 1 grounds alpha only");
    assert_eq!(step2, vec![BETA.to_owned()], "step 2 grounds beta only");
    assert_eq!(rep.steps[0].reason, "single_variant");
    assert_eq!(rep.steps[1].reason, "single_variant");

    // The whole point of N01: beta appears among step 1's ranked candidates
    // (it shares the class token) and is in the *union* the answer uses, but
    // step 1 did not choose it.
    let beta_in_step1 = rep.steps[0]
        .candidates
        .iter()
        .find(|c| c.method == BETA)
        .expect("beta shares the class token, so it ranks for step 1 too");
    assert!(
        !beta_in_step1.selected_this_step,
        "step 1 must not claim a decision it did not make"
    );
    assert!(
        beta_in_step1.selected,
        "beta is still part of the union the answer consumes"
    );

    // The union field is exactly the union of the per-step decisions.
    let mut union: Vec<String> = step1.into_iter().chain(step2).collect();
    union.sort();
    union.dedup();
    assert_eq!(union, vec![ALPHA.to_owned(), BETA.to_owned()]);
    assert!(pred.executes.contains(ALPHA) && pred.executes.contains(BETA));

    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn run_manifest_records_inputs_config_and_engine() {
    let root = temp_root("manifest");
    write_skeleton(&root);
    write_scenario(&root);
    write_ui(&root);
    write_sources(&root);

    let an = TtAnalyzer::load(&root).expect("loads");
    let cfg = AnalyzerConfig::default();
    let scn = load_scenario(&root);
    let pred = an.analyze(&scn, &cfg);
    let doc = report::build(&an, &[(scn.id.clone(), pred, scn.clone())], &cfg);

    assert_eq!(
        doc.schema_version,
        semarch_tt::manifest::REPORT_SCHEMA_VERSION
    );
    let m = &doc.manifest;
    assert_eq!(m.engine.name, "semarch");
    assert_eq!(m.engine.answer_schema, "contest-v1");
    assert!(!m.engine.version.is_empty());

    for key in ["skeleton", "scenarios", "project_sources_java"] {
        let v = m.inputs.get(key).unwrap_or_else(|| panic!("inputs[{key}]"));
        assert!(v.starts_with("fnv1a64:"), "{key} = {v}");
    }
    assert_eq!(m.config.max_candidates, cfg.max_candidates);
    assert_eq!(m.config.mechanisms.len(), 7, "G1..G7 recorded");

    // Fingerprints are a function of the inputs, not of the run.
    let again = TtAnalyzer::load(&root).expect("loads");
    assert_eq!(again.source_hash, an.source_hash);

    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn a_missing_checkout_is_an_explicit_degradation_or_a_hard_error() {
    let root = temp_root("degraded");
    write_skeleton(&root);
    write_scenario(&root);
    // no targets/ checkout at all: guard sources are unavailable

    let an = TtAnalyzer::load(&root).expect("degrades, does not fail");
    let degraded: Vec<&semarch_tt::Diagnostic> = an
        .diagnostics
        .iter()
        .filter(|d| d.severity == Severity::Degraded)
        .collect();
    assert_eq!(
        degraded.len(),
        1,
        "exactly one summary degradation: {:?}",
        an.diagnostics
    );
    assert_eq!(degraded[0].id, "guard_sources_unavailable");
    assert!(
        an.diagnostics
            .iter()
            .any(|d| d.id == "ui_evidence_absent" && d.severity == Severity::Info),
        "absent UI evidence is also reported: {:?}",
        an.diagnostics
    );
    assert_eq!(an.graph.guard_count(), 0, "no guards without sources");

    // The degradation is recorded in the manifest, naming the exact inputs.
    let cfg = AnalyzerConfig::default();
    let scn = load_scenario(&root);
    let pred = an.analyze(&scn, &cfg);
    let doc = report::build(&an, &[(scn.id.clone(), pred, scn.clone())], &cfg);
    assert_eq!(
        doc.manifest
            .inputs
            .get("project_sources_java")
            .map(String::as_str),
        Some("unavailable")
    );
    assert!(doc
        .manifest
        .diagnostics
        .iter()
        .any(|d| d.id == "guard_sources_unavailable"));

    // Strict mode refuses to pretend a degraded run is a clean one.
    let strict = TtAnalyzer::load_with(&root, &LoadOptions { require_sources: true });
    assert!(strict.is_err(), "strict mode must fail when sources are absent");

    let _ = std::fs::remove_dir_all(&root);
}
