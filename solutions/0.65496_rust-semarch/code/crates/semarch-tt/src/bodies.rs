//! Ordered bodies of the project's own sources ("N05/N06" body index).
//!
//! The contest skeleton describes *which* methods exist; the semantic engine
//! needs *what they do*, i.e. the ordered IR lowered by the language frontend.
//! This module reparses the project sources once, on demand, and indexes every
//! lowered body by `(file, name)` so a skeleton method can be matched to the
//! body of the declaration that implements it.
//!
//! Matching is by `(project-relative file, simple name, arity)` with the
//! declared line as the tie-break. All three are facts of the skeleton and of
//! the source; no inference about overload resolution happens here. Overloads
//! of the same name and arity inside one file are legal only if they differ by
//! type, and then the answer must not depend on which one the engine picked:
//! the caller keeps the skeleton id and only uses the body for value flow, so
//! an ambiguous pick is recorded as a gap rather than guessed.

use std::collections::HashMap;
use std::path::Path;
use std::sync::Arc;

use semarch_core::ids::FileId;
use semarch_core::ir::{CallSite, Function, FunctionBody};
use semarch_core::span::SourceSpan;
use semarch_core::{Allocator, Language, LanguageFrontend, ParseContext, ProjectDiscovery};
use semarch_frontend_java::JavaFrontend;

use crate::TtError;

/// Everything of one parsed file that a body needs: call sites and functions
/// are referenced by id from the body, so they must travel together.
#[derive(Debug)]
pub struct FileUnit {
    /// Project-relative source path (`…/TokenServiceImpl.java`).
    pub file: String,
    pub language: Language,
    /// The file's text, kept so a lowered span can be turned back into the
    /// token the skeleton describes (its column, its argument text).
    pub source: Arc<str>,
    pub callsites: Vec<CallSite>,
    pub functions: Vec<Function>,
}

impl FileUnit {
    /// The exact source span of the callee *name token* of one lowered call
    /// site.
    ///
    /// The frontend records it directly (`CallSite::name_span`), so a
    /// multi-line invocation or a receiver expression never moves the anchor.
    /// When a call site carries no name span (hand-built IR in tests, an older
    /// frontend), the token is recovered from the source text with a
    /// string/comment-aware scan of the invocation's own argument list — never
    /// by "the last name before a `(`", which mixed up nested calls, string
    /// contents and comments.
    #[must_use]
    pub fn name_span(&self, cs: &CallSite) -> Option<SourceSpan> {
        if let Some(span) = cs.name_span {
            if span.start_byte < span.end_byte {
                return Some(span);
            }
        }
        let start = usize::try_from(cs.span.start_byte).ok()?;
        let end = usize::try_from(cs.span.end_byte).ok()?;
        if start > end || end > self.source.len() {
            return None;
        }
        let text = self.source.get(start..end)?;
        let (offset, len) = if cs.callee == "<init>" {
            // An `object_creation_expression` starts at `new`, which is what the
            // skeleton reports for a constructor call.
            (0, 3.min(text.len()))
        } else {
            (callee_offset(text, &cs.callee)?, cs.callee.len())
        };
        Some(self.span_at(start + offset, len, cs.span.file))
    }

    /// 0-based (row, UTF-8 byte column) of the callee name token. The row is
    /// the name's own row, not the invocation's first line.
    #[must_use]
    pub fn anchor(&self, cs: &CallSite) -> Option<(u32, u32)> {
        self.name_span(cs).map(|s| (s.start_row, s.start_col))
    }

    /// 0-based UTF-8 byte column of the callee name token.
    ///
    /// `None` when the token cannot be located inside the lowered span; the
    /// caller then falls back to the span start, or to no column at all.
    #[must_use]
    pub fn anchor_col(&self, cs: &CallSite) -> Option<u32> {
        self.anchor(cs).map(|(_, col)| col)
    }

    /// 1-based source line of the callee name token: what a skeleton call-site
    /// fact is keyed by.
    #[must_use]
    pub fn site_line(&self, cs: &CallSite) -> u32 {
        self.name_span(cs)
            .map_or(cs.span.start_row + 1, |s| s.start_row + 1)
    }

