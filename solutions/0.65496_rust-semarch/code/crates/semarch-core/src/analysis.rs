//! Abstract evaluation over the Common IR (N04).
//!
//! Two related questions are answered here, both over the language-neutral IR
//! and never over a language AST:
//!
//! 1. *What does this expression evaluate to?* — with an abstract-value domain
//!    ([`AbstractValue`]) whose top is `Unknown` and whose bottom is
//!    `Unreachable`. `Unknown != false` is structural: nothing here turns
//!    `Unknown` into a definite verdict, and every unsupported operation
//!    returns `Unknown` **and records a gap** (an overflow, a division by zero,
//!    an ordering of non-numbers).
//! 2. *What does this body do on each path?* — [`analyze_body`] walks the
//!    ordered blocks of a [`FunctionBody`] to a bounded fixed point, recording
//!    reachable effects, return alternatives, throws, and the widened-gap when
//!    a loop exceeds the context limit.
//!
//! # Interprocedural summaries
//!
//! A `CallResult` of a project-local callee is evaluated by substituting the
//! *actual* arguments into the callee's parameter slots and evaluating its
//! `return` expressions (summary-based propagation, provenance: Facebook
//! *Infer*'s summary tables and Clang Static Analyzer's `ExprEngine`
//! call-eval). No summary is cached across differently-argumented calls, which
//! is what makes "the same method called with other arguments" safe. Recursion
//! is capped; beyond the cap the result is `Unknown`.
//!
//! # What is deliberately not modeled
//!
//! Heap/field state, object identity, exceptions, and dynamic dispatch: reads
//! of unknown storage yield `Unknown`, never a guess.

use std::collections::{BTreeMap, BTreeSet};
use std::rc::Rc;

use serde::{Deserialize, Serialize};

use crate::cfg::GuardVerdict;
use crate::ids::{BlockId, CallSiteId, FunctionId, GuardId};
use crate::invocation::{CallOutcome, CallTargetProvider};
use crate::ir::{
    AnalysisGap, CallSite, Effect, Evidence, EvidenceStatus, Function, FunctionBody, GapReason,
    Statement, Terminator, ValueExpr,
};
use crate::span::SourceSpan;
use crate::value::{AbstractValue, LanguageProfile};

/// Scenario/local bindings: symbolic name → abstract value.
pub type Env = BTreeMap<String, AbstractValue>;

/// Built-in semantic kinds the analyzer knows about. Each entry is a
/// documented contract, not an inference.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Builtin {
    /// `StringUtils.isEmpty(s)` → `s == ""`.
    StrIsEmpty,
    /// `str.equals(other)` → `str == other`.
    StrEquals,
}

/// Resolve the builtin for a call by receiver and callee name. Names are
/// matched exactly; the registry is intentionally tiny and explicit.
#[must_use]
pub fn lookup_builtin(receiver: Option<&ValueExpr>, callee: &str) -> Option<Builtin> {
    match (receiver, callee) {
        (Some(ValueExpr::Symbolic { name }), "isEmpty") if name == "StringUtils" => {
            Some(Builtin::StrIsEmpty)
        }
        (Some(ValueExpr::Str { .. }), "equals") => Some(Builtin::StrEquals),
        _ => None,
    }
}

/// How the analyzer resolves project-local callees.
///
/// Provenance: simple-name resolution mirrors the *namespace-insensitive*
/// call-graph style of pyan3 / Comex (may-analysis over name matches);
/// ambiguity deliberately degrades to `Unknown`, never to a guess.
pub trait CallResolver {
    /// All project functions whose simple name matches `callee`.
    fn candidates(&self, callee: &str) -> Vec<&Function>;
}

/// Trivial resolver: match by simple name.
pub struct SimpleNameResolver<'p> {
    pub functions: &'p [Function],
}

impl CallResolver for SimpleNameResolver<'_> {
    fn candidates(&self, callee: &str) -> Vec<&Function> {
        self.functions
            .iter()
            .filter(|f| f.name == callee)
            .collect()
    }
}

/// Context for expression evaluation: a binding environment and an optional
/// parameter frame.
#[derive(Default)]
pub struct Frame {
    pub params: Vec<AbstractValue>,
    pub names: BTreeMap<String, AbstractValue>,
}

/// Expression evaluator over the IR.
pub struct Analyzer<'a> {
    pub env: Env,
    pub callsites: &'a [CallSite],
    pub resolver: Option<&'a dyn CallResolver>,
    pub profile: LanguageProfile,
    depth: std::cell::Cell<u8>,
    /// Project-local callee bodies (R04/R05). `None` keeps the flat-summary path
    /// only.
    targets: Option<&'a dyn CallTargetProvider>,
    /// Project-relative file of the body under analysis: a callee name written
    /// there is resolved there, and a nested body is resolved in *its own* file.
    file: &'a str,
    /// Entry depth of nested bodies, bounded like the flat path.
    depth_level: u8,
    /// The outcome computed for each explicit call point of *this* body (the
    /// result slot of the call). A callee's own call points belong to the
    /// callee's arena and are recorded by the nested analysis.
    outcomes: std::cell::RefCell<BTreeMap<CallSiteId, CallOutcome>>,
    /// The shared memo of nested callee outcomes (see [`OutcomeCache`]).
    cache: Option<OutcomeCache>,
}

const MAX_DEPTH: u8 = 8;

impl<'a> Analyzer<'a> {
    #[must_use]
    pub fn new(env: Env, callsites: &'a [CallSite]) -> Self {
        Self {
            env,
            callsites,
            resolver: None,
            profile: LanguageProfile::java(),
            depth: std::cell::Cell::new(0),
            targets: None,
            file: "",
            depth_level: 0,
            outcomes: std::cell::RefCell::new(BTreeMap::new()),
            cache: None,
        }
    }

    /// Attach a project-local callee resolver.
    pub fn with_resolver(mut self, resolver: &'a dyn CallResolver) -> Self {
        self.resolver = Some(resolver);
        self
    }

    /// Select the language profile whose scalar semantics apply.
    pub fn with_profile(mut self, profile: LanguageProfile) -> Self {
        self.profile = profile;
        self
    }

    /// Attach the provider of project-local callee bodies (R04).
    pub fn with_targets(mut self, targets: &'a dyn CallTargetProvider) -> Self {
        self.targets = Some(targets);
        self
    }

    /// Declare which project file this body is written in, so a local callee is
    /// resolved there and a nested body in *its* file.
    pub fn with_file(mut self, file: &'a str) -> Self {
        self.file = file;
        self
    }

    /// Set the entry depth of nested bodies (recursion bound).
    pub fn with_depth_level(mut self, depth: u8) -> Self {
        self.depth_level = depth;
        self
    }

    fn callsite(&self, id: CallSiteId) -> Option<&CallSite> {
        self.callsites.iter().find(|c| c.id == id)
    }

    /// Evaluate a condition to a [`GuardVerdict`] under this profile.
    #[must_use]
    pub fn eval_condition(&self, condition: &ValueExpr) -> GuardVerdict {
        let mut gaps = Vec::new();
        self.eval_expr(condition, &self.env, None, &mut gaps, None)
            .truth(&self.profile)
            .into()
    }

