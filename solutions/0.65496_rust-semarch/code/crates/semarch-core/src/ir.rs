//! Common Semantic IR (v0).
//!
//! Core types contain no Tree-sitter AST nodes; frontends normalize semantic
//! facts into these structures. Every semantic element that can become an
//! edge carries evidence with a status: `confirmed | possible | excluded |
//! unresolved`. `unknown != false` is enforced by making exclusions explicit
//! [`Evidence`] records rather than absence of data.

use serde::{Deserialize, Serialize};

use crate::ids::{BlockId, CallSiteId, FunctionId, GuardId, ResourceId};
use crate::span::SourceSpan;

/// Kind of a named declaration.
#[derive(
    Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub enum SymbolKind {
    Module,
    Class,
    Interface,
    Enum,
    Function,
    Method,
    Field,
    Parameter,
    Variable,
}

/// Abstract value expression, v0. Deliberately not an SMT engine: `Unknown`
/// is a first-class citizen (`unknown != false`).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum ValueExpr {
    /// No information. Must never be treated as `Bool(false)`.
    Unknown,
    Null,
    Bool {
        value: bool,
    },
    Int {
        value: i64,
    },
    Float {
        value: f64,
    },
    Str {
        value: String,
    },
    /// A named symbol (identifier) whose value is tracked symbolically.
    Symbolic {
        name: String,
    },
    Parameter {
        index: u16,
    },
    Field {
        base: Box<ValueExpr>,
        name: String,
    },
    Unary {
        op: UnaryOp,
        operand: Box<ValueExpr>,
    },
    Binary {
        op: BinaryOp,
        lhs: Box<ValueExpr>,
        rhs: Box<ValueExpr>,
    },
    /// Result of a call site (e.g. `verifyCode` return value).
    CallResult {
        callsite: CallSiteId,
    },
}

impl ValueExpr {
    /// Convenience constructor for a named symbol.
    #[must_use]
    pub fn symbolic(name: impl Into<String>) -> Self {
        Self::Symbolic { name: name.into() }
    }
    /// Convenience constructor for a string literal.
    #[must_use]
    pub fn str_val(value: impl Into<String>) -> Self {
        Self::Str { value: value.into() }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum UnaryOp {
    Not,
    Negate,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BinaryOp {
    Eq,
    Ne,
    Lt,
    Le,
    Gt,
    Ge,
    And,
    Or,
    Add,
    Sub,
    Mul,
    Div,
    Rem,
}

/// Evidence status of a derived semantic fact.
#[derive(
    Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceStatus {
    /// Proven by a concrete rule (call edge, direct literal, ..).
    Confirmed,
    /// Plausible under some branch/resolution, not proven.
    Possible,
    /// Proven *not* to happen (guard evaluates to false on a concrete path,
    /// literal comparison, dead wiring). An exclusion is always explicit.
    Excluded,
    /// Could not be decided (unknown callee, dynamic dispatch, missing
    /// seed data).
    Unresolved,
}

/// Why a fact holds / does not hold. `reason` is a short human-readable
/// rule identifier plus anchor; it must be reproducible, never fabricated.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub struct Evidence {
    pub status: EvidenceStatus,
    /// Stable rule id and, when available, the anchoring span
    /// (e.g. `"guard_evaluates_false@f12@67:55:78"`); empty when no anchor
    /// applies.
    pub reason: String,
}

impl Evidence {
    pub fn confirmed(reason: impl Into<String>) -> Self {
        Self {
            status: EvidenceStatus::Confirmed,
            reason: reason.into(),
        }
    }
    pub fn possible(reason: impl Into<String>) -> Self {
        Self {
            status: EvidenceStatus::Possible,
            reason: reason.into(),
        }
    }
    pub fn excluded(reason: impl Into<String>) -> Self {
        Self {
            status: EvidenceStatus::Excluded,
            reason: reason.into(),
        }
    }
    pub fn unresolved(reason: impl Into<String>) -> Self {
        Self {
            status: EvidenceStatus::Unresolved,
            reason: reason.into(),
        }
    }
}

/// Semantic effect a function may have. A single effect entry is always
/// paired with [`Evidence`]; an **excluded** effect stays in the list with
/// status `excluded`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Effect {
    LocalCall {
        callsite: CallSiteId,
        callee: String,
    },
    HttpCall {
        url: String,
    },
    GrpcCall {
        service: String,
        method: String,
    },
    MessagePublish {
        channel: String,
    },
    MessageConsume {
        channel: String,
    },
    DataRead {
        resource: ResourceId,
        table: Option<String>,
    },
    DataWrite {
        resource: ResourceId,
        table: Option<String>,
    },
    StateMutation {
        target: String,
    },
}

/// A concrete action in a minimal action list / CFG block.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Action {
    Assign {
        target: ValueExpr,
        value: ValueExpr,
    },
    Call {
        callsite: CallSiteId,
    },
    Effect(Box<Effect>),
    Return {
        value: Option<ValueExpr>,
    },
    Throw {
        value: ValueExpr,
    },
    /// Enter a loop; the back edge is materialized in the CFG.
    LoopBegin,
    LoopEnd,
}

