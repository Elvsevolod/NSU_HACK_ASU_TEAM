//! Entry grounding: map scenario steps onto endpoint methods.
//!
//! Three project-data sources are combined:
//!
//! * **routes** — Spring `@RequestMapping`/`@GetMapping`/… on the handler and
//!   on its class give the external path the UI calls (public Spring MVC
//!   contract, read from the skeleton's annotation facts);
//! * **UI page + action text** — the file name, enclosing function, target
//!   element and local window around each request path in the web client
//!   ([`crate::ui`]): the screen the user is on and the control they use;
//! * the **step's action clause** ([`semarch_scenario::text::action_query`]) —
//!   the part of the sentence that names the action, without its payload.
//!
//! Ranking is BM25 ([`semarch_scenario::bm25`]) over a document whose fields are
//! weighted by duplication: handler identity once, UI *action* vocabulary
//! [`UI_ACTION_WEIGHT`] times, UI *page* vocabulary once.
//!
//! Selection is explicit rather than a plain top-k. A step picks its best
//! candidate, and may add *sibling* handlers — endpoints of the same method
//! name in a variant module (`OrderController` / `OrderOtherController`,
//! `PreserveController` / `PreserveOtherController`). Siblings whose class or
//! module carries a distinguishing token (`other`) are separated by the
//! scenario's own vocabulary, which is the same mechanism the UI uses when it
//! picks one service by train type. Siblings with no distinguishing vocabulary
//! (`Travel` / `Travel2`) are hedged.

use std::collections::{BTreeMap, BTreeSet, HashMap};

use semarch_scenario::bm25::{self, Bm25Index, Ranked};
use semarch_scenario::scenario::Scenario;
use semarch_scenario::text;
use serde::Serialize;

use crate::graph::TtGraph;
use crate::skeleton::Skeleton;
use crate::ui::UiFact;

/// How often UI *action* vocabulary is repeated in an endpoint's document.
/// BM25 saturates term frequency, so duplication is a bounded field weight.
const UI_ACTION_WEIGHT: usize = 3;

/// Weight of the payload-contract channel relative to the action channel, both
/// normalized within the step. A command step names its request body in the
/// same sentence as its action, so contract evidence is as strong as action
/// evidence; it stays below 1.0 because prose payloads are partial (they do not
/// enumerate every field).
const PAYLOAD_WEIGHT: f64 = 0.6;

/// Weight of the operation channel relative to the action channel, both
/// normalized within the step. It is the strongest structural signal a step
/// carries — a step is a request, and its head verb names the request — so it
/// is weighted above the payload contract (which is partial prose) and can
/// outweigh incidental noun overlap from an unrelated screen.
const VERB_WEIGHT: f64 = 0.8;

/// One request-mapping endpoint.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Endpoint {
    /// Skeleton method id (verbatim answer target).
    pub method: String,
    /// Simple method name (`queryOrdersForRefresh`), the sibling-family key.
    pub name: String,
    /// HTTP verb implied by the mapping annotation.
    pub http: String,
    /// Class-level mapping prefix (`/api/v1/orderservice`).
    pub prefix: String,
    /// Method-level mapping path (`/order/refresh`).
    pub path: String,
    /// Concatenated external path.
    pub full_path: String,
    pub class: String,
    pub module: String,
    /// Retrieval document tokens (identity + weighted UI evidence).
    pub tokens: Vec<String>,
    /// UI action vocabulary bound to this endpoint (function, element, window).
    pub ui_action: Vec<String>,
    /// UI page vocabulary bound to this endpoint (client file names).
    pub ui_page: Vec<String>,
    /// Whether any UI call site bound to this endpoint.
    pub ui_bound: bool,
    /// Identity tokens used for sibling-variant reasoning (class + module).
    pub family_tokens: BTreeSet<String>,
    /// Field-name vocabulary of the request types this handler accepts: the
    /// *payload contract* a client body must satisfy (`seatType`, `foodType`,
    /// `consigneeWeight`).
    pub contract: Vec<String>,
    /// Operation vocabulary of the handler: its own name, its route and the
    /// vocabulary of the control that sends the request. Searched by the
    /// step's head verb (the *operation* channel).
    pub verb: Vec<String>,
}