    /// Abstract evaluation of an expression; unsupported operations become
    /// `Unknown` (their gaps are dropped here — use [`Self::eval_with_gaps`]).
    #[must_use]
    pub fn eval(&self, expr: &ValueExpr) -> AbstractValue {
        self.eval_with_gaps(expr).0
    }

    /// Evaluation that also reports the gaps (overflow, division by zero,
    /// unsupported operator). The span is left `None`; a caller that knows the
    /// source position should use [`Self::eval_at`].
    #[must_use]
    pub fn eval_with_gaps(&self, expr: &ValueExpr) -> (AbstractValue, Vec<AnalysisGap>) {
        let mut gaps = Vec::new();
        let value = self.eval_expr(expr, &self.env, None, &mut gaps, None);
        (value, gaps)
    }

    /// Evaluation anchored at a source span, so a recorded gap points at the
    /// construct that caused it.
    #[must_use]
    pub fn eval_at(&self, expr: &ValueExpr, span: Option<&SourceSpan>) -> (AbstractValue, Vec<AnalysisGap>) {
        let mut gaps = Vec::new();
        let value = self.eval_expr(expr, &self.env, None, &mut gaps, span);
        (value, gaps)
    }

    /// Evaluate an expression in an explicit environment/frame.
    fn eval_expr(
        &self,
        expr: &ValueExpr,
        env: &Env,
        frame: Option<&Frame>,
        gaps: &mut Vec<AnalysisGap>,
        span: Option<&SourceSpan>,
    ) -> AbstractValue {
        match expr {
            ValueExpr::Unknown => AbstractValue::Unknown,
            ValueExpr::Null => AbstractValue::Null,
            ValueExpr::Bool { value } => AbstractValue::Bool { value: *value },
            ValueExpr::Int { value } => AbstractValue::Int { value: *value },
            ValueExpr::Float { value } => AbstractValue::Float { value: *value },
            ValueExpr::Str { value } => AbstractValue::Str {
                value: value.clone(),
            },
            ValueExpr::Symbolic { name } => match frame.and_then(|f| f.names.get(name)) {
                // Callee parameters shadow the environment (closest scope wins).
                Some(value) => value.clone(),
                None => env.get(name).cloned().unwrap_or(AbstractValue::Unknown),
            },
            ValueExpr::Parameter { index } => match frame {
                Some(frame) => frame
                    .params
                    .get(*index as usize)
                    .cloned()
                    .unwrap_or(AbstractValue::Unknown),
                None => AbstractValue::Unknown,
            },
            // Heap values are not modeled: a field read is Unknown, not a guess.
            ValueExpr::Field { .. } => AbstractValue::Unknown,
            ValueExpr::Unary { op, operand } => {
                let v = self.eval_expr(operand, env, frame, gaps, span);
                match AbstractValue::unary(*op, &v, &self.profile) {
                    Ok(out) => out,
                    Err(reason) => {
                        gaps.push(gap(reason, span));
                        AbstractValue::Unknown
                    }
                }
            }
            ValueExpr::Binary { op, lhs, rhs } => {
                let l = self.eval_expr(lhs, env, frame, gaps, span);
                let r = self.eval_expr(rhs, env, frame, gaps, span);
                match AbstractValue::binary(*op, &l, &r, &self.profile) {
                    Ok(out) => out,
                    Err(reason) => {
                        gaps.push(gap(reason, span));
                        AbstractValue::Unknown
                    }
                }
            }
            ValueExpr::CallResult { callsite } => self.eval_callsite(*callsite, env, frame, gaps, span),
        }
    }

    fn eval_callsite(
        &self,
        id: CallSiteId,
        env: &Env,
        frame: Option<&Frame>,
        gaps: &mut Vec<AnalysisGap>,
        span: Option<&SourceSpan>,
    ) -> AbstractValue {
        let Some(cs) = self.callsite(id) else {
            gaps.push(gap("call_site_absent_from_ir", span));
            return AbstractValue::Unknown;
        };
        // Builtin semantics win (they cover library code outside the project).
        match lookup_builtin(cs.receiver.as_ref(), &cs.callee) {
            Some(Builtin::StrIsEmpty) => {
                let arg = cs
                    .args
                    .first()
                    .map(|a| self.eval_expr(a, env, frame, gaps, span));
                match arg {
                    Some(AbstractValue::Str { value }) => AbstractValue::bool(value.is_empty()),
                    // `StringUtils.isEmpty(null)` is `true`: the public Spring
                    // contract accepts an Object and tests both null and "".
                    Some(AbstractValue::Null) => AbstractValue::bool(true),
                    Some(AbstractValue::Unknown) | None => AbstractValue::Unknown,
                    Some(AbstractValue::Unreachable) => AbstractValue::Unreachable,
                    // `isEmpty` on a non-string is not a supported program.
                    Some(_) => AbstractValue::Unknown,
                }
            }
            Some(Builtin::StrEquals) => {
                let receiver = cs
                    .receiver
                    .as_ref()
                    .map(|r| self.eval_expr(r, env, frame, gaps, span));
                let arg = cs.args.first().map(|a| self.eval_expr(a, env, frame, gaps, span));
                match (receiver, arg) {
                    (Some(AbstractValue::Str { value: a }), Some(AbstractValue::Str { value: b })) => {
                        AbstractValue::bool(a == b)
                    }
                    (Some(AbstractValue::Unknown | AbstractValue::Unreachable), _)
                    | (_, Some(AbstractValue::Unknown | AbstractValue::Unreachable))
                    | (_, None) => AbstractValue::Unknown,
                    // Comparing a string to a non-string with `equals` is not
                    // a supported program: stay Unknown rather than guess.
                    _ => AbstractValue::Unknown,
                }
            }
            // No builtin: a JavaBeans accessor reads the property the handler
            // was bound to (`dto.getVerificationCode()`), provided the engine
            // seeded that property on this very receiver.
            None => match self.bound_accessor(cs, env) {
                Some(value) => value,
                None => self.eval_project_callee(cs, env, frame, gaps, span),
            },
        }
    }

    /// Resolve a JavaBeans accessor against a bound request property.
    ///
    /// The rule is the platform convention (`getX()`/`isX()` read property
    /// `x`), not a project fact. It fires only when the receiver is a symbolic
    /// name and the engine has seeded exactly `<receiver>.<property>`, so an
    /// unrelated `getPrice()` on a local variable cannot pick up a request
    /// field of the same name.
    fn bound_accessor(&self, cs: &CallSite, env: &Env) -> Option<AbstractValue> {
        if !self.profile.bean_accessors() {
            return None;
        }
        let property = crate::value::accessor_property(&cs.callee)?;
        let receiver = match cs.receiver.as_ref()? {
            ValueExpr::Symbolic { name } => name,
            _ => return None,
        };
        env.get(&format!("{receiver}.{property}")).cloned()
    }

