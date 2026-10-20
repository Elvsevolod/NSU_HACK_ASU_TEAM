//! Scenario state engine (N06): ordered steps → bound requests → outcomes.
//!
//! The legacy path ([`crate::graph::TtGraph::predict`]) takes the entry set of
//! a scenario and floods the call graph, using *scenario words* to prune call
//! sites behind optional features. That answers "which subgraph is reachable",
//! not "which subgraph this scenario's *requests* produce".
//!
//! This engine answers the second question for one ordered step at a time:
//!
//! 1. the step is bound to the handler's request ([`crate::request`]), giving
//!    concrete values for the fields the step states;
//! 2. the handler's lowered body is evaluated over its ordered CFG
//!    ([`semarch_core::analyze_body`]) with those values, so a call site runs
//!    only if the branch that guards it is *decided* to be taken;
//! 3. every call site the analysis reached contributes its edges
//!    ([`crate::graph::TtGraph::edges_of`]) with the guard decisions as proof;
//! 4. the resolved targets are visited next, and the per-step results are
//!    unioned only after the last step.
//!
//! Two modes are built on top:
//!
//! * **shadow** — the legacy answer is kept and the difference to the semantic
//!   one is written out, per scenario, with a proof for every edge. This is
//!   how the engine is validated without touching the submitted answer;
//! * **semantic** — the semantic prediction becomes the answer (`--mode`).
//!
//! Honest boundaries, all recorded as gaps rather than guessed:
//!
//! * an object argument travels to a callee by *handle*: the bound properties
//!   of the caller's variable are re-seeded under the callee's parameter name,
//!   which is what object passing means. Value copies (a field read into a
//!   primitive argument, a value returned by a helper) do not travel yet, and
//!   the callee's parameters stay unbound in those cases;
//! * heap and field state are not modelled (N08): a value stored in an object
//!   field and read back later is unknown;
//! * a body that lowered with *any* gap keeps every call site of its method
//!   live — value pruning is a proof, so it is switched off where the proof
//!   would be partial.

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet, VecDeque};

use semarch_core::{
    analyze_body_with, AbstractValue, AnalysisGap, AnalyzeInputs, Env, GuardVerdict,
    LanguageProfile,
};
use semarch_scenario::scenario::Scenario;

use crate::bodies::{BodyIndex, BodyMatch, Slot};
use crate::invocations::BodyProvider;
use crate::entry::{Endpoint, EntryIndex, StepRanking, StepSelection};
use crate::graph::{Prediction, ResolutionConfig, SiteResolution, TtGraph};
use crate::request::{self, BoundRequest, FieldDecl, FieldEvidence};
use crate::skeleton::Skeleton;
use crate::ui::UiOption;

/// Which engine produces the answer.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum SemanticMode {
    /// The contest path: entry grounding + call-graph flood + lexical feature
    /// pruning (G6). The submitted answer.
    #[default]
    Legacy,
    /// Legacy answer plus a written diff against the semantic engine.
    Shadow,
    /// The semantic engine's own prediction (opt-in).
    Semantic,
}

impl SemanticMode {
    /// Parse a CLI/programmatic mode name.
    #[must_use]
    pub fn parse(text: &str) -> Option<Self> {
        match text.trim().to_ascii_lowercase().as_str() {
            "legacy" => Some(Self::Legacy),
            "shadow" => Some(Self::Shadow),
            "semantic" => Some(Self::Semantic),
            _ => None,
        }
    }

    /// Stable identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Legacy => "legacy",
            Self::Shadow => "shadow",
            Self::Semantic => "semantic",
        }
    }
}

/// Relation kind of one effect.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, serde::Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Relation {
    Calls,
    Remote,
    Data,
}

/// One effect a step observed, with the proof that it runs.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct EffectEvent {
    pub step: u32,
    /// Method that *contains* the call site (the edge source).
    pub method: String,
    /// Skeleton call site id (the answer's own id space).
    pub call_site: String,
    pub callee: String,
    pub file: Option<String>,
    pub line: Option<u32>,
    pub relation: Relation,
    /// Resolved targets of the edge (skeleton ids).
    pub targets: Vec<String>,
    /// `confirmed` (the path is certain) or `possible` (some branch was open).
    pub status: String,
    /// Guard decisions that lead to the call site (`g0:then`).
    pub proof: Vec<String>,
}

/// One guard decision reached inside one method of one step.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct DecisionEvent {
    pub step: u32,
    pub method: String,
    /// `g<index>` of the guard inside its body.
    pub guard: String,
    /// Source line of the branch.
    pub line: Option<u32>,
    /// `proves_true` / `proves_false` / `unknown`.
    pub verdict: String,
    /// Symbols the condition reads (attribution to a bound field).
    pub symbols: Vec<String>,
    /// Witness path labels reaching the branch.
    pub path: Vec<String>,
}

/// One guard decision that proves a region of a lowered body dead.
///
/// This is the certificate behind every dropped call site: the guard, the
/// verdict, the witness path it was reached on (no `gap:` label, so the values
/// the verdict was computed from are the program text's), and the blocks that
/// decision cuts off and that no other path reaches.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct DeadBlock {
    /// `g<index>` of the guard inside its body.
    pub guard: String,
    /// 1-based line of the branch.
    pub line: Option<u32>,
    /// `proves_true` / `proves_false`.
    pub verdict: String,
    /// Witness path labels that reached the branch.
    pub path: Vec<String>,
    /// One of the blocks this decision proves dead and no other path reaches —
    /// every block of the certificate names the same decision.
    pub block: u32,
    /// Blocks the same decision also proves dead.
    pub blocks: Vec<u32>,
}

/// A call site the value analysis proved dead, with the decision that proves it.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct Suppression {
    /// Skeleton call site id (the answer's own id space).
    pub call_site: String,
    /// Callee as the skeleton records it.
    pub callee: String,
    pub certificate: DeadBlock,
}

impl Suppression {
    /// The one-line form kept in the audit trail.
    #[must_use]
    pub fn describe(&self) -> String {
        let line = self
            .certificate
            .line
            .map_or_else(|| "?".to_owned(), |l| l.to_string());
        let path = if self.certificate.path.is_empty() {
            "unconditional".to_owned()
        } else {
            self.certificate.path.join(",")
        };
        format!(
            "{}: {} — the guard {} at line {line} {} (path {path}); the block is unreachable for \
             the bound request (no lowering gap on the witness path)",
            self.call_site, self.callee, self.certificate.guard, self.certificate.verdict,
        )
    }

