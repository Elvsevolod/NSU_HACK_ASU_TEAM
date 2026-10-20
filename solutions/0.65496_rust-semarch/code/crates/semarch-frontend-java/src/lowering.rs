//! Java statement lowering into ordered basic blocks (N03).
//!
//! This pass runs *after* the flat fact walk and never adds or reorders flat
//! facts: it only reads the call sites the walk already registered (by span)
//! and turns the method bodies into [`FunctionBody`]s. That separation is what
//! keeps the flat contract (`ParsedFile.callsites`, `guard_conditions`,
//! `functions`) byte-identical while the ordered IR becomes real.
//!
//! # Support matrix
//!
//! Lowered to control flow (with the noted semantics):
//!
//! | construct | treatment |
//! |---|---|
//! | `block`, statement sequence | ordered statements, one terminator per block |
//! | `local_variable_declaration`, `=`, `+=` … | `Assign` |
//! | expression statement (`f();`) | `Eval` of the hoisted call |
//! | `i++` / `i--` | `Assign` with the arithmetic operator |
//! | `if` / `if`–`else` | condition value + `Branch` with explicit polarity |
//! | ternary in value position | two `Assign` arms, both calls kept, joined by a temp |
//! | `&&` / `\|\|` | `Branch` on the left value; the right side is reached only on that path |
//! | `return` / `throw` | `Return` / `Throw`, terminating the block |
//! | `while`, `for`, `do`-`while` | real backedges; `do` body runs first |
//! | for-each | header with an `Unknown` condition, body still reached |
//! | `try`–`finally` | the `finally` body is inlined before every `return`/`throw` and on normal completion |
//!
//! Recorded as a gap, never dropped (see [`GapReason`]):
//!
//! | construct | why |
//! |---|---|
//! | `try`–`catch` (with or without `finally`) | which arm runs depends on a thrown value the model does not track; catch bodies stay reachable as *may* paths |
//! | `switch`, `synchronized`, `assert`, `labeled`, `break`/`continue` | outside the supported subset; their statements are still lowered into gap-reachable blocks |
//! | lambda body, anonymous class, `new` with effects | not statements of this body; a value-position gap is recorded |
//! | `array_access` | element state is not modeled (heap, N08) |
//!
//! # AST isolation
//!
//! Everything here is either a tree-sitter `Node` or a `semarch_core` IR type;
//! no tree-sitter type is stored in the IR. Materialized short-circuit and
//! ternary values use generated `$t<n>` names, which cannot collide with a Java
//! identifier (`$` is legal but conventional only in compiler-generated code).

use std::collections::{HashMap, HashSet};

use crate::{map_binop, node_text, span_of, unquote};
use semarch_core::ids::{BlockId, CallSiteId, FileId, FunctionId, GuardId};
use semarch_core::ir::{
    AnalysisGap, BinaryOp, CallSite, Function, FunctionBody, GapReason, Guard, Statement,
    Terminator, UnaryOp, ValueExpr,
};
use semarch_core::lowering::BodyBuilder;
use semarch_core::span::SourceSpan;
use semarch_core::Allocator;
use tree_sitter::Node;

/// Control flow out of a lowered statement.
enum Flow {
    /// Execution continues at this block.
    Next(BlockId),
    /// The statement leaves the function on every path through it.
    Diverges,
}

/// Call-site index: source span → the call site the flat walk registered there.
struct CallIndex<'a> {
    by_span: HashMap<(u32, u32), CallSiteId>,
    _sites: &'a [CallSite],
}

impl CallIndex<'_> {
    fn new(sites: &[CallSite]) -> CallIndex<'_> {
        let by_span = sites
            .iter()
            .map(|c| ((c.span.start_byte, c.span.end_byte), c.id))
            .collect();
        CallIndex {
            by_span,
            _sites: sites,
        }
    }

    fn get(&self, node: Node<'_>) -> Option<CallSiteId> {
        self.by_span
            .get(&(node.start_byte() as u32, node.end_byte() as u32))
            .copied()
    }
}

/// Lower all method and constructor bodies of one file.
#[must_use]
pub fn lower_bodies(
    root: Node<'_>,
    src: &str,
    file: FileId,
    functions: &[Function],
    callsites: &[CallSite],
    alloc: &mut Allocator,
) -> Vec<FunctionBody> {
    let by_start: HashMap<u32, FunctionId> =
        functions.iter().map(|f| (f.span.start_byte, f.id)).collect();
    let mut lowerer = Lowerer {
        src,
        file,
        index: CallIndex::new(callsites),
        alloc,
        builder: None,
        temp: 0,
        guards: Vec::new(),
        finally: Vec::new(),
        recorded: HashSet::new(),
    };
    let mut bodies = Vec::new();
    lowerer.collect(root, &by_start, &mut bodies);
    bodies
}

struct Lowerer<'a> {
    src: &'a str,
    file: FileId,
    index: CallIndex<'a>,
    alloc: &'a mut Allocator,
    builder: Option<BodyBuilder>,
    temp: u32,
    guards: Vec<Guard>,
    finally: Vec<Node<'a>>,
    /// Gaps already recorded, keyed by `(kind, detail, start_byte)`, so one
    /// unsupported construct produces one gap rather than one per traversal.
    recorded: HashSet<(String, u32)>,
}