/// A branch condition was evaluated on some path. Which branch this guard
/// guards is a scenario decision, not a grammar fact.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Guard {
    pub id: GuardId,
    pub condition: ValueExpr,
    pub span: SourceSpan,
}

/// Call site: the syntactic occurrence of an invocation inside a function.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CallSite {
    pub id: CallSiteId,
    /// Callee as written (e.g. `foo`, `Order::new`, `object.method`).
    pub callee: String,
    /// Optional receiver expression, when the call is a member call.
    pub receiver: Option<ValueExpr>,
    pub args: Vec<ValueExpr>,
    /// The whole invocation as lowered (`receiver.name(args)`).
    pub span: SourceSpan,
    /// The callee *name token* exactly as the frontend saw it: `name` starts
    /// here, on any line of a multi-line invocation, inside any receiver
    /// expression. Without it a backend would have to re-find the name by
    /// scanning text, which strings, comments and nested calls defeat; the
    /// column is then recovered from the source text (see
    /// `semarch_tt::bodies::FileUnit::name_span`).
    #[serde(default)]
    pub name_span: Option<SourceSpan>,
}

/// A function or method with its normalized body facts.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Function {
    pub id: FunctionId,
    pub name: String,
    /// Dotted qualified name (`class.name` / `module.func`); `None` when the
    /// language gives no enclosing declaration.
    pub qualified: Option<String>,
    pub kind: SymbolKind,
    pub span: SourceSpan,
    /// Number of parameters plus their normalized expressions (`Parameter
    /// { index }`), in order. `param_names[i]` is the declared name of
    /// parameter `i` (parallel list; same length when the frontend saw
    /// names — the analyzer binds actual arguments by these names).
    pub params: Vec<ValueExpr>,
    pub param_names: Vec<String>,
    /// Expressions of every `return`/exit in the body, in source order.
    /// Multiple returns are treated as a possible-set by analysis; an
    /// empty list means "returns nothing / unknown".
    /// v0 does not distinguish throw-exits; those stay `unknown`.
    pub returns: Vec<ValueExpr>,
    /// Whether the body is a stub/declaration without statements.
    pub is_decl_only: bool,
}

/// Aggregated semantic summary of a function; the analysis output unit.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct FunctionSummary {
    pub function: FunctionId,
    /// Callees this function executes (directly or by may-closure). The
    /// set is only ever *filled* with entries carrying per-callee evidence.
    pub executes: Vec<(FunctionId, Evidence)>,
    /// Local (in-process) call edges.
    pub calls: Vec<(CallSiteId, Option<FunctionId>, Evidence)>,
    /// Semantic effects with explicit statuses (see [`Effect`]).
    pub effects: Vec<(Effect, Evidence)>,
}