    /// Summary-based evaluation of a project-local callee: bind actual
    /// arguments to the callee's parameter slots, evaluate its `return`
    /// expressions, and merge the possible set. The actual arguments are bound
    /// anew on every call, so a summary is never reused for other arguments.
    ///
    /// When a lowered *body* is available it wins: a flat `return` list cannot
    /// see a local assignment, a branch or a `throw`, so the callee is entered
    /// as its own ordered body and its completion is an explicit
    /// [`CallOutcome`].
    fn eval_project_callee(
        &self,
        cs: &CallSite,
        env: &Env,
        caller_frame: Option<&Frame>,
        gaps: &mut Vec<AnalysisGap>,
        span: Option<&SourceSpan>,
    ) -> AbstractValue {
        if let Some(targets) = self.targets {
            if let Some(body) = targets.body_of(self.file, &cs.callee, cs.args.len()) {
                return self
                    .eval_callee_body(cs, &body, env, caller_frame, gaps, span)
                    .value();
            }
        }
        let Some(resolver) = self.resolver else {
            return AbstractValue::Unknown;
        };
        let candidates = resolver.candidates(&cs.callee);
        match candidates.as_slice() {
            [] => {
                gaps.push(gap("callee_not_resolved", span));
                AbstractValue::Unknown
            }
            [callee] => {
                // No `return` in the callee: no value to propagate.
                if callee.returns.is_empty() {
                    return AbstractValue::Unknown;
                }
                let entered = self.depth.get();
                if entered >= MAX_DEPTH {
                    gaps.push(gap("recursion_depth_limit", span));
                    return AbstractValue::Unknown;
                }
                let args: Vec<AbstractValue> = cs
                    .args
                    .iter()
                    .map(|a| self.eval_expr(a, env, caller_frame, gaps, span))
                    .collect();
                self.depth.set(entered + 1);
                let mut names = BTreeMap::new();
                for (i, name) in callee.param_names.iter().enumerate() {
                    if let Some(value) = args.get(i) {
                        if !name.is_empty() {
                            names.insert(name.clone(), value.clone());
                        }
                    }
                }
                let frame = Frame {
                    params: args.clone(),
                    names,
                };
                let values: Vec<AbstractValue> = callee
                    .returns
                    .iter()
                    .map(|r| self.eval_expr(r, env, Some(&frame), gaps, span))
                    .collect();
                self.depth.set(entered);
                merge_returns(values)
            }
            // Ambiguous simple-name resolution: may-analysis does not guess.
            _ => {
                gaps.push(gap("callee_ambiguous", span));
                AbstractValue::Unknown
            }
        }
    }

    /// Enter a project-local callee *body* and summarize how it completes.
    ///
    /// The body is analyzed in its own file and its own call-site arena, with
    /// the actual arguments bound to the declared parameter names, so a local
    /// variable (`boolean ok = !StringUtils.isEmpty(code)`) is tracked and a
    /// `throw`-only body is not mistaken for one that returns.
    fn eval_callee_body(
        &self,
        cs: &CallSite,
        callee: &crate::invocation::CalleeBody<'_>,
        env: &Env,
        caller_frame: Option<&Frame>,
        gaps: &mut Vec<AnalysisGap>,
        span: Option<&SourceSpan>,
    ) -> CallOutcome {
        if self.depth_level >= MAX_DEPTH {
            gaps.push(gap("recursion_depth_limit", span));
            return CallOutcome::Cutoff;
        }
        let args: Vec<AbstractValue> = cs
            .args
            .iter()
            .map(|a| self.eval_expr(a, env, caller_frame, gaps, span))
            .collect();
        // An argument that already has no normal completion means the call is
        // never entered: it is not an unresolved body.
        if args.iter().any(AbstractValue::is_unreachable) {
            return CallOutcome::NoNormal;
        }
        let mut initial = Env::new();
        for (i, name) in callee.param_names.iter().enumerate() {
            if name.is_empty() {
                continue;
            }
            if let Some(ValueExpr::Symbolic { name: arg_name }) = cs.args.get(i) {
                // The object travels by handle: every property the caller bound
                // on the argument variable travels with it.
                let prefix = format!("{arg_name}.");
                for (key, value) in env.range(prefix.clone()..) {
                    let Some(field) = key.strip_prefix(&prefix) else {
                        break;
                    };
                    initial.insert(format!("{name}.{field}"), value.clone());
                }
            }
            match args.get(i) {
                Some(value) if !value.is_unknown() && !value.is_unreachable() => {
                    initial.insert(name.clone(), value.clone());
                }
                _ => {}
            }
        }
        let key = outcome_key(self.depth_level, callee.file, &cs.callee, cs.args.len(), &initial);
        let cached = self
            .cache
            .as_ref()
            .and_then(|c| c.borrow().get(&key).cloned());
        if let Some(hit) = cached {
            self.outcomes
                .borrow_mut()
                .entry(cs.id)
                .and_modify(|previous| *previous = previous.join(&hit))
                .or_insert_with(|| hit.clone());
            return hit;
        }
        let analysis = analyze_body_with(
            callee.body,
            initial,
            AnalyzeInputs {
                callsites: callee.callsites,
                // The flat resolver is file-agnostic; the body path prefers the
                // provider, and nested calls resolve in the callee's own file.
                resolver: self.resolver,
                targets: self.targets,
                file: callee.file,
                profile: callee.profile,
                depth: self.depth_level + 1,
                entry_certain: true,
                cache: self.cache.clone(),
            },
        );
        let outcome = if analysis.returns.is_empty() {
            // No reachable `return`. This is a proof of absence *only* if the
            // body's sweep converged: a widened loop, or a nested call the
            // analysis could not resolve, may have hidden the return, and a
            // budget must never turn a missing return into a proven exception.
            if analysis
                .gaps
                .iter()
                .any(|g| g.reason == crate::ir::GapReason::Widened)
            {
                CallOutcome::Cutoff
            } else {
                // Every path that leaves the body throws, or the body has no
                // reachable exit. Either way this call does not reach the
                // caller's normal continuation.
                CallOutcome::NoNormal
            }
        } else if analysis.returns.iter().any(|r| r.has_value) {
            let values: Vec<AbstractValue> =
                analysis.returns.iter().map(|r| r.value.clone()).collect();
            CallOutcome::Returns(merge_returns(values))
        } else {
            CallOutcome::Void
        };
        self.outcomes
            .borrow_mut()
            .entry(cs.id)
            .and_modify(|previous| *previous = previous.join(&outcome))
            .or_insert_with(|| outcome.clone());
        if let Some(cache) = &self.cache {
            cache.borrow_mut().insert(key, outcome.clone());
        }
        outcome
    }
}

