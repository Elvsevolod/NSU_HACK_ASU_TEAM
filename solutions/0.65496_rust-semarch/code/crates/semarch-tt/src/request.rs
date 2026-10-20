//! Request binding (N05): from a scenario step to a typed request body.
//!
//! An entry decision says *which handler* a step addresses. A semantic engine
//! needs more: which request a step sends, i.e. the field values a handler's
//! request type will actually carry. This module derives that from three
//! sources, and records the provenance of every single value:
//!
//! * the step's payload clause (its own words) — a value stated in prose;
//! * the project's declared request types (skeleton model) — *which* fields
//!   exist and their declared Java types;
//! * static UI option lists — the value a control can actually send.
//!
//! The three-way distinction the engine relies on is deliberate:
//!
//! * [`BoundValue::Literal`] — the step states a value;
//! * [`BoundValue::Empty`] — the step states that the field is empty (`""`);
//! * [`BoundValue::Absent`] — the step states the field is *not sent*;
//! * [`BoundValue::Unknown`] — the step says nothing about the field, so the
//!   request may carry anything. Silence is never read as absence: a scenario
//!   describes what the user does, not the complete body of every request.
//!
//! A value whose declared type is unknown stays [`BoundValue::Literal`] in the
//! report but is *not* seeded into the analyzer (`Env`), because comparing it
//! would invent a type. That is the "unknown ≠ false" rule applied to values.

use std::collections::{BTreeSet, HashMap};

use semarch_core::Env;
use semarch_core::AbstractValue;
use semarch_scenario::text;

use crate::skeleton::Skeleton;
use crate::ui::UiOption;

/// A declared field of a request type.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct FieldDecl {
    /// Name as declared in source (`verificationCode`).
    pub name: String,
    /// Declared type as written in source (`String`, `int`), when known.
    pub type_raw: Option<String>,
}

/// The model facts that decide what an *omitted* request field carries.
///
/// A declared type alone proves nothing: only when the value travels in a body
/// the framework *deserializes* (a `@RequestBody` parameter) and the field
/// declares no initializer of its own does an omitted property leave the Java
/// field at its default `null`.
#[derive(Debug, Clone, Default, PartialEq, Eq, serde::Serialize)]
pub struct FieldEvidence {
    /// The field's type is deserialized from the request body
    /// (`@RequestBody T`), so a property the step does not send is never
    /// applied to it.
    pub deserialized: bool,
    /// The initializer as written in source, `None` when the field declares
    /// none. A field with an initializer does not become `null` on omission.
    pub init_literal: Option<String>,
}

impl FieldEvidence {
    /// Whether the model proves an omitted field of this declared type is
    /// `null`.
    #[must_use]
    pub fn proves_null(&self, declared: Option<&str>) -> bool {
        self.deserialized
            && self.init_literal.is_none()
            && declared.is_some_and(|ty| !is_primitive(ty))
    }
}

/// Per-field omission evidence of one handler's request body.
///
/// Only `@RequestBody` parameters contribute: a field reached through a query
/// parameter or a header has other omission semantics, and the engine must not
/// borrow the body rule for it.
#[must_use]
pub fn request_field_evidence(
    sk: &Skeleton,
    method_id: &str,
) -> HashMap<String, FieldEvidence> {
    let mut fqn_of: HashMap<&str, &str> = HashMap::new();
    for (id, n) in &sk.nodes {
        if n.kind == "type" {
            if let Some(fqn) = n.fqn.as_deref() {
                fqn_of.insert(id.as_str(), fqn);
            }
        }
    }
    // The `type` of a `@RequestBody` parameter is the type the body is read
    // into.
    let mut body_types: BTreeSet<&str> = BTreeSet::new();
    for n in sk.nodes.values() {
        if n.kind != "parameter" || n.method.as_deref() != Some(method_id) {
            continue;
        }
        let is_body = n
            .annotations
            .iter()
            .any(|a| a.name == "RequestBody" || a.name == "ModelAttribute");
        if !is_body {
            continue;
        }
        if let Some(ty) = n.type_.as_deref() {
            body_types.insert(ty);
        }
    }
    let body_ids: BTreeSet<&str> = fqn_of
        .iter()
        .filter(|(_, fqn)| body_types.contains(**fqn))
        .map(|(id, _)| *id)
        .collect();
    let mut out: HashMap<String, FieldEvidence> = HashMap::new();
    for n in sk.nodes.values() {
        if n.kind != "field" {
            continue;
        }
        let (Some(owner), Some(name)) = (n.owner.as_deref(), n.name.as_deref()) else {
            continue;
        };
        if !body_ids.contains(owner) {
            continue;
        }
        out.insert(
            name.to_owned(),
            FieldEvidence {
                deserialized: true,
                init_literal: n.init_literal.clone(),
            },
        );
    }
    out
}