impl<'a> Lowerer<'a> {
    fn collect(
        &mut self,
        node: Node<'a>,
        by_start: &HashMap<u32, FunctionId>,
        out: &mut Vec<FunctionBody>,
    ) {
        if matches!(node.kind(), "method_declaration" | "constructor_declaration") {
            if let (Some(body), Some(&function)) = (
                node.child_by_field_name("body"),
                by_start.get(&(node.start_byte() as u32)),
            ) {
                out.push(self.lower_method(function, body));
                // Methods of local and anonymous classes live inside this
                // body; the flat walk registered them, so lower them too.
                self.collect(body, by_start, out);
            }
            return;
        }
        let mut cursor = node.walk();
        let children: Vec<Node<'a>> = node.children(&mut cursor).collect();
        for child in children {
            // A lambda body is not a method of this file's dense function list;
            // the flat walk already registered the calls inside it.
            if child.kind() == "lambda_expression" {
                continue;
            }
            self.collect(child, by_start, out);
        }
    }

    fn lower_method(&mut self, function: FunctionId, body: Node<'a>) -> FunctionBody {
        self.temp = 0;
        self.guards.clear();
        self.finally.clear();
        self.recorded.clear();
        self.builder = Some(BodyBuilder::new(function));
        let entry = self.block(Some(span_of(body, self.file)));
        if let Flow::Next(tail) = self.lower_stmt(body, entry) {
            // Falling off the end of a body returns no value; that is the
            // normal terminator of a `void` method and a recorded fact for a
            // non-`void` one the compiler would reject anyway.
            self.term(tail, Terminator::Return { value: None });
        }
        let mut builder = self
            .builder
            .take()
            .expect("a builder exists while lowering a method");
        for guard in self.guards.drain(..) {
            builder.guard(guard);
        }
        builder.finish(entry)
    }

    // -- builder helpers ----------------------------------------------------

    fn block(&mut self, span: Option<SourceSpan>) -> BlockId {
        self.builder
            .as_mut()
            .expect("a builder exists while lowering")
            .block(self.alloc, span)
    }

    fn stmt(&mut self, block: BlockId, statement: Statement) {
        self.builder
            .as_mut()
            .expect("a builder exists while lowering")
            .push(block, statement);
    }

    fn term(&mut self, block: BlockId, terminator: Terminator) {
        self.builder
            .as_mut()
            .expect("a builder exists while lowering")
            .terminate(block, terminator);
    }

    fn gap(&mut self, reason: GapReason, detail: impl Into<String>, node: Option<Node<'a>>) {
        let detail = detail.into();
        let span = node.map(|n| span_of(n, self.file));
        let key = (
            format!("{reason:?}/{detail}"),
            span.as_ref().map_or(0, |s| s.start_byte),
        );
        if !self.recorded.insert(key) {
            return;
        }
        self.builder
            .as_mut()
            .expect("a builder exists while lowering")
            .record_gap(AnalysisGap::new(reason, detail, span));
    }

    fn new_guard(&mut self, condition: ValueExpr, span: SourceSpan) -> GuardId {
        let id: GuardId = self.alloc.next_guard();
        self.guards.push(Guard {
            id,
            condition,
            span,
        });
        id
    }

    fn fresh_temp(&mut self) -> ValueExpr {
        let name = format!("$t{}", self.temp);
        self.temp += 1;
        ValueExpr::Symbolic { name }
    }

    // -- statements ---------------------------------------------------------

    fn lower_stmt(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        match node.kind() {
            "block" | "constructor_body" => self.lower_sequence(node, cur),
            "local_variable_declaration" => self.lower_declaration(node, cur),
            "expression_statement" => self.lower_expression_statement(node, cur),
            "update_expression" => self.lower_update(node, cur),
            "assignment_expression" => self.lower_assignment(node, cur),
            "if_statement" => self.lower_if(node, cur),
            "return_statement" => self.lower_return(node, cur),
            "throw_statement" => self.lower_throw(node, cur),
            "while_statement" | "do_statement" | "for_statement" | "enhanced_for_statement" => {
                self.lower_loop(node, cur)
            }
            "try_statement" => self.lower_try(node, cur),
            "try_with_resources_statement" => self.gap_container(
                node,
                cur,
                GapReason::UnsupportedStatement,
                "try-with-resources (resource close order unmodeled)",
            ),
            "synchronized_statement" => self.gap_container(
                node,
                cur,
                GapReason::UnsupportedStatement,
                "synchronized (lock order unmodeled)",
            ),
            "labeled_statement" | "break_statement" | "continue_statement" => self.gap_container(
                node,
                cur,
                GapReason::UnsupportedStatement,
                "abrupt control flow without label tracking",
            ),
            "assert_statement" => {
                self.gap_container(node, cur, GapReason::UnsupportedStatement, "assert")
            }
            "switch_expression" => self.gap_container(
                node,
                cur,
                GapReason::UnsupportedStatement,
                "switch (case dispatch unmodeled; statements kept as may-execute)",
            ),
            // A switch body is a statement container, not a statement: its
            // cases are lowered where the enclosing gap puts them.
            "switch_block" | "switch_block_statement_group" => {
                self.lower_sequence(node, cur)
            }
            // An argument list is an expression container: lower its children
            // in order, never invent an "unsupported statement" for it.
            "argument_list" => {
                let block = self.lower_argument_children(node, cur);
                Flow::Next(block)
            }
            // `this(...)` / `super(...)`: the delegate is not a call site in
            // the flat facts, but its arguments are real effects.
            "explicit_constructor_invocation" => {
                let block = self.lower_argument_children(node, cur);
                self.gap(
                    GapReason::NotInFactContract,
                    "constructor delegation (`this`/`super`) is not a call site in the flat facts",
                    Some(node),
                );
                Flow::Next(block)
            }
            "else_clause" => match first_named_child(node) {
                Some(statement) if statement.kind() != "else" => self.lower_stmt(statement, cur),
                _ => Flow::Next(cur),
            },
            "local_class_declaration" | "class_declaration" => self.gap_container(
                node,
                cur,
                GapReason::UnsupportedStatement,
                "class declaration in a body (its methods are lowered separately)",
            ),
            ";" | "{" | "}" => Flow::Next(cur),
            // An expression where a statement was expected (e.g. the selector
            // of a `switch` inside a gap container) is still an expression: its
            // calls are lowered in order and no "unsupported statement" gap is
            // invented for it.
            other if is_expression_kind(other) => {
                let (_, block) = self.value(node, cur);
                Flow::Next(block)
            }
            other => self.gap_container(
                node,
                cur,
                GapReason::UnsupportedStatement,
                format!("unlowered Java statement `{other}`"),
            ),
        }
    }