    /// Whether the certificate is complete (no blockers).
    #[must_use]
    pub fn is_complete(&self) -> bool {
        self.certificate.path.iter().all(|l| !l.starts_with("gap:"))
    }
}

/// What one step's requests produced.
#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct StepOutcome {
    pub step: u32,
    /// Endpoints this step was grounded on.
    pub entries: Vec<String>,
    /// One bound request per entry.
    pub bindings: Vec<BoundRequest>,
    /// Methods visited for this step, in visit order.
    pub invocations: Vec<String>,
    pub effects: Vec<EffectEvent>,
    pub decisions: Vec<DecisionEvent>,
    /// Number of state-changing steps committed before this one.
    pub state_version: u32,
    /// Call sites of this step's methods the value analysis proved dead, with
    /// the reason (the audit trail behind a missing edge).
    pub suppressed: Vec<String>,
    /// The same drops in structured form: every call site with the guard
    /// decision that proves it dead.
    pub suppressions: Vec<Suppression>,
    /// Call-site coverage counters of this step (see [`SiteStats`]).
    pub sites: SiteStats,
    pub gaps: Vec<String>,
}

/// The full semantic result of one scenario.
#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct ScenarioOutcome {
    pub scenario: String,
    pub steps: Vec<StepOutcome>,
    /// Union of every step, in the answer's own shape.
    pub prediction: Prediction,
    /// Scenario-level gaps (deduplicated).
    pub gaps: Vec<String>,
}

/// Edge counts of one prediction (diff summary).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, serde::Serialize)]
pub struct EdgeCounts {
    pub executes: usize,
    pub calls: usize,
    pub remote: usize,
    pub data: usize,
}

impl EdgeCounts {
    #[must_use]
    fn of(pred: &Prediction) -> Self {
        Self {
            executes: pred.executes.len(),
            calls: pred.calls.len(),
            remote: pred.remote.len(),
            data: pred.data.len(),
        }
    }
}

/// One edge that only one of the two engines produced.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct EdgeDelta {
    pub relation: String,
    pub source: String,
    pub target: String,
    /// Why the other engine does not have it.
    pub explanation: String,
}

/// Diff between the legacy and the semantic prediction of one scenario.
#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct ShadowDiff {
    pub scenario: String,
    pub legacy: EdgeCounts,
    pub semantic: EdgeCounts,
    /// Edges the semantic engine dropped, with the value proof that dropped
    /// them (or the lowering gap that explains why it could not).
    pub only_legacy: Vec<EdgeDelta>,
    /// Edges the semantic engine added, with the reason the legacy engine's
    /// lexical pruning missed them.
    pub only_semantic: Vec<EdgeDelta>,
    /// Methods only the legacy flood executes.
    pub only_legacy_executes: Vec<String>,
    /// Methods only the semantic engine executes.
    pub only_semantic_executes: Vec<String>,
    /// Edges both engines agree on.
    pub agreed: usize,
    pub notes: Vec<String>,
}

/// The scenario state engine.
pub struct ScenarioEngine<'a> {
    graph: &'a TtGraph,
    bodies: &'a BodyIndex,
    skeleton: &'a Skeleton,
    /// Request field declarations of every method, precomputed once.
    fields: HashMap<String, Vec<FieldDecl>>,
    /// Omission evidence of every method's request body, precomputed once.
    evidence: HashMap<String, HashMap<String, FieldEvidence>>,
    options: &'a [UiOption],
    cfg: ResolutionConfig,
    /// Whether the task package's context block is read into the binding.
    use_context: bool,
    /// Upper bound on methods visited per step (a pathological project must
    /// not turn a shadow run into a hang).
    budget: usize,
}

impl<'a> ScenarioEngine<'a> {
    /// Build an engine over one project's indexes.
    #[must_use]
    pub fn new(
        graph: &'a TtGraph,
        bodies: &'a BodyIndex,
        skeleton: &'a Skeleton,
        options: &'a [UiOption],
        cfg: ResolutionConfig,
        use_context: bool,
    ) -> Self {
        let model = request::request_field_decls(skeleton);
        let mut fields = HashMap::new();
        let mut evidence = HashMap::new();
        for (id, node) in &skeleton.nodes {
            if node.kind != "method" {
                continue;
            }
            let decls = request::handler_fields(skeleton, &model, id);
            if !decls.is_empty() {
                fields.insert(id.clone(), decls);
            }
            let ev = request::request_field_evidence(skeleton, id);
            if !ev.is_empty() {
                evidence.insert(id.clone(), ev);
            }
        }
        Self {
            graph,
            bodies,
            skeleton,
            fields,
            evidence,
            options,
            cfg,
            use_context,
            budget: 20_000,
        }
    }