/// Field declarations of every type, keyed by fully-qualified type name.
///
/// This is the project's own data model read from the skeleton, not a guess:
/// a request body of that type can carry exactly these fields.
#[must_use]
pub fn request_field_decls(sk: &Skeleton) -> HashMap<String, Vec<FieldDecl>> {
    let mut fqn_of: HashMap<&str, &str> = HashMap::new();
    for (id, n) in &sk.nodes {
        if n.kind == "type" {
            if let Some(fqn) = n.fqn.as_deref() {
                fqn_of.insert(id.as_str(), fqn);
            }
        }
    }
    let mut fields: HashMap<String, Vec<FieldDecl>> = HashMap::new();
    for n in sk.nodes.values() {
        if n.kind != "field" {
            continue;
        }
        let (Some(owner), Some(name)) = (n.owner.as_deref(), n.name.as_deref()) else {
            continue;
        };
        let Some(fqn) = fqn_of.get(owner) else {
            continue;
        };
        fields
            .entry((*fqn).to_owned())
            .or_default()
            .push(FieldDecl {
                name: name.to_owned(),
                type_raw: n.type_raw.clone(),
            });
    }
    // `sk.nodes` is a hash map, so the per-owner order above is arbitrary. Every
    // consumer (the bound request, the audit trail) must be byte-stable across
    // runs, so the declaration order is fixed here.
    for decls in fields.values_mut() {
        decls.sort_by(|a, b| a.name.cmp(&b.name).then(a.type_raw.cmp(&b.type_raw)));
    }
    fields
}

/// The declared fields of the request types a handler accepts, framework
/// parameters (`HttpServletRequest`, `HttpHeaders`) excluded.
#[must_use]
pub fn handler_fields(
    sk: &Skeleton,
    model: &HashMap<String, Vec<FieldDecl>>,
    method_id: &str,
) -> Vec<FieldDecl> {
    let Some(node) = sk.nodes.get(method_id) else {
        return Vec::new();
    };
    let Some(descriptor) = node.descriptor.as_deref() else {
        return Vec::new();
    };
    let mut out: Vec<FieldDecl> = Vec::new();
    let mut seen: BTreeSet<String> = BTreeSet::new();
    for fqn in descriptor.split(',') {
        let fqn = fqn.trim();
        if fqn.is_empty() || crate::entry::is_framework_type(fqn) {
            continue;
        }
        for f in model.get(fqn).into_iter().flatten() {
            if seen.insert(f.name.clone()) {
                out.push(f.clone());
            }
        }
    }
    out
}

/// A bound value of one request field.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "snake_case")]
pub enum BoundValue {
    /// The step states this value.
    Literal(String),
    /// The step states the field is empty (`""`).
    Empty,
    /// The step states the field is not sent at all.
    Absent,
    /// The step says nothing about the field.
    Unknown,
}

impl BoundValue {
    /// Stable identifier used by the shadow/report output.
    #[must_use]
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Literal(_) => "literal",
            Self::Empty => "empty",
            Self::Absent => "absent",
            Self::Unknown => "unknown",
        }
    }

    /// The abstract value this binding seeds, or `None` when the binding does
    /// not determine a value the analyzer may rely on.
    ///
    /// An omitted field is **not** `null` by declared type alone: the type must
    /// be deserialized and the field must declare no initializer of its own,
    /// which is model evidence the caller supplies through
    /// [`BoundValue::omitted_value`].
    #[must_use]
    pub fn abstract_value(&self, declared: Option<&str>) -> Option<AbstractValue> {
        let ty = declared?;
        match self {
            Self::Literal(raw) => literal_value(raw, ty),
            Self::Empty => matches!(scalar_kind(ty), Scalar::Str).then(|| AbstractValue::Str {
                value: String::new(),
            }),
            Self::Absent | Self::Unknown => None,
        }
    }

    /// The value this binding seeds, using the model facts about the field.
    ///
    /// Only the omission case needs them: everything else is decided by the
    /// binding and the declared type.
    #[must_use]
    pub fn omitted_value(
        &self,
        declared: Option<&str>,
        evidence: &FieldEvidence,
    ) -> Option<AbstractValue> {
        match self {
            Self::Absent if evidence.proves_null(declared) => Some(AbstractValue::Null),
            other => other.abstract_value(declared),
        }
    }
}

/// Where a binding came from.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "snake_case")]
pub enum FieldOrigin {
    /// The step's own payload clause.
    Payload,
    /// A static option list of the UI control bound to the handler.
    UiOption,
    /// The task package's own statement of the starting point
    /// (`context.account`), which the step did not contradict.
    Context,
    /// Nothing in the step mentions the field.
    Unmentioned,
}

impl FieldOrigin {
    /// Stable identifier used by the shadow/report output.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Payload => "payload",
            Self::UiOption => "ui_option",
            Self::Context => "context",
            Self::Unmentioned => "unmentioned",
        }
    }
}