/// Ranking of one scenario step.
#[derive(Debug, Clone, PartialEq)]
pub struct StepRanking {
    pub step: u32,
    pub ranked: Vec<Ranked>,
}

/// The rule that shaped one step's selection. Recorded so the report states
/// *why* a step kept the entries it kept, instead of only which ones.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum StepReason {
    /// The step ranked no candidate at all.
    NoCandidate,
    /// The best candidate has no sibling variant: one unambiguous entry.
    SingleVariant,
    /// A sibling variant is named by the scenario vocabulary established so far.
    SiblingNamed,
    /// No sibling named: the base variant (fewest distinguishing tokens) wins.
    SiblingBase,
    /// No sibling has distinguishing vocabulary: the near-tie family is hedged.
    SiblingHedged,
}

impl StepReason {
    /// Stable identifier, identical to the serialized form.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::NoCandidate => "no_candidate",
            Self::SingleVariant => "single_variant",
            Self::SiblingNamed => "sibling_named",
            Self::SiblingBase => "sibling_base",
            Self::SiblingHedged => "sibling_hedged",
        }
    }
}

/// What one step alone contributes, with the rule that decided it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StepSelection {
    /// Endpoint indexes this step contributes (may be empty).
    pub members: Vec<usize>,
    /// The rule that produced [`Self::members`].
    pub reason: StepReason,
}

/// Entry index over all endpoints of a project.
pub struct EntryIndex {
    pub endpoints: Vec<Endpoint>,
    /// Vocabulary of the corpus, used to relate a query term to its
    /// morphological variants that actually occur (`consignment` → `consign`).
    vocab: BTreeSet<String>,
    index: Bm25Index,
    /// Second channel: the *payload contract* of each endpoint. A command step
    /// describes its request body in prose; the handler whose request type has
    /// those fields is the entry. Kept separate from the action channel so a
    /// read-only step (no payload) ranks exactly as it does without it.
    contract: Bm25Index,
    /// Third channel: the *operation* of each endpoint (name, route, control
    /// vocabulary), searched by the step's head verb. It separates handlers
    /// that share nouns (`book` vs `add price` both mention "first class")
    /// by the operation the step actually names.
    verb: Bm25Index,
}