    fn span_at(&self, abs: usize, len: usize, file: FileId) -> SourceSpan {
        let abs = abs.min(self.source.len());
        let row = self.source[..abs].bytes().filter(|b| *b == b'\n').count();
        let line_start = self.source[..abs].rfind('\n').map_or(0, |i| i + 1);
        let col = abs - line_start;
        let end = (abs + len).min(self.source.len());
        SourceSpan {
            file,
            start_byte: abs as u32,
            end_byte: end as u32,
            start_row: row as u32,
            start_col: col as u32,
            end_row: row as u32,
            end_col: (col + len) as u32,
        }
    }
}

/// Byte offset of the callee name token inside an invocation's text.
///
/// The name is the identifier that immediately precedes the `(` of the
/// invocation's own argument list. That list is found from its closing `)` on a
/// text with string literals and comments blanked out, so an argument's nested
/// call, a string that looks like a call, and a comment that looks like one are
/// all invisible. A whole-word scan is the fallback when the text is not an
/// invocation (a bare name).
fn callee_offset(text: &str, callee: &str) -> Option<usize> {
    if callee.is_empty() {
        return None;
    }
    let mask = code_mask(text);
    if let Some(close) = mask.iter().rposition(|b| *b == b')') {
        if let Some(open) = matching_open(&mask, close) {
            let (start, end) = ident_ending_at(text, open)?;
            if &text[start..end] == callee {
                return Some(start);
            }
        }
    }
    let mut from = 0;
    while let Some(i) = text.get(from..)?.find(callee) {
        let abs = from + i;
        if is_whole_word(text, abs, callee.len()) {
            let after = &text[abs + callee.len()..];
            if after.trim_start().starts_with('(') {
                return Some(abs);
            }
        }
        from = abs + callee.len();
    }
    None
}

/// The `(` matching a `)` at `close`, scanning backwards. Comments and string
/// contents are already blanked in `mask`.
fn matching_open(mask: &[u8], close: usize) -> Option<usize> {
    let mut depth: i32 = 0;
    let mut i = close;
    loop {
        match mask[i] {
            b')' => depth += 1,
            b'(' => {
                depth -= 1;
                if depth == 0 {
                    return Some(i);
                }
            }
            _ => {}
        }
        if i == 0 {
            return None;
        }
        i -= 1;
    }
}

/// The identifier ending (exclusively) at `end`, after skipping any whitespace
/// before it. `text` is the original (unmasked) text.
fn ident_ending_at(text: &str, end: usize) -> Option<(usize, usize)> {
    let bytes = text.as_bytes();
    let mut i = end;
    while i > 0 && bytes[i - 1].is_ascii_whitespace() {
        i -= 1;
    }
    let mut start = i;
    while start > 0 && is_ident_byte(bytes[start - 1]) {
        start -= 1;
    }
    (start < i).then_some((start, i))
}

fn is_ident_byte(b: u8) -> bool {
    b.is_ascii_alphanumeric() || b == b'_' || b == b'$'
}

fn is_whole_word(text: &str, start: usize, len: usize) -> bool {
    let bytes = text.as_bytes();
    let before = start == 0 || !is_ident_byte(bytes[start - 1]);
    let after = start + len >= bytes.len() || !is_ident_byte(bytes[start + len]);
    before && after
}

