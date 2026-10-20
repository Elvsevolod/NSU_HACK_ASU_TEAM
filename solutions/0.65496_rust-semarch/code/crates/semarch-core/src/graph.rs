//! Function-level architecture graph and the *may-closure* (`executes`)
//! computation (T12).
//!
//! Provenance of the algorithms:
//!
//! - **Call graph construction** follows the language-neutral extractor
//!   shape of pyan3 / Comex: call sites are matched to functions by simple
//!   name, call-site ownership by innermost-span containment; ambiguity
//!   stays `Unresolved` rather than being resolved by guessing.
//! - **May-closure** is reachability over call edges — the transitive
//!   closure those same tools use to decide which methods may execute in a
//!   scenario. Implemented with `petgraph::visit::Dfs`, so cycles terminate
//!   naturally.
//! - Every edge carries explicit [`Evidence`]; an unresolvable callee is
//!   not dropped but becomes an `External` node with `Unresolved` evidence.
//!
//! Nodes are only [`FunctionId`]s and external callee labels — the canonical
//! Train Ticket skeleton IDs enter later, in the exporter, bound by
//! verbatim string matching (never synthesized here). Storage is dense and
//! serde-friendly; petgraph is used transiently for reachability only.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::ids::CallSiteId;
use crate::ir::{CallSite, Evidence, Function};
use crate::span::SourceSpan;

/// A graph node: a project function or an external/unresolved callee.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum NodeKind {
    /// A function parsed inside the analyzed project.
    Function {
        id: crate::ids::FunctionId,
    },
    /// An external or unresolvable callee; `label` is the callee text as
    /// written. Kept so unresolved edges are never silently dropped.
    External {
        label: String,
    },
}

/// A call relation with its evidence.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GraphEdge {
    pub callsite: Option<CallSiteId>,
    pub callee: String,
    pub evidence: Evidence,
}

/// The architecture graph over one or more parsed files.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct ArchitectureGraph {
    /// Dense node payloads indexed by node id (`u32`).
    pub nodes: Vec<NodeKind>,
    /// Dense edges: `(from, to, payload)`.
    pub edges: Vec<(u32, u32, GraphEdge)>,
    /// Function node id lookup for the may-closure.
    pub function_nodes: BTreeMap<crate::ids::FunctionId, u32>,
}

/// Counters produced while building the graph (diagnostics surface).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct GraphStats {
    pub functions: usize,
    pub callsites: usize,
    pub confirmed_edges: usize,
    pub possible_edges: usize,
    pub unresolved_edges: usize,
}

impl ArchitectureGraph {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Node payload of a dense id.
    #[must_use]
    pub fn node(&self, id: u32) -> &NodeKind {
        &self.nodes[id as usize]
    }

    /// Add a function node (interning by function id).
    pub fn add_function(&mut self, id: crate::ids::FunctionId) -> u32 {
        if let Some(ix) = self.function_nodes.get(&id) {
            return *ix;
        }
        let ix = self.nodes.len() as u32;
        self.nodes.push(NodeKind::Function { id });
        self.function_nodes.insert(id, ix);
        ix
    }

    /// Add (or intern) an external callee node.
    pub fn add_external(&mut self, label: impl Into<String>) -> u32 {
        let kind = NodeKind::External { label: label.into() };
        if let Some(ix) = self.nodes.iter().position(|n| *n == kind) {
            return ix as u32;
        }
        let ix = self.nodes.len() as u32;
        self.nodes.push(kind);
        ix
    }

    /// Add a call edge with evidence.
    pub fn add_edge(&mut self, from: u32, to: u32, edge: GraphEdge) {
        self.edges.push((from, to, edge));
    }