impl EntryIndex {
    /// Build the index from skeleton route facts plus UI evidence.
    #[must_use]
    pub fn build(sk: &Skeleton, graph: &TtGraph, ui: &[UiFact]) -> Self {
        let model = request_model(sk);
        let mut endpoints = Vec::new();
        for m in graph.all_methods() {
            if !m.has_mapping_annotation() || m.owner.is_empty() {
                continue;
            }
            let type_node = sk.nodes.get(&m.owner);
            let prefix = type_node
                .and_then(|t| mapping_path(&t.annotations, "RequestMapping"))
                .unwrap_or_default();
            let (http, path) = method_mapping(&m.annotations, m.name.as_str());
            if path.is_empty() && http.is_empty() {
                continue;
            }
            let full_path = join_paths(&prefix, &path);
            let class = m.owner.rsplit(':').next().unwrap_or(&m.owner).to_owned();
            let module = m.module.clone().unwrap_or_default();
            let mut tokens = text::tokenize(&format!("{class} {} {module} {full_path}", m.name));
            // route segment tokens carry the business noun (contacts, consigns, order)
            tokens.extend(text::tokenize(&full_path));
            let contract = request_fields(sk, &m.id, &model);
            endpoints.push(Endpoint {
                method: m.id.clone(),
                name: m.name.clone(),
                http,
                prefix,
                path,
                full_path,
                family_tokens: text::tokenize(&format!("{class} {module}")).into_iter().collect(),
                class,
                module,
                tokens,
                ui_action: Vec::new(),
                ui_page: Vec::new(),
                ui_bound: false,
                contract,
                verb: Vec::new(),
            });
        }
        endpoints.sort_by(|a, b| a.method.cmp(&b.method));

        // Attach UI evidence to the *most specific* matching route. A UI path
        // that stops at a static prefix (`/consigns/account/` + id) matches both
        // `/consigns/account/{id}` and `/consigns/{consignee}`; only the route
        // with the most literal segments keeps the evidence, so label text is
        // not smeared across unrelated handlers. When the call site states an
        // HTTP verb, only handlers that answer that verb are addressed — a
        // `POST /contacts` literal does not describe a `GET /contacts/{id}`.
        for fact in ui {
            let mut best = 0usize;
            let mut hits: Vec<usize> = Vec::new();
            for (i, e) in endpoints.iter().enumerate() {
                if let Some(v) = fact.http.as_deref() {
                    if e.http != "ANY" && !e.http.eq_ignore_ascii_case(v) {
                        continue;
                    }
                }
                if let Some(score) = route_literal_score(&fact.url, &e.full_path, &e.path) {
                    if score > best {
                        best = score;
                        hits.clear();
                        hits.push(i);
                    } else if score == best {
                        hits.push(i);
                    }
                }
            }
            for i in hits {
                let e = &mut endpoints[i];
                e.ui_bound = true;
                e.ui_action.extend(fact.action_tokens.iter().cloned());
                e.ui_page.extend(fact.page_tokens.iter().cloned());
                // The window around the call site is screen vocabulary (field
                // labels, payload identifiers) and is weighted as such.
                e.ui_page.extend(fact.context_tokens.iter().cloned());
            }
        }

        // Retrieval document: identity tokens, then UI evidence weighted by
        // field role. Page vocabulary is shared by every endpoint of one screen
        // (it says *where* the step happens); action vocabulary is specific to
        // the control (it says *what* the user does).
        for e in &mut endpoints {
            let action = e.ui_action.clone();
            for _ in 0..UI_ACTION_WEIGHT {
                e.tokens.extend(action.iter().cloned());
            }
            e.tokens.extend(e.ui_page.iter().cloned());
            // Operation document: what the handler *does*, named by its own
            // identity and by the control that sends the request.
            e.verb = text::tokenize(&format!("{} {}", e.name, e.full_path));
            e.verb.extend(action);
        }

        let vocab: BTreeSet<String> =
            endpoints.iter().flat_map(|e| e.tokens.iter().cloned()).collect();
        let index = Bm25Index::build(endpoints.iter().map(|e| e.tokens.as_slice()));
        let contract = Bm25Index::build(endpoints.iter().map(|e| e.contract.as_slice()));
        let verb = Bm25Index::build(endpoints.iter().map(|e| e.verb.as_slice()));
        Self {
            endpoints,
            vocab,
            index,
            contract,
            verb,
        }
    }

    /// Number of indexed endpoints.
    #[must_use]
    pub fn len(&self) -> usize {
        self.endpoints.len()
    }

