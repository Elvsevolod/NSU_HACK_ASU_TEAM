//! Run manifest: what one analysis run executed, on which inputs, with which
//! configuration, and which degradations it observed.
//!
//! The contest answer is a function of the skeleton, the project sources, the
//! UI sources and the scenario text. This module records the *identity* of
//! exactly those inputs (as content fingerprints), the mechanism switches that
//! were on, the engine version, and any silent-looking degradation the loader
//! had to accept (for example: project sources absent, so optional-feature
//! guards are unknown). Nothing here reads the golden answer or a scenario id.

use std::collections::BTreeMap;
use std::path::Path;

use serde::Serialize;

use crate::hash::{content_hash, set_hash};
use crate::pipeline::{AnalyzerConfig, TtAnalyzer};

/// Report schema version. Bumped whenever the audit-trail JSON gains or changes
/// meaning, so a consumer can tell a re-shaped report from a re-shaped answer.
pub const REPORT_SCHEMA_VERSION: u32 = 2;

/// Answer schema this build emits (`submission.json` shape).
pub const ANSWER_SCHEMA: &str = "contest-v1";

/// Severity of a non-fatal diagnostic.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Severity {
    /// The run proceeded, but a declared input was missing or unreadable, so a
    /// mechanism could not be exercised. The answer is *degraded*, not wrong by
    /// construction — but a reader must know.
    Degraded,
    /// An observation that does not change the answer.
    Info,
}

/// One non-fatal diagnostic of a run.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Diagnostic {
    /// Stable rule id (`guard_sources_unavailable`, `ui_evidence_absent`).
    pub id: String,
    pub severity: Severity,
    /// Human-readable detail, including the underlying error when there is one.
    pub message: String,
}

impl Diagnostic {
    pub fn degraded(id: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            severity: Severity::Degraded,
            message: message.into(),
        }
    }

    pub fn info(id: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            severity: Severity::Info,
            message: message.into(),
        }
    }
}

/// Engine identity of one run.
#[derive(Debug, Clone, Serialize)]
pub struct EngineInfo {
    pub name: &'static str,
    pub version: &'static str,
    /// `submission.json` shape this build emits.
    pub answer_schema: &'static str,
    /// `report.json` shape this build emits.
    pub report_schema: u32,
}

impl Default for EngineInfo {
    fn default() -> Self {
        Self {
            name: "semarch",
            version: env!("CARGO_PKG_VERSION"),
            answer_schema: ANSWER_SCHEMA,
            report_schema: REPORT_SCHEMA_VERSION,
        }
    }
}

/// The configuration a run used, recorded verbatim.
#[derive(Debug, Clone, Serialize)]
pub struct RunConfig {
    pub entry_ratio: f64,
    pub max_candidates: usize,
    /// Mechanism id → enabled (the G1..G7 ablation switches).
    pub mechanisms: BTreeMap<String, bool>,
}

/// The recorded facts of one run.
#[derive(Debug, Clone, Serialize)]
pub struct RunManifest {
    pub engine: EngineInfo,
    pub config: RunConfig,
    /// Fingerprints of every input that can change the answer. Values are
    /// labelled (`fnv1a64:<hex>`) or an explicit `absent`/`unavailable`.
    pub inputs: BTreeMap<String, String>,
    /// Non-fatal degradations observed while loading or analyzing.
    pub diagnostics: Vec<Diagnostic>,
}

/// Build the manifest for one loaded analyzer and configuration.
#[must_use]
pub fn build(
    an: &TtAnalyzer,
    cfg: &AnalyzerConfig,
    mechanisms: BTreeMap<String, bool>,
) -> RunManifest {
    let mut inputs = BTreeMap::new();

    inputs.insert(
        "skeleton".to_owned(),
        fingerprint_file(&an.skeleton_path).unwrap_or_else(|| "absent".to_owned()),
    );
    inputs.insert("scenarios".to_owned(), fingerprint_scenarios(an.root()));
    inputs.insert(
        "project_sources_java".to_owned(),
        if an.source_hash.is_empty() {
            "unavailable".to_owned()
        } else {
            an.source_hash.clone()
        },
    );

    RunManifest {
        engine: EngineInfo::default(),
        config: RunConfig {
            entry_ratio: cfg.entry_ratio,
            max_candidates: cfg.max_candidates,
            mechanisms,
        },
        inputs,
        diagnostics: an.diagnostics.clone(),
    }
}

/// Fingerprint one file, or `None` if it cannot be read.
#[must_use]
pub fn fingerprint_file(path: &Path) -> Option<String> {
    std::fs::read(path).ok().map(|bytes| content_hash(&bytes))
}

/// Fingerprint every `*.json` scenario under `<root>/scenarios`, order-free.
fn fingerprint_scenarios(root: &Path) -> String {
    let dir = root.join("scenarios");
    let Ok(entries) = std::fs::read_dir(&dir) else {
        return "absent".to_owned();
    };
    let mut owned: Vec<(String, Vec<u8>)> = Vec::new();
    for e in entries.flatten() {
        let path = e.path();
        if !path.extension().is_some_and(|x| x == "json") {
            continue;
        }
        let Ok(bytes) = std::fs::read(&path) else {
            continue;
        };
        let name = e.file_name().to_string_lossy().into_owned();
        owned.push((name, bytes));
    }
    if owned.is_empty() {
        return "absent".to_owned();
    }
    let pairs: Vec<(&str, &[u8])> =
        owned.iter().map(|(n, b)| (n.as_str(), b.as_slice())).collect();
    set_hash(pairs)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn engine_info_is_self_describing() {
        let e = EngineInfo::default();
        assert_eq!(e.name, "semarch");
        assert_eq!(e.answer_schema, ANSWER_SCHEMA);
        assert_eq!(e.report_schema, REPORT_SCHEMA_VERSION);
        assert!(!e.version.is_empty());
    }

    #[test]
    fn severity_serializes_as_a_stable_word() {
        let d = Diagnostic::degraded("guard_sources_unavailable", "no sources");
        let json = serde_json::to_string(&d).unwrap();
        assert!(json.contains("\"severity\":\"degraded\""), "{json}");
    }
}