    /// Lower a container's statements in order. Statements after a definite
    /// exit are dead; their exclusion is recorded, not silent.
    fn lower_sequence(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let mut block = cur;
        let mut cursor = node.walk();
        let children: Vec<Node<'a>> = node.children(&mut cursor).collect();
        // A statement that diverges (`return`, `throw`, an `if` whose arms all
        // leave) is not itself a gap: only the statements *after* it are
        // unreachable, and each of those is recorded instead of dropped.
        let mut diverged = false;
        for child in children {
            if !child.is_named() || is_non_statement(child.kind()) {
                continue;
            }
            if diverged {
                self.gap(
                    GapReason::UnsupportedStatement,
                    format!(
                        "unreachable after a definite exit, not lowered (`{}`)",
                        child.kind()
                    ),
                    Some(child),
                );
                continue;
            }
            match self.lower_stmt(child, block) {
                Flow::Next(next) => block = next,
                Flow::Diverges => diverged = true,
            }
        }
        if diverged {
            Flow::Diverges
        } else {
            Flow::Next(block)
        }
    }

    fn lower_declaration(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let mut block = cur;
        let mut cursor = node.walk();
        let children: Vec<Node<'a>> = node.children(&mut cursor).collect();
        for declarator in children {
            if declarator.kind() != "variable_declarator" {
                continue;
            }
            let (Some(name), Some(initializer)) = (
                declarator.child_by_field_name("name"),
                declarator.child_by_field_name("value"),
            ) else {
                // A declared-but-uninitialized local carries no value; nothing
                // is known about it, which is exactly `Unknown` on read.
                continue;
            };
            let target = ValueExpr::Symbolic {
                name: node_text(name, self.src),
            };
            let (value, next) = self.value(initializer, block);
            self.stmt(next, Statement::Assign { target, value });
            block = next;
        }
        Flow::Next(block)
    }

    fn lower_expression_statement(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let mut cursor = node.walk();
        let children: Vec<Node<'a>> = node.children(&mut cursor).collect();
        for child in children {
            if !child.is_named() {
                continue;
            }
            if matches!(
                child.kind(),
                "assignment_expression" | "update_expression"
            ) {
                return self.lower_stmt(child, cur);
            }
            let (_, block) = self.value(child, cur);
            return Flow::Next(block);
        }
        Flow::Next(cur)
    }

    fn lower_assignment(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let (Some(left), Some(right)) = (
            node.child_by_field_name("left"),
            node.child_by_field_name("right"),
        ) else {
            return Flow::Next(cur);
        };
        let (target, block) = self.lvalue(left, cur);
        let (value, block) = self.value(right, block);
        self.stmt(block, Statement::Assign { target, value });
        Flow::Next(block)
    }

    fn lower_update(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let op = if node_text(node, self.src).contains("++") {
            BinaryOp::Add
        } else {
            BinaryOp::Sub
        };
        let Some(operand) = first_named_child(node) else {
            return Flow::Next(cur);
        };
        let (target, block) = self.lvalue(operand, cur);
        let value = ValueExpr::Binary {
            op,
            lhs: Box::new(target.clone()),
            rhs: Box::new(ValueExpr::Int { value: 1 }),
        };
        self.stmt(block, Statement::Assign { target, value });
        Flow::Next(block)
    }

    /// Left-hand side of an assignment. Names and field paths are values;
    /// anything else is a heap position the model does not track.
    fn lvalue(&mut self, node: Node<'a>, cur: BlockId) -> (ValueExpr, BlockId) {
        let (target, block) = self.value(node, cur);
        if target == ValueExpr::Unknown {
            self.gap(
                GapReason::UnsupportedExpression,
                "assignment target is not a tracked name",
                Some(node),
            );
        }
        (target, block)
    }

    fn lower_if(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let condition_node = node.child_by_field_name("condition");
        let (condition, block) = match condition_node {
            Some(condition) => self.value(condition, cur),
            None => (ValueExpr::Unknown, cur),
        };
        let guard = self.new_guard(condition.clone(), span_of(node, self.file));
        let then_block = self.block(Some(span_of(node, self.file)));
        let else_block = self.block(None);
        self.term(
            block,
            Terminator::Branch {
                guard,
                condition,
                then_block,
                else_block,
            },
        );
        let then_flow = match node.child_by_field_name("consequence") {
            Some(consequence) => self.lower_stmt(consequence, then_block),
            None => Flow::Next(then_block),
        };
        let else_flow = match node.child_by_field_name("alternative") {
            Some(alternative) => self.lower_stmt(alternative, else_block),
            None => Flow::Next(else_block),
        };
        self.join(then_flow, else_flow)
    }

