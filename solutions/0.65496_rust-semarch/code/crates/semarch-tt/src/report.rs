//! Audit trail for one answer.
//!
//! The contest asks for a *reasoned* answer: every semantic edge should rest on
//! evidence, and anything that could not be decided should be visible as an
//! unknown rather than silently guessed. This module produces, per scenario, a
//! machine-readable report that names
//!
//! * the ranked entry candidates and which of them the near-tie policy kept;
//! * for every predicted edge, the skeleton call site (file, line, receiver)
//!   and the skeleton relation it rests on;
//! * for every executed method, why it is in the answer (entry, framework
//!   callback, ORM materialization, or the predecessor that reaches it);
//! * every call site the scenario's feature set kills, and which feature would
//!   revive it.
//!
//! It is intentionally *redundant* with the prediction: the evidence is
//! re-derived from the skeleton, so an LLM or a human can check a call path by
//! hand instead of trusting the engine's own bookkeeping.
//!
//! Nothing here reads the golden answer, a scenario id, or any project name:
//! the report is a function of the skeleton, the sources and the scenario text.

use std::collections::{BTreeMap, BTreeSet};

use semarch_scenario::bm25::Ranked;
use semarch_scenario::scenario::Scenario;
use serde::Serialize;

use crate::entry::StepSelection;
use crate::graph::{EdgeEvidence, Prediction, TtGraph, Witness};
use crate::guards::scenario_features;
use crate::manifest::RunManifest;
use crate::pipeline::{AnalyzerConfig, TtAnalyzer};

/// How many ranked candidates to record per step.
const CANDIDATES_PER_STEP: usize = 6;
/// How many pruned call sites to record per scenario (keeps the file readable).
const PRUNED_MAX: usize = 400;

/// One ranked entry candidate for a step.
#[derive(Debug, Clone, Serialize)]
pub struct Candidate {
    pub method: String,
    /// External route a client would call (`/api/v1/...`), when the method is
    /// an endpoint.
    pub route: Option<String>,
    /// Normalized score in `[0, 1]` relative to the best candidate of the step.
    pub score: f64,
    /// Whether *this step alone* kept the candidate as an entry. This is the
    /// real per-step decision; the answer unions it across steps.
    pub selected_this_step: bool,
    /// Whether *any* step of the scenario kept the candidate as an entry (the
    /// union the answer used). Kept for compatibility with the previous report
    /// schema; it is not a per-step decision.
    pub selected: bool,
}

/// One scenario step and its grounding evidence.
#[derive(Debug, Clone, Serialize)]
pub struct StepReport {
    pub n: u32,
    pub action: String,
    /// Query tokens actually searched for.
    pub query: Vec<String>,
    /// The rule that decided this step's selection (see
    /// [`crate::entry::StepReason`]).
    pub reason: String,
    /// Endpoint methods this step alone contributed.
    pub selected_this_step: Vec<String>,
    pub candidates: Vec<Candidate>,
}

/// A predicted edge together with the skeleton fact behind it.
#[derive(Debug, Clone, Serialize)]
pub struct EdgeReport {
    pub relation: String,
    pub source: String,
    pub target: String,
    /// See [`EdgeEvidence::mapping`].
    pub mapping: String,
    pub call_site: Option<String>,
    pub file: Option<String>,
    pub line: Option<u32>,
    pub receiver: Option<String>,
    pub receiver_type: Option<String>,
    pub args_text: Option<String>,
    /// Every call site that justifies the edge (see [`EdgeEvidence::witnesses`]).
    pub witnesses: Vec<Witness>,
    /// See [`EdgeEvidence::basis`].
    pub basis: String,
    pub note: String,
}

impl From<EdgeEvidence> for EdgeReport {
    fn from(e: EdgeEvidence) -> Self {
        Self {
            relation: e.relation,
            source: e.source,
            target: e.target,
            mapping: e.mapping,
            call_site: e.call_site,
            file: e.file,
            line: e.line,
            receiver: e.receiver,
            receiver_type: e.receiver_type,
            args_text: e.args_text,
            witnesses: e.witnesses,
            basis: e.basis,
            note: e.note,
        }
    }
}

/// Per-scenario audit trail.
#[derive(Debug, Clone, Serialize)]
pub struct ScenarioReport {
    pub id: String,
    pub title: String,
    pub description: String,
    pub steps: Vec<StepReport>,
    /// Answer sizes: `executes`, `calls`, `remote`, `data`, `edges`,
    /// `edges_without_call_site`.
    pub counts: BTreeMap<String, usize>,
    /// Why each executed method is in the answer.
    pub executes: BTreeMap<String, String>,
    pub edges: Vec<EdgeReport>,
    /// Call sites this scenario's feature set kills (G6).
    pub pruned: Vec<EdgeReport>,
    /// Emitted ids that are not skeleton vertices. Must stay empty.
    pub unknown_ids: Vec<String>,
}