    /// Whether no endpoint was found (a discovery failure worth surfacing).
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.endpoints.is_empty()
    }

    /// Rank endpoints for every step of a scenario.
    #[must_use]
    pub fn rank_scenario(&self, scn: &Scenario) -> Vec<StepRanking> {
        scn.steps
            .iter()
            .enumerate()
            .map(|(i, s)| StepRanking {
                step: s.n,
                ranked: self.rank_step(scn, i),
            })
            .collect()
    }

    /// Rank one step: the action channel, the operation (verb) channel, and —
    /// when the step states a payload — the payload-contract channel.
    ///
    /// The channels answer different questions. The action channel asks "which
    /// request *does* this?" (handler, route and control vocabulary); the
    /// operation channel asks "which handler *performs this operation*?" (the
    /// step's head verb against handler name, route and control vocabulary);
    /// the contract channel asks "which handler accepts a body *shaped like
    /// this*?" (the request type's fields). Merging them is what separates
    /// `preserve(OrderTicketsInfo)` — whose body has `seatType`, `foodType`,
    /// `assurance`, `consigneeWeight` — from a look-up handler that merely
    /// mentions "assurance" in its name, and from `addPrice(PriceInfo)`, whose
    /// admin form labels ("first class price rate") share the step's adjectives
    /// but none of its operation.
    fn rank_step(&self, scn: &Scenario, i: usize) -> Vec<Ranked> {
        let action = bm25::normalize(self.index.search(&self.step_query(scn, i)));
        let mut scores: BTreeMap<usize, f64> = action.iter().map(|r| (r.doc, r.score)).collect();
        let payload = self.payload_tokens(scn, i);
        if !payload.is_empty() {
            for r in bm25::normalize(self.contract.search(&payload)) {
                *scores.entry(r.doc).or_insert(0.0) += PAYLOAD_WEIGHT * r.score;
            }
        }
        // The operation channel *modulates* the ranking instead of adding to
        // it. A step's head verb is often generic ("open" → get/find/query/list)
        // and then matches half the project; as a bonus it would promote any
        // short-named look-up above the handler the screen actually sends. As a
        // factor it can only amplify a candidate that already ranks, and it
        // reorders exactly the near-tie the step's own verb should decide.
        let verb = bm25::normalize(self.verb.search(&self.verb_query(scn, i)));
        for r in verb {
            if let Some(score) = scores.get_mut(&r.doc) {
                *score *= 1.0 + VERB_WEIGHT * r.score;
            }
        }
        let mut out: Vec<Ranked> = scores
            .into_iter()
            .map(|(doc, score)| Ranked { doc, score })
            .collect();
        out.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then(a.doc.cmp(&b.doc))
        });
        bm25::normalize(out)
    }

    /// The operation tokens searched in the verb channel: the step's head verb
    /// and its synonyms.
    #[must_use]
    pub fn verb_query(&self, scn: &Scenario, i: usize) -> Vec<String> {
        let Some(step) = scn.steps.get(i) else {
            return Vec::new();
        };
        text::verb_tokens(&step.action).into_iter().collect()
    }

    /// The payload tokens searched in the contract channel (empty for
    /// read-only steps).
    #[must_use]
    pub fn payload_tokens(&self, scn: &Scenario, i: usize) -> Vec<String> {
        let Some(step) = scn.steps.get(i) else {
            return Vec::new();
        };
        let raw = text::payload_query(&step.action);
        if raw.trim().is_empty() {
            return Vec::new();
        }
        self.expand(text::tokenize(&raw).into_iter().collect())
    }

    /// The query tokens searched for one step. Ranking and the audit trail use
    /// this one function, so a report always shows the query that was used.
    #[must_use]
    pub fn step_query(&self, scn: &Scenario, i: usize) -> Vec<String> {
        let Some(step) = scn.steps.get(i) else {
            return Vec::new();
        };
        let tokens = text::tokenize(&scn.query_for(step));
        self.expand(text::synonyms_for_action(&tokens))
    }

    /// Expand a query with the corpus's own morphological variants of its
    /// terms.
    ///
    /// Scenario prose and identifiers derive words differently: the step says
    /// "luggage consignments", the handler says `findByAccountId` inside
    /// `ts-consign-service`. A corpus term whose remainder over the query term
    /// is a derivational suffix is that word's variant; identifier
    /// concatenations (`orderid`, `orderservice`) are not, so `order` does not
    /// pull in half the project.
    fn expand(&self, tokens: BTreeSet<String>) -> Vec<String> {
        let mut out = tokens.clone();
        for t in &tokens {
            for v in &self.vocab {
                if derivation(t, v) || derivation(v, t) {
                    out.insert(v.clone());
                }
            }
        }
        out.into_iter().collect()
    }

    /// Rank endpoints against a pre-tokenized query (tests/diagnostics).
    #[must_use]
    pub fn rank_query(&self, query: &[String]) -> Vec<Ranked> {
        bm25::normalize(self.index.search(query))
    }

    /// Select entry methods under a near-tie policy (legacy top-k heuristic).
    ///
    /// * `ratio` — keep every candidate scoring at least `ratio × best`;
    /// * `max` — hard cap to bound the hedge.
    #[must_use]
    pub fn select(&self, rankings: &[StepRanking], ratio: f64, max: usize) -> Vec<String> {
        let mut entries = BTreeSet::new();
        for r in rankings {
            for cand in r.ranked.iter().take(max) {
                if cand.score >= ratio {
                    entries.insert(self.endpoints[cand.doc].method.clone());
                }
            }
        }
        entries.into_iter().collect()
    }

    /// Select entry methods for a scenario, resolving sibling handlers.
    ///
    /// Per step: take the best candidate, then consider its *sibling family*
    /// (endpoints with the same method name). Siblings are separated by their
    /// distinguishing identity tokens against the vocabulary the scenario has
    /// established so far — a step may rely on a train type named in an earlier
    /// step ("the first trip found" after "search high-speed trains"). When no
    /// sibling is distinguished by the scenario's vocabulary, the base variant
    /// (fewest distinguishing tokens) wins; when no sibling has any
    /// distinguishing token at all, the family is hedged.
    ///
    /// * `ratio` — near-tie threshold for hedging an indistinguishable family;
    /// * `max` — how many ranked candidates a step may consider.
    ///
    /// The returned set is the union of the per-step decisions
    /// ([`EntryIndex::select_per_step`]), which is what the answer uses.
    #[must_use]
    pub fn select_scenario(
        &self,
        scn: &Scenario,
        rankings: &[StepRanking],
        ratio: f64,
        max: usize,
    ) -> Vec<String> {
        let mut entries = BTreeSet::new();
        for sel in self.select_per_step(scn, rankings, ratio, max) {
            for idx in sel.members {
                entries.insert(self.endpoints[idx].method.clone());
            }
        }
        entries.into_iter().collect()
    }

    /// The per-step selection decisions, in step order.
    ///
    /// This is the single code path behind the answer *and* the audit trail:
    /// the report shows exactly the members and reason computed here, so a
    /// step's own decision can never be mistaken for a union across steps.
    #[must_use]
    pub fn select_per_step(
        &self,
        scn: &Scenario,
        rankings: &[StepRanking],
        ratio: f64,
        max: usize,
    ) -> Vec<StepSelection> {
        let mut context: BTreeSet<String> = BTreeSet::new();
        let mut out = Vec::with_capacity(rankings.len());
        for (i, r) in rankings.iter().enumerate() {
            if let Some(step) = scn.steps.get(i) {
                context.extend(text::tokenize(&step.action));
            }
            out.push(self.select_step(r, &context, ratio, max));
        }
        out
    }

    /// Entry candidates one step contributes, given the vocabulary the scenario
    /// has established up to and including it.
    ///
    /// Exposed separately from [`EntryIndex::select_per_step`] so audit tooling
    /// can attribute every entry to the step that produced it, together with
    /// the rule that decided it.
    #[must_use]
    pub fn select_step(
        &self,
        r: &StepRanking,
        context: &BTreeSet<String>,
        ratio: f64,
        max: usize,
    ) -> StepSelection {
        let Some(best) = r.ranked.first() else {
            return StepSelection {
                members: Vec::new(),
                reason: StepReason::NoCandidate,
            };
        };
        let best_name = self.endpoints[best.doc].name.clone();
        let score_of = |idx: usize| {
            r.ranked
                .iter()
                .find(|c| c.doc == idx)
                .map_or(0.0, |c| c.score)
        };
        let family: Vec<usize> = (0..self.endpoints.len())
            .filter(|&i| self.endpoints[i].name == best_name)
            .collect();
        if family.len() <= 1 {
            return StepSelection {
                members: vec![best.doc],
                reason: StepReason::SingleVariant,
            };
        }
        // (endpoint index, distinguishing tokens, named by the scenario)
        let dist = self.distinguishing_tokens(&family);
        let mut members: Vec<(usize, &BTreeSet<String>, bool)> = family
            .iter()
            .copied()
            .zip(dist.iter())
            .map(|(idx, d)| {
                let named = !d.is_empty() && d.iter().all(|t| context.contains(t));
                (idx, d, named)
            })
            .filter(|(idx, _d, named)| score_of(*idx) > 0.0 || *named)
            .collect();
        members.sort_by(|a, b| b.1.len().cmp(&a.1.len()).then_with(|| a.0.cmp(&b.0)));
        if members.is_empty() {
            StepSelection {
                members: vec![best.doc],
                reason: StepReason::SingleVariant,
            }
        } else if members.iter().any(|(_, _, named)| *named) {
            StepSelection {
                members: members
                    .iter()
                    .filter(|(_, _, named)| *named)
                    .map(|(idx, _, _)| *idx)
                    .collect(),
                reason: StepReason::SiblingNamed,
            }
        } else if members.iter().any(|(_, d, _)| !d.is_empty()) {
            // No sibling named: prefer the base variant (fewest distinguishing
            // tokens).
            let min = members.iter().map(|(_, d, _)| d.len()).min().unwrap_or(0);
            StepSelection {
                members: members
                    .iter()
                    .filter(|(_, d, _)| d.len() == min)
                    .map(|(idx, _, _)| *idx)
                    .collect(),
                reason: StepReason::SiblingBase,
            }
        } else {
            // No sibling has distinguishing vocabulary: keep the near-tie
            // family (bounded by `max` and `ratio`).
            StepSelection {
                members: r
                    .ranked
                    .iter()
                    .take(max)
                    .filter(|c| family.contains(&c.doc) && c.score >= best.score * ratio)
                    .map(|c| c.doc)
                    .collect(),
                reason: StepReason::SiblingHedged,
            }
        }
    }

    /// Distinguishing identity tokens for each member of a sibling family: the
    /// member's class/module tokens that the whole family does not share.
    fn distinguishing_tokens(&self, family: &[usize]) -> Vec<BTreeSet<String>> {
        let common: BTreeSet<String> = family
            .iter()
            .map(|&i| self.endpoints[i].family_tokens.clone())
            .fold(None, |acc: Option<BTreeSet<String>>, t| {
                Some(match acc {
                    None => t,
                    Some(a) => a.intersection(&t).cloned().collect(),
                })
            })
            .unwrap_or_default();
        family
            .iter()
            .map(|&i| {
                self.endpoints[i]
                    .family_tokens
                    .difference(&common)
                    .cloned()
                    .collect()
            })
            .collect()
    }

    /// Endpoint lookup by full path (diagnostics/tests).
    #[must_use]
    pub fn by_full_path(&self, full_path: &str) -> Option<&Endpoint> {
        self.endpoints.iter().find(|e| e.full_path == full_path)
    }
}