/// One bound request field with the evidence that produced it.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct BoundField {
    pub name: String,
    pub declared: Option<String>,
    pub value: BoundValue,
    pub origin: FieldOrigin,
    /// Human-readable provenance (the clause or option that decided it).
    pub provenance: String,
}

/// A request bound to a handler, or the reasons some fields stayed open.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct BoundRequest {
    pub step: u32,
    pub endpoint: String,
    pub method: String,
    pub fields: Vec<BoundField>,
    /// Payload words that name no declared field of this request type.
    pub unmatched: Vec<String>,
    /// Binding-level gaps, in a stable order.
    pub gaps: Vec<String>,
}

impl BoundRequest {
    /// Whether any field carries a value the analyzer can use.
    ///
    /// Without model evidence this reports the fields the step itself decided;
    /// an omitted field needs [`BoundRequest::env_with_evidence`] to become
    /// `null`.
    #[must_use]
    pub fn has_evidence(&self) -> bool {
        self.fields
            .iter()
            .any(|f| f.value.abstract_value(f.declared.as_deref()).is_some())
    }

    /// The seed environment for the entry body.
    ///
    /// Each bound field is seeded twice:
    ///
    /// * under its bare name, for a handler that reads a request field as a
    ///   local variable;
    /// * under `<parameter>.<field>`, for the JavaBeans getter contract
    ///   (`dto.getVerificationCode()`), where the receiver must be the name of
    ///   a declared handler parameter that carries a request type.
    ///
    /// Seeding under the parameter name (and not under every receiver) keeps
    /// the accessor rule from firing on unrelated `getX()` calls.
    ///
    /// This is the *no-evidence* form: an omitted field is not seeded at all.
    /// Callers that know the request model must use
    /// [`BoundRequest::env_with_evidence`].
    #[must_use]
    pub fn env(&self, request_params: &[String]) -> Env {
        self.env_with_evidence(request_params, &HashMap::new())
    }

    /// The seed environment for the entry body, with the model evidence that
    /// decides omitted fields (see [`FieldEvidence`]).
    #[must_use]
    pub fn env_with_evidence(
        &self,
        request_params: &[String],
        evidence: &HashMap<String, FieldEvidence>,
    ) -> Env {
        let none = FieldEvidence::default();
        let mut env = Env::new();
        for f in &self.fields {
            let ev = evidence.get(&f.name).unwrap_or(&none);
            let Some(value) = f.value.omitted_value(f.declared.as_deref(), ev) else {
                continue;
            };
            env.insert(f.name.clone(), value.clone());
            for p in request_params {
                env.insert(format!("{p}.{}", f.name), value.clone());
            }
        }
        env
    }
}

/// A statement the task package makes about the scenario's starting point.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct ContextFact {
    /// The clause as written, for the audit trail.
    pub clause: String,
    /// The declared field the clause constrains.
    pub field: String,
    /// The clause states the field is not sent.
    pub absent: bool,
    /// The scope word of the clause ("at login"), when it has one.
    pub scope: Option<String>,
}

/// Read the task package's statements about the scenario's starting point and
/// resolve them against one handler's request fields.
///
/// The package says, for example, "no verification code at login": a clause
/// with a negator, a field phrase and a scope. Both halves are required — the
/// phrase must name a declared field of *this* handler, and the scope must name
/// this handler's action or route — so a fact about the account is never
/// applied to a step it does not belong to. A clause without a scope is a
/// statement about the starting point as such and applies wherever the field
/// appears.
#[must_use]
pub fn context_facts(
    sk: &Skeleton,
    decls: &[FieldDecl],
    action: &str,
    route: &str,
) -> Vec<ContextFact> {
    let Some(ctx) = sk.context.as_ref() else {
        return Vec::new();
    };
    let action_tokens = text::tokenize(action);
    let route_tokens = text::tokenize(route);
    let mut out: Vec<ContextFact> = Vec::new();
    for clause in clause_split(&ctx.account) {
        // The scenario tokenizer drops stopwords, and with them the negator and
        // the scope word, so the clause is read with its words intact.
        let tokens = clause_tokens(&clause);
        if tokens.is_empty() {
            continue;
        }
        let Some(neg) = tokens.iter().position(|t| NEGATORS.contains(&t.as_str())) else {
            continue;
        };
        // The field phrase: the longest declared field whose name tokens all
        // appear after the negator. A tie is ambiguous and is not applied.
        let after = &tokens[neg + 1..];
        let mut matches: Vec<&FieldDecl> = decls
            .iter()
            .filter(|d| {
                let ft = text::tokenize(&d.name);
                !ft.is_empty() && ft.iter().all(|t| after.iter().any(|a| related_token(t, a)))
            })
            .collect();
        matches.sort_by_key(|d| std::cmp::Reverse(text::tokenize(&d.name).len()));
        let Some(field) = matches.first() else {
            continue;
        };
        if matches.len() > 1 {
            let tied = text::tokenize(&field.name).len();
            let others = matches
                .iter()
                .filter(|d| text::tokenize(&d.name).len() == tied)
                .count();
            if others > 1 {
                continue;
            }
        }
        // The scope: the word after "at"/"on"/"during", which must name this
        // handler's action or route.
        let scope = tokens
            .windows(2)
            .find(|w| matches!(w[0].as_str(), "at" | "on" | "during"))
            .map(|w| w[1].clone());
        if let Some(s) = &scope {
            let hit = action_tokens
                .iter()
                .chain(route_tokens.iter())
                .any(|t| related_token(s, t));
            if !hit {
                continue;
            }
        }
        out.push(ContextFact {
            clause: clause.trim().to_owned(),
            field: field.name.clone(),
            absent: true,
            scope: scope.clone(),
        });
    }
    out
}