/// The memo key of one callee-body entry: its identity, its depth, and the
/// whole value projection it is entered with. Two calls of one helper with
/// different arguments get different keys, so their summaries never merge.
fn outcome_key(depth: u8, file: &str, callee: &str, arity: usize, env: &Env) -> String {
    let mut key = String::with_capacity(file.len() + callee.len() + 16 * env.len() + 16);
    key.push('d');
    key.push_str(&depth.to_string());
    key.push('|');
    key.push_str(file);
    key.push('|');
    key.push_str(callee);
    key.push('|');
    key.push_str(&arity.to_string());
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

fn gap(reason: &str, span: Option<&SourceSpan>) -> AnalysisGap {
    let kind = match reason {
        "integer_overflow"
        | "floating_division_by_zero"
        | "integer_division_by_zero"
        | "integer_remainder_by_zero" => GapReason::Widened,
        "callee_not_resolved" | "callee_ambiguous" => GapReason::UnresolvedCall,
        _ => GapReason::UnsupportedExpression,
    };
    AnalysisGap::new(kind, reason.to_string(), span.cloned())
}

/// Merge the possible set of callee return values: a single value wins;
/// diverging or unknown results become `Unknown` (conservative).
fn merge_returns(values: Vec<AbstractValue>) -> AbstractValue {
    let mut iter = values.into_iter();
    let Some(first) = iter.next() else {
        return AbstractValue::Unknown;
    };
    if first.is_unknown() {
        return AbstractValue::Unknown;
    }
    for v in iter {
        if v != first {
            return AbstractValue::Unknown;
        }
    }
    first
}

// ---------------------------------------------------------------------------
// Whole-body analysis over the ordered CFG.
// ---------------------------------------------------------------------------

/// A `return` reached on some path.
///
/// `value` is the *join* of every visit to the block. `path` is the witness of
/// the visit that recorded the block first, and is emptied as soon as a later
/// visit changes the joined value: a single witness never describes a joined
/// result.
#[derive(Debug, Clone, PartialEq)]
pub struct ReturnSite {
    pub block: BlockId,
    pub value: AbstractValue,
    /// The `return` had an expression: `false` for a bare `return;`/`return` in
    /// a `void` method, which is what distinguishes a value-returning callee
    /// from a `void` one.
    pub has_value: bool,
    /// Guard decisions of the recording visit, as `g<id>:then|else`.
    pub path: Vec<String>,
    pub span: Option<SourceSpan>,
}

/// A `throw` reached on some path. Same join/witness rule as [`ReturnSite`].
#[derive(Debug, Clone, PartialEq)]
pub struct ThrowSite {
    pub block: BlockId,
    pub value: AbstractValue,
    pub path: Vec<String>,
}

/// A block whose own value computation has no normal completion: a statement
/// evaluated a call that provably never returns normally (R04).
///
/// The block's terminator is therefore never reached, and neither is its gap
/// content. The witness `path` says how the block was entered; a `gap:` label
/// or a tainted block makes the cut untrustworthy, exactly as for a guard.
#[derive(Debug, Clone, PartialEq)]
pub struct NoReturnSite {
    pub block: BlockId,
    pub path: Vec<String>,
}

/// The result of analyzing one body: what it may execute, what it may return,
/// and what it could not decide.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct BodyAnalysis {
    pub function: Option<FunctionId>,
    /// Blocks reached on at least one path, in body order.
    pub reached_blocks: Vec<BlockId>,
    /// Blocks reached only through an unmodeled mechanism (a lowering gap),
    /// whose witness path carries a `gap:` label. A proof computed inside such
    /// a block is not a proof about the program text: the construct the
    /// frontend could not lower may have changed the values it was made from.
    pub tainted_blocks: Vec<BlockId>,
    /// Return alternatives, in block order.
    pub returns: Vec<ReturnSite>,
    pub throws: Vec<ThrowSite>,
    /// Reachable effects with their evidence.
    pub effects: Vec<(Effect, Evidence)>,
    /// Every branch the analysis had to decide, with the verdict it reached
    /// and the witness path that reached it. This is what turns "the remote
    /// call is absent" into "the guard was proved false on this path".
    pub decisions: Vec<GuardDecision>,
    /// The actual arguments of each reached call site, evaluated in the
    /// environment of the block that performs the call. This is what a callee
    /// must be entered with: the value the caller's variable *had at the call*,
    /// not the value it has at the entry of the method.
    pub observations: BTreeMap<(BlockId, CallSiteId), CallObservation>,
    /// The explicit outcome of each reached project-local call of *this* body,
    /// keyed by the call's result slot. A call whose callee body was available
    /// is present here; a library call or an unresolved name is not, and its
    /// absence is never a proof of absence.
    pub call_outcomes: BTreeMap<CallSiteId, CallOutcome>,
    /// Blocks whose own value computation provably has no normal completion
    /// (R04), with the witness path that reached each. A block here is an
    /// *exclusion certificate* for everything it dominates: the call it made
    /// never returns, so neither does the rest of the block nor its successors.
    pub no_return_blocks: Vec<NoReturnSite>,
    /// Everything the analysis could not decide.
    pub gaps: Vec<AnalysisGap>,
}

/// The values a call site was reached with.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CallObservation {
    /// The block-local environment at the call (parameters, locals, heap
    /// properties known by name).
    pub env: Env,
    /// Received value, when the call has a receiver expression.
    pub receiver: Option<AbstractValue>,
    /// Argument values, in declared order.
    pub args: Vec<AbstractValue>,
}

impl CallObservation {
    /// Join two visits to the same call site: a value they disagree on becomes
    /// `Unknown`. Order-independent and monotone.
    #[must_use]
    pub fn join(&self, other: &Self) -> Self {
        Self {
            env: join_env(&self.env, &other.env),
            receiver: match (&self.receiver, &other.receiver) {
                (Some(a), Some(b)) => Some(a.join(b)),
                _ => None,
            },
            args: if self.args.len() == other.args.len() {
                self.args
                    .iter()
                    .zip(&other.args)
                    .map(|(a, b)| a.join(b))
                    .collect()
            } else {
                Vec::new()
            },
        }
    }
}

/// Reasons whose construct may have *changed* a tracked binding: the normal
/// continuation of such a gap cannot be trusted to carry the values the text
/// appears to set. A pure value gap (`new Foo()`) or a value-position gap
/// whose sub-expressions were lowered in order is not in this set.
fn mutates_state(reason: GapReason) -> bool {
    matches!(
        reason,
        GapReason::UnsupportedStatement | GapReason::UnsupportedExpression | GapReason::Widened
    )
}

/// One guard decision with its witness path.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GuardDecision {
    pub guard: GuardId,
    pub block: BlockId,
    /// Join of every visit's verdict: two visits that disagree leave `Unknown`.
    pub verdict: crate::cfg::GuardVerdict,
    /// Symbols the condition reads, so the decision can be attributed to a
    /// bound request field.
    pub symbols: Vec<String>,
    /// Witness path labels of the recording visit (`g0:then`); empty once the
    /// joined verdict stopped being the recording visit's verdict.
    pub path: Vec<String>,
}

/// Bound on the number of work-list passes; beyond it remaining bindings are
/// widened to `Unknown` and a [`GapReason::Widened`] gap is recorded.
const SWEEP_LIMIT: usize = 64;

/// Prefix of a witness-path label that marks a path reached through a lowering
/// gap: the construct the frontend could not lower may have changed the values
/// the path carries.
const GAP_LABEL: &str = "gap:";

/// A function body with its unmodeled content indexed by the block that owns
/// it. Built once per analysis and handed to every block visit.
struct BodyFacts<'a> {
    body: &'a FunctionBody,
    /// Gap content, keyed by the block whose normal continuation runs
    /// alongside it.
    gap_content: BTreeMap<BlockId, Vec<(GapReason, BlockId)>>,
}