    fn join(&mut self, then_flow: Flow, else_flow: Flow) -> Flow {
        match (then_flow, else_flow) {
            (Flow::Diverges, Flow::Diverges) => Flow::Diverges,
            (then_flow, else_flow) => {
                let join = self.block(None);
                if let Flow::Next(block) = then_flow {
                    self.term(block, Terminator::Goto { next: join });
                }
                if let Flow::Next(block) = else_flow {
                    self.term(block, Terminator::Goto { next: join });
                }
                Flow::Next(join)
            }
        }
    }

    fn lower_return(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let (value, block) = match first_named_child(node) {
            Some(expression) => {
                let (value, block) = self.value(expression, cur);
                (Some(value), block)
            }
            None => (None, cur),
        };
        // The value is read *before* any `finally` body runs: `return x;` with a
        // `finally` that writes `x` returns the value `x` had here, so it is
        // stamped into a temporary first.
        let value = value.map(|value| self.stamped(block, value));
        // `finally` runs before control actually leaves, so it is inlined here.
        match self.inline_finally(block) {
            Some(block) => {
                self.term(block, Terminator::Return { value });
                Flow::Diverges
            }
            // A `finally` body that returns or throws supersedes this
            // completion: it already terminated the path, and this `return`
            // must not be emitted at all.
            None => Flow::Diverges,
        }
    }

    fn lower_throw(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let (value, block) = match first_named_child(node) {
            Some(expression) => self.value(expression, cur),
            None => (ValueExpr::Unknown, cur),
        };
        let value = self.stamped(block, value);
        match self.inline_finally(block) {
            Some(block) => {
                self.term(block, Terminator::Throw { value });
                Flow::Diverges
            }
            None => Flow::Diverges,
        }
    }

    /// Stamp a value that must be read before a `finally` body runs.
    fn stamped(&mut self, block: BlockId, value: ValueExpr) -> ValueExpr {
        if self.finally.is_empty() || matches!(value, ValueExpr::Unknown) {
            return value;
        }
        let temp = self.fresh_temp();
        self.stmt(
            block,
            Statement::Assign {
                target: temp.clone(),
                value,
            },
        );
        temp
    }

    /// Run exactly the `finally` clause of the `try` being lowered, if any: the
    /// cleanup of a completion that stays inside this `try` (its normal end, or
    /// a `catch` that ends normally). Enclosing clauses are deliberately *not*
    /// run — they belong to their own `try` and run when it completes or when a
    /// `return`/`throw` leaves it.
    ///
    /// `None` in, `None` out: a previous step already diverged. `None` out with
    /// a clause means the clause's own body diverged (it returned or threw),
    /// superseding the completion being carried.
    fn run_finally(&mut self, clause: Option<Node<'a>>, block: Option<BlockId>) -> Option<BlockId> {
        let block = block?;
        let Some(clause) = clause else {
            return Some(block);
        };
        let Some(body) = finally_body(clause) else {
            return Some(block);
        };
        // The clause must not re-enter itself while its own body is lowered:
        // a `return`/`throw` inside it inlines the clauses *outside* it.
        let pos = self.finally.iter().position(|c| c.id() == clause.id());
        let removed = pos.map(|p| self.finally.remove(p));
        let out = match self.lower_stmt(body, block) {
            Flow::Next(next) => Some(next),
            Flow::Diverges => None,
        };
        if let (Some(p), Some(removed)) = (pos, removed) {
            self.finally.insert(p, removed);
        }
        out
    }

    /// Inline every active `finally` body, innermost first, into `block`.
    ///
    /// `Some(block)` is where normal completion continues. `None` means a
    /// `finally` body diverged: a `return` or `throw` inside it overrides the
    /// completion being carried, so the caller must not emit its own
    /// `return`/`goto` — the clause already terminated the path (and, by
    /// recursing through `lower_return`, the clauses outside it).
    ///
    /// A `finally` body only sees the `finally` clauses *outside* it, so a
    /// `return` inside a `finally` cannot re-enter the clause it belongs to.
    fn inline_finally(&mut self, block: BlockId) -> Option<BlockId> {
        let saved = std::mem::take(&mut self.finally);
        let mut block = Some(block);
        for (i, clause) in saved.iter().enumerate().rev() {
            self.finally = saved[..i].to_vec();
            let Some(body) = finally_body(*clause) else {
                continue;
            };
            let Some(current) = block else {
                // The clause further in already diverged and inlined the
                // clauses outside it on its way out.
                break;
            };
            match self.lower_stmt(body, current) {
                Flow::Next(next) => block = Some(next),
                Flow::Diverges => block = None,
            }
        }
        self.finally = saved;
        block
    }

    fn lower_loop(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        match node.kind() {
            "do_statement" => self.lower_do(node, cur),
            "for_statement" => self.lower_for(node, cur),
            "enhanced_for_statement" => self.lower_foreach(node, cur),
            _ => self.lower_while(node, cur),
        }
    }

    fn lower_while(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let header = self.block(None);
        self.term(cur, Terminator::Goto { next: header });
        let (condition, block) = match node.child_by_field_name("condition") {
            Some(condition) => self.value(condition, header),
            None => (ValueExpr::Bool { value: true }, header),
        };
        let guard = self.new_guard(condition.clone(), span_of(node, self.file));
        let body = self.block(Some(span_of(node, self.file)));
        let exit = self.block(None);
        self.term(
            block,
            Terminator::Branch {
                guard,
                condition,
                then_block: body,
                else_block: exit,
            },
        );
        let flow = match node.child_by_field_name("body") {
            Some(body_node) => self.lower_stmt(body_node, body),
            None => Flow::Next(body),
        };
        if let Flow::Next(end) = flow {
            self.term(end, Terminator::Goto { next: header });
        }
        Flow::Next(exit)
    }