/// Split a context block into clauses on the sentence and list marks.
fn clause_split(text_: &str) -> Vec<String> {
    text_
        .split(['.', ';', ',', '(', ')'])
        .map(str::trim)
        .filter(|c| !c.is_empty())
        .map(ToOwned::to_owned)
        .collect()
}

/// Lower-cased words of a context clause, stopwords kept: the negator and the
/// scope word are exactly what the scenario tokenizer drops.
fn clause_tokens(clause: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut cur = String::new();
    for c in clause.chars() {
        if c.is_alphanumeric() {
            cur.extend(c.to_lowercase());
        } else if !cur.is_empty() {
            out.push(std::mem::take(&mut cur));
        }
    }
    if !cur.is_empty() {
        out.push(cur);
    }
    out
}

/// Token relatedness for context clauses (the scenario text rules).
fn related_token(a: &str, b: &str) -> bool {
    a == b || text::related(a, b) || text::related(b, a)
}

/// Apply the package's own statements to a binding.
///
/// A clause only fills a field the step left **open**: a value the step states
/// is never overwritten by the context, so the package states the default and
/// the scenario states what it changes.
pub fn apply_context(request: &mut BoundRequest, facts: &[ContextFact]) {
    for f in &mut request.fields {
        let Some(fact) = facts.iter().find(|x| x.field == f.name) else {
            continue;
        };
        if f.value != BoundValue::Unknown || !fact.absent {
            continue;
        }
        f.value = BoundValue::Absent;
        f.origin = FieldOrigin::Context;
        f.provenance = match &fact.scope {
            Some(scope) => format!(
                "the task package states {:?} (at {scope}) and the step states nothing about it",
                fact.clause
            ),
            None => format!(
                "the task package states {:?} and the step states nothing about it",
                fact.clause
            ),
        };
        request
            .gaps
            .push(format!("{}:context_states_absent", f.name));
    }
}

/// Bind a step to the request body of one handler.
///
/// `step_text` is the scenario action; `method` and `route` identify the
/// handler, so the binding can be attributed to the very id the answer uses;
/// `decls` are its request fields; `options` are static UI option values of the
/// project (possibly empty).
#[must_use]
pub fn bind(
    step: u32,
    step_text: &str,
    method: &str,
    route: &str,
    decls: &[FieldDecl],
    options: &[UiOption],
) -> BoundRequest {
    let payload = payload_text(step_text);
    let words = words(&payload);
    let mut unmatched: Vec<String> = Vec::new();
    let mut fields: Vec<BoundField> = Vec::with_capacity(decls.len());
    let mut claimed: BTreeSet<usize> = BTreeSet::new();

    for d in decls {
        let ftokens = text::tokenize(&d.name);
        if ftokens.is_empty() {
            continue;
        }
        // The mention: the position of the last field token inside the payload.
        let mention = mention_position(&words, &ftokens);
        if let Some(pos) = mention {
            for (i, w) in words.iter().enumerate().take(pos + 1) {
                if mentions(w, &ftokens) {
                    claimed.insert(i);
                }
            }
        }
        let (mut value, mut origin, mut provenance) = match mention {
            // The step names the field: read the value it states, if any.
            Some(pos) => {
                let (value, provenance) = extract_value(&words, pos, &ftokens, decls);
                (value, FieldOrigin::Payload, provenance)
            }
            None => (
                BoundValue::Unknown,
                FieldOrigin::Unmentioned,
                "the step does not mention this field; silence is not absence".to_owned(),
            ),
        };
        // A field the step names but does not *value* can still carry the value
        // of the option the step picked: "with train food" names the field
        // (`foodType`) and the option (`Train Food` → `1`).
        if value == BoundValue::Unknown {
            if let Some((option_value, label)) = match_option(&words, &ftokens, options) {
                value = BoundValue::Literal(option_value);
                origin = FieldOrigin::UiOption;
                provenance = format!("UI option {label:?} of the control carrying this field");
            }
        }
        if let BoundValue::Literal(literal) = &value {
            // The value token is consumed by the field it belongs to, not a
            // stray payload word.
            if let Some(pos) = mention {
                if let Some(i) = words[pos + 1..]
                    .iter()
                    .position(|w| w.raw == *literal)
                    .map(|i| i + pos + 1)
                {
                    claimed.insert(i);
                }
            }
        }
        fields.push(BoundField {
            name: d.name.clone(),
            declared: d.type_raw.clone(),
            value,
            origin,
            provenance,
        });
    }

    // Payload words that name no declared field: they may be a value the
    // handler's request type cannot carry (a renamed DTO field, a typo, or a
    // field of a *nested* body). Reported, never guessed into a field.
    for (i, w) in words.iter().enumerate() {
        if claimed.contains(&i) || w.tokens.iter().any(|t| VALUE_STOP.contains(&t.as_str())) {
            continue;
        }
        if w.raw.len() < 3 {
            continue;
        }
        if decls
            .iter()
            .any(|d| text::tokenize(&d.name).iter().any(|t| mentions(w, std::slice::from_ref(t))))
        {
            continue;
        }
        if !unmatched.contains(&w.raw) {
            unmatched.push(w.raw.clone());
        }
    }

    let mut gaps = Vec::new();
    for f in &fields {
        if f.value == BoundValue::Unknown {
            gaps.push(format!("{}:unknown", f.name));
        }
        if matches!(f.value, BoundValue::Literal(_)) && f.abstract_value_is_untyped() {
            gaps.push(format!("{}:value_without_declared_type", f.name));
        }
    }

    BoundRequest {
        step,
        endpoint: route.to_owned(),
        method: method.to_owned(),
        fields,
        unmatched,
        gaps,
    }
}

