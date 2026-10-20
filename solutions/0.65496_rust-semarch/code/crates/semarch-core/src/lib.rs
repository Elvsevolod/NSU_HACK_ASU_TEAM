//! # semarch-core
//!
//! Language-neutral semantic core of the analyzer: Common Semantic IR,
//! project discovery, the [`LanguageFrontend`] trait, and the minimal
//! CFG/guard machinery.
//!
//! Core types never mention Tree-sitter AST nodes; frontend crates normalize
//! semantic facts into [`ir`] types. `unknown != false` is enforced: every
//! semantic fact that can become an edge carries explicit [`ir::Evidence`]
//! with status; exclusions are records, not absences.

#![deny(clippy::correctness)]
#![warn(clippy::suspicious, clippy::complexity, clippy::perf)]

pub mod cfg;
pub mod analysis;
pub mod discovery;
pub mod frontend;
pub mod graph;
pub mod ids;
pub mod index;
pub mod invocation;
pub mod ir;
pub mod lang;
pub mod lowering;
pub mod span;
pub mod value;

pub use analysis::{
    analyze_body, analyze_body_with, AnalyzeInputs, Analyzer, BodyAnalysis, Builtin, Env, Frame,
    NoReturnSite, ReturnSite, ThrowSite, lookup_builtin,
};
pub use invocation::{CallOutcome, CallTargetProvider, CalleeBody};
pub use cfg::{GuardVerdict, apply_verdict, evaluate_condition, linear_cfg};
pub use discovery::{DiscoveredFile, ProjectDiscovery};
pub use graph::{ArchitectureGraph, GraphEdge, GraphStats, NodeKind};

use serde_json::Error as JsonError;
use thiserror::Error;

pub use frontend::{
    Allocator, AnnotationFact, FrontendError, GuardCondition, ImportFact,
    LanguageFrontend, LoopKind, ModuleDecl, ParsedFile, ParseContext,
};
pub use index::{roundtrip_json, SemanticIndex};
pub use ir::{
    Action, AnalysisGap, BasicBlock, BinaryOp, CallSite, Cfg, CfgBlock, Effect, Evidence,
    EvidenceStatus, Function, FunctionBody, FunctionSummary, GapReason, Guard, Statement,
    SymbolKind, Terminator, UnaryOp, ValueExpr,
};
pub use lang::{Capability, Language};
pub use lowering::{block_index, guard_index, validate as validate_body, BodyBuilder, BodyCheck};
pub use span::SourceSpan;
pub use value::{AbstractValue, LanguageProfile, Truth};

/// Library error type (`thiserror` at the library boundary).
#[derive(Debug, Error)]
pub enum Error {
    /// A frontend reported a real parse-level failure.
    #[error("frontend failure: {0}")]
    Frontend(#[from] FrontendError),
    /// Walking/discovering the project root failed.
    #[error("discovery failed: {0}")]
    Discovery(String),
    /// IR serialization round-trip failed.
    #[error("serialization failed: {0}")]
    Json(#[from] JsonError),
    /// Io failure.
    #[error(transparent)]
    Io(#[from] std::io::Error),
}

/// Library result alias.
pub type Result<T> = std::result::Result<T, Error>;