    /// Run one scenario: one ordered step at a time, union at the end.
    #[must_use]
    pub fn run(
        &self,
        scn: &Scenario,
        rankings: &[StepRanking],
        selections: &[StepSelection],
        entries: &EntryIndex,
    ) -> ScenarioOutcome {
        let mut steps: Vec<StepOutcome> = Vec::new();
        let mut prediction = Prediction::default();
        let mut gaps: BTreeSet<String> = BTreeSet::new();
        let mut state_version = 0u32;
        let _ = rankings;

        // G5: request-scoped framework callbacks (the container invokes them
        // for the scenario, not for one step). They carry no request binding —
        // their arguments are framework values — so their parameters stay
        // unknown and that is recorded.
        let mut callback_walk = Walk::default();
        let mut callback_visited: BTreeSet<String> = BTreeSet::new();
        for c in self.graph.callbacks() {
            if c.traverse {
                let walk = self.walk(0, &c.method, Env::new(), &mut callback_visited);
                callback_walk.absorb(walk);
            } else {
                callback_walk.executes.insert(c.method.clone());
            }
            gaps.insert(format!(
                "framework_callback_without_request_binding:{}",
                c.method
            ));
        }
        prediction.executes.extend(callback_walk.executes);
        prediction.calls.extend(callback_walk.calls);
        prediction.remote.extend(callback_walk.remote);
        prediction.data.extend(callback_walk.data);
        for g in callback_walk.gaps {
            gaps.insert(g);
        }

        for (i, step) in scn.steps.iter().enumerate() {
            let members = selections.get(i).map_or(&[][..], |s| s.members.as_slice());
            let mut outcome = StepOutcome {
                step: step.n,
                entries: Vec::new(),
                bindings: Vec::new(),
                invocations: Vec::new(),
                effects: Vec::new(),
                decisions: Vec::new(),
                state_version,
                suppressed: Vec::new(),
                suppressions: Vec::new(),
                sites: SiteStats::default(),
                gaps: Vec::new(),
            };
            let mut visited_all: BTreeSet<String> = BTreeSet::new();
            for idx in members {
                let Some(endpoint) = entries.endpoints.get(*idx) else {
                    continue;
                };
                outcome.entries.push(endpoint.method.clone());
                let binding = self.bind_step(step.n, &step.action, endpoint, self.use_context);
                let env = self.entry_env(endpoint, &binding);
                let walk = self.walk(step.n, &endpoint.method, env, &mut visited_all);
                outcome.bindings.push(binding);
                outcome.effects.extend(walk.effects);
                outcome.decisions.extend(walk.decisions);
                outcome.gaps.extend(walk.gaps);
                outcome.suppressed.extend(walk.suppressed);
                outcome.suppressions.extend(walk.suppressions);
                outcome.sites.absorb(&walk.sites);
                prediction.executes.extend(walk.executes);
                prediction.calls.extend(walk.calls);
                prediction.remote.extend(walk.remote);
                prediction.data.extend(walk.data);
            }
            outcome.invocations = visited_all.into_iter().collect();
            outcome.effects.sort_by(|a, b| {
                (&a.method, &a.call_site, a.relation).cmp(&(&b.method, &b.call_site, b.relation))
            });
            outcome
                .effects
                .dedup_by(|a, b| a.method == b.method && a.call_site == b.call_site && a.relation == b.relation && a.targets == b.targets);
            outcome.decisions.sort_by(|a, b| (&a.method, &a.guard).cmp(&(&b.method, &b.guard)));
            outcome.decisions.dedup();
            outcome.gaps.sort();
            outcome.gaps.dedup();
            outcome.suppressed.sort();
            outcome.suppressed.dedup();
            outcome
                .suppressions
                .sort_by(|a, b| a.call_site.cmp(&b.call_site));
            outcome.suppressions.dedup();
            for g in &outcome.gaps {
                gaps.insert(g.clone());
            }
            if outcome
                .effects
                .iter()
                .any(|e| e.relation == Relation::Data)
            {
                state_version += 1;
            }
            steps.push(outcome);
        }

        ScenarioOutcome {
            scenario: scn.id.clone(),
            steps,
            prediction,
            gaps: gaps.into_iter().collect(),
        }
    }

    /// The diff of the legacy and the semantic prediction of one scenario.
    #[must_use]
    pub fn shadow(
        &self,
        scn: &Scenario,
        legacy: &Prediction,
        outcome: &ScenarioOutcome,
        engagements: &HashSet<String>,
    ) -> ShadowDiff {
        let semantic = &outcome.prediction;
        let mut only_legacy = Vec::new();
        for (source, target) in &legacy.calls {
            if !semantic.calls.contains(&(source.clone(), target.clone())) {
                only_legacy.push(EdgeDelta {
                    relation: "calls".to_owned(),
                    source: source.clone(),
                    target: target.clone(),
                    explanation: self.dropped_explanation(outcome, source, target, "calls"),
                });
            }
        }
        for (source, target) in &legacy.remote {
            if !semantic.remote.contains(&(source.clone(), target.clone())) {
                only_legacy.push(EdgeDelta {
                    relation: "remote".to_owned(),
                    source: source.clone(),
                    target: target.clone(),
                    explanation: self.dropped_explanation(outcome, source, target, "remote"),
                });
            }
        }
        for (source, target) in &legacy.data {
            if !semantic.data.contains(&(source.clone(), target.clone())) {
                only_legacy.push(EdgeDelta {
                    relation: "data".to_owned(),
                    source: source.clone(),
                    target: target.clone(),
                    explanation: "the data access is behind a call site the value analysis proved dead"
                        .to_owned(),
                });
            }
        }
        let mut only_semantic = Vec::new();
        for (source, target) in &semantic.calls {
            if !legacy.calls.contains(&(source.clone(), target.clone())) {
                only_semantic.push(EdgeDelta {
                    relation: "calls".to_owned(),
                    source: source.clone(),
                    target: target.clone(),
                    explanation: self.added_explanation(outcome, source, target, engagements),
                });
            }
        }
        for (source, target) in &semantic.remote {
            if !legacy.remote.contains(&(source.clone(), target.clone())) {
                only_semantic.push(EdgeDelta {
                    relation: "remote".to_owned(),
                    source: source.clone(),
                    target: target.clone(),
                    explanation: self.added_explanation(outcome, source, target, engagements),
                });
            }
        }
        for (source, target) in &semantic.data {
            if !legacy.data.contains(&(source.clone(), target.clone())) {
                only_semantic.push(EdgeDelta {
                    relation: "data".to_owned(),
                    source: source.clone(),
                    target: target.clone(),
                    explanation: self.added_explanation(outcome, source, target, engagements),
                });
            }
        }
        let mut only_legacy_executes: Vec<String> = legacy
            .executes
            .difference(&semantic.executes)
            .cloned()
            .collect();
        let mut only_semantic_executes: Vec<String> = semantic
            .executes
            .difference(&legacy.executes)
            .cloned()
            .collect();
        only_legacy_executes.sort();
        only_semantic_executes.sort();
        let agreed = intersect_len(&legacy.calls, &semantic.calls)
            + intersect_len(&legacy.remote, &semantic.remote)
            + intersect_len(&legacy.data, &semantic.data);

        let mut notes = Vec::new();
        for g in &outcome.gaps {
            notes.push(format!("gap: {g}"));
        }
        ShadowDiff {
            scenario: scn.id.clone(),
            legacy: EdgeCounts::of(legacy),
            semantic: EdgeCounts::of(semantic),
            only_legacy,
            only_semantic,
            only_legacy_executes,
            only_semantic_executes,
            agreed,
            notes,
        }
    }

