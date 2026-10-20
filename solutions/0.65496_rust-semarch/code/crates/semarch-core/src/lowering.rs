//! Language-neutral construction and validation of ordered function bodies.
//!
//! Frontends lower their statement syntax into [`BasicBlock`]s and
//! [`Terminator`]s; this module owns the *bookkeeping* so that every frontend
//! produces structurally valid CFGs: blocks exist, terminators are exactly one
//! per block, guard references resolve, and every construct left outside a
//! frontend's supported subset is recorded as a gap instead of vanishing.
//!
//! It deliberately knows nothing about tree-sitter or any language AST: the
//! contract is the IR, not the tree.

use std::collections::{BTreeMap, BTreeSet};

use crate::frontend::Allocator;
use crate::ids::{BlockId, FunctionId};
use crate::ir::{
    AnalysisGap, BasicBlock, FunctionBody, GapReason, Guard, Statement, Terminator,
};
use crate::span::SourceSpan;

/// Assembles blocks and terminators for one function body.
///
/// A frontend creates blocks, appends statements in execution order, and sets a
/// terminator on each block. `finish` derives `entry`/`exits` and records every
/// gap that a `Gap` terminator introduced, so the body is self-describing.
#[derive(Debug)]
pub struct BodyBuilder {
    function: FunctionId,
    blocks: Vec<BasicBlock>,
    guards: Vec<Guard>,
    gaps: Vec<AnalysisGap>,
}

impl BodyBuilder {
    #[must_use]
    pub fn new(function: FunctionId) -> Self {
        Self {
            function,
            blocks: Vec::new(),
            guards: Vec::new(),
            gaps: Vec::new(),
        }
    }

    /// Register a guard referenced by a branch terminator. Guards are also
    /// returned from [`Self::finish`] so a branch reference always resolves.
    pub fn guard(&mut self, guard: Guard) {
        self.guards.push(guard);
    }

    /// Create a fresh block with an `Unreachable` terminator (frontends must
    /// set a real terminator before `finish`).
    pub fn block(&mut self, alloc: &mut Allocator, span: Option<SourceSpan>) -> BlockId {
        let id = alloc.next_block();
        self.blocks.push(BasicBlock {
            id,
            statements: Vec::new(),
            terminator: Terminator::Unreachable,
            span,
        });
        id
    }

    /// Append a statement to `block`.
    ///
    /// # Panics
    /// Panics when `block` does not belong to this builder; that is a frontend
    /// bug, and silently dropping the statement would hide it.
    pub fn push(&mut self, block: BlockId, statement: Statement) {
        self.block_mut(block).statements.push(statement);
    }

    /// Set the terminator of `block`, recording the gap when it is a
    /// [`Terminator::Gap`].
    ///
    /// # Panics
    /// Panics when `block` does not belong to this builder.
    pub fn terminate(&mut self, block: BlockId, terminator: Terminator) {
        if let Terminator::Gap {
            reason, detail, ..
        } = &terminator
        {
            let span = self
                .blocks
                .iter()
                .find(|b| b.id == block)
                .and_then(|b| b.span);
            let gap =
                AnalysisGap::new(*reason, detail.clone(), span).in_block(block);
            self.gaps.push(gap);
        }
        self.block_mut(block).terminator = terminator;
    }

    /// Record a gap that is not tied to a terminator (e.g. an unsupported
    /// expression inside a supported statement).
    pub fn record_gap(&mut self, gap: AnalysisGap) {
        self.gaps.push(gap);
    }

    /// Create a block that is reachable only through an unsupported mechanism
    /// (a `Gap` terminator's unmodeled route), and record it.
    ///
    /// `owner` is the block whose normal continuation runs alongside this
    /// content; the analysis treats the content as a *may*-path out of it, so
    /// content belonging to a dead arm stays dead instead of being seeded as
    /// reachable from nowhere.
    pub fn gap_block(
        &mut self,
        alloc: &mut Allocator,
        reason: GapReason,
        detail: impl Into<String>,
        span: Option<SourceSpan>,
        owner: BlockId,
    ) -> BlockId {
        let id = self.block(alloc, span);
        let mut gap = AnalysisGap::new(reason, detail, span).owned_by(owner);
        gap.block = Some(id);
        self.gaps.push(gap);
        id
    }

    /// Enter a block: `from` falls through to a fresh block, which is
    /// returned. Convenience for statement sequences.
    pub fn enter(&mut self, alloc: &mut Allocator, from: BlockId) -> BlockId {
        let next = self.block(alloc, None);
        self.terminate(from, Terminator::Goto { next });
        next
    }

    fn block_mut(&mut self, id: BlockId) -> &mut BasicBlock {
        self.blocks
            .iter_mut()
            .find(|b| b.id == id)
            .expect("block belongs to this builder")
    }