/// Whether `long` is `short` plus a derivational suffix (`consign` +
/// `ment` = `consignment`), i.e. the two are the same word in different
/// grammatical clothes — unlike an identifier concatenation.
fn derivation(short: &str, long: &str) -> bool {
    const SUFFIXES: &[&str] = &[
        "ment", "ments", "ance", "ances", "ence", "ences", "tion", "tions", "sion", "sions",
        "ation", "ations", "ness", "ity", "ities", "ure", "ures", "able", "ible", "age", "ages",
        "ist", "ists", "ism", "ant", "ants", "ent", "ents", "ary", "ory", "ive", "ives", "al",
        "ly", "ic", "ate", "ated", "ates",
    ];
    short.len() >= 3
        && long
            .strip_prefix(short)
            .is_some_and(|rest| !rest.is_empty() && SUFFIXES.contains(&rest))
}

/// Field-name vocabulary of every declared type, keyed by fully-qualified name.
///
/// This is the project's own data model read from the skeleton: which fields a
/// request body of a given type actually carries. The vocabulary is derived
/// from the declared names; [`crate::request::request_field_decls`] keeps the
/// names and types for the value binder.
fn request_model(sk: &Skeleton) -> HashMap<String, Vec<String>> {
    crate::request::request_field_decls(sk)
        .into_iter()
        .map(|(fqn, decls)| {
            let tokens = decls
                .iter()
                .flat_map(|d| text::tokenize(&d.name))
                .collect();
            (fqn, tokens)
        })
        .collect()
}