    fn dropped_explanation(
        &self,
        outcome: &ScenarioOutcome,
        source: &str,
        target: &str,
        relation: &str,
    ) -> String {
        let decisions: Vec<String> = outcome
            .steps
            .iter()
            .flat_map(|s| &s.decisions)
            .filter(|d| d.method == source)
            .map(|d| format!("{}:{}({})", d.guard, d.verdict, d.symbols.join(",")))
            .collect();
        if decisions.is_empty() {
            format!(
                "the semantic engine reached no {relation} call site of {source} for {target}; the call site sits on a path the bound request values made unreachable"
            )
        } else {
            format!(
                "the semantic engine decided {decision} on the path to {target}; the {relation} call site does not run",
                decision = decisions.join(" ")
            )
        }
    }

    fn added_explanation(
        &self,
        outcome: &ScenarioOutcome,
        source: &str,
        target: &str,
        engagements: &HashSet<String>,
    ) -> String {
        // A call site the legacy engine pruned by scenario vocabulary is the
        // interesting case: give the feature names, so the reader can see the
        // difference is the pruning rule, not resolution.
        let mut blocked: Vec<String> = Vec::new();
        for cid in self.graph.call_sites_of(source) {
            for feats in self.graph.call_site_blocking_features(cid, engagements) {
                blocked.push(format!("{} ({})", cid, feats.join("+")));
            }
        }
        let decisions: Vec<String> = outcome
            .steps
            .iter()
            .flat_map(|s| &s.decisions)
            .filter(|d| d.method == source)
            .map(|d| format!("{}:{}", d.guard, d.verdict))
            .collect();
        if !blocked.is_empty() {
            format!(
                "legacy pruned a call site of {source} by scenario vocabulary ({}); the semantic engine keeps {target} because it decides the branch by value, not by words",
                blocked.join(", ")
            )
        } else if decisions.is_empty() {
            format!(
                "the semantic engine reached a call site of {source} the legacy flood did not expand (target {target})"
            )
        } else {
            format!(
                "the semantic engine's value decisions ({}) kept the call site that reaches {target} live",
                decisions.join(" ")
            )
        }
    }

    /// Bind one step to one handler's request.
    ///
    /// The step's own prose is the first source; the task package's statements
    /// about the starting point (`context`) fill only the fields the step left
    /// open, with their provenance recorded. `use_context` off turns that
    /// second source off, which is how the engine shows that *generic* silence
    /// is not absence.
    #[must_use]
    pub fn bind_step(
        &self,
        step: u32,
        action: &str,
        endpoint: &Endpoint,
        use_context: bool,
    ) -> BoundRequest {
        let decls = self.fields.get(&endpoint.method).map_or(&[][..], Vec::as_slice);
        let mut request = request::bind(
            step,
            action,
            &endpoint.method,
            &endpoint.full_path,
            decls,
            self.options,
        );
        if use_context {
            let facts =
                request::context_facts(self.skeleton, decls, action, &endpoint.full_path);
            request::apply_context(&mut request, &facts);
        }
        request
    }

    /// Seed environment of the entry method.
    fn entry_env(&self, endpoint: &Endpoint, binding: &BoundRequest) -> Env {
        let evidence = self.evidence.get(&endpoint.method);
        let empty = HashMap::new();
        let evidence = evidence.unwrap_or(&empty);
        let Some(slot) = self.slot(&endpoint.method) else {
            return binding.env_with_evidence(&[], evidence);
        };
        binding.env_with_evidence(
            &request_param_names(self.skeleton, &endpoint.method, slot),
            evidence,
        )
    }

    /// The lowered body implementing one skeleton method.
    #[must_use]
    pub fn slot(&self, method: &str) -> Option<&Slot> {
        self.body_of(method).into_slot()
    }

