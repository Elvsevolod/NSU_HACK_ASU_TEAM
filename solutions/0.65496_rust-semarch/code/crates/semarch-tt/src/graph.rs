//! Resolution of *possible* skeleton edges into *executing* ones.
//!
//! # What this module does
//!
//! The skeleton states what *may* happen (`calls`, `runtime_dispatch`,
//! `data_access`, `remote_call`). Scenario prediction needs what *does*
//! happen for one entry method. The gap is closed by mechanisms that are all
//! either language semantics or public framework contracts:
//!
//! | # | mechanism | contract |
//! |---|---|---|
//! | G1 | interface/abstract target → runtime implementation | OO virtual dispatch (`runtime_dispatch`, `overrides`) |
//! | G2 | declarations never *execute* | a method without a body has no execution |
//! | G3 | repository proxies issue SQL but are not project methods | Spring Data proxy generation |
//! | G4 | reading an entity materializes it | JPA: the provider instantiates the entity via its no-arg constructor |
//! | G5 | request-scoped callbacks | Servlet `Filter`, Spring Security `UserDetailsService` / `UserDetails` |
//! | G6 | optional features the scenario omits do not run | the request carries the flag; the scenario states the intent |
//! | G7 | a call on a type-named receiver resolves to that type's method | Java name resolution (`Status.PAID.getCode()`) |
//!
//! Data attribution (G3) follows the contest rule: the SQL a proxy issues is
//! credited to the *project method that holds the repository call*.
//!
//! Every mechanism is switchable through [`ResolutionConfig`] so each can be
//! ablated against the open scenario instead of being assumed.

use std::collections::{BTreeSet, HashMap, HashSet};

use serde::Serialize;

use crate::framework;
use crate::guards::GuardIndex;
use crate::skeleton::{Annotation, Skeleton};

/// Resolution-time facts about a skeleton method.
#[derive(Debug, Clone)]
pub struct MethodInfo {
    pub id: String,
    /// Owning `type:` id.
    pub owner: String,
    pub name: String,
    pub arity: usize,
    pub is_abstract: bool,
    /// Return type as written (`ArrayList<Order>`); used for ORM
    /// materialization (G4).
    pub return_raw: Option<String>,
    pub module: Option<String>,
    pub annotations: Vec<Annotation>,
}

impl MethodInfo {
    /// Spring request-mapping annotations, if any.
    #[must_use]
    pub fn has_mapping_annotation(&self) -> bool {
        self.annotations.iter().any(|a| {
            matches!(
                a.name.as_str(),
                "RequestMapping" | "GetMapping" | "PostMapping" | "PutMapping" | "DeleteMapping"
                    | "PatchMapping"
            )
        })
    }
}

/// Per-mechanism switches for ablation experiments.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ResolutionConfig {
    /// G1: expand abstract targets to implementations.
    pub dispatch: bool,
    /// G2: drop body-less declarations from `executes`.
    pub drop_declarations: bool,
    /// G3: drop Spring Data proxy methods; credit their SQL to the caller.
    pub drop_repository_proxies: bool,
    /// G4: materialize entities read through repositories.
    pub materialize_entities: bool,
    /// G5: seed request-scoped framework callbacks.
    pub framework_callbacks: bool,
    /// G6: skip call sites behind an optional feature the scenario omits.
    pub feature_guards: bool,
    /// G7: resolve a call the skeleton left unresolved when its receiver
    /// names a type (`Status.PAID.getCode()`).
    pub static_receiver: bool,
}

impl Default for ResolutionConfig {
    fn default() -> Self {
        Self {
            dispatch: true,
            drop_declarations: true,
            drop_repository_proxies: true,
            materialize_entities: true,
            framework_callbacks: true,
            feature_guards: true,
            static_receiver: true,
        }
    }
}

/// Per-scenario prediction in contest terms.
#[derive(Debug, Clone, Default, PartialEq, Eq, serde::Serialize)]
pub struct Prediction {
    pub executes: BTreeSet<String>,
    pub calls: BTreeSet<(String, String)>,
    pub remote: BTreeSet<(String, String)>,
    pub data: BTreeSet<(String, String)>,
}

impl Prediction {
    /// Union another prediction into this one.
    pub fn merge(&mut self, other: &Self) {
        self.executes.extend(other.executes.iter().cloned());
        self.calls.extend(other.calls.iter().cloned());
        self.remote.extend(other.remote.iter().cloned());
        self.data.extend(other.data.iter().cloned());
    }

    /// Total number of edges (diagnostics).
    #[must_use]
    pub fn edge_count(&self) -> usize {
        self.executes.len() + self.calls.len() + self.remote.len() + self.data.len()
    }
}

/// Syntax facts of one call site that resolution needs beyond its edges.
///
/// These are the *location and shape* of the invocation as the skeleton
/// recorded it. They are what makes a witness checkable: two calls to the same
/// callee in one method differ in line, receiver type or argument text.
#[derive(Debug, Clone, Default)]
struct CallFact {
    /// Project-relative source file and 1-based line (guard lookups).
    file: Option<String>,
    line: Option<u32>,
    /// 1-based last line of the invocation, when it spans several lines.
    /// (The contest skeleton records no `end` for call sites, so this stays
    /// `None` on Train Ticket; it is carried through for skeletons that do.)
    end_line: Option<u32>,
    /// Callee and receiver as written (`getCode`, `SeatClass.PAID`).
    callee: String,
    receiver: Option<String>,
    /// Static type of the receiver, when the skeleton resolved one.
    receiver_type: Option<String>,
    arg_count: Option<u32>,
    /// 1-based byte column of the token the skeleton reports (callee name, or
    /// `new` for a constructor call). The discriminator between two calls to
    /// the same callee on one line.
    col: Option<u32>,
    /// Argument text as written (`verifyCode, remote`).
    args_text: Option<String>,
    /// String literals passed at this call site, as written.
    string_args: Vec<String>,
}