impl BodyFacts<'_> {
    fn content_of(&self, block: BlockId) -> &[(GapReason, BlockId)] {
        self.gap_content.get(&block).map_or(&[][..], Vec::as_slice)
    }
}

/// Memo of callee-body outcomes, keyed by identity, bound arguments and depth.
///
/// One nested body can be entered from many call sites of one analysis; without
/// the memo a project whose bodies call each other would re-enter the same body
/// once per path and thrash. The key is the *whole* input projection — the
/// callee's file, name, the bound parameter and property values, and the entry
/// depth — so a summary is never reused for different arguments, which is what
/// keeps two calls of one helper independent.
pub type OutcomeCache = Rc<std::cell::RefCell<BTreeMap<String, CallOutcome>>>;

/// Tunable inputs of one body analysis (R04).
#[derive(Clone)]
pub struct AnalyzeInputs<'a> {
    /// The file's call-site arena.
    pub callsites: &'a [CallSite],
    /// Flat-summary resolver. Ignored when `targets` resolves the callee body.
    pub resolver: Option<&'a dyn CallResolver>,
    /// Project-local callee bodies, entered as their own ordered bodies.
    pub targets: Option<&'a dyn CallTargetProvider>,
    /// Project-relative file of *this* body: a local callee is resolved here.
    pub file: &'a str,
    pub profile: LanguageProfile,
    /// Entry depth of nested bodies.
    pub depth: u8,
    /// `true` when the body is entered unconditionally. A body reached only
    /// through a possible call is entered `false`: every effect in it is then
    /// `Possible`, never `Confirmed`, so a conditional caller cannot make its
    /// callee's remote call unconditionally confirmed.
    pub entry_certain: bool,
    /// The summary memo shared by a whole top-level analysis and every body it
    /// enters. `None` disables sharing (each body is entered once).
    pub cache: Option<OutcomeCache>,
}

impl<'a> AnalyzeInputs<'a> {
    /// The defaults of [`analyze_body`]: no callee bodies, entry certain.
    #[must_use]
    pub fn new(callsites: &'a [CallSite], profile: LanguageProfile) -> Self {
        Self {
            callsites,
            resolver: None,
            targets: None,
            file: "",
            profile,
            depth: 0,
            entry_certain: true,
            cache: Some(Rc::new(std::cell::RefCell::new(BTreeMap::new()))),
        }
    }
}

/// Analyze a lowered body.
///
/// `initial` binds the function's parameters (by name) and any scenario
/// knowledge; `callsites` is the file's call-site arena. The analysis is a
/// may-analysis: a block reached on some path contributes `Possible` effects,
/// a block reached without any branch decision contributes `Confirmed` ones.
///
/// This is [`analyze_body_with`] with the flat-summary inputs: no callee bodies
/// are entered and the entry is certain.
#[must_use]
pub fn analyze_body(
    body: &FunctionBody,
    initial: Env,
    callsites: &[CallSite],
    resolver: Option<&dyn CallResolver>,
    profile: LanguageProfile,
) -> BodyAnalysis {
    let mut inputs = AnalyzeInputs::new(callsites, profile);
    inputs.resolver = resolver;
    analyze_body_with(body, initial, inputs)
}

/// Analyze a lowered body with explicit inputs (R04/R05).
#[must_use]
pub fn analyze_body_with(
    body: &FunctionBody,
    initial: Env,
    inputs: AnalyzeInputs<'_>,
) -> BodyAnalysis {
    let mut analyzer = Analyzer::new(initial.clone(), inputs.callsites)
        .with_profile(inputs.profile)
        .with_file(inputs.file)
        .with_depth_level(inputs.depth);
    analyzer.resolver = inputs.resolver;
    analyzer.targets = inputs.targets;
    analyzer.cache = inputs.cache.clone();

    let blocks: BTreeMap<BlockId, &crate::ir::BasicBlock> =
        body.blocks.iter().map(|b| (b.id, b)).collect();

    // Joined input environment and the witness path for every reachable block.
    let mut input: BTreeMap<BlockId, Env> = BTreeMap::new();
    let mut path: BTreeMap<BlockId, Vec<String>> = BTreeMap::new();
    // Blocks reached on at least one path that required a branch decision. A
    // block can be visited first through a certain path (a loop body on its
    // first iteration) and later through an uncertain one, so uncertainty is
    // tracked separately from the witness path and never cleared.
    let mut uncertain: BTreeSet<BlockId> = BTreeSet::new();
    // A body entered only through a possible call is uncertain from its first
    // block: nothing in it can be `Confirmed` on the caller's premises.
    if !inputs.entry_certain {
        uncertain.insert(body.entry);
    }
    // Property validity, joined structurally and never derived from a single
    // witness. A block is *tainted* when some reaching path went through an
    // unmodeled construct that may have changed the values the block's text
    // appears to set. The witness `path` map keeps only the first visit, so it
    // must never be the certificate: a clean first visit followed by a tainted
    // second one leaves the block tainted. Like `uncertain`, this set only
    // grows, so its growth terminates.
    let mut tainted: BTreeSet<BlockId> = BTreeSet::new();
    // Effects/returns are collected once per (block, callsite) and per block.
    let mut records = Records {
        gaps: body.gaps.clone(),
        ..Records::default()
    };

    input.insert(body.entry, initial.clone());
    path.insert(body.entry, Vec::new());
    // A gap's *content* is not reachable from nowhere: it is a may-path out of
    // the block the construct appears in (`owner`). Index it by owner so the
    // sweep can extend that block's successors — a gap inside a dead arm stays
    // dead, and a gap on a live path is reached with that path's environment,
    // under a `gap:` witness that keeps its own proofs from being trusted.
    let mut gap_content: BTreeMap<BlockId, Vec<(GapReason, BlockId)>> = BTreeMap::new();
    for g in &body.gaps {
        if let (Some(owner), Some(content)) = (g.owner, g.block) {
            gap_content
                .entry(owner)
                .or_default()
                .push((g.reason, content));
        }
    }
    let facts = BodyFacts { body, gap_content };

    let order: Vec<BlockId> = body.blocks.iter().map(|b| b.id).collect();
    let mut widened = false;
    for sweep in 0..SWEEP_LIMIT {
        let mut changed = false;
        for id in &order {
            let Some(env) = input.get(id).cloned() else {
                continue;
            };
            let Some(block) = blocks.get(id).copied() else {
                continue;
            };
            let here = path.get(id).cloned().unwrap_or_default();
            let unconditional = !uncertain.contains(id);
            let here_tainted = tainted.contains(id);
            let nexts = run_block(
                &analyzer,
                &facts,
                block,
                &env,
                &here,
                &mut records,
                unconditional,
            );
            // The gap content is a may-path out of this block: if this block is
            // already tainted, everything it may reach is too.
            if here_tainted {
                for (_, content) in facts.content_of(*id) {
                    if tainted.insert(*content) {
                        changed = true;
                    }
                }
            }
            for success in nexts {
                // An edge that appended a guard decision is uncertain; so is
                // any edge leaving an already uncertain block.
                if (!unconditional || success.path.len() > here.len())
                    && uncertain.insert(success.block)
                {
                    // New uncertainty is a summary change in its own right: the
                    // exits and decisions already recorded for that block were
                    // computed under `Confirmed` evidence and must be re-joined
                    // under the weaker one. `uncertain` only grows, so this
                    // cannot loop.
                    changed = true;
                }
                // Prove-validity is a join over *every* reaching path: a single
                // clean witness cannot certify a block another path taints.
                let step_tainted = here_tainted
                    || success
                        .path
                        .iter()
                        .any(|l| l.starts_with(GAP_LABEL));
                if step_tainted && tainted.insert(success.block) {
                    changed = true;
                }
                match input.get_mut(&success.block) {
                    None => {
                        input.insert(success.block, success.env);
                        path.insert(success.block, success.path);
                        changed = true;
                    }
                    Some(old) => {
                        let joined = join_env(old, &success.env);
                        if joined != *old {
                            *old = joined;
                            changed = true;
                        }
                    }
                }
            }
        }
        if !changed {
            break;
        }
        if sweep == SWEEP_LIMIT - 1 {
            // Did not converge (a loop is generating fresh values): widen every
            // tracked binding to `Unknown` rather than guessing, and say so.
            widened = true;
            for env in input.values_mut() {
                for value in env.values_mut() {
                    *value = AbstractValue::Unknown;
                }
            }
        }
    }
    if widened {
        records.gaps.push(AnalysisGap::new(
            GapReason::Widened,
            format!("body did not converge within {SWEEP_LIMIT} passes; bindings widened"),
            None,
        ));
    }

    let mut reached_blocks: Vec<BlockId> = order
        .iter()
        .copied()
        .filter(|id| input.contains_key(id))
        .collect();
    reached_blocks.sort();
    reached_blocks.dedup();

    let mut tainted_blocks: Vec<BlockId> = order
        .iter()
        .copied()
        .filter(|id| tainted.contains(id))
        .collect();
    tainted_blocks.sort();
    tainted_blocks.dedup();

    let mut effect_list: Vec<(Effect, Evidence)> = records.effects.into_values().collect();
    effect_list.sort_by(|a, b| {
        let ka = effect_key(&a.0);
        let kb = effect_key(&b.0);
        ka.cmp(&kb).then_with(|| a.1.reason.cmp(&b.1.reason))
    });
    let mut return_list: Vec<ReturnSite> = records.returns.into_values().collect();
    return_list.sort_by_key(|r| r.block);
    let mut throw_list: Vec<ThrowSite> = records.throws.into_values().collect();
    throw_list.sort_by_key(|t| t.block);

    let mut decision_list: Vec<GuardDecision> = records.decisions.into_values().collect();
    decision_list.sort_by_key(|d| d.block);

    let call_outcomes = analyzer.outcomes.borrow().clone();
    let no_return_blocks: Vec<NoReturnSite> = records
        .no_return
        .into_iter()
        .map(|(block, path)| NoReturnSite { block, path })
        .collect();

    BodyAnalysis {
        function: Some(body.function),
        reached_blocks,
        tainted_blocks,
        returns: return_list,
        throws: throw_list,
        effects: effect_list,
        decisions: decision_list,
        observations: records.observations,
        call_outcomes,
        no_return_blocks,
        gaps: records.gaps,
    }
}