/// A copy of `text` with the bytes of string literals, character literals and
/// comments replaced by spaces, so delimiters inside them cannot be counted.
/// Byte length is preserved.
fn code_mask(text: &str) -> Vec<u8> {
    let b = text.as_bytes();
    let mut out = b.to_vec();
    let blank = |out: &mut [u8], from: usize, to: usize| {
        let end = to.min(out.len());
        for byte in &mut out[from..end] {
            *byte = b' ';
        }
    };
    let mut i = 0;
    while i < b.len() {
        match b[i] {
            b'/' if i + 1 < b.len() && b[i + 1] == b'/' => {
                let mut j = i;
                while j < b.len() && b[j] != b'\n' {
                    j += 1;
                }
                blank(&mut out, i, j);
                i = j;
            }
            b'/' if i + 1 < b.len() && b[i + 1] == b'*' => {
                let mut j = i + 2;
                while j + 1 < b.len() && !(b[j] == b'*' && b[j + 1] == b'/') {
                    j += 1;
                }
                let end = if j + 1 < b.len() { j + 2 } else { b.len() };
                blank(&mut out, i, end);
                i = end;
            }
            b'#' => {
                let mut j = i;
                while j < b.len() && b[j] != b'\n' {
                    j += 1;
                }
                blank(&mut out, i, j);
                i = j;
            }
            q @ (b'"' | b'\'') => {
                let triple = i + 2 < b.len() && b[i + 1] == q && b[i + 2] == q;
                let mut j = i + if triple { 3 } else { 1 };
                while j < b.len() {
                    if !triple && b[j] == b'\\' {
                        j += 2;
                        continue;
                    }
                    if b[j] == q {
                        if triple {
                            if j + 2 < b.len() && b[j + 1] == q && b[j + 2] == q {
                                j += 3;
                                break;
                            }
                        } else {
                            j += 1;
                            break;
                        }
                    }
                    if !triple && b[j] == b'\n' {
                        break;
                    }
                    j += 1;
                }
                blank(&mut out, i, j.min(b.len()));
                i = j;
            }
            _ => i += 1,
        }
    }
    out
}

/// One lowered body plus the file unit that resolves its ids.
#[derive(Debug)]
pub struct Slot {
    pub unit: Arc<FileUnit>,
    pub body: FunctionBody,
    /// Declared parameter count (`descriptor` arity of the skeleton method).
    pub arity: usize,
    /// 1-based line of the declaration.
    pub line: u32,
    /// Declared parameter names, in order (empty when the frontend saw none).
    pub param_names: Vec<String>,
}

impl Slot {
    /// The declaration's source span.
    #[must_use]
    pub fn span(&self) -> Option<semarch_core::SourceSpan> {
        self.unit
            .functions
            .iter()
            .find(|f| f.id == self.body.function)
            .map(|f| f.span)
    }
}

/// How a skeleton method identity maps to a lowered body.
#[derive(Debug)]
pub enum BodyMatch<'a> {
    /// One body implements the identity, with the evidence used.
    Exact { slot: &'a Slot, evidence: &'static str },
    /// Several bodies of the same file could implement it: no body is used.
    Ambiguous {
        candidates: Vec<&'a Slot>,
        reason: String,
    },
    /// No lowered body matches the identity.
    Missing { reason: String },
}

impl<'a> BodyMatch<'a> {
    /// The body, when the identity is established.
    #[must_use]
    pub fn into_slot(self) -> Option<&'a Slot> {
        match self {
            Self::Exact { slot, .. } => Some(slot),
            Self::Ambiguous { .. } | Self::Missing { .. } => None,
        }
    }

    /// Why the identity could not be established, for the report.
    #[must_use]
    pub fn reason(&self) -> Option<&str> {
        match self {
            Self::Exact { .. } => None,
            Self::Ambiguous { reason, .. } | Self::Missing { reason } => Some(reason),
        }
    }
}

/// All lowered bodies of a project, indexed for lookup by skeleton identity.
#[derive(Debug, Default)]
pub struct BodyIndex {
    by_name: HashMap<(String, String), Vec<Slot>>,
    /// Java files parsed (a project may also contain UI sources).
    pub files: usize,
    /// Lowered bodies indexed across those files.
    pub bodies: usize,
    /// Bodies the frontend lowered but whose declaration was not indexed
    /// (defensive; should stay 0 for Java).
    pub unindexed: usize,
}

impl BodyIndex {
    /// Parse every Java source under `root` and index its lowered bodies.
    ///
    /// # Errors
    /// Propagates discovery and parse failures: a semantic run that silently
    /// skipped a file would report a smaller program than the one on disk.
    pub fn build(root: &Path) -> Result<Self, TtError> {
        let root = root.canonicalize().map_err(TtError::Io)?;
        let mut frontend = JavaFrontend::new()?;
        let mut index = Self::default();
        for f in ProjectDiscovery::new(&root).discover()? {
            if f.language != Language::Java {
                continue;
            }
            let Ok(rel) = f.path.strip_prefix(&root) else {
                continue;
            };
            let rel = rel.to_string_lossy().replace('\\', "/");
            let source = std::fs::read_to_string(&f.path).map_err(TtError::Io)?;
            let mut alloc = Allocator::default();
            let mut diagnostics = Vec::new();
            let mut ctx = ParseContext::new(
                FileId::from_raw(0),
                Language::Java,
                &mut alloc,
                &mut diagnostics,
            );
            let parsed = frontend.parse(&mut ctx, &source)?;
            index.files += 1;
            index.absorb(rel, source, parsed);
        }
        Ok(index)
    }