/// How one lowered IR call site maps to the skeleton call site that names it.
///
/// The distinction matters for pruning: only an [`SiteResolution::Exact`]
/// mapping carries enough identity to prove *that* site dead. An ambiguous
/// mapping keeps every candidate, and a missing one means the skeleton recorded
/// no call there at all.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SiteResolution {
    /// Exactly one skeleton call site, with the evidence that distinguished it.
    Exact { id: String, evidence: &'static str },
    /// Several candidates remain: no proof may be broadcast over them.
    Ambiguous { ids: Vec<String>, reason: String },
    /// No skeleton call site matches.
    Missing { reason: String },
}

impl SiteResolution {
    /// The skeleton ids this resolution covers (one for `Exact`, none for
    /// `Missing`).
    #[must_use]
    pub fn ids(&self) -> Vec<String> {
        match self {
            Self::Exact { id, .. } => vec![id.clone()],
            Self::Ambiguous { ids, .. } => ids.clone(),
            Self::Missing { .. } => Vec::new(),
        }
    }

    /// How the resolution was decided, for the report.
    #[must_use]
    pub fn evidence(&self) -> String {
        match self {
            Self::Exact { evidence, .. } => (*evidence).to_owned(),
            Self::Ambiguous { reason, .. } => format!("ambiguous: {reason}"),
            Self::Missing { reason } => format!("missing: {reason}"),
        }
    }
}

/// The resolvable execution graph of one project.
pub struct TtGraph {
    methods: HashMap<String, MethodInfo>,
    /// `owner|name|arity` → candidate method ids.
    method_key: HashMap<String, Vec<String>>,
    /// simple type name → type ids (deterministic order).
    simple_to_types: HashMap<String, Vec<String>>,
    /// type id → module.
    type_module: HashMap<String, String>,
    /// call site id → syntax facts (filename/line/callee/receiver).
    cs_facts: HashMap<String, CallFact>,
    /// (source file, 1-based line) → call sites, for mapping a lowered IR call
    /// to the skeleton call site it came from.
    cs_by_line: HashMap<(String, u32), Vec<String>>,
    cs_owner: HashMap<String, String>,
    cs_calls: HashMap<String, Vec<String>>,
    cs_dispatch: HashMap<String, Vec<String>>,
    cs_data: HashMap<String, Vec<String>>,
    cs_remote: HashMap<String, Vec<String>>,
    cs_by_owner: HashMap<String, Vec<String>>,
    /// declaration → implementations (from `overrides`).
    overrides: HashMap<String, Vec<String>>,
    repo_types: HashSet<String>,
    repo_methods: HashSet<String>,
    /// Request-scoped callbacks that execute without a project call site (G5).
    callbacks: Vec<CallbackSeed>,
    /// Servlet filters (subset of `callbacks`, diagnostics).
    pub filters: Vec<String>,
    /// All skeleton method ids (the answer's ID whitelist).
    pub method_ids: HashSet<String>,
    /// All skeleton `data_resource` ids.
    pub table_ids: HashSet<String>,
    /// Optional feature guards of the project sources (G6).
    guards: Option<GuardIndex>,
}

impl TtGraph {
    /// Build resolution indexes from a loaded skeleton.
    #[must_use]
    pub fn build(sk: &Skeleton) -> Self {
        let mut methods = HashMap::new();
        let mut method_key: HashMap<String, Vec<String>> = HashMap::new();
        let mut cs_facts: HashMap<String, CallFact> = HashMap::new();
        let mut cs_by_line: HashMap<(String, u32), Vec<String>> = HashMap::new();
        let mut cs_owner = HashMap::new();
        let mut cs_calls: HashMap<String, Vec<String>> = HashMap::new();
        let mut cs_dispatch: HashMap<String, Vec<String>> = HashMap::new();
        let mut cs_data: HashMap<String, Vec<String>> = HashMap::new();
        let mut cs_remote: HashMap<String, Vec<String>> = HashMap::new();
        let mut cs_by_owner: HashMap<String, Vec<String>> = HashMap::new();
        let mut method_ids = HashSet::new();
        let mut table_ids = HashSet::new();

        // type id -> (fqn simple name, declared supertype simple names)
        let mut type_super: HashMap<String, Vec<String>> = HashMap::new();
        let mut simple_to_types: HashMap<String, Vec<String>> = HashMap::new();
        let mut type_module: HashMap<String, String> = HashMap::new();

        for (id, n) in &sk.nodes {
            match n.kind.as_str() {
                "method" => {
                    let owner = n.owner.clone().unwrap_or_default();
                    let name = n.name.clone().unwrap_or_default();
                    let arity = match n.descriptor.as_deref() {
                        None | Some("") => 0,
                        Some(d) => d.split(',').count(),
                    };
                    let info = MethodInfo {
                        id: id.clone(),
                        owner: owner.clone(),
                        name: name.clone(),
                        arity,
                        is_abstract: n.is_abstract,
                        return_raw: n.return_raw.clone().or_else(|| n.return_type.clone()),
                        module: n.module.clone(),
                        annotations: n.annotations.clone(),
                    };
                    method_key
                        .entry(format!("{owner}|{name}|{arity}"))
                        .or_default()
                        .push(id.clone());
                    methods.insert(id.clone(), info);
                    method_ids.insert(id.clone());
                }
                "call_site" => {
                    if let Some(o) = &n.method {
                        cs_owner.insert(id.clone(), o.clone());
                        cs_by_owner.entry(o.clone()).or_default().push(id.clone());
                    }
                    if let (Some(file), Some(line)) = (n.file.clone(), n.line) {
                        cs_by_line.entry((file, line)).or_default().push(id.clone());
                    }
                    cs_facts.insert(
                        id.clone(),
                        CallFact {
                            file: n.file.clone(),
                            line: n.line,
                            end_line: n.end,
                            callee: n.callee.clone().unwrap_or_default(),
                            receiver: n.receiver.clone(),
                            receiver_type: n.receiver_type.clone(),
                            arg_count: n.arg_count,
                            col: n.col,
                            args_text: n.args_text.clone(),
                            string_args: n.string_args.clone(),
                        },
                    );
                }
                "type" => {
                    let mut supers = Vec::new();
                    supers.extend(n.implements_raw.iter().cloned());
                    supers.extend(n.extends_raw.iter().cloned());
                    if let Some(fqn) = &n.fqn {
                        simple_to_types
                            .entry(framework::simple_name(fqn).to_owned())
                            .or_default()
                            .push(id.clone());
                    }
                    if let Some(m) = &n.module {
                        type_module.insert(id.clone(), m.clone());
                    }
                    type_super.insert(id.clone(), supers);
                }
                "data_resource" => {
                    table_ids.insert(id.clone());
                }
                _ => {}
            }
        }

        // repository hierarchy (in-project types whose declared supertypes are
        // Spring Data base contracts) + in-project inheritance closure.
        let mut repo_types: HashSet<String> = HashSet::new();
        for (tid, supers) in &type_super {
            if framework::has_base(supers.iter().cloned(), framework::REPOSITORY_BASES) {
                repo_types.insert(tid.clone());
            }
        }
        // A type whose in-project supertype is a repository is a repository too.
        let mut changed = true;
        while changed {
            changed = false;
            for (tid, supers) in &type_super {
                if repo_types.contains(tid) {
                    continue;
                }
                for s in supers {
                    let module = type_module.get(tid).cloned().unwrap_or_default();
                    if let Some(super_id) =
                        resolve_type(&simple_to_types, &type_module, &module, framework::simple_name(s))
                    {
                        if repo_types.contains(&super_id) {
                            repo_types.insert(tid.clone());
                            changed = true;
                            break;
                        }
                    }
                }
            }
        }

        // edge pass
        let mut overrides: HashMap<String, Vec<String>> = HashMap::new();
        for e in &sk.edges {
            match e.type_.as_str() {
                "calls" => cs_calls
                    .entry(e.source.clone())
                    .or_default()
                    .push(e.target.clone()),
                "runtime_dispatch" => cs_dispatch
                    .entry(e.source.clone())
                    .or_default()
                    .push(e.target.clone()),
                "data_access" => cs_data
                    .entry(e.source.clone())
                    .or_default()
                    .push(e.target.clone()),
                "remote_call" | "message_delivery" => cs_remote
                    .entry(e.source.clone())
                    .or_default()
                    .push(e.target.clone()),
                "overrides" => overrides
                    .entry(e.target.clone())
                    .or_default()
                    .push(e.source.clone()),
                _ => {}
            }
        }

        // `sk.nodes` is a `HashMap`: every list built by iterating it comes out
        // in hash order, which is random per process. Sort the id lists here so
        // that name resolution, witness order and the audit trail are
        // reproducible; the exported edge set is unaffected because it is
        // sorted at export time.
        for ids in cs_by_owner.values_mut() {
            ids.sort();
        }
        for ids in method_key.values_mut() {
            ids.sort();
        }
        for names in simple_to_types.values_mut() {
            names.sort();
        }

        let repo_methods: HashSet<String> = methods
            .values()
            .filter(|m| repo_types.contains(&m.owner))
            .map(|m| m.id.clone())
            .collect();

        let (callbacks, filters) =
            detect_callbacks(sk, &type_super, &method_key, &simple_to_types, &type_module);

        Self {
            methods,
            method_key,
            simple_to_types,
            type_module,
            cs_facts,
            cs_by_line,
            cs_owner,
            cs_calls,
            cs_dispatch,
            cs_data,
            cs_remote,
            cs_by_owner,
            overrides,
            repo_types,
            repo_methods,
            callbacks,
            filters,
            method_ids,
            table_ids,
            guards: None,
        }
    }