impl BoundField {
    fn abstract_value_is_untyped(&self) -> bool {
        self.declared.is_none()
            && matches!(self.value, BoundValue::Literal(_) | BoundValue::Empty | BoundValue::Absent)
    }
}

/// One payload word: the text as written, plus the normalised tokens used to
/// match it against a field name.
///
/// The raw text matters: a literal must keep the case and the separators the
/// step wrote (`AbC-4578`, `-12.50`, `FDSE_microservice`). The tokens matter for
/// matching, where `verification code` has to reach `verificationCode`.
#[derive(Debug, Clone, PartialEq, Eq)]
struct Word {
    /// The word with surrounding punctuation trimmed, as written.
    raw: String,
    /// `raw` lower-cased verbatim, for the stopword/negator tables.
    lower: String,
    /// Lower-cased alphanumeric tokens (`AbC-4578` → `abc`, `4578`).
    tokens: Vec<String>,
}

impl Word {
    fn new(raw: &str) -> Option<Self> {
        let raw = trim_word(raw);
        if raw.is_empty() {
            return None;
        }
        let tokens = split_tokens(raw);
        if tokens.is_empty() {
            return None;
        }
        Some(Self {
            raw: raw.to_owned(),
            lower: raw.to_lowercase(),
            tokens,
        })
    }
}

/// The payload clause of a step: the part that describes the request body.
fn payload_text(step: &str) -> String {
    let q = text::payload_query(step);
    if q.trim().is_empty() {
        step.to_owned()
    } else {
        q
    }
}

/// Whitespace-delimited words of a clause, in order, with the raw text kept
/// (stopwords included: they carry the negators and copulas the binder reads).
fn words(clause: &str) -> Vec<Word> {
    clause.split_whitespace().filter_map(Word::new).collect()
}

/// Trim surrounding punctuation from one word, keeping the signs and separators
/// a value can contain (`-12.50`, `AbC-4578`, `FDSE_microservice`) while
/// dropping the quotes and sentence marks around it.
fn trim_word(raw: &str) -> &str {
    let lead = |c: char| c.is_alphanumeric() || c == '-' || c == '_';
    let tail = |c: char| c.is_alphanumeric();
    let start = raw.find(lead).unwrap_or(raw.len());
    let end = raw[start..].rfind(tail).map_or(start, |i| {
        let rest = &raw[start + i..];
        start + i + rest.chars().next().map_or(0, char::len_utf8)
    });
    &raw[start..end]
}

/// Lower-cased alphanumeric tokens of a word.
fn split_tokens(word: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut cur = String::new();
    for c in word.chars() {
        if c.is_alphanumeric() {
            cur.extend(c.to_lowercase());
        } else if !cur.is_empty() {
            out.push(std::mem::take(&mut cur));
        }
    }
    if !cur.is_empty() {
        out.push(cur);
    }
    out
}

/// Position of the last word of a field mention, if the field is mentioned.
fn mention_position(words: &[Word], ftokens: &[String]) -> Option<usize> {
    let mut last = None;
    for (i, w) in words.iter().enumerate() {
        if mentions(w, ftokens) {
            last = Some(i);
        }
    }
    last
}

fn mentions(word: &Word, ftokens: &[String]) -> bool {
    word.tokens
        .iter()
        .any(|t| ftokens.contains(t) || ftokens.iter().any(|f| text::related(f, t) || text::related(t, f)))
}