fn effect_key(effect: &Effect) -> (u8, String) {
    match effect {
        Effect::LocalCall { callsite, .. } => (0, format!("{}", callsite.raw())),
        Effect::DataRead { table, .. } => (1, table.clone().unwrap_or_default()),
        Effect::DataWrite { table, .. } => (2, table.clone().unwrap_or_default()),
        Effect::HttpCall { url } => (3, url.clone()),
        Effect::GrpcCall { service, method } => (4, format!("{service}#{method}")),
        Effect::MessagePublish { channel } => (5, channel.clone()),
        Effect::MessageConsume { channel } => (6, channel.clone()),
        Effect::StateMutation { target } => (7, target.clone()),
    }
}

/// Everything the sweep accumulates while walking the blocks.
#[derive(Default)]
struct Records {
    /// One entry per (block, call site), so a call reached on several paths is
    /// recorded once with its weakest evidence.
    effects: BTreeMap<(BlockId, CallSiteId), (Effect, Evidence)>,
    /// The values each reached call site was called with, joined over the
    /// visits to that (block, call site).
    observations: BTreeMap<(BlockId, CallSiteId), CallObservation>,
    /// The return value of a block, keyed by block: a block's return
    /// alternatives are merged into one value.
    returns: BTreeMap<BlockId, ReturnSite>,
    throws: BTreeMap<BlockId, ThrowSite>,
    gaps: Vec<AnalysisGap>,
    /// Guard decisions keyed by block: a loop re-visit must not duplicate a
    /// decision already recorded for that block.
    decisions: BTreeMap<BlockId, GuardDecision>,
    /// Blocks whose own value computation had no normal completion (R04), with
    /// the witness path that reached them. A re-visit keeps the first witness:
    /// the cut is a property of the block, not of one visit.
    no_return: BTreeMap<BlockId, Vec<String>>,
}

/// One successor edge out of a block, with the environment and witness path
/// that reach it.
struct Successor {
    block: BlockId,
    env: Env,
    path: Vec<String>,
}