/// A CFG block of the minimal CFG (v0: action list + successor edges).
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct CfgBlock {
    pub id: BlockId,
    /// Terminating guard id (if/while condition), when present.
    pub guard: Option<GuardId>,
    /// Branch taken when the guard holds (`true`-arm).
    pub true_succ: Option<BlockId>,
    /// Branch taken when the guard does not hold, or sequential successor.
    /// For a guard this arm corresponds to `condition == false` **on some
    /// path** — guard polarity is resolved by analysis, never assumed.
    pub false_succ: Option<BlockId>,
    pub actions: Vec<Action>,
}

/// Minimal CFG for one function.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct Cfg {
    pub function: FunctionId,
    pub entry: Option<BlockId>,
    pub exit: Option<BlockId>,
    pub blocks: Vec<CfgBlock>,
    pub guards: Vec<Guard>,
}

// ---------------------------------------------------------------------------
// Ordered statement IR and real control flow (N03).
//
// `Cfg`/`CfgBlock` above are the v0 flat shape kept for the old API. The
// structures below are the ordered, terminator-based form: a frontend lowers
// statements into basic blocks and the block terminator decides control flow.
// They carry no language AST — only normalized operations — so the core stays
// language-neutral while each frontend expresses its own control semantics.
// ---------------------------------------------------------------------------

/// One ordered statement inside a basic block.
///
/// Statements are executed in order. Calls appearing in a value are *hoisted*
/// by the lowering frontend into their own statement, so "was this call
/// executed on this path" is a property of block reachability, not of
/// expression shape. That is what makes short-circuit reachability decidable.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Statement {
    /// `target = value`.
    Assign { target: ValueExpr, value: ValueExpr },
    /// Evaluate `value` for its effects and discard the result (`f();`).
    Eval { value: ValueExpr },
    /// A construct outside the supported subset that still had to be recorded
    /// instead of dropped. The statement has no value; the *block* it sits in
    /// is reachable only through the unsupported mechanism.
    Unsupported { reason: GapReason, detail: String },
}

/// Why a construct is outside the supported subset of a frontend. The list is
/// deliberately closed and small: a new value is a support-matrix change.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GapReason {
    /// A statement form the frontend does not lower (e.g. `switch`,
    /// `synchronized`, `assert`).
    UnsupportedStatement,
    /// An expression form the frontend does not lower (lambda body, anonymous
    /// class, `new` with effects, …).
    UnsupportedExpression,
    /// A ternary in a position where its arms cannot be materialized as two
    /// blocks (argument, condition of a wider expression).
    TernaryInValuePosition,
    /// `try`/`catch` dispatch: which arm runs depends on a thrown value the
    /// model does not track.
    ExceptionDispatch,
    /// A loop did not reach a fixed point within the context limit; the
    /// remaining values were widened to `Unknown` instead of guessing.
    Widened,
    /// The callee of a call could not be resolved to a project function, so
    /// its return value and effects stay unknown at the call site.
    UnresolvedCall,
    /// The construct has no representation in the flat fact contract the
    /// frontend emits (e.g. `new Foo(...)` is not a call site), so it cannot be
    /// referenced from the IR. Its sub-expressions are still lowered in order;
    /// this gap separates a *contract* hole from an implementation hole.
    NotInFactContract,
}

/// A recorded uncertainty: something the analysis saw but cannot decide.
/// Gaps are part of the output, never silently swallowed.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AnalysisGap {
    pub reason: GapReason,
    pub detail: String,
    #[serde(default)]
    pub span: Option<SourceSpan>,
    /// Basic block the gap belongs to, when it is block-local.
    #[serde(default)]
    pub block: Option<BlockId>,
    /// The block whose normal continuation runs alongside the gap.
    ///
    /// A gap's *content* is lowered into [`AnalysisGap::block`], which is
    /// reachable only through the unmodeled mechanism, never through a normal
    /// successor edge. The owner is what keeps that content from being treated
    /// as reachable from nowhere: it is a *may*-path out of the owner, and a
    /// gap inside a dead arm stays dead. `None` for a gap raised during
    /// expression evaluation, which has no block of its own.
    #[serde(default)]
    pub owner: Option<BlockId>,
}