    /// The lowered body of one skeleton method, with the reason when the
    /// identity could not be established.
    #[must_use]
    pub fn body_of(&self, method: &str) -> BodyMatch<'_> {
        let Some(node) = self.skeleton.nodes.get(method) else {
            return BodyMatch::Missing {
                reason: format!("{method} is not a skeleton node"),
            };
        };
        let (Some(file), Some(name)) = (node.file.as_deref(), node.name.as_deref()) else {
            return BodyMatch::Missing {
                reason: format!("{method} records no source file or name"),
            };
        };
        let arity = match node.descriptor.as_deref() {
            None | Some("") => 0,
            Some(d) => d.split(',').count(),
        };
        self.bodies.resolve(file, name, arity, node.line.unwrap_or(0))
    }

    /// Visit one step's reachable subgraph starting at `entry` with `env`.
    fn walk(&self, step: u32, entry: &str, env: Env, visited_all: &mut BTreeSet<String>) -> Walk {
        let mut out = Walk::default();
        // A method is a *function*: the same body reached with different
        // argument values is a different visit, and must be analyzed again.
        // Keying the visit set by the method alone made the second call to a
        // helper disappear (`helper("")` then `helper("X")`), so the whole
        // second configuration was silently dropped.
        let mut visited: BTreeSet<String> = BTreeSet::new();
        // A call site is a *premise*: a method reached only through a possible
        // call is entered as a possible one, so its effects are `Possible`, not
        // `Confirmed`. The flag travels with the state so the same method+env
        // reached once certainly and once possibly is analyzed twice.
        let mut queue: VecDeque<(String, Env, bool)> = VecDeque::new();
        queue.push_back((entry.to_owned(), env, true));
        let mut budget = self.budget;
        while let Some((method, env, certain)) = queue.pop_front() {
            if budget == 0 {
                out.gaps.push("method_budget_exhausted".to_owned());
                break;
            }
            if !visited.insert(visit_key(&method, &env, certain)) {
                continue;
            }
            budget -= 1;
            out.executes.insert(method.clone());
            visited_all.insert(method.clone());

            let body_match = self.body_of(&method);
            let missing_body = body_match.reason().map(ToOwned::to_owned);
            let Some(slot) = body_match.into_slot() else {
                // No unambiguous lowered body (a proxy, a library type, a file
                // outside the checkout, or an overload identity that could not
                // be established): every skeleton call site stays live, exactly
                // as the legacy flood assumes.
                let reason = missing_body.unwrap_or_else(|| "no lowered body".to_owned());
                for cid in self.graph.call_sites_of(&method) {
                    self.expand(
                        step,
                        &method,
                        cid,
                        None,
                        None,
                        None,
                        &env,
                        &[],
                        &mut out,
                        &mut queue,
                    );
                }
                out.unlowered += 1;
                out.sites.methods_without_body += 1;
                out.gaps
                    .push(format!("{method}:no_lowered_body:{reason}"));
                continue;
            };
            let provider = BodyProvider::new(self.bodies);
            let mut inputs = AnalyzeInputs::new(
                &slot.unit.callsites,
                LanguageProfile::for_language(slot.unit.language),
            );
            inputs.targets = Some(&provider);
            inputs.file = slot.unit.file.as_str();
            inputs.entry_certain = certain;
            let analysis = analyze_body_with(&slot.body, env.clone(), inputs);
            let file = slot.unit.file.clone();
            for d in &analysis.decisions {
                let guard = slot
                    .body
                    .guards
                    .iter()
                    .position(|g| g.id == d.guard)
                    .map_or_else(|| format!("g{}", d.guard.raw()), |i| format!("g{i}"));
                let line = slot
                    .body
                    .guards
                    .iter()
                    .find(|g| g.id == d.guard)
                    .map(|g| g.span.start_row + 1);
                out.decisions.push(DecisionEvent {
                    step,
                    method: method.clone(),
                    guard,
                    line,
                    verdict: verdict_str(d.verdict).to_owned(),
                    symbols: d.symbols.clone(),
                    path: d.path.clone(),
                });
            }

            // Exact IR <-> skeleton call-site identity.
            //
            // Candidates come from (project file, line, callee); the anchor
            // column of the token the skeleton reports and the argument count
            // then decide. A lowered call that is *not* resolved exactly is
            // never pruned, and neither is any of its candidates: one IR call
            // must not broadcast a proof over several skeleton sites, which the
            // same-line collisions of the contested project would otherwise do.
            let mut bound: BTreeMap<u32, String> = BTreeMap::new();
            let mut of_ir: BTreeMap<String, semarch_core::CallSite> = BTreeMap::new();
            let mut ambiguous_ids: BTreeSet<String> = BTreeSet::new();
            for cs in &slot.unit.callsites {
                let resolution = self.graph.resolve_site(
                    &file,
                    slot.unit.site_line(cs),
                    &cs.callee,
                    Some(cs.args.len()),
                    slot.unit.anchor_col(cs),
                );
                match &resolution {
                    SiteResolution::Exact { id, evidence } => {
                        out.sites.resolved_exact += 1;
                        if *evidence != "unique_file_line_callee" {
                            out.gaps.push(format!("{method}:site:{id}:{evidence}"));
                        }
                        bound.insert(cs.id.raw(), id.clone());
                        of_ir.insert(id.clone(), cs.clone());
                    }
                    SiteResolution::Ambiguous { ids, reason } => {
                        out.sites.resolved_ambiguous += 1;
                        out.gaps.push(format!("{method}:ambiguous_site:{reason}"));
                        ambiguous_ids.extend(ids.iter().cloned());
                    }
                    SiteResolution::Missing { .. } => out.sites.resolved_missing += 1,
                }
            }
            let mut lowered: BTreeSet<String> = bound.values().cloned().collect();
            lowered.extend(ambiguous_ids.iter().cloned());
            let mut live: BTreeSet<String> = BTreeSet::new();
            let mut proof_of: BTreeMap<String, (String, Vec<String>)> = BTreeMap::new();
            for (effect, evidence) in &analysis.effects {
                let semarch_core::Effect::LocalCall { callsite, .. } = effect else {
                    continue;
                };
                let Some(id) = bound.get(&callsite.raw()) else {
                    continue;
                };
                let status = match evidence.status {
                    semarch_core::EvidenceStatus::Confirmed => "confirmed",
                    _ => "possible",
                };
                live.insert(id.clone());
                proof_of.insert(id.clone(), (status.to_owned(), vec![evidence.reason.clone()]));
            }
            // A skeleton site whose lowered identity stayed ambiguous keeps its
            // liveness and carries no proof of its own.
            for id in &ambiguous_ids {
                if live.insert(id.clone()) {
                    proof_of.insert(
                        id.clone(),
                        (
                            "possible".to_owned(),
                            vec!["ambiguous_call_site_identity".to_owned()],
                        ),
                    );
                }
            }

            // The values each lowered call site was reached with, joined over
            // the blocks that reach it: a callee is entered with the arguments
            // the caller actually passed at that call, not with the method's
            // entry state.
            let mut observations: BTreeMap<u32, semarch_core::analysis::CallObservation> =
                BTreeMap::new();
            for ((_, cs), obs) in &analysis.observations {
                observations
                    .entry(cs.raw())
                    .and_modify(|previous: &mut semarch_core::analysis::CallObservation| {
                        *previous = previous.join(obs);
                    })
                    .or_insert_with(|| obs.clone());
            }

            // Pruning is a proof *per call site*, not a property of the whole
            // body. The old rule ("this method has any lowering gap, so keep
            // everything the legacy flood finds") lost every proof in a method
            // that contains an unrelated `new` or a later `catch`. A call site
            // is dropped only when a guard decision on an **untainted** witness
            // path proves its block dead and no other path reaches it.
            let (dead_blocks, certificates) = self.dead_blocks(&slot.body, &analysis);
            let site_block = block_of_call_site(&slot.body);
            for cid in self.graph.call_sites_of(&method) {
                let ir = of_ir.get(cid);
                let (status, proof) = proof_of.get(cid).cloned().unwrap_or_default();
                let observation = ir.and_then(|cs| observations.get(&cs.id.raw()));
                if live.contains(cid) {
                    self.expand(
                        step,
                        &method,
                        cid,
                        Some((status, proof)),
                        ir,
                        observation,
                        &env,
                        &slot.unit.callsites,
                        &mut out,
                        &mut queue,
                    );
                    continue;
                }
                if !lowered.contains(cid) {
                    // The frontend lowered no call at that place: the site is
                    // kept, and the reason is recorded (never silently).
                    out.unlowered_call_sites += 1;
                    *out.sites
                        .kept
                        .entry("skeleton_site_absent_from_lowered_body".to_owned())
                        .or_default() += 1;
                    self.expand(
                        step,
                        &method,
                        cid,
                        None,
                        ir,
                        observation,
                        &env,
                        &slot.unit.callsites,
                        &mut out,
                        &mut queue,
                    );
                    continue;
                }
                let certificate = ir
                    .and_then(|cs| site_block.get(&cs.id.raw()))
                    .and_then(|block| certificates.get(block));
                match certificate {
                    Some(cert) if dead_blocks.contains(&cert.block) => {
                        let callee = self
                            .graph
                            .call_fact(cid)
                            .map_or_else(String::new, |(_, _, c, _)| c.to_owned());
                        let suppression = Suppression {
                            call_site: cid.clone(),
                            callee,
                            certificate: cert.clone(),
                        };
                        out.suppressed.push(suppression.describe());
                        out.suppressions.push(suppression);
                        out.sites.suppressed += 1;
                    }
                    _ => {
                        // Lowered, not reached, and no untainted decision proves
                        // its block dead: kept, with the reason it could not be
                        // dropped.
                        *out.sites
                            .kept
                            .entry("no_exclusion_certificate".to_owned())
                            .or_default() += 1;
                        out.gaps
                            .push(format!("{method}:site:{cid}:no_exclusion_certificate"));
                        self.expand(
                            step,
                            &method,
                            cid,
                            None,
                            ir,
                            observation,
                            &env,
                            &slot.unit.callsites,
                            &mut out,
                            &mut queue,
                        );
                    }
                }
            }
            for gap in &analysis.gaps {
                out.gaps.push(format!("{}:{}", method, gap_key(gap)));
            }
        }
        out.gaps.sort();
        out.gaps.dedup();
        out.suppressed.sort();
        out.suppressed.dedup();
        out
    }

    /// The blocks the value analysis proved dead, with the decision proving
    /// each of them.
    ///
    /// A decision counts only when its witness path carries no `gap:` label:
    /// inside a block reached through an unmodeled construct the values the
    /// verdict was computed from are not the program text's, so the verdict
    /// proves nothing about the text. Blocks still reached on another path are
    /// never returned: a shared exit is not dead.
    fn dead_blocks(
        &self,
        body: &semarch_core::ir::FunctionBody,
        analysis: &semarch_core::analysis::BodyAnalysis,
    ) -> (BTreeSet<u32>, BTreeMap<u32, DeadBlock>) {
        let reached: BTreeSet<semarch_core::ids::BlockId> =
            analysis.reached_blocks.iter().copied().collect();
        let mut dead: BTreeSet<u32> = BTreeSet::new();
        let mut certificates: BTreeMap<u32, DeadBlock> = BTreeMap::new();
        for d in &analysis.decisions {
            if d.path.iter().any(|label| label.starts_with("gap:")) {
                // The decision itself was made after the analysis lost the
                // construct: it says nothing about the text and proves nothing.
                continue;
            }
            if analysis.tainted_blocks.contains(&d.block) {
                // Prove-validity is a join over every reaching path, not the
                // first witness: another path reaches this block through an
                // unmodeled construct, so the block's values are not the
                // program text's and its decision proves nothing.
                continue;
            }
            let Some(block) = body.blocks.iter().find(|b| b.id == d.block) else {
                continue;
            };
            let semarch_core::ir::Terminator::Branch {
                then_block,
                else_block,
                ..
            } = &block.terminator
            else {
                continue;
            };
            let (dead_arm, verdict) = match d.verdict {
                semarch_core::cfg::GuardVerdict::ProvesFalse => (*then_block, "proves_false"),
                semarch_core::cfg::GuardVerdict::ProvesTrue => (*else_block, "proves_true"),
                semarch_core::cfg::GuardVerdict::Unknown => continue,
            };
            let guard = body
                .guards
                .iter()
                .position(|g| g.id == d.guard)
                .map_or_else(|| format!("g{}", d.guard.raw()), |i| format!("g{i}"));
            let line = body
                .guards
                .iter()
                .find(|g| g.id == d.guard)
                .map(|g| g.span.start_row + 1);
            let arm = self.dead_arm(body, dead_arm, &reached);
            if arm.is_empty() {
                continue;
            }
            for b in &arm {
                dead.insert(b.raw());
                certificates.insert(
                    b.raw(),
                    DeadBlock {
                        guard: guard.clone(),
                        line,
                        verdict: verdict.to_owned(),
                        path: d.path.clone(),
                        block: b.raw(),
                        blocks: arm.iter().map(|b| b.raw()).collect(),
                    },
                );
            }
        }
        // R04: a block whose own value computation has no normal completion cuts
        // everything it leads to. This is the same kind of proof as a guard —
        // a clean witness path and an untainted block — so it earns the same
        // certificate: the caller's continuation after a call to a body that
        // never returns is unreachable, and its remote call is not "possible".
        for site in &analysis.no_return_blocks {
            if site.path.iter().any(|label| label.starts_with("gap:")) {
                continue;
            }
            if analysis.tainted_blocks.contains(&site.block) {
                continue;
            }
            let Some(block) = body.blocks.iter().find(|b| b.id == site.block) else {
                continue;
            };
            let mut cut: BTreeSet<u32> = BTreeSet::new();
            // The rest of the block itself is unreachable, too: a call in the
            // same block after the diverging statement has no effect recorded
            // and no other path reaches it.
            cut.insert(block.id.raw());
            for target in block.terminator.successors() {
                for b in self.dead_arm(body, target, &reached) {
                    cut.insert(b.raw());
                }
            }
            let line = block.span.map(|s| s.start_row + 1);
            for b in &cut {
                dead.insert(*b);
                certificates.insert(
                    *b,
                    DeadBlock {
                        guard: "(call_without_normal_return)".to_owned(),
                        line,
                        verdict: "no_normal_return".to_owned(),
                        path: site.path.clone(),
                        block: *b,
                        blocks: cut.iter().copied().collect(),
                    },
                );
            }
        }
        (dead, certificates)
    }

    /// Everything reachable from one arm that no other path reaches.
    ///
    /// Walking stops at a block the analysis reached: from there another path
    /// continues, and what lies beyond it is not this decision's to cut off.
    fn dead_arm(
        &self,
        body: &semarch_core::ir::FunctionBody,
        root: semarch_core::ids::BlockId,
        reached: &BTreeSet<semarch_core::ids::BlockId>,
    ) -> Vec<semarch_core::ids::BlockId> {
        let mut out: Vec<semarch_core::ids::BlockId> = Vec::new();
        let mut seen: BTreeSet<semarch_core::ids::BlockId> = BTreeSet::new();
        let mut stack = vec![root];
        while let Some(id) = stack.pop() {
            if !seen.insert(id) || reached.contains(&id) {
                continue;
            }
            out.push(id);
            if let Some(block) = body.blocks.iter().find(|b| b.id == id) {
                stack.extend(block.terminator.successors());
            }
        }
        out.sort();
        out
    }

    /// Add the edges of one live call site and enqueue its targets.
    ///
    /// Targets are visited with the *actual arguments* of this call bound to
    /// their declared parameters, so a request object passed from a controller
    /// to a service keeps the properties it was bound with. Only symbolic
    /// arguments transfer bindings (`param.field` → `callee_param.field`),
    /// which is what an object handle does; anything else arrives unbound and
    /// is recorded as such by the caller.
    #[allow(clippy::too_many_arguments)]
    fn expand(
        &self,
        step: u32,
        method: &str,
        cid: &str,
        proof: Option<(String, Vec<String>)>,
        ir: Option<&semarch_core::CallSite>,
        observation: Option<&semarch_core::analysis::CallObservation>,
        caller_env: &Env,
        callsites: &[semarch_core::CallSite],
        out: &mut Walk,
        queue: &mut VecDeque<(String, Env, bool)>,
    ) {
        let edges = self.graph.edges_of(cid, self.cfg);
        let (file, line, callee, _) = self
            .graph
            .call_fact(cid)
            .map_or((None, None, String::new(), None), |(f, l, c, r)| {
                (Some(f.to_owned()), l, c.to_owned(), r.map(ToOwned::to_owned))
            });
        let (status, proof) = proof.unwrap_or_else(|| {
            (
                "possible".to_owned(),
                vec!["call_site_taken_from_skeleton_without_lowered_body".to_owned()],
            )
        });
        // The premise travels with the call: a callee reached through a
        // *possible* call is entered possibly, so nothing inside it is
        // confirmed on the caller's account.
        let certain = status == "confirmed";
        if !edges.calls.is_empty() {
            for t in &edges.calls {
                out.calls.insert((method.to_owned(), t.clone()));
            }
            out.effects.push(EffectEvent {
                step,
                method: method.to_owned(),
                call_site: cid.to_owned(),
                callee: callee.clone(),
                file: file.clone(),
                line,
                relation: Relation::Calls,
                targets: edges.calls.clone(),
                status: status.clone(),
                proof: proof.clone(),
            });
        }
        if !edges.remote.is_empty() {
            for t in &edges.remote {
                out.remote.insert((method.to_owned(), t.clone()));
            }
            out.effects.push(EffectEvent {
                step,
                method: method.to_owned(),
                call_site: cid.to_owned(),
                callee: callee.clone(),
                file: file.clone(),
                line,
                relation: Relation::Remote,
                targets: edges.remote.clone(),
                status: status.clone(),
                proof: proof.clone(),
            });
        }
        if !edges.data.is_empty() {
            for t in &edges.data {
                out.data.insert((method.to_owned(), t.clone()));
            }
            out.effects.push(EffectEvent {
                step,
                method: method.to_owned(),
                call_site: cid.to_owned(),
                callee,
                file,
                line,
                relation: Relation::Data,
                targets: edges.data.clone(),
                status,
                proof,
            });
        }
        for t in edges.enqueue {
            let env = self.bind_arguments(&t, ir, observation, caller_env, callsites);
            queue.push_back((t, env, certain));
        }
    }

    /// Bind a callee's declared parameters from the actual arguments of a call.
    ///
    /// The values come from the **call observation**: the arguments as they
    /// were evaluated in the caller's block-local environment at that call
    /// (`String code = dto.getVerificationCode(); helper(code);` passes the
    /// empty string, not the entry state). Only when no observation exists does
    /// the argument expression get evaluated in the caller's entry environment.
    fn bind_arguments(
        &self,
        target: &str,
        ir: Option<&semarch_core::CallSite>,
        observation: Option<&semarch_core::analysis::CallObservation>,
        caller_env: &Env,
        callsites: &[semarch_core::CallSite],
    ) -> Env {
        let Some(ir) = ir else {
            return Env::new();
        };
        let Some(slot) = self.slot(target) else {
            return Env::new();
        };
        let observed_env = observation.map_or(caller_env, |o| &o.env);
        let mut env = Env::new();
        for (i, arg) in ir.args.iter().enumerate() {
            let Some(param) = slot.param_names.get(i) else {
                break;
            };
            let observed = observation.and_then(|o| o.args.get(i)).cloned();
            match arg {
                semarch_core::ValueExpr::Symbolic { name } => {
                    // The object travels by handle: every property bound on the
                    // caller's variable travels with it.
                    let prefix = format!("{name}.");
                    for (key, value) in observed_env.range(prefix.clone()..) {
                        let Some(field) = key.strip_prefix(&prefix) else {
                            break;
                        };
                        env.insert(format!("{param}.{field}"), value.clone());
                    }
                    // A *scalar* variable travels by value: `helper(code)` with
                    // `code` bound to the empty string passes the empty string.
                    let direct = observed.or_else(|| observed_env.get(name).cloned());
                    if let Some(value) = direct {
                        if !value.is_unknown() {
                            env.insert(param.clone(), value);
                        }
                    }
                }
                other => {
                    let value = observed.unwrap_or_else(|| {
                        let analyzer = semarch_core::Analyzer::new(observed_env.clone(), callsites);
                        analyzer.eval(other)
                    });
                    if !value.is_unknown() {
                        env.insert(param.clone(), value);
                    }
                }
            }
        }
        env
    }
}