/// Field tokens of the request types a handler accepts, framework types
/// excluded.
fn request_fields(
    sk: &Skeleton,
    method_id: &str,
    model: &HashMap<String, Vec<String>>,
) -> Vec<String> {
    let Some(node) = sk.nodes.get(method_id) else {
        return Vec::new();
    };
    let Some(descriptor) = node.descriptor.as_deref() else {
        return Vec::new();
    };
    let mut out = Vec::new();
    for fqn in descriptor.split(',') {
        let fqn = fqn.trim();
        if fqn.is_empty() || is_framework_type(fqn) {
            continue;
        }
        if let Some(fields) = model.get(fqn) {
            out.extend(fields.iter().cloned());
        }
    }
    out
}

/// Whether a parameter type belongs to the HTTP framework rather than to the
/// business payload.
pub(crate) fn is_framework_type(fqn: &str) -> bool {
    ["java.", "javax.", "jakarta.", "org.springframework."]
        .iter()
        .any(|p| fqn.starts_with(p))
}

/// The path argument of the first annotation named `name`.
#[must_use]
pub fn mapping_path(annotations: &[crate::skeleton::Annotation], name: &str) -> Option<String> {
    annotations
        .iter()
        .find(|a| a.name == name)
        .and_then(|a| first_quoted(&a.args))
}