impl AnalysisGap {
    #[must_use]
    pub fn new(reason: GapReason, detail: impl Into<String>, span: Option<SourceSpan>) -> Self {
        Self {
            reason,
            detail: detail.into(),
            span,
            block: None,
            owner: None,
        }
    }

    #[must_use]
    pub fn in_block(mut self, block: BlockId) -> Self {
        self.block = Some(block);
        self
    }

    /// The block whose normal continuation runs alongside this gap's content.
    #[must_use]
    pub fn owned_by(mut self, owner: BlockId) -> Self {
        self.owner = Some(owner);
        self
    }
}

/// How a basic block hands control on. Exactly one per block.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Terminator {
    /// Unconditional fall-through.
    Goto { next: BlockId },
    /// Two-way branch: `condition` holds → `then_block`, does not hold →
    /// `else_block`. Polarity is explicit here; `Unknown` reaches both.
    Branch {
        guard: GuardId,
        condition: ValueExpr,
        then_block: BlockId,
        else_block: BlockId,
    },
    /// `return value?`. Terminates the path.
    Return { value: Option<ValueExpr> },
    /// `throw value`. Terminates the path (the exception itself is unmodeled).
    Throw { value: ValueExpr },
    /// The block is not reachable on any path.
    Unreachable,
    /// The block ends in a construct outside the supported subset. `next` is
    /// the *normal* continuation (may-execute); the unmodeled content lives in
    /// the block named by [`FunctionBody::gaps`].
    Gap {
        reason: GapReason,
        detail: String,
        next: Option<BlockId>,
    },
}

impl Terminator {
    /// Successor blocks reachable from this terminator, in a deterministic
    /// order. `Gap` contributes only its normal continuation.
    #[must_use]
    pub fn successors(&self) -> Vec<BlockId> {
        match self {
            Terminator::Goto { next } => vec![*next],
            Terminator::Branch {
                then_block,
                else_block,
                ..
            } => vec![*then_block, *else_block],
            Terminator::Return { .. } | Terminator::Throw { .. } | Terminator::Unreachable => {
                Vec::new()
            }
            Terminator::Gap { next, .. } => next.iter().copied().collect(),
        }
    }

    /// Whether control leaves the function here on every path through the
    /// terminator (`return`/`throw`) or never returns (`unreachable`).
    #[must_use]
    pub fn is_exit(&self) -> bool {
        matches!(
            self,
            Terminator::Return { .. } | Terminator::Throw { .. } | Terminator::Unreachable
        )
    }
}

/// A basic block: ordered statements plus exactly one terminator.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BasicBlock {
    pub id: BlockId,
    pub statements: Vec<Statement>,
    pub terminator: Terminator,
    #[serde(default)]
    pub span: Option<SourceSpan>,
}

/// A function body lowered to basic blocks. `guards` holds every guard
/// referenced by a [`Terminator::Branch`], so a branch reference always
/// resolves; `gaps` explains every construct left outside the subset.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FunctionBody {
    pub function: FunctionId,
    pub entry: BlockId,
    pub blocks: Vec<BasicBlock>,
    pub guards: Vec<Guard>,
    /// Blocks that terminate with `Return`/`Throw`/`Unreachable`.
    pub exits: Vec<BlockId>,
    /// Constructs preserved but not placed in the CFG, with their explanations
    /// (see [`Terminator::Gap`]).
    #[serde(default)]
    pub gaps: Vec<AnalysisGap>,
}

impl BasicBlock {
    /// Statements of this block, in execution order.
    #[must_use]
    pub fn statements(&self) -> &[Statement] {
        &self.statements
    }
}