    /// Attach project source guards (G6) to the graph.
    #[must_use]
    pub fn with_guards(mut self, guards: GuardIndex) -> Self {
        self.guards = Some(guards);
        self
    }

    /// Number of feature guards known to this graph (diagnostics).
    #[must_use]
    pub fn guard_count(&self) -> usize {
        self.guards.as_ref().map_or(0, GuardIndex::len)
    }

    /// Look up a method by owning type, name and arity.
    #[must_use]
    pub fn find_method(&self, owner: &str, name: &str, arity: usize) -> Option<&str> {
        self.method_key
            .get(&format!("{owner}|{name}|{arity}"))
            .and_then(|v| v.first())
            .map(String::as_str)
    }

    /// Resolution-relevant facts about a method.
    #[must_use]
    pub fn method(&self, id: &str) -> Option<&MethodInfo> {
        self.methods.get(id)
    }

    /// The owning method of a skeleton call site (edge provenance).
    #[must_use]
    pub fn call_site_owner(&self, call_site: &str) -> Option<&str> {
        self.cs_owner.get(call_site).map(String::as_str)
    }

    /// Call sites of a method, in skeleton order (edge provenance).
    #[must_use]
    pub fn call_sites_of(&self, method: &str) -> &[String] {
        self.cs_by_owner.get(method).map_or(&[], Vec::as_slice)
    }

    /// Resolve one lowered IR call site to the skeleton call site that names
    /// it, with the evidence that distinguished it.
    ///
    /// The candidates are the skeleton call sites recorded at the same
    /// project-relative file, line and callee. `anchor_col` is the *0-based
    /// UTF-8 byte column* of the token the skeleton tool reports for that node
    /// (the callee name, or `new` for a constructor call); the skeleton stores
    /// it 1-based, so the comparison adds one. `arity` is the number of
    /// arguments the lowered call passes.
    ///
    /// Tie-breaking stops at the first signal that leaves exactly one
    /// candidate. Anything still tied is [`SiteResolution::Ambiguous`]: the
    /// caller must keep every candidate, because one IR call may not broadcast
    /// a proof over several skeleton sites.
    #[must_use]
    pub fn resolve_site(
        &self,
        file: &str,
        line: u32,
        callee: &str,
        arity: Option<usize>,
        anchor_col: Option<u32>,
    ) -> SiteResolution {
        let ids: Vec<&String> = self
            .cs_by_line
            .get(&(file.to_owned(), line))
            .map_or_else(Vec::new, |ids| {
                ids.iter()
                    .filter(|id| {
                        self.cs_facts
                            .get(id.as_str())
                            .is_some_and(|f| f.callee == callee)
                    })
                    .collect()
            });
        match ids.len() {
            0 => SiteResolution::Missing {
                reason: format!("no skeleton call site at {file}:{line} with callee {callee}"),
            },
            1 => SiteResolution::Exact {
                id: ids[0].clone(),
                evidence: "unique_file_line_callee",
            },
            _ => {
                if let Some(col) = anchor_col {
                    let skeleton_col = col + 1;
                    let hits: Vec<&String> = ids
                        .iter()
                        .copied()
                        .filter(|id| {
                            self.cs_facts
                                .get(id.as_str())
                                .and_then(|f| f.col)
                                .is_some_and(|c| c == skeleton_col)
                        })
                        .collect();
                    if let [only] = hits[..] {
                        return SiteResolution::Exact {
                            id: only.clone(),
                            evidence: "anchor_column",
                        };
                    }
                }
                if let Some(arity) = arity {
                    let arity = u32::try_from(arity).ok();
                    let hits: Vec<&String> = ids
                        .iter()
                        .copied()
                        .filter(|id| {
                            self.cs_facts.get(id.as_str()).and_then(|f| f.arg_count) == arity
                        })
                        .collect();
                    if let [only] = hits[..] {
                        return SiteResolution::Exact {
                            id: only.clone(),
                            evidence: "arity",
                        };
                    }
                }
                SiteResolution::Ambiguous {
                    ids: ids.into_iter().cloned().collect(),
                    reason: format!(
                        "several skeleton call sites share {file}:{line} with callee {callee}"
                    ),
                }
            }
        }
    }