fn method_mapping(
    annotations: &[crate::skeleton::Annotation],
    fallback_name: &str,
) -> (String, String) {
    for (ann, http) in [
        ("GetMapping", "GET"),
        ("PostMapping", "POST"),
        ("PutMapping", "PUT"),
        ("DeleteMapping", "DELETE"),
        ("PatchMapping", "PATCH"),
        ("RequestMapping", "ANY"),
    ] {
        if let Some(a) = annotations.iter().find(|a| a.name == ann) {
            return (http.to_owned(), first_quoted(&a.args).unwrap_or_default());
        }
    }
    let _ = fallback_name;
    (String::new(), String::new())
}

/// Extract the first single- or double-quoted literal from annotation args.
#[must_use]
pub fn first_quoted(args: &str) -> Option<String> {
    let mut out = String::new();
    let mut quote: Option<char> = None;
    for c in args.chars() {
        match quote {
            Some(q) => {
                if c == q {
                    return Some(out);
                }
                out.push(c);
            }
            None => {
                if c == '"' || c == '\'' {
                    quote = Some(c);
                }
            }
        }
    }
    None
}

/// Join a class prefix and a method path into one external path.
#[must_use]
pub fn join_paths(prefix: &str, path: &str) -> String {
    let p = normalize_path(prefix);
    let m = normalize_path(path);
    match (p.is_empty(), m.is_empty()) {
        (true, true) => String::new(),
        (true, false) => m,
        (false, true) => p,
        (false, false) => format!("{p}{m}"),
    }
}

fn normalize_path(p: &str) -> String {
    let p = p.trim();
    if p.is_empty() {
        return String::new();
    }
    let p = if p.starts_with('/') {
        p.to_owned()
    } else {
        format!("/{p}")
    };
    p.trim_end_matches('/').to_owned()
}

fn segments(path: &str) -> Vec<&str> {
    path.split('/').filter(|s| !s.is_empty()).collect()
}

/// Whether a UI path literal plausibly addresses `full_path`.
///
/// The UI often writes only the static prefix of a path whose tail is built at
/// runtime (`/consigns/account/` + id), so a UI path may be *shorter* than the
/// route; every remaining route segment must then be a path variable.
#[must_use]
pub fn route_matches(url: &str, full_path: &str, method_path: &str) -> bool {
    route_literal_score(url, full_path, method_path).is_some()
}

