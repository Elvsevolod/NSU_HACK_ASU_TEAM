//! Frontend-facing parse results and the [`LanguageFrontend`] trait.
//!
//! Frontends turn source text into [`ParsedFile`] facts. They never depend on
//! framework semantics (Spring/Flask/gRPC knowledge lives above), and their
//! tree-sitter AST types never leak into core.

use serde::{Deserialize, Serialize};

use crate::ids::{FileId, ModuleId};
use crate::ir::{CallSite, Function, ValueExpr};
use crate::lang::{Capability, Language};
use crate::span::SourceSpan;
use crate::Result;

/// Dense id allocator shared across files of one program.
#[derive(Debug, Default, Clone, Copy)]
pub struct Allocator {
    /// Next `FunctionId`.
    pub functions: u32,
    /// Next `CallSiteId`.
    pub callsites: u32,
    /// Next `GuardId`.
    pub guards: u32,
    /// Next `BlockId`.
    pub blocks: u32,
}

impl Allocator {
    pub fn next_function(&mut self) -> crate::ids::FunctionId {
        let v: u32 = self.functions;
        self.functions += 1;
        v.into()
    }
    pub fn next_callsite(&mut self) -> crate::ids::CallSiteId {
        let v: u32 = self.callsites;
        self.callsites += 1;
        v.into()
    }
    pub fn next_guard(&mut self) -> crate::ids::GuardId {
        let v: u32 = self.guards;
        self.guards += 1;
        v.into()
    }
    pub fn next_block(&mut self) -> crate::ids::BlockId {
        let v: u32 = self.blocks;
        self.blocks += 1;
        v.into()
    }
}

/// Parse context handed to each frontend: file identity, the shared id
/// allocator, and the diagnostic accumulator. All fields are public by
/// design — frontends are first-class citizens of the library, not plugin
/// sandbox guests.
pub struct ParseContext<'a> {
    /// Id of the file being parsed; every span must carry it.
    pub file: FileId,
    pub language: Language,
    /// Shared dense id allocator for the whole program.
    pub alloc: &'a mut Allocator,
    /// Non-fatal diagnostics accumulate here; per-source `ERROR`s never panic
    /// and never silently vanish.
    pub diagnostics: &'a mut Vec<FrontendError>,
}

impl<'a> ParseContext<'a> {
    /// Build a context; used by [`crate::SemanticIndex::parse_with`] and by
    /// frontend tests feeding standalone fixtures.
    pub fn new(
        file: FileId,
        language: Language,
        alloc: &'a mut Allocator,
        diagnostics: &'a mut Vec<FrontendError>,
    ) -> Self {
        Self {
            file,
            language,
            alloc,
            diagnostics,
        }
    }

    /// Record a non-fatal frontend diagnostic with optional span.
    pub fn diagnose(&mut self, message: impl Into<String>, span: Option<SourceSpan>) {
        self.diagnostics.push(FrontendError {
            language: self.language,
            message: message.into(),
            span,
        });
    }
}

/// A resolved import fact (what is imported from where), normalized.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ImportFact {
    /// Dotted path as written (`com.foo.bar` / `foo.bar`).
    pub path: String,
    /// Local alias, if any (`import x as y`); Java static imports carry
    /// the pseudo-alias `"static"`.
    pub alias: Option<String>,
    /// Span of the import statement.
    pub span: SourceSpan,
}

/// An annotation / decorator occurrence attached to a declaration.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AnnotationFact {
    /// Annotation name without sigils (`GetMapping`, `app.route`).
    pub name: String,
    /// Attribute arguments as written, when present; raw text, not parsed
    /// semantics (framework mapping happens above the frontend).
    pub args: Option<String>,
    pub span: SourceSpan,
}

/// Module/namespace declaration of a file. v0 mapping: Java package → module
/// (dense 1:1 with file); Python/JS/Go/TS/C# are added in their frontends.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ModuleDecl {
    pub id: ModuleId,
    /// Dotted module/package path (e.g. `fallback.msproject`).
    pub path: String,
}