    /// The feature sets that would have to be engaged for one call site to
    /// run, when the project's optional-feature guards kill it for the
    /// scenario. Empty when no guard blocks it (or guards are unknown).
    #[must_use]
    pub fn call_site_blocking_features(
        &self,
        cid: &str,
        engaged: &HashSet<String>,
    ) -> Vec<Vec<String>> {
        let Some(guards) = &self.guards else {
            return Vec::new();
        };
        let Some(fact) = self.cs_facts.get(cid) else {
            return Vec::new();
        };
        match (fact.file.as_deref(), fact.line) {
            (Some(file), Some(line)) => guards.blocking_features(file, line, engaged),
            _ => Vec::new(),
        }
    }

    /// Syntax facts of one call site (audit output).
    #[must_use]
    pub fn call_fact(&self, cid: &str) -> Option<(&str, Option<u32>, &str, Option<&str>)> {
        self.cs_facts.get(cid).map(|f| {
            (
                f.file.as_deref().unwrap_or_default(),
                f.line,
                f.callee.as_str(),
                f.receiver.as_deref(),
            )
        })
    }

    /// Everything one *running* call site contributes to the answer.
    ///
    /// This is the same rule set [`Self::predict`] applies while flooding the
    /// call graph, factored out so the semantic engine asks per call site:
    /// which calls, which remote calls, which data accesses, and which methods
    /// must be visited next without an edge of their own (materialized entity
    /// constructors).
    #[must_use]
    pub fn edges_of(&self, cid: &str, cfg: ResolutionConfig) -> CallSiteEdges {
        let calls = self.executing_targets(cid, cfg);
        let mut data: Vec<String> = self.cs_data.get(cid).cloned().unwrap_or_default();
        // G3: SQL issued by a non-executing callee belongs to the caller.
        let mut attributed: BTreeSet<(String, String)> = BTreeSet::new();
        let mut seen = HashSet::new();
        let mut budget = 4_096usize;
        for t in self.direct_targets(cid) {
            if !self.is_executing(&t) {
                self.attribute_data(&t, "", &mut attributed, &mut seen, &mut budget);
            }
        }
        data.extend(attributed.into_iter().map(|(_, table)| table));
        data.sort();
        data.dedup();
        let remote = self.cs_remote.get(cid).cloned().unwrap_or_default();
        let mut enqueue = calls.clone();
        enqueue.extend(remote.iter().cloned());
        if cfg.materialize_entities {
            enqueue.extend(self.materialized_entities(cid));
        }
        enqueue.sort();
        enqueue.dedup();
        CallSiteEdges {
            calls,
            remote,
            data,
            enqueue,
        }
    }

    /// All methods, in deterministic id order.
    #[must_use]
    pub fn all_methods(&self) -> Vec<&MethodInfo> {
        let mut out: Vec<&MethodInfo> = self.methods.values().collect();
        out.sort_by(|a, b| a.id.cmp(&b.id));
        out
    }

    /// All methods of a type, in deterministic id order.
    #[must_use]
    pub fn methods_of_type(&self, type_id: &str) -> Vec<&MethodInfo> {
        let mut out: Vec<&MethodInfo> = self.methods.values().filter(|m| m.owner == type_id).collect();
        out.sort_by(|a, b| a.id.cmp(&b.id));
        out
    }

    /// The request-scoped framework callbacks (seeded into every scenario).
    #[must_use]
    pub fn callbacks(&self) -> &[CallbackSeed] {
        &self.callbacks
    }

    /// Whether a type is a Spring Data repository hierarchy member.
    #[must_use]
    pub fn is_repository_type(&self, tid: &str) -> bool {
        self.repo_types.contains(tid)
    }

    /// Whether a method is backed by a container-generated proxy.
    #[must_use]
    pub fn is_repository_method(&self, mid: &str) -> bool {
        self.repo_methods.contains(mid)
    }

    /// A method that never executes: a body-less declaration or a proxy.
    #[must_use]
    pub fn is_executing(&self, mid: &str) -> bool {
        let Some(m) = self.methods.get(mid) else {
            return false;
        };
        !m.is_abstract && !self.repo_methods.contains(mid)
    }

    /// Direct (unexpanded) call targets of one call site.
    fn direct_targets(&self, cid: &str) -> Vec<String> {
        let mut out = Vec::new();
        for t in self.cs_calls.get(cid).into_iter().flatten() {
            out.push(t.clone());
        }
        for t in self.cs_dispatch.get(cid).into_iter().flatten() {
            out.push(t.clone());
        }
        out
    }