/// Words that cannot be a request value.
const VALUE_STOP: &[&str] = &[
    "a", "an", "the", "with", "and", "or", "of", "for", "to", "in", "on", "by", "from", "is",
    "are", "be", "as", "at", "new", "this", "that", "then", "if", "user", "one",
];

/// Negators that precede a field mention and decide a negative binding.
const NEGATORS: &[&str] = &["without", "no", "none", "missing", "lacks", "lacking", "empty", "blank"];

/// Extract the value a step states for the field at `pos`.
///
/// The rules are positional and small on purpose:
///
/// * a quoted literal right after the mention is the value;
/// * the first word after the mention that is not a stopword, not another
///   field and not a negator is the value;
/// * an explicit negator before the mention decides `Empty` (`empty`/`blank`)
///   or `Absent` (everything else);
/// * otherwise the field is mentioned but unspecified → `Unknown`.
fn extract_value(
    words: &[Word],
    pos: usize,
    ftokens: &[String],
    decls: &[FieldDecl],
) -> (BoundValue, String) {
    // Negation is scoped to the words before this mention, stopping at another
    // field's mention: "without a code" negates `code`, while in "with price 5
    // and code 7" the `without` of the price cannot reach `code`.
    let mut negator: Option<&Word> = None;
    for w in words[..pos].iter().rev() {
        if NEGATORS.contains(&w.lower.as_str()) {
            negator = Some(w);
            break;
        }
        if mentions(w, ftokens) {
            continue;
        }
        let other_field = decls.iter().any(|d| {
            text::tokenize(&d.name)
                .iter()
                .any(|t| mentions(w, std::slice::from_ref(t)))
        });
        if other_field {
            break;
        }
    }
    if let Some(neg) = negator {
        return if matches!(neg.lower.as_str(), "empty" | "blank") {
            (
                BoundValue::Empty,
                format!("the step states {:?} is empty", ftokens.join(" ")),
            )
        } else {
            (
                BoundValue::Absent,
                format!(
                    "the step states {:?} is not sent ({})",
                    ftokens.join(" "),
                    neg.lower
                ),
            )
        };
    }
    for w in &words[pos + 1..] {
        if VALUE_STOP.contains(&w.lower.as_str()) || NEGATORS.contains(&w.lower.as_str()) {
            continue;
        }
        if decls
            .iter()
            .any(|d| text::tokenize(&d.name).iter().any(|t| mentions(w, std::slice::from_ref(t))))
        {
            break;
        }
        // The value is the word **as written**: a lower-cased search token is
        // not the value the request carries (`AbC-4578` is not `abc`).
        return (
            BoundValue::Literal(w.raw.clone()),
            format!("the step states {:?} = {:?}", ftokens.join(" "), w.raw),
        );
    }
    (
        BoundValue::Unknown,
        format!(
            "the step mentions {:?} without a value; any value remains possible",
            ftokens.join(" ")
        ),
    )
}

/// A static option the step *picked*: the control that carries this field
/// offers the option, and the step's own words name that option's label.
///
/// Both halves are required. A control offering an option is not a statement
/// that the user chose it, and a label in the prose without a control that
/// carries the field would be a value the handler cannot receive.
fn match_option(
    words: &[Word],
    ftokens: &[String],
    options: &[UiOption],
) -> Option<(String, String)> {
    options.iter().find_map(|o| {
        if !plausible_option_value(&o.value) || o.label.contains('{') || o.value.contains('{') {
            return None;
        }
        let label = text::tokenize(&o.label);
        if label.is_empty() {
            return None;
        }
        let picked = label.iter().all(|t| {
            words
                .iter()
                .any(|w| w.tokens.iter().any(|wt| text::related(t, wt) || text::related(wt, t)))
        });
        let control = text::tokenize(&o.field);
        let carries_field = !control.is_empty()
            && control
                .iter()
                .any(|t| ftokens.iter().any(|f| text::related(f, t) || text::related(t, f)));
        (picked && carries_field).then(|| (o.value.clone(), o.label.clone()))
    })
}

/// Whether an option value is a literal the control can submit.
///
/// Template-driven lists (`<option value="{{item.value}}">`) are placeholders
/// bound at runtime: their "value" is a JavaScript expression, not a value.
fn plausible_option_value(value: &str) -> bool {
    !value.is_empty()
        && value
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '-' | '.' | ':' | '/'))
}

/// Scalar families the binder can type a literal with.
enum Scalar {
    Str,
    Int,
    Float,
    Bool,
    Other,
}

fn scalar_kind(ty: &str) -> Scalar {
    let ty = ty.trim();
    let simple = ty.rsplit('.').next().unwrap_or(ty);
    match simple {
        "String" | "CharSequence" | "char" | "Character" => Scalar::Str,
        "int" | "Integer" | "long" | "Long" | "short" | "Short" | "byte" | "Byte" => Scalar::Int,
        "double" | "Double" | "float" | "Float" | "BigDecimal" => Scalar::Float,
        "boolean" | "Boolean" => Scalar::Bool,
        _ => Scalar::Other,
    }
}