/// The whole answer's audit trail.
#[derive(Debug, Clone, Serialize)]
pub struct Report {
    /// Report schema version (see [`crate::manifest::REPORT_SCHEMA_VERSION`]).
    pub schema_version: u32,
    /// What this run executed, on which inputs, with which configuration.
    pub manifest: RunManifest,
    pub project: String,
    /// Resolution mechanisms that were on for this run.
    pub mechanisms: BTreeMap<String, bool>,
    pub skeleton: BTreeMap<String, usize>,
    pub scenarios: BTreeMap<String, ScenarioReport>,
}

/// Build the whole audit-trail document: run manifest plus one report per
/// scenario. This is the single constructor of [`Report`], so the CLI and tests
/// describe a run identically.
#[must_use]
pub fn build(
    an: &TtAnalyzer,
    runs: &[(String, Prediction, Scenario)],
    cfg: &AnalyzerConfig,
) -> Report {
    let mech = mechanisms(cfg);
    let mut scenarios = BTreeMap::new();
    for (id, pred, scn) in runs {
        scenarios.insert(id.clone(), scenario_report(an, scn, pred, cfg));
    }
    Report {
        schema_version: crate::manifest::REPORT_SCHEMA_VERSION,
        manifest: crate::manifest::build(an, cfg, mech.clone()),
        project: an.skeleton.project.clone(),
        mechanisms: mech,
        skeleton: skeleton_stats(an),
        scenarios,
    }
}

/// Which mechanisms were enabled, as a stable, printable map.
#[must_use]
pub fn mechanisms(cfg: &AnalyzerConfig) -> BTreeMap<String, bool> {
    let r = cfg.resolution;
    BTreeMap::from([
        ("G1_dispatch".to_owned(), r.dispatch),
        ("G2_declarations".to_owned(), r.drop_declarations),
        ("G3_repositories".to_owned(), r.drop_repository_proxies),
        ("G4_entities".to_owned(), r.materialize_entities),
        ("G5_callbacks".to_owned(), r.framework_callbacks),
        ("G6_feature_guards".to_owned(), r.feature_guards),
        ("G7_static_receiver".to_owned(), r.static_receiver),
    ])
}

/// Sizes of the loaded project, for the report header.
#[must_use]
pub fn skeleton_stats(an: &TtAnalyzer) -> BTreeMap<String, usize> {
    let s = an.graph.stats();
    BTreeMap::from([
        ("nodes".to_owned(), an.skeleton.nodes.len()),
        ("edges".to_owned(), an.skeleton.edges.len()),
        ("methods".to_owned(), s.methods),
        ("call_sites".to_owned(), s.call_sites),
        ("repository_types".to_owned(), s.repository_types),
        ("repository_methods".to_owned(), s.repository_methods),
        ("framework_callbacks".to_owned(), s.callbacks),
        ("servlet_filters".to_owned(), s.filters),
        ("tables".to_owned(), an.graph.table_ids.len()),
        ("endpoints".to_owned(), an.entries.len()),
        ("ui_facts".to_owned(), an.ui_facts),
        ("feature_guards".to_owned(), an.graph.guard_count()),
    ])
}

