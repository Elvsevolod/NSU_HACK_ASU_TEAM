//! # semarch-tt
//!
//! Train Ticket contour adapter. Three responsibilities, all *project-bound*
//! (this crate is allowed to know Train Ticket, the core is not):
//!
//! 1. [`skeleton`] — typed view of the organizer-provided project skeleton;
//! 2. [`graph`] — resolution of *possible* skeleton edges into *executing*
//!    ones using general mechanisms (interface dispatch, Spring Data
//!    repository proxies, ORM entity materialization, framework callbacks);
//! 3. [`entry`] — grounding scenario steps onto endpoints (routes + UI text),
//!    plus [`export`] of the contest answer.
//!
//! Every mechanism here is expressed in terms of (a) language semantics,
//! (b) a public framework contract (JPA / Spring Data / Servlet / Spring
//! Security / Spring Cloud Gateway), or (c) project data files. No rule
//! mentions a scenario id, an entity name or a hand-written route table.

#![deny(clippy::correctness)]
#![warn(clippy::suspicious, clippy::complexity, clippy::perf)]

pub mod bodies;
pub mod engine;
pub mod entry;
pub mod export;
pub mod framework;
pub mod graph;
pub mod guards;
pub mod hash;
pub mod invocations;
pub mod manifest;
pub mod pipeline;
pub mod request;
pub mod report;
pub mod skeleton;
pub mod ui;

pub use bodies::{BodyIndex, FileUnit, Slot};
pub use engine::{
    DecisionEvent, EdgeCounts, EdgeDelta, EffectEvent, Relation, ScenarioEngine, ScenarioOutcome,
    SemanticMode, ShadowDiff, StepOutcome,
};
pub use entry::{Endpoint, EntryIndex, StepRanking, StepReason, StepSelection};
pub use export::{Submission, SubmissionScenario};
pub use graph::{
    CallSiteEdges, EdgeEvidence, GraphStats, MethodInfo, Prediction, ResolutionConfig, TtGraph,
    Witness,
};
pub use guards::{GuardIndex, scenario_features};
pub use manifest::{Diagnostic, RunManifest, Severity};
pub use pipeline::{AnalyzerConfig, LoadOptions, TtAnalyzer};
pub use report::{Report, ScenarioReport};
pub use request::{BoundField, BoundRequest, BoundValue, FieldDecl, FieldOrigin};
pub use ui::UiOption;
pub use skeleton::Skeleton;

use thiserror::Error;

/// Adapter-level error type.
#[derive(Debug, Error)]
pub enum TtError {
    /// Filesystem failure while reading project inputs.
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
    /// Malformed skeleton / scenario / config JSON.
    #[error("json: {0}")]
    Json(#[from] serde_json::Error),
    /// Corrupt gzip stream.
    #[error("gzip: {0}")]
    Gzip(String),
    /// A required project input is missing.
    #[error("missing project input: {0}")]
    Missing(String),
    /// A core frontend/analysis failure while reading project sources.
    #[error("core: {0}")]
    Core(#[from] semarch_core::Error),
}