    /// Targets of a call the skeleton left unresolved whose *receiver names a
    /// type* (`SeatClass.FIRSTCLASS.getCode()`, `StringUtils.Date2String(d)`).
    ///
    /// This is Java name resolution, not a guess: a receiver whose head segment
    /// is capitalized and names a project type can only be that type (a
    /// variable would be lower-case), and a method of that name and arity then
    /// exists on it. Receivers written as plain variables (`qi.isX()`) are left
    /// unresolved on purpose — a variable's type is not in the receiver text,
    /// and inferring it would invent edges the answer does not have.
    fn static_receiver_targets(&self, cid: &str) -> Vec<String> {
        let Some(fact) = self.cs_facts.get(cid) else {
            return Vec::new();
        };
        if fact.callee.is_empty() || fact.callee == "<init>" {
            return Vec::new();
        }
        let Some(receiver) = &fact.receiver else {
            return Vec::new();
        };
        let head = receiver.split('.').next().unwrap_or_default();
        if !head.chars().next().is_some_and(char::is_uppercase) {
            return Vec::new();
        }
        let module = self
            .cs_owner
            .get(cid)
            .and_then(|m| self.methods.get(m))
            .and_then(|m| m.module.clone())
            .unwrap_or_default();
        let Some(tid) = resolve_type(&self.simple_to_types, &self.type_module, &module, head)
        else {
            return Vec::new();
        };
        let arity = fact.arg_count.unwrap_or(0) as usize;
        let mut out = Vec::new();
        if let Some(mid) = self.find_method(&tid, &fact.callee, arity) {
            out.push(mid.to_owned());
        }
        out
    }

    /// Whether a call site runs at all: it must not sit behind an optional
    /// feature the scenario omits.
    fn call_site_live(&self, cid: &str, cfg: ResolutionConfig, engaged: &HashSet<String>) -> bool {
        if !cfg.feature_guards {
            return true;
        }
        let Some(guards) = &self.guards else {
            return true;
        };
        let Some(fact) = self.cs_facts.get(cid) else {
            return true;
        };
        match (fact.file.as_deref(), fact.line) {
            (Some(file), Some(line)) => !guards.blocks(file, line, engaged),
            _ => true,
        }
    }

    /// Executing targets of one call site under `cfg`.
    fn executing_targets(&self, cid: &str, cfg: ResolutionConfig) -> Vec<String> {
        let mut out: Vec<String> = Vec::new();
        let mut seen: HashSet<String> = HashSet::new();
        let mut queue: Vec<String> = self.direct_targets(cid);
        if queue.is_empty() && cfg.static_receiver {
            queue = self.static_receiver_targets(cid);
        }
        let mut depth = 0;
        while let Some(t) = queue.pop() {
            if !seen.insert(t.clone()) {
                continue;
            }
            let abstract_decl = self.methods.get(&t).is_some_and(|m| m.is_abstract);
            if abstract_decl {
                if cfg.dispatch {
                    for imp in self.overrides.get(&t).into_iter().flatten() {
                        queue.push(imp.clone());
                    }
                }
                // G2: the declaration itself never executes either way.
                if cfg.drop_declarations {
                    continue;
                }
                out.push(t);
                continue;
            }
            if cfg.drop_repository_proxies && self.repo_methods.contains(&t) {
                continue;
            }
            if self.methods.contains_key(&t) {
                out.push(t);
            }
            depth += 1;
            if depth > 4096 {
                break;
            }
        }
        out
    }

    /// SQL issued by a non-executing call chain, credited to `caller` (G3).
    fn attribute_data(
        &self,
        start: &str,
        caller: &str,
        out: &mut BTreeSet<(String, String)>,
        seen: &mut HashSet<String>,
        budget: &mut usize,
    ) {
        if *budget == 0 || !seen.insert(start.to_owned()) {
            return;
        }
        *budget -= 1;
        for cid in self.cs_by_owner.get(start).into_iter().flatten() {
            for t in self.cs_data.get(cid).into_iter().flatten() {
                out.insert((caller.to_owned(), t.clone()));
            }
            for t in self.direct_targets(cid) {
                if !self.is_executing(&t) {
                    self.attribute_data(&t, caller, out, seen, budget);
                }
            }
        }
    }

    /// Entity types materialized by an ORM read through one call site (G4).
    ///
    /// The provider instantiates *the* entity the repository declares, so the
    /// element type is resolved to one type (the repository's own module first,
    /// as an entity lives beside its repository) and only that type's no-arg
    /// constructor is materialized. Matching by simple name instead would pull
    /// in every `Order` of the project, inventing constructors that never run.
    fn materialized_entities(&self, cid: &str) -> Vec<String> {
        let mut out = Vec::new();
        for t in self.direct_targets(cid) {
            if !self.repo_methods.contains(&t) {
                continue;
            }
            let Some(raw) = self.methods.get(&t).and_then(|m| m.return_raw.clone()) else {
                continue;
            };
            let Some(elem) = framework::element_type(&raw) else {
                continue;
            };
            let module = self
                .methods
                .get(&t)
                .and_then(|m| m.module.clone())
                .or_else(|| {
                    self.cs_owner
                        .get(cid)
                        .and_then(|m| self.methods.get(m))
                        .and_then(|m| m.module.clone())
                })
                .unwrap_or_default();
            let Some(tid) = resolve_type(
                &self.simple_to_types,
                &self.type_module,
                &module,
                framework::simple_name(&elem),
            ) else {
                continue;
            };
            if let Some(mid) = self.find_method(&tid, "<init>", 0) {
                out.push(mid.to_owned());
            }
        }
        out.sort();
        out.dedup();
        out
    }