    fn lower_do(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let body = self.block(Some(span_of(node, self.file)));
        self.term(cur, Terminator::Goto { next: body });
        let flow = match node.child_by_field_name("body") {
            Some(body_node) => self.lower_stmt(body_node, body),
            None => Flow::Next(body),
        };
        let Flow::Next(end) = flow else {
            return Flow::Diverges;
        };
        let (condition, block) = match node.child_by_field_name("condition") {
            Some(condition) => self.value(condition, end),
            None => (ValueExpr::Bool { value: true }, end),
        };
        let guard = self.new_guard(condition.clone(), span_of(node, self.file));
        let exit = self.block(None);
        self.term(
            block,
            Terminator::Branch {
                guard,
                condition,
                // `do` runs the body before testing: the exit is reached only
                // when the condition does not hold.
                then_block: body,
                else_block: exit,
            },
        );
        Flow::Next(exit)
    }

    fn lower_for(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let mut block = cur;
        if let Some(init) = node.child_by_field_name("init") {
            match self.lower_stmt(init, block) {
                Flow::Next(next) => block = next,
                Flow::Diverges => return Flow::Diverges,
            }
        }
        let header = self.block(None);
        self.term(block, Terminator::Goto { next: header });
        let (condition, block) = match node.child_by_field_name("condition") {
            Some(condition) => self.value(condition, header),
            None => (ValueExpr::Bool { value: true }, header),
        };
        let guard = self.new_guard(condition.clone(), span_of(node, self.file));
        let body = self.block(Some(span_of(node, self.file)));
        let exit = self.block(None);
        self.term(
            block,
            Terminator::Branch {
                guard,
                condition,
                then_block: body,
                else_block: exit,
            },
        );
        let flow = match node.child_by_field_name("body") {
            Some(body_node) => self.lower_stmt(body_node, body),
            None => Flow::Next(body),
        };
        if let Flow::Next(end) = flow {
            let end = match node.child_by_field_name("update") {
                Some(update) => match self.lower_stmt(update, end) {
                    Flow::Next(next) => next,
                    // An update that leaves the function ends the loop; the
                    // exit block is then dead (reported as a note).
                    Flow::Diverges => return Flow::Next(exit),
                },
                None => end,
            };
            self.term(end, Terminator::Goto { next: header });
        }
        Flow::Next(exit)
    }

    fn lower_foreach(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let header = self.block(None);
        self.term(cur, Terminator::Goto { next: header });
        // The iterator protocol is not modeled: the header condition is
        // `Unknown`, which reaches both the body and the exit.
        let condition = ValueExpr::Unknown;
        let guard = self.new_guard(condition.clone(), span_of(node, self.file));
        let body = self.block(Some(span_of(node, self.file)));
        let exit = self.block(None);
        self.term(
            header,
            Terminator::Branch {
                guard,
                condition,
                then_block: body,
                else_block: exit,
            },
        );
        let flow = match node.child_by_field_name("body") {
            Some(body_node) => self.lower_stmt(body_node, body),
            None => Flow::Next(body),
        };
        if let Flow::Next(end) = flow {
            self.term(end, Terminator::Goto { next: header });
        }
        Flow::Next(exit)
    }

    fn lower_try(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let mut cursor = node.walk();
        let children: Vec<Node<'a>> = node.children(&mut cursor).collect();
        let body = children
            .iter()
            .copied()
            .find(|c| c.kind() == "block")
            .or_else(|| node.child_by_field_name("body"));
        let catches: Vec<Node<'a>> = children
            .iter()
            .copied()
            .filter(|c| c.kind() == "catch_clause")
            .collect();
        let finally = children
            .iter()
            .copied()
            .find(|c| c.kind() == "finally_clause");
        let Some(body) = body else {
            return Flow::Next(cur);
        };

        if let Some(finally) = finally {
            self.finally.push(finally);
        }
        let flow = self.lower_stmt(body, cur);

        // Normal completion: only *this* `try`'s own cleanup runs, then control
        // continues after the statement. An enclosing `finally` belongs to its
        // own `try`: it runs when that `try` completes, or when control leaves
        // it through a `return`/`throw` (which inlines every active clause).
        // Running the whole stack here made an outer `finally` execute in the
        // middle of an inner `try`, so `return x` read the cleanup's value.
        let after = self.block(None);
        let normal = match flow {
            Flow::Next(block) => match self.run_finally(finally, Some(block)) {
                Some(block) => {
                    self.term(block, Terminator::Goto { next: after });
                    true
                }
                // The `finally` body returned or threw: normal completion never
                // reaches the statement after the `try`.
                None => false,
            },
            Flow::Diverges => false,
        };

        // `catch` dispatch is unmodeled: each catch body stays reachable as a
        // *may* path, so its calls are `Possible`, never `Confirmed`. A catch
        // that completes normally also runs the `finally` body.
        let mut catch_reachable = false;
        for catch in catches {
            let block = self.builder.as_mut().expect("builder").gap_block(
                self.alloc,
                GapReason::ExceptionDispatch,
                "catch clause: which arm runs depends on a thrown value",
                Some(span_of(catch, self.file)),
                cur,
            );
            let end = match catch.child_by_field_name("body") {
                Some(body) => match self.lower_stmt(body, block) {
                    Flow::Next(end) => Some(end),
                    Flow::Diverges => None,
                },
                None => Some(block),
            };
            let end = self.run_finally(finally, end);
            if let Some(end) = end {
                self.term(end, Terminator::Goto { next: after });
                catch_reachable = true;
            }
        }

        if finally.is_some() {
            self.finally.pop();
        }

        if normal || catch_reachable {
            Flow::Next(after)
        } else {
            // Neither the normal path nor a catch reaches `after`; leave it
            // unreachable rather than pretend it is live.
            Flow::Diverges
        }
    }