    /// Build the graph from parsed files. Call sites are owned by the
    /// innermost function whose span contains the call-site span; callees
    /// resolve by simple name (unique → `confirmed`, ambiguous →
    /// `possible`, absent → `External` node with `Unresolved` evidence).
    #[must_use]
    pub fn build(functions: &[Function], callsites_by_file: &[&[CallSite]]) -> (Self, GraphStats) {
        let mut graph = Self::new();
        for f in functions {
            graph.add_function(f.id);
        }

        let mut stats = GraphStats {
            functions: functions.len(),
            ..GraphStats::default()
        };

        for file_callsites in callsites_by_file {
            for cs in *file_callsites {
                stats.callsites += 1;

                // Owner: innermost containing function (same rule as return
                // assignment in the frontends).
                let Some(owner) = functions
                    .iter()
                    .filter(|f| covers(f.span, cs.span))
                    .min_by_key(|f| f.span.end_byte - f.span.start_byte)
                else {
                    stats.unresolved_edges += 1;
                    continue;
                };
                let from = graph.function_nodes[&owner.id];

                let (candidates, unique) = resolve_by_name(functions, &cs.callee);
                match candidates.len() {
                    0 => {
                        stats.unresolved_edges += 1;
                        let to = graph.add_external(cs.callee.clone());
                        graph.add_edge(
                            from,
                            to,
                            GraphEdge {
                                callsite: Some(cs.id),
                                callee: cs.callee.clone(),
                                evidence: Evidence::unresolved("no project callee matched by name"),
                            },
                        );
                    }
                    n if n > 1 => {
                        stats.possible_edges += n;
                        for cid in candidates {
                            let to = graph.function_nodes[&cid];
                            graph.add_edge(
                                from,
                                to,
                                GraphEdge {
                                    callsite: Some(cs.id),
                                    callee: cs.callee.clone(),
                                    evidence: Evidence::possible("ambiguous simple-name match"),
                                },
                            );
                        }
                    }
                    _ => {
                        stats.confirmed_edges += 1;
                        let _ = unique;
                        let to = graph.function_nodes[&candidates[0]];
                        graph.add_edge(
                            from,
                            to,
                            GraphEdge {
                                callsite: Some(cs.id),
                                callee: cs.callee.clone(),
                                evidence: Evidence::confirmed("direct call; unique name match"),
                            },
                        );
                    }
                }
            }
        }

        (graph, stats)
    }

    /// May-closure (`executes`): for every function, the reachable function
    /// ids via call edges, computed with `petgraph::visit::Dfs`.
    #[must_use]
    pub fn may_closure(&self) -> BTreeMap<crate::ids::FunctionId, Vec<crate::ids::FunctionId>> {
        let mut dig = petgraph::graph::DiGraph::<u32, ()>::with_capacity(
            self.nodes.len(),
            self.edges.len(),
        );
        let mut by_id: BTreeMap<u32, petgraph::graph::NodeIndex> = BTreeMap::new();
        for (i, _) in self.nodes.iter().enumerate() {
            let ix = dig.add_node(i as u32);
            by_id.insert(i as u32, ix);
        }
        for (from, to, _) in &self.edges {
            dig.add_edge(by_id[from], by_id[to], ());
        }

        let mut out = BTreeMap::new();
        for (fid, start) in &self.function_nodes {
            let start_ix = by_id[start];
            let mut dfs = petgraph::visit::Dfs::new(&dig, start_ix);
            let mut reachable = Vec::new();
            while let Some(nx) = dfs.next(&dig) {
                let node = self.nodes[dig[nx] as usize].clone();
                if let NodeKind::Function { id } = node {
                    if id != *fid {
                        reachable.push(id);
                    }
                }
                // External nodes do not contribute to `executes`.
            }
            reachable.sort_unstable();
            reachable.dedup();
            out.insert(*fid, reachable);
        }
        out
    }
}

/// Callee resolution by simple name: `(ids, unique)` — sorted, deduped.
fn resolve_by_name(functions: &[Function], callee: &str) -> (Vec<crate::ids::FunctionId>, bool) {
    let mut ids: Vec<crate::ids::FunctionId> = functions
        .iter()
        .filter(|f| f.name == callee)
        .map(|f| f.id)
        .collect();
    ids.sort_unstable();
    ids.dedup();
    let unique = ids.len() == 1;
    (ids, unique)
}

/// `outer` covers `inner` (same file, span containment).
fn covers(outer: SourceSpan, inner: SourceSpan) -> bool {
    outer.file == inner.file
        && outer.start_byte <= inner.start_byte
        && inner.end_byte <= outer.end_byte
}