    /// Finish the body. `entry` is the first block; exits are the blocks that
    /// leave the function on every path through them.
    ///
    /// # Panics
    /// Panics when `entry` does not belong to this builder.
    #[must_use]
    pub fn finish(self, entry: BlockId) -> FunctionBody {
        assert!(
            self.blocks.iter().any(|b| b.id == entry),
            "entry block belongs to this builder"
        );
        let exits = self
            .blocks
            .iter()
            .filter(|b| b.terminator.is_exit())
            .map(|b| b.id)
            .collect();
        FunctionBody {
            function: self.function,
            entry,
            blocks: self.blocks,
            guards: self.guards,
            exits,
            gaps: self.gaps,
        }
    }
}

/// The result of structural validation.
///
/// `Valid { notes }` means the CFG is well formed; notes describe legitimate
/// but noteworthy states (a block no path reaches, such as the exit of a
/// non-terminating loop, or code after a definite `return`). `Invalid` means a
/// consumer could trip over a dangling reference.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BodyCheck {
    Valid { notes: Vec<String> },
    Invalid { problems: Vec<String> },
}

impl BodyCheck {
    #[must_use]
    pub fn is_valid(&self) -> bool {
        matches!(self, BodyCheck::Valid { .. })
    }

    #[must_use]
    pub fn problems(&self) -> Vec<String> {
        match self {
            BodyCheck::Valid { .. } => Vec::new(),
            BodyCheck::Invalid { problems } => problems.clone(),
        }
    }

    #[must_use]
    pub fn notes(&self) -> Vec<String> {
        match self {
            BodyCheck::Valid { notes } => notes.clone(),
            BodyCheck::Invalid { .. } => Vec::new(),
        }
    }
}

/// Structural validation of a lowered body. Every problem is a defect a
/// consumer must not have to discover: a dangling successor, an unresolved
/// guard reference, a duplicated block id, an entry/gap pointing outside the
/// body, or a block that is neither reachable from the entry nor explained by a
/// gap.
#[must_use]
pub fn validate(body: &FunctionBody) -> BodyCheck {
    let mut problems = Vec::new();
    let ids: BTreeSet<BlockId> = body.blocks.iter().map(|b| b.id).collect();
    if body.blocks.len() != ids.len() {
        problems.push("duplicate block ids".to_owned());
    }
    if !ids.contains(&body.entry) {
        problems.push("entry block is not in the body".to_owned());
    }
    let guard_ids: BTreeSet<crate::ids::GuardId> = body.guards.iter().map(|g| g.id).collect();
    for b in &body.blocks {
        for next in b.terminator.successors() {
            if !ids.contains(&next) {
                problems.push(format!(
                    "block {:?} points to a successor outside the body",
                    b.id
                ));
            }
        }
        if let Terminator::Branch { guard, .. } = &b.terminator {
            if !guard_ids.contains(guard) {
                problems.push(format!("block {:?} references an unregistered guard", b.id));
            }
        }
    }
    for g in &body.gaps {
        if let Some(block) = g.block {
            if !ids.contains(&block) {
                problems.push(format!("gap names a block outside the body: {block:?}"));
            }
        }
    }
    if !problems.is_empty() {
        return BodyCheck::Invalid { problems };
    }

    // Reachability: blocks no path reaches are legitimate dead code when the
    // lowering explains why (an unreachable loop exit, code after a definite
    // `return`). They are reported as notes, not as defects.
    let mut reachable: BTreeSet<BlockId> = BTreeSet::new();
    let mut stack = vec![body.entry];
    for g in &body.gaps {
        if let Some(b) = g.block {
            stack.push(b);
        }
    }
    while let Some(id) = stack.pop() {
        if !reachable.insert(id) {
            continue;
        }
        if let Some(b) = body.blocks.iter().find(|b| b.id == id) {
            for next in b.terminator.successors() {
                stack.push(next);
            }
        }
    }
    let mut notes = Vec::new();
    for b in &body.blocks {
        if !reachable.contains(&b.id) {
            notes.push(format!(
                "block {:?} is not reached by any path and is not explained by a gap",
                b.id
            ));
        }
    }
    BodyCheck::Valid { notes }
}

/// Blocks in a deterministic work-list order: the reverse of the recorded
/// order, which visits successors before predecessors for typical forward
/// lowering and keeps iteration counts small.
#[must_use]
pub fn worklist_order(body: &FunctionBody) -> Vec<BlockId> {
    let mut order: Vec<BlockId> = body.blocks.iter().map(|b| b.id).collect();
    order.reverse();
    order
}

/// Index of blocks by id.
#[must_use]
pub fn block_index(body: &FunctionBody) -> BTreeMap<BlockId, &BasicBlock> {
    body.blocks.iter().map(|b| (b.id, b)).collect()
}

/// Guards of a body by id.
#[must_use]
pub fn guard_index(body: &FunctionBody) -> BTreeMap<crate::ids::GuardId, &Guard> {
    body.guards.iter().map(|g| (g.id, g)).collect()
}