    /// Lower an unsupported construct conservatively: `cur` keeps its normal
    /// continuation, and the construct's statements are lowered into a block
    /// reachable only through the unmodeled mechanism, so their effects remain
    /// possible instead of disappearing.
    fn gap_container(
        &mut self,
        node: Node<'a>,
        cur: BlockId,
        reason: GapReason,
        detail: impl Into<String>,
    ) -> Flow {
        let detail = detail.into();
        let after = self.block(None);
        let gap_block = self.builder.as_mut().expect("builder").gap_block(
            self.alloc,
            reason,
            detail.clone(),
            Some(span_of(node, self.file)),
            cur,
        );
        self.term(
            cur,
            Terminator::Gap {
                reason,
                detail,
                next: Some(after),
            },
        );
        if let Flow::Next(end) = self.lower_sequence(node, gap_block) {
            self.term(end, Terminator::Goto { next: after });
        }
        Flow::Next(after)
    }

    // -- values -------------------------------------------------------------

    /// Lower an expression in value position. Ternary and short-circuit
    /// operators are *control flow*, so the returned value may be a
    /// materialized temp and the continuation block may differ from `cur`.
    fn value(&mut self, node: Node<'a>, cur: BlockId) -> (ValueExpr, BlockId) {
        match node.kind() {
            "ternary_expression" => self.lower_ternary(node, cur),
            "binary_expression" if self.binary_op(node) == Some(BinaryOp::And) => {
                self.lower_short_circuit(node, cur, BinaryOp::And)
            }
            "binary_expression" if self.binary_op(node) == Some(BinaryOp::Or) => {
                self.lower_short_circuit(node, cur, BinaryOp::Or)
            }
            "parenthesized_expression" | "cast_expression" => {
                let inner = if node.kind() == "cast_expression" {
                    node.child_by_field_name("value")
                } else {
                    first_named_child(node)
                };
                match inner {
                    Some(inner) => self.value(inner, cur),
                    None => (ValueExpr::Unknown, cur),
                }
            }
            _ => self.simple_value(node, cur),
        }
    }

    fn binary_op(&self, node: Node<'a>) -> Option<BinaryOp> {
        let operator = node.child_by_field_name("operator")?;
        map_binop(&node_text(operator, self.src))
    }

    fn lower_ternary(&mut self, node: Node<'a>, cur: BlockId) -> (ValueExpr, BlockId) {
        let condition_node = node.child_by_field_name("condition");
        let (condition, block) = match condition_node {
            Some(condition) => self.value(condition, cur),
            None => (ValueExpr::Unknown, cur),
        };
        let guard = self.new_guard(
            condition.clone(),
            condition_node.map_or_else(|| span_of(node, self.file), |n| span_of(n, self.file)),
        );
        let then_block = self.block(None);
        let else_block = self.block(None);
        self.term(
            block,
            Terminator::Branch {
                guard,
                condition,
                then_block,
                else_block,
            },
        );
        let temp = self.fresh_temp();
        let mut exits: Vec<BlockId> = Vec::new();
        for (arm, block) in [
            (node.child_by_field_name("consequence"), then_block),
            (node.child_by_field_name("alternative"), else_block),
        ] {
            let (value, block) = match arm {
                Some(arm) => self.value(arm, block),
                None => (ValueExpr::Unknown, block),
            };
            self.stmt(
                block,
                Statement::Assign {
                    target: temp.clone(),
                    value,
                },
            );
            // An arm's expression may have materialized blocks of its own (a
            // nested ternary): the arm *exits* here, which is not the block it
            // entered. Terminating the entry instead used to overwrite the
            // nested branch and drop the arm's value.
            exits.push(block);
        }
        let join = self.block(None);
        for exit in exits {
            self.term(exit, Terminator::Goto { next: join });
        }
        (temp, join)
    }

    fn lower_short_circuit(
        &mut self,
        node: Node<'a>,
        cur: BlockId,
        op: BinaryOp,
    ) -> (ValueExpr, BlockId) {
        let lhs = node.child_by_field_name("left");
        let rhs = node.child_by_field_name("right");
        let (left, block) = match lhs {
            Some(lhs) => self.value(lhs, cur),
            None => (ValueExpr::Unknown, cur),
        };
        let guard = self.new_guard(
            left.clone(),
            lhs.map_or_else(|| span_of(node, self.file), |n| span_of(n, self.file)),
        );
        let rhs_block = self.block(None);
        let short_block = self.block(None);
        // `&&`: a false left value short-circuits (else arm). `||`: a true left
        // value short-circuits (then arm).
        let (then_block, else_block) = match op {
            BinaryOp::And => (rhs_block, short_block),
            _ => (short_block, rhs_block),
        };
        self.term(
            block,
            Terminator::Branch {
                guard,
                condition: left.clone(),
                then_block,
                else_block,
            },
        );
        let temp = self.fresh_temp();
        // The short-circuit arm takes the left value itself.
        self.stmt(
            short_block,
            Statement::Assign {
                target: temp.clone(),
                value: left,
            },
        );
        let (right, block) = match rhs {
            Some(rhs) => self.value(rhs, rhs_block),
            None => (ValueExpr::Unknown, rhs_block),
        };
        self.stmt(
            block,
            Statement::Assign {
                target: temp.clone(),
                value: right,
            },
        );
        let join = self.block(None);
        self.term(short_block, Terminator::Goto { next: join });
        self.term(block, Terminator::Goto { next: join });
        (temp, join)
    }