    fn absorb(&mut self, rel: String, source: String, parsed: semarch_core::ParsedFile) {
        if parsed.bodies.is_empty() {
            return;
        }
        let unit = Arc::new(FileUnit {
            file: rel.clone(),
            language: Language::Java,
            source: Arc::from(source),
            callsites: parsed.callsites,
            functions: parsed.functions,
        });
        for body in parsed.bodies {
            let Some(func) = unit.functions.iter().find(|f| f.id == body.function) else {
                self.unindexed += 1;
                continue;
            };
            let slot = Slot {
                unit: Arc::clone(&unit),
                arity: func.params.len(),
                line: func.span.start_row + 1,
                param_names: func.param_names.clone(),
                body,
            };
            self.by_name
                .entry((rel.clone(), func.name.clone()))
                .or_default()
                .push(slot);
            self.bodies += 1;
        }
    }

    /// Find the body implementing a skeleton method.
    ///
    /// `arity` and `line` disambiguate overloads of the same simple name in one
    /// file. A body is only *borrowed* when its identity is established:
    ///
    /// * one body of that file and name has the declared arity → that one;
    /// * several do, but exactly one is declared on the skeleton's line → that
    ///   one;
    /// * otherwise the identity is [`BodyMatch::Ambiguous`] and **no** body is
    ///   returned. A neighbouring overload would deliver another method's
    ///   values, which is exactly what the semantic path must not do.
    ///
    /// A name without a body of the declared arity is [`BodyMatch::Missing`]:
    /// the earlier revision silently borrowed an overload of a different arity.
    #[must_use]
    pub fn resolve(&self, file: &str, name: &str, arity: usize, line: u32) -> BodyMatch<'_> {
        let Some(slots) = self.by_name.get(&(file.to_owned(), name.to_owned())) else {
            return BodyMatch::Missing {
                reason: format!("no lowered body named {name} in {file}"),
            };
        };
        let same: Vec<&Slot> = slots.iter().filter(|s| s.arity == arity).collect();
        match same.len() {
            0 => BodyMatch::Missing {
                reason: format!("no lowered body of {name} in {file} with arity {arity}"),
            },
            1 => BodyMatch::Exact {
                slot: same[0],
                evidence: "arity",
            },
            _ => {
                let by_line: Vec<&Slot> = same.iter().copied().filter(|s| s.line == line).collect();
                if let [only] = by_line[..] {
                    return BodyMatch::Exact {
                        slot: only,
                        evidence: "declared_line",
                    };
                }
                BodyMatch::Ambiguous {
                    candidates: same,
                    reason: format!(
                        "{} bodies of {name} in {file} share arity {arity} and none is declared on line {line}",
                        by_line.len().max(1)
                    ),
                }
            }
        }
    }

    /// Find the body implementing a skeleton method, taking the first exact
    /// match. Kept for the legacy callers that only need a body when the
    /// identity is unambiguous.
    #[must_use]
    pub fn find(&self, file: &str, name: &str, arity: usize, line: u32) -> Option<&Slot> {
        self.resolve(file, name, arity, line).into_slot()
    }

    /// Whether a skeleton identity matches more than one body of that file.
    #[must_use]
    pub fn ambiguous(&self, file: &str, name: &str, arity: usize) -> bool {
        self.by_name
            .get(&(file.to_owned(), name.to_owned()))
            .is_some_and(|s| s.iter().filter(|s| s.arity == arity).count() > 1)
    }

    /// Every lowered body, for coverage diagnostics. Each body appears once.
    pub fn slots(&self) -> impl Iterator<Item = &Slot> {
        self.by_name.values().flatten()
    }
}