/// Request parameters of a handler that carry a declared request type.
fn request_param_names(skeleton: &Skeleton, method: &str, slot: &Slot) -> Vec<String> {
    let Some(node) = skeleton.nodes.get(method) else {
        return Vec::new();
    };
    let Some(descriptor) = node.descriptor.as_deref() else {
        return Vec::new();
    };
    let types: Vec<&str> = descriptor.split(',').map(str::trim).collect();
    let known: BTreeSet<String> = request::request_field_decls(skeleton).keys().cloned().collect();
    slot.param_names
        .iter()
        .enumerate()
        .filter(|(i, _)| types.get(*i).is_some_and(|t| known.contains(*t)))
        .map(|(_, n)| n.clone())
        .collect()
}

fn verdict_str(v: GuardVerdict) -> &'static str {
    match v {
        GuardVerdict::ProvesTrue => "proves_true",
        GuardVerdict::ProvesFalse => "proves_false",
        GuardVerdict::Unknown => "unknown",
    }
}

/// Visit-set key: a method *and* the environment it is entered with.
///
/// One body reached with two different argument values is two analyses. The
/// fingerprint is canonical (`Env` is an ordered map) so the same state is
/// recognized and the walk still terminates.
fn visit_key(method: &str, env: &Env, certain: bool) -> String {
    let mut key = String::with_capacity(method.len() + 16 * env.len() + 1);
    key.push(if certain { '+' } else { '-' });
    key.push_str(method);
    for (name, value) in env {
        key.push('\u{1}');
        key.push_str(name);
        key.push('=');
        match value {
            AbstractValue::Unknown => key.push('?'),
            AbstractValue::Unreachable => key.push('_'),
            AbstractValue::Null => key.push('n'),
            AbstractValue::Bool { value } => key.push(if *value { 'T' } else { 'F' }),
            AbstractValue::Int { value } => key.push_str(&format!("i{value}")),
            AbstractValue::Float { value } => key.push_str(&format!("f{value}")),
            AbstractValue::Str { value } => {
                key.push('s');
                key.push_str(value);
            }
        }
    }
    key
}