    /// Lower an expression that is a *value* and cannot change control flow on
    /// its own. Calls are hoisted into the continuation block in evaluation
    /// order; nested control-flow values (a ternary or `&&` inside another
    /// expression) materialize their own blocks and return the join.
    fn simple_value(&mut self, node: Node<'a>, cur: BlockId) -> (ValueExpr, BlockId) {
        match node.kind() {
            "identifier" | "type_identifier" | "scoped_identifier" => (
                ValueExpr::Symbolic {
                    name: node_text(node, self.src),
                },
                cur,
            ),
            "this" | "super" => (
                ValueExpr::Symbolic {
                    name: node_text(node, self.src),
                },
                cur,
            ),
            "string_literal" | "character_literal" => (
                ValueExpr::Str {
                    value: unquote(&node_text(node, self.src)),
                },
                cur,
            ),
            "decimal_integer_literal" | "hex_integer_literal" | "octal_integer_literal"
            | "binary_integer_literal" => (self.integer(node), cur),
            "decimal_floating_point_literal" | "hex_floating_point_literal" => {
                (self.float(node), cur)
            }
            "true" => (ValueExpr::Bool { value: true }, cur),
            "false" => (ValueExpr::Bool { value: false }, cur),
            "null_literal" => (ValueExpr::Null, cur),
            "field_access" => {
                let (base, block) = match node.child_by_field_name("object") {
                    Some(object) => self.value(object, cur),
                    None => (ValueExpr::Unknown, cur),
                };
                let name = node
                    .child_by_field_name("field")
                    .map_or_else(String::new, |f| node_text(f, self.src));
                (
                    ValueExpr::Field {
                        base: Box::new(base),
                        name,
                    },
                    block,
                )
            }
            "array_access" => {
                let mut block = cur;
                for part in [
                    node.child_by_field_name("array"),
                    node.child_by_field_name("index"),
                ]
                .into_iter()
                .flatten()
                {
                    let (_, next) = self.value(part, block);
                    block = next;
                }
                self.gap(
                    GapReason::UnsupportedExpression,
                    "array element state is not modeled",
                    Some(node),
                );
                (ValueExpr::Unknown, block)
            }
            "method_invocation" => {
                let mut block = cur;
                if let Some(object) = node.child_by_field_name("object") {
                    let (_, next) = self.value(object, block);
                    block = next;
                }
                let block = self.lower_argument_children(node, block);
                match self.index.get(node) {
                    Some(id) => {
                        self.stmt(
                            block,
                            Statement::Eval {
                                value: ValueExpr::CallResult { callsite: id },
                            },
                        );
                        (ValueExpr::CallResult { callsite: id }, block)
                    }
                    // The flat walk registers exactly one call site per
                    // `method_invocation`; a miss means the shape is outside
                    // that contract, so the value stays unknown.
                    None => {
                        self.gap(
                            GapReason::UnresolvedCall,
                            format!("no call site registered for `{}`", self.callee(node)),
                            Some(node),
                        );
                        (ValueExpr::Unknown, block)
                    }
                }
            }
            "binary_expression" => {
                let op = self.binary_op(node);
                let (left, block) = match node.child_by_field_name("left") {
                    Some(left) => self.value(left, cur),
                    None => (ValueExpr::Unknown, cur),
                };
                let (right, block) = match node.child_by_field_name("right") {
                    Some(right) => self.value(right, block),
                    None => (ValueExpr::Unknown, block),
                };
                match op {
                    Some(op) => (
                        ValueExpr::Binary {
                            op,
                            lhs: Box::new(left),
                            rhs: Box::new(right),
                        },
                        block,
                    ),
                    None => {
                        let operator = node
                            .child_by_field_name("operator")
                            .map_or_else(String::new, |o| node_text(o, self.src));
                        self.gap(
                            GapReason::UnsupportedExpression,
                            format!("unmapped binary operator `{operator}`"),
                            Some(node),
                        );
                        (ValueExpr::Unknown, block)
                    }
                }
            }
            "unary_expression" => {
                let operator = node
                    .child_by_field_name("operator")
                    .map_or_else(String::new, |o| node_text(o, self.src));
                let (operand, block) = match node.child_by_field_name("operand") {
                    Some(operand) => self.value(operand, cur),
                    None => (ValueExpr::Unknown, cur),
                };
                match operator.as_str() {
                    "!" => (
                        ValueExpr::Unary {
                            op: UnaryOp::Not,
                            operand: Box::new(operand),
                        },
                        block,
                    ),
                    "-" => (
                        ValueExpr::Unary {
                            op: UnaryOp::Negate,
                            operand: Box::new(operand),
                        },
                        block,
                    ),
                    _ => {
                        self.gap(
                            GapReason::UnsupportedExpression,
                            format!("unmapped unary operator `{operator}`"),
                            Some(node),
                        );
                        (ValueExpr::Unknown, block)
                    }
                }
            }
            "update_expression" => {
                if let Some(operand) = first_named_child(node) {
                    let _ = self.value(operand, cur);
                }
                (ValueExpr::Unknown, cur)
            }
            "object_creation_expression" => {
                let block = self.lower_argument_children(node, cur);
                self.gap(
                    GapReason::NotInFactContract,
                    "object creation (`new`) is not a call site in the flat facts",
                    Some(node),
                );
                (ValueExpr::Unknown, block)
            }
            "array_creation_expression" | "array_initializer" => {
                let block = self.lower_argument_children(node, cur);
                (ValueExpr::Unknown, block)
            }
            // `Foo.class` is a static reference to a class object. The class
            // object itself is not a tracked value, but the literal has no
            // effects and needs no gap.
            "class_literal" => (
                ValueExpr::Symbolic {
                    name: node_text(node, self.src),
                },
                cur,
            ),
            "lambda_expression" | "switch_expression" => {
                self.gap(
                    GapReason::UnsupportedExpression,
                    format!("`{}` in value position", node.kind()),
                    Some(node),
                );
                (ValueExpr::Unknown, cur)
            }
            other => {
                self.gap(
                    GapReason::UnsupportedExpression,
                    format!("unlowered Java expression `{other}`"),
                    Some(node),
                );
                (ValueExpr::Unknown, cur)
            }
        }
    }

