//! # semarch-scenario
//!
//! Language-neutral scenario grounding layer (L4). It owns two generic,
//! framework-agnostic concerns:
//!
//! * the scenario *text model* ([`scenario::Scenario`]) — a sequence of
//!   user actions with no addresses attached;
//! * *retrieval* of candidate entry points ([`bm25`]) over caller-supplied
//!   documents.
//!
//! Nothing here knows about Spring, HTTP routes or Train Ticket. Adapters
//! build documents (from code, routes, UI text, configs) and call the ranker.

#![deny(clippy::correctness)]
#![warn(clippy::suspicious, clippy::complexity, clippy::perf)]

pub mod bm25;
pub mod scenario;
pub mod text;

pub use bm25::{Bm25Index, Ranked};
pub use scenario::{Scenario, Step};
pub use text::{synonyms, tokenize};