/// A syntactic condition that will later become a [`crate::ir::Guard`].
/// `ValueExpr` carries floats, so this is `PartialEq`, not `Eq`.
///
/// The three spans are *not* interchangeable, and analysis must use
/// [`Self::then_span`] when it asks "which statements does this condition
/// protect":
///
/// * `span` — the predicate expression, evaluated before the branch decision;
/// * `then_span` — the statements that run when the predicate holds; the
///   predicate itself and the `else` branch are *outside* it;
/// * `else_span` — the `else`/`elif` branch, recorded so it can never be
///   confused with the guarded body;
/// * `body_span` — the whole construct, kept for compatibility with consumers
///   written against the older schema.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GuardCondition {
    pub condition: ValueExpr,
    /// Span of the condition expression itself.
    pub span: SourceSpan,
    /// Span of the guarded body: the statements that execute when the
    /// condition holds. `None` when the body always runs at least once
    /// (`do { … } while (…)`) or cannot be delimited — in which case no region
    /// may be treated as protected by this condition.
    #[serde(default)]
    pub then_span: Option<SourceSpan>,
    /// Span of the alternative branch (`else` / `elif`), when the language and
    /// the construct have one.
    #[serde(default)]
    pub else_span: Option<SourceSpan>,
    /// Span of the whole construct (`if`/`while` statement including its body).
    /// **Legacy:** it contains the predicate and the `else` branch, so it must
    /// not be used to decide which statements a condition protects.
    #[serde(default)]
    pub body_span: Option<SourceSpan>,
    /// Whether the body runs regardless of the condition (`do { … } while`).
    /// When true, `then_span` is `None` and nothing is guarded by this
    /// condition.
    #[serde(default)]
    pub body_always_runs: bool,
}

/// Action kinds a frontend may attach to loops for the minimal CFG. v0 keeps
/// loops unmaterialized; the variant exists so capability claims can be
/// extended without an IR break.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LoopKind {
    For,
    While,
    DoWhile,
    EnhancedFor,
    Range,
}

/// Parsed file facts, all spans referencing `file`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ParsedFile {
    pub file: FileId,
    pub language: Language,
    /// Module declaration carrying this file, when the language has one.
    pub module: Option<ModuleDecl>,
    pub imports: Vec<ImportFact>,
    pub annotations: Vec<AnnotationFact>,
    pub functions: Vec<Function>,
    pub callsites: Vec<CallSite>,
    /// Conditions produced by if/while constructs; CFG polarity is attached
    /// later by analysis.
    pub guard_conditions: Vec<GuardCondition>,
    /// Ordered bodies lowered to basic blocks (N03). Additive: a consumer that
    /// only needs the flat facts above is unaffected, and an older serialized
    /// file without bodies still parses (`#[serde(default)]`).
    #[serde(default)]
    pub bodies: Vec<crate::ir::FunctionBody>,
}

/// What a frontend saw wrong in the source. Analysis continues; the fact is
/// recorded rather than silently dropped.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub struct FrontendError {
    pub language: Language,
    pub message: String,
    pub span: Option<SourceSpan>,
}

impl std::fmt::Display for FrontendError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self.span {
            Some(s) => {
                write!(
                    f,
                    "{} frontend: {} ({})",
                    self.language.name(),
                    self.message,
                    s.anchor()
                )
            }
            None => write!(f, "{} frontend: {}", self.language.name(), self.message),
        }
    }
}

impl std::error::Error for FrontendError {}

/// Language frontend. Implementations build a parser once and reuse it.
pub trait LanguageFrontend {
    /// Crate-local id, e.g. `"frontend-java"`.
    fn id(&self) -> &'static str;
    fn language(&self) -> Language;

    /// Capability matrix of this frontend version. Facts required by a
    /// capability must be emitted whenever the construct exists; absence of a
    /// capability means the fact is never claimed.
    fn capabilities(&self) -> &'static [Capability];

    /// # Errors
    /// Returns [`crate::Error`] on tree-sitter level failure (out of v0: a
    /// flat `ERROR` node is a diagnostic, not a parse panic).
    fn parse(&mut self, ctx: &mut ParseContext<'_>, source: &str) -> Result<ParsedFile>;
}