    fn callee(&self, node: Node<'a>) -> String {
        node.child_by_field_name("name")
            .map_or_else(String::new, |n| node_text(n, self.src))
    }

    /// Lower the children of an argument list (or of a literal) for their
    /// effects, preserving order.
    fn lower_argument_children(&mut self, node: Node<'a>, cur: BlockId) -> BlockId {
        // `method_invocation`, `object_creation_expression` and
        // `explicit_constructor_invocation` all carry an `arguments` field;
        // anything else is itself the list.
        let list = node.child_by_field_name("arguments").or(Some(node));
        let Some(list) = list else {
            return cur;
        };
        let mut block = cur;
        let mut cursor = list.walk();
        let children: Vec<Node<'a>> = list.children(&mut cursor).collect();
        for child in children {
            if child.is_named() && !child.kind().contains("comment") {
                let (_, next) = self.value(child, block);
                block = next;
            }
        }
        block
    }

    fn integer(&mut self, node: Node<'a>) -> ValueExpr {
        let text = node_text(node, self.src);
        let (radix, digits) = literal_radix(&text);
        match i64::from_str_radix(&digits, radix) {
            Ok(value) => ValueExpr::Int { value },
            Err(_) => {
                self.gap(
                    GapReason::UnsupportedExpression,
                    format!("integer literal outside i64: `{text}`"),
                    Some(node),
                );
                ValueExpr::Unknown
            }
        }
    }

    fn float(&mut self, node: Node<'a>) -> ValueExpr {
        let text = node_text(node, self.src);
        let cleaned: String = text.trim_end_matches(['f', 'F', 'd', 'D']).replace('_', "");
        match cleaned.parse::<f64>() {
            Ok(value) => ValueExpr::Float { value },
            Err(_) => {
                self.gap(
                    GapReason::UnsupportedExpression,
                    format!("floating literal outside f64: `{text}`"),
                    Some(node),
                );
                ValueExpr::Unknown
            }
        }
    }
}

/// Radix and digit string of a Java integer literal.
fn literal_radix(text: &str) -> (u32, String) {
    let trimmed = text.trim_end_matches(['l', 'L']);
    let lower = trimmed.to_ascii_lowercase();
    if let Some(digits) = lower.strip_prefix("0x") {
        (16, digits.replace('_', ""))
    } else if let Some(digits) = lower.strip_prefix("0b") {
        (2, digits.replace('_', ""))
    } else if trimmed.len() > 1 && trimmed.starts_with('0') {
        (8, trimmed[1..].replace('_', ""))
    } else {
        (10, trimmed.replace('_', ""))
    }
}

fn first_named_child(node: Node<'_>) -> Option<Node<'_>> {
    let mut cursor = node.walk();
    let children: Vec<Node<'_>> = node.children(&mut cursor).collect();
    children.into_iter().find(Node::is_named)
}

fn finally_body(clause: Node<'_>) -> Option<Node<'_>> {
    let mut cursor = clause.walk();
    let children: Vec<Node<'_>> = clause.children(&mut cursor).collect();
    children
        .into_iter()
        .find(|c| c.kind() == "block")
        .or_else(|| clause.child_by_field_name("body"))
}

/// Kinds of expressions. An expression appearing where a statement was
/// expected is lowered for its effects, not recorded as an unsupported
/// statement.
fn is_expression_kind(kind: &str) -> bool {
    matches!(
        kind,
        "identifier"
            | "field_access"
            | "method_invocation"
            | "binary_expression"
            | "unary_expression"
            | "ternary_expression"
            | "parenthesized_expression"
            | "cast_expression"
            | "object_creation_expression"
            | "array_creation_expression"
            | "array_access"
            | "array_initializer"
            | "update_expression"
            | "assignment_expression"
            | "lambda_expression"
            | "string_literal"
            | "character_literal"
            | "decimal_integer_literal"
            | "hex_integer_literal"
            | "octal_integer_literal"
            | "binary_integer_literal"
            | "decimal_floating_point_literal"
            | "hex_floating_point_literal"
            | "true"
            | "false"
            | "null_literal"
            | "this"
    )
}

/// Kinds that appear as children of a statement container but are not
/// statements themselves (modifiers, types, parameters, labels).
fn is_non_statement(kind: &str) -> bool {
    matches!(
        kind,
        "comment"
            | "line_comment"
            | "block_comment"
            | "modifiers"
            | "marker_annotation"
            | "annotation"
            | "type_identifier"
            | "integral_type"
            | "floating_point_type"
            | "boolean_type"
            | "void_type"
            | "catch_formal_parameter"
            | "formal_parameter"
            | "variable_declarator"
            | "switch_label"
            | "switch_rule"
            | "identifier"
            | "this"
            | "super"
            | "spread_parameter"
    )
}