/// Which basic block each lowered call site of a body sits in.
///
/// A skeleton call site is dropped only when *its own* block is proved dead:
/// the certificate is about that block, not about the method.
fn block_of_call_site(body: &semarch_core::ir::FunctionBody) -> BTreeMap<u32, u32> {
    use semarch_core::ir::{Statement, Terminator};

    let mut out = BTreeMap::new();
    let remember = |expr: &semarch_core::ValueExpr, block: u32, out: &mut BTreeMap<u32, u32>| {
        for cs in semarch_core::analysis::callsites_of(expr) {
            out.insert(cs.raw(), block);
        }
    };
    for block in &body.blocks {
        for statement in &block.statements {
            match statement {
                Statement::Assign { value, .. } | Statement::Eval { value } => {
                    remember(value, block.id.raw(), &mut out);
                }
                Statement::Unsupported { .. } => {}
            }
        }
        match &block.terminator {
            Terminator::Branch { condition, .. } => remember(condition, block.id.raw(), &mut out),
            Terminator::Return { value: Some(value) } => {
                remember(value, block.id.raw(), &mut out);
            }
            Terminator::Throw { value } => remember(value, block.id.raw(), &mut out),
            _ => {}
        }
    }
    out
}

fn gap_key(gap: &AnalysisGap) -> String {
    format!("{:?}@{}", gap.reason, gap.span.map_or(0, |s| s.start_row + 1))
}