/// Execute one block under `env`: record effects/returns, and return the
/// successor edges.
fn run_block(
    analyzer: &Analyzer<'_>,
    facts: &BodyFacts<'_>,
    block: &crate::ir::BasicBlock,
    env: &Env,
    here: &[String],
    records: &mut Records,
    unconditional: bool,
) -> Vec<Successor> {
    let body = facts.body;
    let gap_content = facts.content_of(block.id);
    let mut local = env.clone();
    let mut seen: BTreeSet<CallSiteId> = BTreeSet::new();
    let span = block.span;
    let reason = if unconditional {
        "unconditional_path".to_owned()
    } else {
        format!("path:{}", here.join(","))
    };
    let status = if unconditional {
        EvidenceStatus::Confirmed
    } else {
        EvidenceStatus::Possible
    };

    let mut diverged = false;
    for statement in &block.statements {
        let value = match statement {
            Statement::Assign { target, value } => {
                let v = analyzer.eval_expr_pub(value, &local, None, &mut records.gaps, span.as_ref());
                if v.is_unreachable() {
                    diverged = true;
                }
                apply_assign(&mut local, target, v);
                Some(value)
            }
            Statement::Eval { value } => {
                // The call's own result slot: evaluating it is what turns a
                // callee that never returns normally into a cut path.
                let v = analyzer.eval_expr_pub(value, &local, None, &mut records.gaps, span.as_ref());
                if v.is_unreachable() {
                    diverged = true;
                }
                Some(value)
            }
            Statement::Unsupported { reason, detail } => {
                records.gaps.push(AnalysisGap::new(*reason, detail.clone(), span));
                None
            }
        };
        if let Some(value) = value {
            for cs in callsites_of(value) {
                if seen.insert(cs) {
                    record_effect(analyzer, cs, block.id, status, &reason, &local, records);
                }
            }
        }
        if diverged {
            // Nothing after the diverging statement runs, not even the rest of
            // this block's statements: their effects must not be recorded, or a
            // later call in the same block would look reached.
            break;
        }
    }
    if diverged {
        // The block's own value computation has no normal completion (a call to
        // a body that never returns): nothing after it in this block runs, and
        // neither the terminator nor this block's gap content.
        records.no_return.entry(block.id).or_insert_with(|| here.to_vec());
        return Vec::new();
    }

    let mut nexts: Vec<Successor> = Vec::new();
    // The environment the unmodeled content is reached with: this block's
    // values, cloned because the terminator below moves `local`.
    let may_env = local.clone();
    match &block.terminator {
        Terminator::Goto { next } => nexts.push(Successor {
            block: *next,
            env: local,
            path: here.to_vec(),
        }),
        Terminator::Branch {
            guard,
            condition,
            then_block,
            else_block,
        } => {
            let condition_value =
                analyzer.eval_expr_pub(condition, &local, None, &mut records.gaps, span.as_ref());
            if condition_value.is_unreachable() {
                // The guard expression itself has no normal completion: the
                // branch is never reached, so it decides nothing and this
                // block's gap content does not run either.
                return Vec::new();
            }
            let verdict: GuardVerdict = condition_value.truth(&analyzer.profile).into();
            for cs in callsites_of(condition) {
                if seen.insert(cs) {
                    record_effect(analyzer, cs, block.id, status, &reason, &local, records);
                }
            }
            let label = guard_label(*guard, body);
            let symbols = guard_symbols(condition, analyzer.callsites);
            records
                .decisions
                .entry(block.id)
                .and_modify(|previous| {
                    // A block can be entered on several paths. The recorded
                    // verdict is the *join* of all of them: two visits that
                    // disagree leave no decision, never the first visit's
                    // provisional truth.
                    if previous.verdict != verdict {
                        previous.verdict = GuardVerdict::Unknown;
                        // One witness path cannot describe a joined verdict.
                        previous.path.clear();
                    }
                    for s in &symbols {
                        if !previous.symbols.contains(s) {
                            previous.symbols.push(s.clone());
                        }
                    }
                    previous.symbols.sort();
                })
                .or_insert_with(|| GuardDecision {
                    guard: *guard,
                    block: block.id,
                    verdict,
                    symbols,
                    path: here.to_vec(),
                });
            match verdict {
                GuardVerdict::ProvesTrue => nexts.push(Successor {
                    block: *then_block,
                    env: local,
                    path: here.to_vec(),
                }),
                GuardVerdict::ProvesFalse => nexts.push(Successor {
                    block: *else_block,
                    env: local,
                    path: here.to_vec(),
                }),
                GuardVerdict::Unknown => {
                    for (block_id, arm) in [(then_block, "then"), (else_block, "else")] {
                        let mut step = here.to_vec();
                        step.push(format!("{label}:{arm}"));
                        nexts.push(Successor {
                            block: *block_id,
                            env: local.clone(),
                            path: step,
                        });
                    }
                }
            }
        }
        Terminator::Return { value } => {
            let v = value.as_ref().map_or(AbstractValue::Unknown, |e| {
                analyzer.eval_expr_pub(e, &local, None, &mut records.gaps, span.as_ref())
            });
            if let Some(e) = value {
                for cs in callsites_of(e) {
                    if seen.insert(cs) {
                        record_effect(analyzer, cs, block.id, status, &reason, &local, records);
                    }
                }
            }
            if v.is_unreachable() {
                // `return f()` where `f` never returns normally: the return is
                // never reached, so it is not a return alternative.
                return Vec::new();
            }
            let has_value = value.is_some();
            records
                .returns
                .entry(block.id)
                .and_modify(|previous| {
                    // The exit value is the join of every visit; the first
                    // visit's value is only an approximation.
                    previous.has_value |= has_value;
                    let joined = previous.value.join(&v);
                    if joined != previous.value {
                        previous.value = joined;
                        // No single witness certifies a joined value.
                        previous.path.clear();
                    }
                })
                .or_insert_with(|| ReturnSite {
                    block: block.id,
                    value: v,
                    has_value,
                    path: here.to_vec(),
                    span: block.span,
                });
        }
        Terminator::Throw { value } => {
            let v = analyzer.eval_expr_pub(value, &local, None, &mut records.gaps, span.as_ref());
            for cs in callsites_of(value) {
                if seen.insert(cs) {
                    record_effect(analyzer, cs, block.id, status, &reason, &local, records);
                }
            }
            if v.is_unreachable() {
                return Vec::new();
            }
            records
                .throws
                .entry(block.id)
                .and_modify(|previous| {
                    let joined = previous.value.join(&v);
                    if joined != previous.value {
                        previous.value = joined;
                        previous.path.clear();
                    }
                })
                .or_insert_with(|| ThrowSite {
                    block: block.id,
                    value: v,
                    path: here.to_vec(),
                });
        }
        Terminator::Unreachable => {}
        Terminator::Gap { next, reason, .. } => {
            if let Some(next) = next {
                // The construct was not lowered: whatever it does to the
                // values the text appears to set is unknown, so the normal
                // continuation is reached with a taint that keeps its proofs
                // from being trusted. A pure value gap (an allocation, a call
                // whose return is unmodeled) does not change a tracked binding
                // and keeps the continuation clean.
                let mut step = here.to_vec();
                if mutates_state(*reason) {
                    step.push(format!("{GAP_LABEL}{reason:?}"));
                }
                nexts.push(Successor {
                    block: *next,
                    env: local,
                    path: step,
                });
            }
        }
    }
    // The construct's own content may run through the unmodeled mechanism: it
    // is a may-path out of *this* block, reached with this block's environment
    // and a witness that keeps decisions made inside it from being trusted.
    for (reason, content) in gap_content {
        let mut step = here.to_vec();
        step.push(format!("{GAP_LABEL}{reason:?}"));
        nexts.push(Successor {
            block: *content,
            env: may_env.clone(),
            path: step,
        });
    }
    nexts
}

/// Apply an assignment to the block-local environment.
///
/// Three cases, and none of them may leave a *stale* property readable:
///
/// * a scalar/object binding (`x = v`): the old object's heap properties are
///   not inherited by the new value, so every `<x>.<field>` fact is dropped
///   before the binding is replaced;
/// * a known field write (`dto.field = v`): the property is modeled directly
///   when the receiver is a symbolic handle, so a later accessor reads the
///   written value;
/// * a field write on an unknown receiver: the property name may be stale for
///   *any* handle, so every cached `.<field>` suffix is invalidated. Modelling
///   the whole heap is out of scope; keeping a wrong known constant is not.
fn apply_assign(env: &mut Env, target: &ValueExpr, value: AbstractValue) {
    match target {
        ValueExpr::Symbolic { name } => {
            invalidate_properties(env, name);
            env.insert(name.clone(), value);
        }
        ValueExpr::Field { base, name } => match base.as_ref() {
            ValueExpr::Symbolic { name: receiver } => {
                env.insert(format!("{receiver}.{name}"), value);
            }
            _ => {
                let suffix = format!(".{name}");
                env.retain(|key, _| !key.ends_with(&suffix));
            }
        },
        _ => {}
    }
}

