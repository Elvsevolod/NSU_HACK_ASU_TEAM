//! Contest answer projection: internal [`Prediction`] → `submission.json`.
//!
//! Hard rules enforced here (from the task statement):
//!
//! * the relation field is `relation`, never `type`;
//! * every endpoint id is copied **verbatim** from the skeleton `nodes`; a
//!   synthesized id is dropped and reported, never emitted;
//! * `executes` edges originate from the service id `scenario:<S>`;
//! * one edge appears once (the answer describes the scenario, not the steps).
//!
//! [`crate::export`] is the only place that knows the wire format.

use std::collections::{BTreeMap, HashSet};

use serde::{Deserialize, Serialize};

use crate::graph::Prediction;

/// Whole-answer document.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct Submission {
    pub project: String,
    pub scenarios: BTreeMap<String, SubmissionScenario>,
}

/// One scenario block.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct SubmissionScenario {
    pub edges: Vec<SubmissionEdge>,
}

/// One answer edge.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
pub struct SubmissionEdge {
    pub source: String,
    pub relation: String,
    pub target: String,
}

/// Non-fatal export diagnostics.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ExportReport {
    /// Edges emitted after whitelist filtering.
    pub emitted: usize,
    /// Ids dropped because they are not skeleton vertices.
    pub rejected: Vec<String>,
}

/// Exactly what the task asks: four relation sets per scenario.
pub const RELATION_EXECUTES: &str = "executes";
pub const RELATION_CALLS: &str = "calls";
pub const RELATION_REMOTE: &str = "remote";
pub const RELATION_DATA: &str = "data";

/// Project one prediction into a scenario block.
#[must_use]
pub fn scenario_block(
    scenario_id: &str,
    pred: &Prediction,
    method_ids: &HashSet<String>,
    table_ids: &HashSet<String>,
) -> (SubmissionScenario, ExportReport) {
    let mut edges: Vec<SubmissionEdge> = Vec::new();
    let mut report = ExportReport::default();
    let mut push = |source: &str, relation: &str, target: &str, ok: bool, r: &mut ExportReport| {
        if ok {
            edges.push(SubmissionEdge {
                source: source.to_owned(),
                relation: relation.to_owned(),
                target: target.to_owned(),
            });
        } else {
            r.rejected.push(format!("{relation}: {target}"));
        }
    };

    for m in &pred.executes {
        let ok = method_ids.contains(m);
        push(&format!("scenario:{scenario_id}"), RELATION_EXECUTES, m, ok, &mut report);
    }
    for (a, b) in &pred.calls {
        let ok = method_ids.contains(a) && method_ids.contains(b);
        push(a, RELATION_CALLS, b, ok, &mut report);
    }
    for (a, b) in &pred.remote {
        let ok = method_ids.contains(a) && method_ids.contains(b);
        push(a, RELATION_REMOTE, b, ok, &mut report);
    }
    for (a, t) in &pred.data {
        let ok = method_ids.contains(a) && table_ids.contains(t);
        push(a, RELATION_DATA, t, ok, &mut report);
    }

    edges.sort();
    edges.dedup();
    report.emitted = edges.len();
    (SubmissionScenario { edges }, report)
}

/// Build a whole-answer document from per-scenario predictions.
#[must_use]
pub fn build(
    project: &str,
    predictions: &[(String, Prediction)],
    method_ids: &HashSet<String>,
    table_ids: &HashSet<String>,
) -> (Submission, BTreeMap<String, ExportReport>) {
    let mut submission = Submission {
        project: project.to_owned(),
        scenarios: BTreeMap::new(),
    };
    let mut reports = BTreeMap::new();
    for (sid, pred) in predictions {
        let (block, report) = scenario_block(sid, pred, method_ids, table_ids);
        reports.insert(sid.clone(), report);
        submission.scenarios.insert(sid.clone(), block);
    }
    (submission, reports)
}

/// Serialize with stable key order (pretty for reviewable diffs).
///
/// # Errors
/// Propagates `serde_json` failures (practically unreachable for this shape).
pub fn to_json(submission: &Submission) -> Result<String, serde_json::Error> {
    serde_json::to_string_pretty(submission)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ids(items: &[&str]) -> HashSet<String> {
        items.iter().map(|s| (*s).to_owned()).collect()
    }

    #[test]
    fn emits_four_relation_kinds_with_verbatim_ids() {
        let mut pred = Prediction::default();
        pred.executes.insert("method:m:A#x()".into());
        pred.calls.insert(("method:m:A#x()".into(), "method:m:B#y()".into()));
        pred.remote.insert(("method:m:A#x()".into(), "method:n:C#z()".into()));
        pred.data.insert(("method:m:A#x()".into(), "res:table:m.t".into()));
        let (block, rep) =
            scenario_block("S1", &pred, &ids(&["method:m:A#x()", "method:m:B#y()", "method:n:C#z()"]), &ids(&["res:table:m.t"]));
        assert!(rep.rejected.is_empty());
        let rels: Vec<&str> = block.edges.iter().map(|e| e.relation.as_str()).collect();
        assert_eq!(rels, vec!["calls", "data", "remote", "executes"]);
        assert!(block.edges.iter().any(|e| e.source == "scenario:S1" && e.relation == "executes"));
    }

    #[test]
    fn invented_ids_are_rejected_not_emitted() {
        let mut pred = Prediction::default();
        pred.executes.insert("method:m:Ghost#x()".into());
        pred.data.insert(("method:m:A#x()".into(), "res:table:nope.t".into()));
        let (block, rep) = scenario_block("S2", &pred, &ids(&["method:m:A#x()"]), &ids(&[]));
        assert!(block.edges.is_empty(), "{:?}", block.edges);
        assert_eq!(rep.rejected.len(), 2);
    }

    #[test]
    fn duplicates_collapse() {
        let mut pred = Prediction::default();
        pred.executes.insert("method:m:A#x()".into());
        let pred2 = pred.clone();
        pred.merge(&pred2);
        let (block, _) = scenario_block("S3", &pred, &ids(&["method:m:A#x()"]), &ids(&[]));
        assert_eq!(block.edges.len(), 1);
    }

    #[test]
    fn json_shape_uses_relation_key() {
        let mut pred = Prediction::default();
        pred.executes.insert("method:m:A#x()".into());
        let (sub, _) = build("trainticket", &[("S0".to_owned(), pred)], &ids(&["method:m:A#x()"]), &ids(&[]));
        let json = to_json(&sub).unwrap();
        assert!(json.contains("\"relation\""), "{json}");
        assert!(!json.contains("\"type\""), "{json}");
        assert!(json.contains("\"project\": \"trainticket\""));
    }
}