fn intersect_len<T: Ord + Clone>(a: &BTreeSet<T>, b: &BTreeSet<T>) -> usize {
    a.intersection(b).count()
}

/// Call-site coverage counters of one step.
///
/// Coverage is *reported*, never inferred from the size of the answer: how many
/// lowered calls were identified exactly, how many kept several candidates, how
/// many the skeleton does not record, and why the rest were kept.
#[derive(Debug, Clone, Default, PartialEq, Eq, serde::Serialize)]
pub struct SiteStats {
    /// Lowered IR call sites resolved to exactly one skeleton call site.
    pub resolved_exact: usize,
    /// Lowered IR call sites that kept several candidates (no proof carried).
    pub resolved_ambiguous: usize,
    /// Lowered IR call sites the skeleton records nothing for.
    pub resolved_missing: usize,
    /// Skeleton call sites kept because the method has no unambiguous body.
    pub methods_without_body: usize,
    /// Skeleton call sites kept although the body was lowered, by cause.
    pub kept: BTreeMap<String, usize>,
    /// Skeleton call sites dropped with a proof.
    pub suppressed: usize,
}

impl SiteStats {
    fn absorb(&mut self, other: &Self) {
        self.resolved_exact += other.resolved_exact;
        self.resolved_ambiguous += other.resolved_ambiguous;
        self.resolved_missing += other.resolved_missing;
        self.methods_without_body += other.methods_without_body;
        for (cause, n) in &other.kept {
            *self.kept.entry(cause.clone()).or_default() += n;
        }
        self.suppressed += other.suppressed;
    }
}

/// What a walk needs to carry without being part of the answer.
#[derive(Debug, Default)]
struct Walk {
    executes: BTreeSet<String>,
    calls: BTreeSet<(String, String)>,
    remote: BTreeSet<(String, String)>,
    data: BTreeSet<(String, String)>,
    effects: Vec<EffectEvent>,
    decisions: Vec<DecisionEvent>,
    gaps: Vec<String>,
    /// Call sites the value analysis proved dead (kept as an audit trail).
    suppressed: Vec<String>,
    /// The same drops with their certificates.
    suppressions: Vec<Suppression>,
    /// Methods with no lowered body.
    unlowered: usize,
    /// Call sites absent from the lowered IR (kept live conservatively).
    unlowered_call_sites: usize,
    /// Call-site coverage counters.
    sites: SiteStats,
}

impl Walk {
    /// Merge another walk into this one (framework callbacks into a scenario).
    fn absorb(&mut self, other: Walk) {
        self.executes.extend(other.executes);
        self.calls.extend(other.calls);
        self.remote.extend(other.remote);
        self.data.extend(other.data);
        self.effects.extend(other.effects);
        self.decisions.extend(other.decisions);
        self.gaps.extend(other.gaps);
        self.suppressed.extend(other.suppressed);
        self.suppressions.extend(other.suppressions);
        self.unlowered += other.unlowered;
        self.unlowered_call_sites += other.unlowered_call_sites;
        self.sites.absorb(&other.sites);
    }
}