fn is_primitive(ty: &str) -> bool {
    matches!(
        ty.trim(),
        "int" | "long" | "short" | "byte" | "double" | "float" | "boolean" | "char"
    )
}

/// A literal promoted to the declared type, or `None` when the text is not a
/// value of that type.
fn literal_value(raw: &str, ty: &str) -> Option<AbstractValue> {
    match scalar_kind(ty) {
        Scalar::Str => Some(AbstractValue::Str {
            value: raw.to_owned(),
        }),
        Scalar::Int => raw
            .parse::<i64>()
            .ok()
            .map(|value| AbstractValue::Int { value }),
        Scalar::Float => raw
            .parse::<f64>()
            .ok()
            .map(|value| AbstractValue::Float { value }),
        Scalar::Bool => match raw {
            "true" => Some(AbstractValue::bool(true)),
            "false" => Some(AbstractValue::bool(false)),
            _ => None,
        },
        Scalar::Other => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn decls() -> Vec<FieldDecl> {
        vec![
            FieldDecl {
                name: "verificationCode".to_owned(),
                type_raw: Some("String".to_owned()),
            },
            FieldDecl {
                name: "foodType".to_owned(),
                type_raw: Some("int".to_owned()),
            },
        ]
    }

    fn value_of(request: &BoundRequest, name: &str) -> BoundValue {
        request
            .fields
            .iter()
            .find(|f| f.name == name)
            .unwrap_or_else(|| panic!("{name} is bound: {request:?}"))
            .value
            .clone()
    }

    /// A skeleton carrying the contested package's `context.account` clause.
    fn skeleton_with_context() -> Skeleton {
        Skeleton {
            project: "probe".to_owned(),
            schema: None,
            context: Some(crate::skeleton::Context {
                account: "Unless the scenario registers a new one, the passenger is the \
                          pre-registered user fdse_microservice / 111111 (internal account \
                          balance 10 000, one contact 'Contacts_One' in the contact book, no \
                          verification code at login)."
                    .to_owned(),
                ..crate::skeleton::Context::default()
            }),
            nodes: HashMap::new(),
            edges: Vec::new(),
        }
    }

    #[test]
    fn a_stated_value_is_typed_and_seeded_on_the_request_parameter() {
        let request = bind(
            1,
            "Log in with verification code 4578",
            "m",
            "/login",
            &decls(),
            &[],
        );
        assert_eq!(value_of(&request, "verificationCode"), BoundValue::Literal("4578".to_owned()));
        let env = request.env(&["dto".to_owned()]);
        assert_eq!(env.get("verificationCode"), Some(&AbstractValue::Str { value: "4578".to_owned() }));
        assert_eq!(env.get("dto.verificationCode"), Some(&AbstractValue::Str { value: "4578".to_owned() }));
        // The field the step says nothing about is not seeded at all.
        assert!(!env.contains_key("dto.foodType"));
    }

    #[test]
    fn negation_emptiness_and_silence_are_distinct_bindings() {
        let empty = bind(1, "Pay with an empty verification code", "m", "/pay", &decls(), &[]);
        assert_eq!(value_of(&empty, "verificationCode"), BoundValue::Empty);
        let absent = bind(1, "Pay without a verification code", "m", "/pay", &decls(), &[]);
        assert_eq!(value_of(&absent, "verificationCode"), BoundValue::Absent);
        let silent = bind(1, "Pay with username passenger", "m", "/pay", &decls(), &[]);
        assert_eq!(value_of(&silent, "verificationCode"), BoundValue::Unknown);

        // An omitted field is `null` only with model evidence: the value
        // travels in a deserialized body and the field has no initializer. The
        // declared type alone proves nothing, so the plain `env` seeds nothing.
        let model: HashMap<String, FieldEvidence> = HashMap::from([(
            "verificationCode".to_owned(),
            FieldEvidence {
                deserialized: true,
                init_literal: None,
            },
        )]);
        let bare = absent.env(&["dto".to_owned()]);
        assert!(!bare.contains_key("dto.verificationCode"));
        let env = absent.env_with_evidence(&["dto".to_owned()], &model);
        assert_eq!(env.get("dto.verificationCode"), Some(&AbstractValue::Null));
        let no_food = silent.env_with_evidence(&["dto".to_owned()], &model);
        assert!(!no_food.contains_key("dto.foodType"));
    }

    #[test]
    fn an_initialized_field_is_not_null_when_the_body_omits_it() {
        let absent = bind(1, "Pay without a verification code", "m", "/pay", &decls(), &[]);
        let initialized: HashMap<String, FieldEvidence> = HashMap::from([(
            "verificationCode".to_owned(),
            FieldEvidence {
                deserialized: true,
                init_literal: Some("\"\"".to_owned()),
            },
        )]);
        let env = absent.env_with_evidence(&["dto".to_owned()], &initialized);
        assert!(!env.contains_key("dto.verificationCode"));
        // A field reached through a query parameter is not a body field, so
        // the body rule does not apply to it either.
        let query_only: HashMap<String, FieldEvidence> = HashMap::from([(
            "verificationCode".to_owned(),
            FieldEvidence {
                deserialized: false,
                init_literal: None,
            },
        )]);
        let env = absent.env_with_evidence(&["dto".to_owned()], &query_only);
        assert!(!env.contains_key("dto.verificationCode"));
    }

    #[test]
    fn a_context_clause_fills_only_a_field_the_step_left_open() {
        let sk = skeleton_with_context();
        // The step names the code: the package default must not overwrite it.
        let mut stated = bind(
            1,
            "Log in with username fdse_microservice and verification code 4578",
            "m",
            "/login",
            &decls(),
            &[],
        );
        let facts = context_facts(&sk, &decls(), "Log in with verification code 4578", "/login");
        assert_eq!(facts.len(), 1, "{facts:?}");
        apply_context(&mut stated, &facts);
        assert_eq!(value_of(&stated, "verificationCode"), BoundValue::Literal("4578".to_owned()));

        // The step leaves it open: the package default applies, with origin.
        let mut open = bind(
            1,
            "Log in with username fdse_microservice and password 111111",
            "m",
            "/login",
            &decls(),
            &[],
        );
        apply_context(&mut open, &facts);
        assert_eq!(value_of(&open, "verificationCode"), BoundValue::Absent);
        assert_eq!(open.fields[0].origin, FieldOrigin::Context);

        // A far-away step is out of scope: the clause says "at login".
        let mut other = bind(1, "Book a ticket", "m", "/book", &decls(), &[]);
        let no_scope = context_facts(&sk, &decls(), "Book a ticket", "/book");
        assert!(no_scope.is_empty(), "{no_scope:?}");
        apply_context(&mut other, &no_scope);
        assert_eq!(value_of(&other, "verificationCode"), BoundValue::Unknown);
    }

    #[test]
    fn a_negator_cannot_reach_across_another_field() {
        // `without` belongs to the food type, not to the code.
        let request = bind(
            1,
            "Pay without train food and with verification code 9999",
            "m",
            "/pay",
            &decls(),
            &[],
        );
        assert_eq!(value_of(&request, "verificationCode"), BoundValue::Literal("9999".to_owned()));
        assert_eq!(value_of(&request, "foodType"), BoundValue::Absent);
    }

    #[test]
    fn only_a_picked_static_option_binds_a_value() {
        let options = vec![
            UiOption {
                field: "preserve_food_type".to_owned(),
                label: "Train Food".to_owned(),
                value: "1".to_owned(),
                file: "x.html".to_owned(),
            },
            UiOption {
                field: "preserve_food_type".to_owned(),
                label: "{{option.text}}".to_owned(),
                value: "{{item.value}}".to_owned(),
                file: "y.html".to_owned(),
            },
        ];
        let picked = bind(1, "Book a ticket with train food", "m", "/book", &decls(), &options);
        assert_eq!(value_of(&picked, "foodType"), BoundValue::Literal("1".to_owned()));
        assert_eq!(picked.fields[1].origin, FieldOrigin::UiOption);

        // Offering an option is not choosing it.
        let plain = bind(1, "Book a ticket", "m", "/book", &decls(), &options);
        assert_eq!(value_of(&plain, "foodType"), BoundValue::Unknown);
        assert_eq!(plain.fields[1].origin, FieldOrigin::Unmentioned);

        // A template list carries no value at all.
        let template_only = vec![options[1].clone()];
        let none = bind(1, "Book a ticket with train food", "m", "/book", &decls(), &template_only);
        assert_eq!(value_of(&none, "foodType"), BoundValue::Unknown);
    }

    #[test]
    fn an_untyped_literal_is_reported_but_never_seeded() {
        let request = bind(
            1,
            "Pay with verification code 4578",
            "m",
            "/pay",
            &[FieldDecl {
                name: "verificationCode".to_owned(),
                type_raw: None,
            }],
            &[],
        );
        assert_eq!(value_of(&request, "verificationCode"), BoundValue::Literal("4578".to_owned()));
        assert!(request.gaps.iter().any(|g| g.ends_with("value_without_declared_type")));
        assert!(request.env(&["dto".to_owned()]).is_empty());
    }

    #[test]
    fn a_payload_word_that_names_no_field_is_reported() {
        let request = bind(
            1,
            "Pay with verification code 4578 and coupon CODE10",
            "m",
            "/pay",
            &decls(),
            &[],
        );
        assert!(request.unmatched.contains(&"coupon".to_owned()));
        // The value token itself belongs to its field, not to `unmatched`.
        assert!(!request.unmatched.contains(&"4578".to_owned()));
    }
}