    /// Predict the scenario subgraph reachable from `entries`.
    ///
    /// `engaged` is the scenario's feature vocabulary (see [`crate::guards`]);
    /// pass an empty set to disable feature gating for a run.
    #[must_use]
    pub fn predict(
        &self,
        entries: &[String],
        cfg: ResolutionConfig,
        engaged: &HashSet<String>,
    ) -> Prediction {
        let mut pred = Prediction::default();
        let mut visited: HashSet<String> = HashSet::new();
        let mut queue: Vec<String> = Vec::new();
        for e in entries {
            queue.push(e.clone());
        }
        if cfg.framework_callbacks {
            for c in &self.callbacks {
                if c.traverse {
                    queue.push(c.method.clone());
                } else {
                    pred.executes.insert(c.method.clone());
                }
            }
        }
        let mut budget = 200_000usize;
        while let Some(m) = queue.pop() {
            if budget == 0 {
                break;
            }
            if !visited.insert(m.clone()) {
                continue;
            }
            budget -= 1;
            pred.executes.insert(m.clone());
            for cid in self.cs_by_owner.get(&m).into_iter().flatten() {
                // G6: a call site behind an optional feature the scenario omits
                // does not run — it contributes no edge and no vertex.
                if !self.call_site_live(cid, cfg, engaged) {
                    continue;
                }
                for t in self.executing_targets(cid, cfg) {
                    pred.calls.insert((m.clone(), t.clone()));
                    queue.push(t);
                }
                for table in self.cs_data.get(cid).into_iter().flatten() {
                    pred.data.insert((m.clone(), table.clone()));
                }
                for t in self.cs_remote.get(cid).into_iter().flatten() {
                    pred.remote.insert((m.clone(), t.clone()));
                    queue.push(t.clone());
                }
                if cfg.materialize_entities {
                    for ctor in self.materialized_entities(cid) {
                        queue.push(ctor);
                    }
                }
                // G3: SQL behind non-executing callees belongs to `m`
                let mut seen = HashSet::new();
                let mut local_budget = 4_096usize;
                for t in self.direct_targets(cid) {
                    if !self.is_executing(&t) {
                        self.attribute_data(&t, &m, &mut pred.data, &mut seen, &mut local_budget);
                    }
                }
            }
        }
        pred
    }

    /// Predict without scenario feature gating (tests and callers that have no
    /// scenario text).
    #[must_use]
    pub fn predict_plain(&self, entries: &[String], cfg: ResolutionConfig) -> Prediction {
        self.predict(entries, cfg, &HashSet::new())
    }

    /// Human-readable summary for diagnostics.
    #[must_use]
    pub fn stats(&self) -> GraphStats {
        GraphStats {
            methods: self.methods.len(),
            call_sites: self.cs_by_owner.values().map(Vec::len).sum(),
            repository_types: self.repo_types.len(),
            repository_methods: self.repo_methods.len(),
            callbacks: self.callbacks.len(),
            filters: self.filters.len(),
        }
    }