/// Like [`route_matches`], but reports *how many* segments matched literally.
/// A higher score means a more specific match, which decides which route keeps
/// a piece of UI evidence.
///
/// A literal that ends with `/` is a *prefix* the client concatenates a value
/// onto (`/consigns/account/` + id), so the route may have extra variable
/// segments. A literal without a trailing slash is a complete request path and
/// must have exactly as many segments as the route: a client calling
/// `/contacts` never reaches `/contacts/{id}`.
#[must_use]
pub fn route_literal_score(url: &str, full_path: &str, method_path: &str) -> Option<usize> {
    if full_path.is_empty() {
        return None;
    }
    let url = url.split(['?', '#']).next().unwrap_or(url);
    let complete = !url.ends_with('/');
    let u = segments(url);
    let f = segments(full_path);
    if u.is_empty() || f.is_empty() || u.len() > f.len() {
        return None;
    }
    // Guard against absurdly generic matches on a single shared segment.
    if segments(method_path).is_empty() && u.len() < 2 {
        return None;
    }
    if complete && u.len() != f.len() {
        return None;
    }
    let n = u.len();
    let mut literal = 0usize;
    for i in 0..n {
        let (a, b) = (u[i], f[i]);
        if b.starts_with('{') || a.starts_with('{') {
            continue;
        }
        if a != b {
            return None;
        }
        literal += 1;
    }
    if f.len() > n && !f[n..].iter().all(|s| s.starts_with('{')) {
        return None;
    }
    Some(literal)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::skeleton::Annotation;

    fn ann(name: &str, args: &str) -> Annotation {
        Annotation {
            name: name.to_owned(),
            args: args.to_owned(),
        }
    }

    #[test]
    fn extracts_first_quoted_literal() {
        assert_eq!(
            first_quoted("(path = \"/contacts/account/{accountId}\")").as_deref(),
            Some("/contacts/account/{accountId}")
        );
        assert_eq!(first_quoted("(\"/api/v1/users\")").as_deref(), Some("/api/v1/users"));
        assert_eq!(first_quoted("(value = \"/consigns\")").as_deref(), Some("/consigns"));
        assert_eq!(first_quoted(""), None);
    }

    #[test]
    fn joins_prefix_without_double_slash() {
        assert_eq!(
            join_paths("api/v1/contactservice", "/contacts/account/{id}"),
            "/api/v1/contactservice/contacts/account/{id}"
        );
        assert_eq!(join_paths("/api/v1/users", "/login"), "/api/v1/users/login");
        assert_eq!(join_paths("/api/v1/users", ""), "/api/v1/users");
    }

    #[test]
    fn route_matching_handles_static_prefix_and_variables() {
        let full = "/api/v1/contactservice/contacts/account/{accountId}";
        assert!(route_matches("/api/v1/contactservice/contacts/account/", full, "/contacts/account/{accountId}"));
        assert!(route_matches("/api/v1/orderservice/order/refresh", "/api/v1/orderservice/order/refresh", "/order/refresh"));
        assert!(!route_matches("/api/v1/orderservice/order/refresh", "/api/v1/orderOtherService/orderOther/refresh", "/orderOther/refresh"));
        // both routes match the URL, but the literal-segment score separates them
        let ui = "/api/v1/consignservice/consigns/account/";
        let specific = route_literal_score(ui, "/api/v1/consignservice/consigns/account/{id}", "/consigns/account/{id}");
        let generic = route_literal_score(ui, "/api/v1/consignservice/consigns/{consignee}", "/consigns/{consignee}");
        assert!(specific > generic, "{specific:?} vs {generic:?}");
    }

    #[test]
    fn mapping_helpers_pick_verb_and_path() {
        let a = vec![ann("CrossOrigin", "(origins = \"*\")"), ann("GetMapping", "(path = \"/contacts\")")];
        let (http, path) = method_mapping(&a, "x");
        assert_eq!(http, "GET");
        assert_eq!(path, "/contacts");
    }
}