/// Build the audit trail for one scenario and its prediction.
#[must_use]
pub fn scenario_report(
    an: &TtAnalyzer,
    scn: &Scenario,
    pred: &Prediction,
    cfg: &AnalyzerConfig,
) -> ScenarioReport {
    let rankings = an.rank(scn);
    let per_step = an
        .entries
        .select_per_step(scn, &rankings, cfg.entry_ratio, cfg.max_candidates);
    let selected: BTreeSet<String> = per_step
        .iter()
        .flat_map(|s| s.members.iter())
        .map(|&i| an.entries.endpoints[i].method.clone())
        .collect();

    let steps = rankings
        .iter()
        .enumerate()
        .map(|(i, r)| {
            let sel = per_step.get(i).cloned().unwrap_or(StepSelection {
                members: Vec::new(),
                reason: crate::entry::StepReason::NoCandidate,
            });
            let this_step: BTreeSet<String> = sel
                .members
                .iter()
                .map(|&j| an.entries.endpoints[j].method.clone())
                .collect();
            StepReport {
                n: r.step,
                action: step_action(scn, r.step),
                query: an.entries.step_query(scn, i),
                reason: sel.reason.as_str().to_owned(),
                selected_this_step: this_step.iter().cloned().collect(),
                candidates: r
                    .ranked
                    .iter()
                    .take(CANDIDATES_PER_STEP)
                    .map(|c| candidate(an, c, &selected, &this_step))
                    .collect(),
            }
        })
        .collect();

    let mut edges: Vec<EdgeReport> = Vec::new();
    for (a, b) in &pred.calls {
        edges.push(an.graph.evidence_for("calls", a, b).into());
    }
    for (a, b) in &pred.remote {
        edges.push(an.graph.evidence_for("remote", a, b).into());
    }
    for (a, b) in &pred.data {
        edges.push(an.graph.evidence_for("data", a, b).into());
    }
    edges.sort_by(|x, y| {
        (&x.relation, &x.source, &x.target).cmp(&(&y.relation, &y.source, &y.target))
    });

    let engaged = scenario_features(scn);
    let mut pruned: Vec<EdgeReport> = Vec::new();
    for m in &pred.executes {
        pruned.extend(an.graph.guard_pruned(m, &engaged).into_iter().map(Into::into));
    }
    pruned.truncate(PRUNED_MAX);

    let unbacked = edges.iter().filter(|e| e.basis == "framework").count();
    let ambiguous = edges.iter().filter(|e| e.mapping == "ambiguous").count();
    let counts = BTreeMap::from([
        ("executes".to_owned(), pred.executes.len()),
        ("calls".to_owned(), pred.calls.len()),
        ("remote".to_owned(), pred.remote.len()),
        ("data".to_owned(), pred.data.len()),
        ("edges".to_owned(), pred.edge_count()),
        ("edges_without_call_site".to_owned(), unbacked),
        ("edges_with_ambiguous_witness".to_owned(), ambiguous),
        ("pruned_call_sites".to_owned(), pruned.len()),
    ]);

    ScenarioReport {
        id: scn.id.clone(),
        title: scn.title.clone(),
        description: scn.description.clone(),
        steps,
        counts,
        executes: executes_reasons(an, pred, &selected),
        edges,
        pruned,
        unknown_ids: an.unknown_ids(pred).into_iter().collect(),
    }
}

fn candidate(
    an: &TtAnalyzer,
    c: &Ranked,
    selected: &BTreeSet<String>,
    this_step: &BTreeSet<String>,
) -> Candidate {
    let endpoint = an.entries.endpoints.get(c.doc);
    let method = endpoint.map_or_else(String::new, |e| e.method.clone());
    Candidate {
        selected_this_step: this_step.contains(&method),
        selected: selected.contains(&method),
        route: endpoint.map(|e| e.full_path.clone()),
        method,
        score: c.score,
    }
}

fn step_action(scn: &Scenario, n: u32) -> String {
    scn.steps
        .iter()
        .find(|s| s.n == n)
        .map_or_else(String::new, |s| s.action.clone())
}

/// Why every executed method is in the answer.
fn executes_reasons(
    an: &TtAnalyzer,
    pred: &Prediction,
    entries: &BTreeSet<String>,
) -> BTreeMap<String, String> {
    let graph: &TtGraph = &an.graph;
    let mut out = BTreeMap::new();
    for m in &pred.executes {
        let reason = if entries.contains(m) {
            let route = an
                .entries
                .endpoints
                .iter()
                .find(|e| &e.method == m)
                .map_or_else(|| "no route".to_owned(), |e| e.full_path.clone());
            format!("entry point, grounded by step text (route {route})")
        } else if let Some(c) = graph.callbacks().iter().find(|c| &c.method == m) {
            if c.traverse {
                "framework callback, traversed (Spring Security UserDetailsService)".to_owned()
            } else {
                "framework callback, container-invoked (Servlet Filter): executes only".to_owned()
            }
        } else {
            let from: Vec<String> = pred
                .calls
                .iter()
                .chain(pred.remote.iter())
                .filter(|(_, t)| t == m)
                .map(|(s, _)| s.clone())
                .collect();
            if !from.is_empty() {
                format!("reached from {}", from.join(", "))
            } else if graph.method(m).is_some_and(|mi| mi.name == "<init>") {
                "ORM materialization: JPA runs the entity's no-arg constructor".to_owned()
            } else {
                "no project call site: framework or container contract".to_owned()
            }
        };
        out.insert(m.clone(), reason);
    }
    out
}