    /// Re-derive the skeleton evidence for one *predicted* edge.
    ///
    /// This is deliberately independent of the prediction path: it walks the
    /// skeleton again and reports which call site(s) justify the edge, together
    /// with the skeleton relation used.
    ///
    /// The mapping is explicit, because "the first call site that matches" is a
    /// post-hoc choice, not evidence:
    ///
    /// * `unique` — exactly one call site of `source` justifies the edge; the
    ///   location fields name it (file, line, receiver, receiver type, argument
    ///   text), so it can be checked by hand;
    /// * `ambiguous` — several call sites do; no single one is presented as
    ///   *the* witness, and [`EdgeEvidence::witnesses`] lists all of them with a
    ///   reason in the note;
    /// * `contract` — no call site exists (framework/language contract); the
    ///   edge is exactly what a human should check by hand.
    #[must_use]
    pub fn evidence_for(&self, relation: &str, source: &str, target: &str) -> EdgeEvidence {
        let mut hits: Vec<(String, &'static str)> = Vec::new();
        for cid in self.call_sites_of(source) {
            let basis = match relation {
                "calls" => {
                    if self.has_edge(cid, &self.cs_calls, target) {
                        Some("calls")
                    } else if self.has_edge(cid, &self.cs_dispatch, target) {
                        Some("runtime_dispatch")
                    } else if self
                        .static_receiver_targets(cid)
                        .iter()
                        .any(|t| t == target)
                    {
                        Some("name-resolution")
                    } else {
                        None
                    }
                }
                "remote" => self.has_edge(cid, &self.cs_remote, target).then_some("remote_call"),
                "data" => self.has_edge(cid, &self.cs_data, target).then_some("data_access"),
                _ => None,
            };
            if let Some(basis) = basis {
                hits.push((cid.clone(), basis));
            }
        }

        let mut ev = EdgeEvidence {
            relation: relation.to_owned(),
            source: source.to_owned(),
            target: target.to_owned(),
            mapping: String::new(),
            call_site: None,
            file: None,
            line: None,
            receiver: None,
            receiver_type: None,
            args_text: None,
            witnesses: Vec::new(),
            basis: String::new(),
            note: String::new(),
        };

        if hits.is_empty() {
            // Nothing in the project calls it: the edge rests on a contract.
            ev.mapping = "contract".to_owned();
            ev.basis = "framework".to_owned();
            ev.note = match relation {
                "data" => "SQL issued by a container-generated repository proxy, credited to the calling method (Spring Data)".to_owned(),
                "remote" => "HTTP call with no project call site (gateway route / framework client)".to_owned(),
                _ => "no project call site: language or framework contract".to_owned(),
            };
            return ev;
        }

        // Witness order must not depend on hash-map iteration: sort by source
        // position (then by id) so the report is reproducible across runs.
        hits.sort_by(|(a, _), (b, _)| {
            let fa = self.cs_facts.get(a);
            let fb = self.cs_facts.get(b);
            fa.and_then(|f| f.line)
                .cmp(&fb.and_then(|f| f.line))
                .then_with(|| a.cmp(b))
        });
        ev.witnesses = hits.iter().map(|(cid, _)| self.witness(cid)).collect();
        ev.basis = distinct_bases(&hits);
        if let [(cid, _)] = hits.as_slice() {
            let w = &ev.witnesses[0];
            ev.mapping = "unique".to_owned();
            ev.call_site = Some(cid.clone());
            ev.file.clone_from(&w.file);
            ev.line = w.line;
            ev.receiver.clone_from(&w.receiver);
            ev.receiver_type.clone_from(&w.receiver_type);
            ev.args_text.clone_from(&w.args_text);
            ev.note = self.evidence_note(relation, cid, target);
        } else {
            // The edge holds for at least one of these call sites, but the
            // skeleton records no per-path value to choose between them.
            ev.mapping = "ambiguous".to_owned();
            let places: Vec<String> = ev
                .witnesses
                .iter()
                .map(Witness::anchor)
                .collect();
            let name = self
                .method(target)
                .map_or_else(|| target.to_owned(), |m| format!("{}#{}", m.owner, m.name));
            ev.note = format!(
                "{} call sites of this method justify {name} ({}); the skeleton records no per-path value, so the edge rests on at least one of them",
                hits.len(),
                places.join(", ")
            );
        }
        ev
    }

    /// The checkable location and shape of one call site.
    fn witness(&self, cid: &str) -> Witness {
        let f = self.cs_facts.get(cid);
        Witness {
            call_site: cid.to_owned(),
            file: f.and_then(|f| f.file.clone()),
            line: f.and_then(|f| f.line),
            end_line: f.and_then(|f| f.end_line),
            receiver: f.and_then(|f| f.receiver.clone()),
            receiver_type: f.and_then(|f| f.receiver_type.clone()),
            args_text: f.and_then(|f| f.args_text.clone()),
            string_args: f.map_or_else(Vec::new, |f| f.string_args.clone()),
        }
    }

    fn has_edge(&self, cid: &str, map: &HashMap<String, Vec<String>>, target: &str) -> bool {
        map.get(cid).is_some_and(|v| v.iter().any(|t| t == target))
    }

    fn evidence_note(&self, relation: &str, cid: &str, target: &str) -> String {
        let fact = self.cs_facts.get(cid);
        let callee = fact.map_or_else(String::new, |f| f.callee.clone());
        let receiver = fact
            .and_then(|f| f.receiver.clone())
            .unwrap_or_else(|| "<implicit>".to_owned());
        let callee_desc = if receiver == "<implicit>" {
            format!("`{callee}()`")
        } else {
            format!("`{receiver}.{callee}()`")
        };
        let name = self
            .method(target)
            .map_or_else(|| target.to_owned(), |m| format!("{}#{}", m.owner, m.name));
        match relation {
            "remote" => format!("{callee_desc} crosses a service boundary to {name}"),
            "data" => format!("{callee_desc} reaches the table through a repository proxy"),
            _ => format!("{callee_desc} calls {name}"),
        }
    }

    /// Call sites of `method` that this scenario's feature set kills (G6).
    ///
    /// The `target` of each returned item is the *callee name as written*, not
    /// a resolved id, because no answer edge exists for a dead call site.
    #[must_use]
    pub fn guard_pruned(&self, method: &str, engaged: &HashSet<String>) -> Vec<EdgeEvidence> {
        let Some(guards) = self.guards.as_ref() else {
            return Vec::new();
        };
        let mut out = Vec::new();
        for cid in self.call_sites_of(method) {
            let Some(f) = self.cs_facts.get(cid) else {
                continue;
            };
            let (Some(file), Some(line)) = (f.file.clone(), f.line) else {
                continue;
            };
            let blocked = guards.blocking_features(&file, line, engaged);
            if blocked.is_empty() {
                continue;
            }
            let revive: Vec<String> = blocked.iter().map(|b| b.join("|")).collect();
            out.push(EdgeEvidence {
                relation: "calls".to_owned(),
                source: method.to_owned(),
                target: f.callee.clone(),
                mapping: "unique".to_owned(),
                call_site: Some(cid.to_owned()),
                file: Some(file),
                line: Some(line),
                receiver: f.receiver.clone(),
                receiver_type: f.receiver_type.clone(),
                args_text: f.args_text.clone(),
                witnesses: vec![self.witness(cid)],
                basis: "feature-guard".to_owned(),
                note: format!("dead for this scenario; revive by engaging {}", revive.join(" or ")),
            });
        }
        out
    }
}

/// One call site that justifies a predicted edge, with the facts needed to find
/// it in the source again.
#[derive(Debug, Clone, Serialize)]
pub struct Witness {
    pub call_site: String,
    /// Project-relative file of the call site.
    pub file: Option<String>,
    /// 1-based first line.
    pub line: Option<u32>,
    /// 1-based last line (the invocation may span several lines). `None` when
    /// the skeleton does not record it.
    pub end_line: Option<u32>,
    /// Receiver expression as written (`restTemplate`, `StringUtils`, …).
    pub receiver: Option<String>,
    /// Static receiver type, when the skeleton resolved one.
    pub receiver_type: Option<String>,
    /// Argument text as written (`verifyCode, remote`).
    pub args_text: Option<String>,
    /// String literals passed at the call site, as written.
    pub string_args: Vec<String>,
}

impl Witness {
    /// `file:line` anchor for notes and diagnostics.
    #[must_use]
    pub fn anchor(&self) -> String {
        format!(
            "{}:{}",
            self.file.clone().unwrap_or_else(|| "<unknown>".to_owned()),
            self.line.map_or_else(|| "?".to_owned(), |l| l.to_string())
        )
    }
}

/// Distinct relation bases of a witness set, joined deterministically.
fn distinct_bases(hits: &[(String, &'static str)]) -> String {
    let mut bases: Vec<&str> = hits.iter().map(|(_, b)| *b).collect();
    bases.sort_unstable();
    bases.dedup();
    bases.join("+")
}

/// Edges one running call site contributes to the answer.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CallSiteEdges {
    /// Executing in-process callees (dispatch expanded).
    pub calls: Vec<String>,
    /// Remote handlers bound through the skeleton.
    pub remote: Vec<String>,
    /// Data resources read or written.
    pub data: Vec<String>,
    /// Methods to visit next without an edge of their own.
    pub enqueue: Vec<String>,
}

/// One skeleton fact behind a predicted edge (see [`TtGraph::evidence_for`]).
#[derive(Debug, Clone, Serialize)]
pub struct EdgeEvidence {
    pub relation: String,
    pub source: String,
    pub target: String,
    /// `unique` | `ambiguous` | `contract` — how well the edge is grounded in
    /// project call sites. See [`TtGraph::evidence_for`].
    pub mapping: String,
    /// Skeleton call-site id, present only when `mapping == "unique"`.
    pub call_site: Option<String>,
    /// Project-relative file of the unique witness.
    pub file: Option<String>,
    /// 1-based line of the unique witness.
    pub line: Option<u32>,
    /// Receiver expression as written (`restTemplate`, `StringUtils`, …).
    pub receiver: Option<String>,
    /// Static receiver type of the unique witness.
    pub receiver_type: Option<String>,
    /// Argument text of the unique witness, as written.
    pub args_text: Option<String>,
    /// Every call site that justifies the edge (empty for `contract`).
    pub witnesses: Vec<Witness>,
    /// `calls` | `runtime_dispatch` | `name-resolution` | `remote_call` |
    /// `data_access` | `framework` | `feature-guard`; several bases are joined
    /// with `+` when the witnesses disagree.
    pub basis: String,
    pub note: String,
}

/// A framework callback that executes without a project call site (G5).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CallbackSeed {
    /// Callback method id.
    pub method: String,
    /// Whether to follow the callback's own call sites. A servlet filter is
    /// invoked by the container but its *internals* are library plumbing in the
    /// contested answer, so it contributes an `executes` vertex only; an
    /// authenticating `UserDetailsService` performs real project work (SQL) and
    /// is traversed.
    pub traverse: bool,
}

/// Framework callbacks that execute without a project call site (G5).
fn detect_callbacks(
    sk: &Skeleton,
    type_super: &HashMap<String, Vec<String>>,
    method_key: &HashMap<String, Vec<String>>,
    simple_to_types: &HashMap<String, Vec<String>>,
    type_module: &HashMap<String, String>,
) -> (Vec<CallbackSeed>, Vec<String>) {
    let mut callbacks: Vec<CallbackSeed> = Vec::new();
    let mut filters = Vec::new();
    let mut principals: Vec<String> = Vec::new();

    for (tid, supers) in type_super {
        if framework::has_base(supers.iter().cloned(), framework::FILTER_BASES) {
            for name in ["doFilterInternal", "doFilter", "preHandle", "postHandle"] {
                let key = format!("{tid}|{name}");
                for (k, v) in method_key {
                    if k.starts_with(&key) {
                        for m in v {
                            filters.push(m.clone());
                            callbacks.push(CallbackSeed {
                                method: m.clone(),
                                traverse: false,
                            });
                        }
                    }
                }
            }
        }
        if supers
            .iter()
            .any(|s| framework::simple_name(s) == framework::USER_DETAILS_SERVICE)
        {
            let key = format!("{tid}|loadUserByUsername");
            for (k, v) in method_key {
                if k.starts_with(&key) {
                    for m in v {
                        callbacks.push(CallbackSeed {
                            method: m.clone(),
                            traverse: true,
                        });
                        if let Some(ret) = sk
                            .nodes
                            .get(m)
                            .and_then(|n| n.return_raw.clone().or_else(|| n.return_type.clone()))
                        {
                            let module = sk
                                .nodes
                                .get(m)
                                .and_then(|n| n.module.clone())
                                .or_else(|| type_module.get(tid).cloned())
                                .unwrap_or_default();
                            principals.extend(resolve_principal(
                                sk,
                                simple_to_types,
                                type_module,
                                &module,
                                &ret,
                            ));
                        }
                    }
                }
            }
        }
    }

    // UserDetails members of the principal type are read by the auth machinery.
    for m in method_key
        .iter()
        .filter(|(k, _)| principals.iter().any(|p| k.starts_with(&format!("{p}|"))))
        .filter(|(k, _)| {
            k.split('|')
                .nth(1)
                .is_some_and(|n| framework::USER_DETAILS_MEMBERS.contains(&n))
        })
        .flat_map(|(_, v)| v.iter())
    {
        callbacks.push(CallbackSeed {
            method: m.clone(),
            traverse: true,
        });
    }

    callbacks.sort_by(|a, b| a.method.cmp(&b.method));
    callbacks.dedup_by(|a, b| a.method == b.method);
    filters.sort();
    filters.dedup();
    (callbacks, filters)
}

/// Resolve the principal type produced by a framework callback.
///
/// A `UserDetailsService` commonly declares the *interface* as its return type
/// while returning a project entity. Resolution therefore prefers the declared
/// type when it is a project class, and otherwise takes the project types of
/// the same module that implement/extend the declared interface.
fn resolve_principal(
    sk: &Skeleton,
    simple_to_types: &HashMap<String, Vec<String>>,
    type_module: &HashMap<String, String>,
    module: &str,
    declared: &str,
) -> Vec<String> {
    let Some(elem) = framework::element_type(declared) else {
        return Vec::new();
    };
    let simple = framework::simple_name(&elem);
    if let Some(tid) = resolve_type(simple_to_types, type_module, module, simple) {
        let is_interface = sk
            .nodes
            .get(&tid)
            .and_then(|n| n.type_kind.as_deref())
            .is_some_and(|k| k == "interface");
        if !is_interface {
            return vec![tid];
        }
    }
    let mut out: Vec<String> = sk
        .nodes
        .iter()
        .filter(|(_, n)| n.kind == "type")
        .filter(|(_, n)| n.module.as_deref().is_some_and(|m| m == module))
        .filter(|(_, n)| {
            n.implements_raw
                .iter()
                .chain(n.extends_raw.iter())
                .any(|s| framework::simple_name(s) == simple)
        })
        .map(|(id, _)| id.clone())
        .collect();
    out.sort();
    out.dedup();
    out
}

/// Resolve a simple type name to a project type id.
///
/// A service almost always refers to its own DTOs/entities, so a type in the
/// same module wins; ties are broken by id to keep the whole pipeline
/// deterministic (an arbitrary `HashMap` pick would make re-runs unstable).
fn resolve_type(
    simple_to_types: &HashMap<String, Vec<String>>,
    type_module: &HashMap<String, String>,
    module: &str,
    simple: &str,
) -> Option<String> {
    let candidates = simple_to_types.get(simple)?;
    let mut same_module: Vec<&String> = candidates
        .iter()
        .filter(|c| type_module.get(*c).is_some_and(|m| m == module))
        .collect();
    same_module.sort();
    if let Some(c) = same_module.first() {
        return Some((*c).clone());
    }
    let mut all = candidates.clone();
    all.sort();
    all.first().cloned()
}

/// Diagnostics for one built graph.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GraphStats {
    pub methods: usize,
    pub call_sites: usize,
    pub repository_types: usize,
    pub repository_methods: usize,
    pub callbacks: usize,
    pub filters: usize,
}