/// Drop every cached property of the object bound to `name`.
fn invalidate_properties(env: &mut Env, name: &str) {
    let prefix = format!("{name}.");
    env.retain(|key, _| !key.starts_with(&prefix));
}

fn guard_label(guard: GuardId, body: &FunctionBody) -> String {
    body.guards
        .iter()
        .position(|g| g.id == guard)
        .map_or_else(|| format!("g{}", guard.raw()), |i| format!("g{i}"))
}

fn record_effect(
    analyzer: &Analyzer<'_>,
    cs: CallSiteId,
    block: BlockId,
    status: EvidenceStatus,
    reason: &str,
    env: &Env,
    records: &mut Records,
) {
    let callee = analyzer
        .callsite(cs)
        .map_or_else(String::new, |c| c.callee.clone());
    let evidence = Evidence {
        status,
        reason: reason.to_owned(),
    };
    observe(analyzer, cs, block, env, &mut records.observations);
    // A block can be reached on several paths, and the work list may visit it
    // first through the certain one (a loop body on the first iteration, say).
    // Evidence may only get *weaker* on re-visit: if any reaching path is
    // uncertain, the effect is `Possible`, never upgraded back to `Confirmed`.
    let effects = &mut records.effects;
    let entry = effects.entry((block, cs));
    match entry {
        std::collections::btree_map::Entry::Occupied(mut occupied) => {
            let existing = &mut occupied.get_mut().1;
            if existing.status == EvidenceStatus::Confirmed
                && status != EvidenceStatus::Confirmed
            {
                *existing = evidence;
            }
        }
        std::collections::btree_map::Entry::Vacant(vacant) => {
            vacant.insert((Effect::LocalCall { callsite: cs, callee }, evidence));
        }
    }
}

/// Record the values one call site was reached with, joined over the visits to
/// that `(block, call site)`.
///
/// The environment is the *block-local* one: a scalar local
/// (`String code = dto.getVerificationCode(); helper(code);`) arrives with the
/// value the variable had at the call, which is what the callee must be
/// entered with. A call reached twice is entered with the join of both visits.
fn observe(
    analyzer: &Analyzer<'_>,
    cs: CallSiteId,
    block: BlockId,
    env: &Env,
    observations: &mut BTreeMap<(BlockId, CallSiteId), CallObservation>,
) {
    let Some(callsite) = analyzer.callsite(cs) else {
        return;
    };
    let mut scratch: Vec<AnalysisGap> = Vec::new();
    let receiver = callsite
        .receiver
        .as_ref()
        .map(|r| analyzer.eval_expr_pub(r, env, None, &mut scratch, None));
    let args: Vec<AbstractValue> = callsite
        .args
        .iter()
        .map(|a| analyzer.eval_expr_pub(a, env, None, &mut scratch, None))
        .collect();
    match observations.entry((block, cs)) {
        std::collections::btree_map::Entry::Vacant(vacant) => {
            vacant.insert(CallObservation {
                env: env.clone(),
                receiver,
                args,
            });
        }
        std::collections::btree_map::Entry::Occupied(mut occupied) => {
            let visit = CallObservation {
                env: env.clone(),
                receiver,
                args,
            };
            let joined = occupied.get().join(&visit);
            *occupied.get_mut() = joined;
        }
    }
}

/// Names a guard condition reads: symbolic identifiers and the callees whose
/// results it tests. Used to attribute a decision to a bound request field.
fn guard_symbols(expr: &ValueExpr, callsites: &[CallSite]) -> Vec<String> {
    let mut out: BTreeSet<String> = BTreeSet::new();
    collect_symbols(expr, callsites, &mut out);
    out.into_iter().collect()
}

fn collect_symbols(expr: &ValueExpr, callsites: &[CallSite], out: &mut BTreeSet<String>) {
    match expr {
        ValueExpr::Symbolic { name } => {
            out.insert(name.clone());
        }
        ValueExpr::Field { base, .. } => collect_symbols(base, callsites, out),
        // A guard usually tests a *call result* (`!StringUtils.isEmpty(code)`):
        // the names it reads are the call's receiver and arguments, which is
        // what ties the decision to a bound request field.
        ValueExpr::CallResult { callsite } => {
            if let Some(cs) = callsites.iter().find(|c| c.id == *callsite) {
                if let Some(receiver) = &cs.receiver {
                    collect_symbols(receiver, callsites, out);
                }
                for arg in &cs.args {
                    collect_symbols(arg, callsites, out);
                }
            }
        }
        ValueExpr::Unknown | ValueExpr::Null | ValueExpr::Bool { .. } | ValueExpr::Int { .. }
        | ValueExpr::Float { .. } | ValueExpr::Str { .. } | ValueExpr::Parameter { .. } => {}
        ValueExpr::Unary { operand, .. } => collect_symbols(operand, callsites, out),
        ValueExpr::Binary { lhs, rhs, .. } => {
            collect_symbols(lhs, callsites, out);
            collect_symbols(rhs, callsites, out);
        }
    }
}

/// Every call site referenced by a value expression, in source order.
///
/// A caller uses this to place a call site in its basic block: the certificate
/// behind a dropped edge is about the site's own block.
#[must_use]
pub fn callsites_of(expr: &ValueExpr) -> Vec<CallSiteId> {
    let mut out = Vec::new();
    collect_callsites(expr, &mut out);
    out
}

fn collect_callsites(expr: &ValueExpr, out: &mut Vec<CallSiteId>) {
    match expr {
        ValueExpr::Unknown
        | ValueExpr::Null
        | ValueExpr::Bool { .. }
        | ValueExpr::Int { .. }
        | ValueExpr::Float { .. }
        | ValueExpr::Str { .. }
        | ValueExpr::Symbolic { .. }
        | ValueExpr::Parameter { .. } => {}
        ValueExpr::Field { base, .. } => collect_callsites(base, out),
        ValueExpr::Unary { operand, .. } => collect_callsites(operand, out),
        ValueExpr::Binary { lhs, rhs, .. } => {
            collect_callsites(lhs, out);
            collect_callsites(rhs, out);
        }
        ValueExpr::CallResult { callsite } => out.push(*callsite),
    }
}

/// Join two environments at a merge point. A name absent on either side has no
/// information on that side, so the join is `Unknown`.
#[must_use]
pub fn join_env(a: &Env, b: &Env) -> Env {
    let mut out = Env::new();
    for (k, v) in b {
        match a.get(k) {
            Some(old) => {
                out.insert(k.clone(), old.join(v));
            }
            None => {
                out.insert(k.clone(), AbstractValue::Unknown);
            }
        }
    }
    for k in a.keys() {
        if !b.contains_key(k) {
            out.insert(k.clone(), AbstractValue::Unknown);
        }
    }
    out
}

impl Analyzer<'_> {
    /// Public entry to expression evaluation in an explicit environment, used
    /// by the body analysis.
    fn eval_expr_pub(
        &self,
        expr: &ValueExpr,
        env: &Env,
        frame: Option<&Frame>,
        gaps: &mut Vec<AnalysisGap>,
        span: Option<&SourceSpan>,
    ) -> AbstractValue {
        self.eval_expr(expr, env, frame, gaps, span)
    }
}
