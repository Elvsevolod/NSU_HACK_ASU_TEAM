//! Python statement lowering into ordered basic blocks (N03).
//!
//! The Python counterpart of `semarch_frontend_java::lowering`, proving the
//! ordered IR and its control-flow semantics are language-neutral: the same
//! [`Statement`](semarch_core::ir::Statement) /
//! [`Terminator`](semarch_core::ir::Terminator) types, the same gap discipline,
//! but Python's own constructs. As in Java, this pass runs after the flat fact
//! walk and only reads the call sites the walk registered (by span), so the
//! flat contract stays unchanged.
//!
//! # Support matrix
//!
//! Lowered: `block` statement sequences, `assignment` / `augmented_assignment`
//! (including chains), expression statements, `if` / `elif` / `else`, `while`
//! (with `else`), `for` (with `else`), `return`, `raise`, `try`–`finally` (the
//! `finally` body is inlined before every exit), `and` / `or` as branching, and
//! `a if c else b` as two arms joined by a temp.
//!
//! Recorded as a gap, never dropped: `except` / `else` dispatch (their bodies
//! stay reachable as *may* paths), `with` (context-manager enter/exit
//! unmodeled), `assert`, `del`, `match`, `break` / `continue`, comprehensions,
//! lambda bodies, `yield` / `await`.
//!
//! Falsy truthiness (`if 0:`) is *not* decided here: the guard carries the
//! value and [`semarch_core::value::LanguageProfile::python`] decides it.

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
    Next(BlockId),
    Diverges,
}

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

/// Lower all function bodies of one file.
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
    recorded: HashSet<(String, u32)>,
}

impl<'a> Lowerer<'a> {
    fn collect(
        &mut self,
        node: Node<'a>,
        by_start: &HashMap<u32, FunctionId>,
        out: &mut Vec<FunctionBody>,
    ) {
        if node.kind() == "function_definition" {
            if let (Some(body), Some(&function)) = (
                node.child_by_field_name("body"),
                by_start.get(&(node.start_byte() as u32)),
            ) {
                out.push(self.lower_method(function, body));
                // A nested `def` also has a dense function id (the flat walk
                // collects it too), so lower it.
                self.collect(body, by_start, out);
            }
            return;
        }
        let mut cursor = node.walk();
        let children: Vec<Node<'a>> = node.children(&mut cursor).collect();
        for child in children {
            if child.kind() == "lambda" {
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
            // Falling off the end of a Python body returns `None`; that is
            // both the implicit return of a procedure and the value of a
            // function with no explicit `return`.
            self.term(
                tail,
                Terminator::Return {
                    value: Some(ValueExpr::Null),
                },
            );
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
            "block" => self.lower_sequence(node, cur),
            "expression_statement" => self.lower_expression_statement(node, cur),
            "assignment" => self.lower_assignment(node, cur),
            "augmented_assignment" => self.lower_augmented(node, cur),
            "if_statement" => self.lower_conditional(node, cur),
            "elif_clause" => self.lower_conditional(node, cur),
            "else_clause" => match suite_body(node) {
                Some(body) => self.lower_stmt(body, cur),
                None => Flow::Next(cur),
            },
            "while_statement" => self.lower_while(node, cur),
            "for_statement" => self.lower_for(node, cur),
            "return_statement" => self.lower_return(node, cur),
            "raise_statement" => self.lower_raise(node, cur),
            "try_statement" => self.lower_try(node, cur),
            "with_statement" => self.gap_container(
                node,
                cur,
                GapReason::UnsupportedStatement,
                "with (context-manager enter/exit unmodeled)",
            ),
            "assert_statement" => {
                self.gap_container(node, cur, GapReason::UnsupportedStatement, "assert")
            }
            "delete_statement" => {
                self.gap_container(node, cur, GapReason::UnsupportedStatement, "del")
            }
            "match_statement" => self.gap_container(
                node,
                cur,
                GapReason::UnsupportedStatement,
                "match (pattern dispatch unmodeled)",
            ),
            "break_statement" | "continue_statement" => self.gap_container(
                node,
                cur,
                GapReason::UnsupportedStatement,
                "abrupt control flow without loop-target tracking",
            ),
            "pass_statement" | "comment" | "line_continuation" | "decorated_definition"
            | "import_statement" | "import_from_statement" | "future_import_statement"
            | "global_statement" | "nonlocal_statement" => Flow::Next(cur),
            other => self.gap_container(
                node,
                cur,
                GapReason::UnsupportedStatement,
                format!("unlowered Python statement `{other}`"),
            ),
        }
    }

    fn lower_sequence(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let mut block = cur;
        let mut cursor = node.walk();
        let children: Vec<Node<'a>> = node.children(&mut cursor).collect();
        // As in Java: the diverging statement is not a gap, only the
        // statements after it are, and each is recorded rather than dropped.
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

    fn lower_expression_statement(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        match first_named_child(node) {
            // tree-sitter-python wraps assignments in `expression_statement`;
            // they are statements, not values, and must not be lowered as one.
            Some(child) if matches!(child.kind(), "assignment" | "augmented_assignment") => {
                self.lower_stmt(child, cur)
            }
            Some(statement) => {
                let (_, block) = self.value(statement, cur);
                Flow::Next(block)
            }
            None => Flow::Next(cur),
        }
    }

    fn lower_assignment(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let (Some(left), Some(right)) = (
            node.child_by_field_name("left"),
            node.child_by_field_name("right"),
        ) else {
            return Flow::Next(cur);
        };
        let (target, block) = self.lvalue(left, cur);
        // `a = b = c` nests on the right: the inner assignment runs first, and
        // the outer target then takes the inner target's value.
        if right.kind() == "assignment" {
            let inner_target = right.child_by_field_name("left");
            let Flow::Next(block) = self.lower_assignment(right, block) else {
                return Flow::Diverges;
            };
            let value = match inner_target {
                Some(inner) => self.value(inner, block).0,
                None => ValueExpr::Unknown,
            };
            self.stmt(block, Statement::Assign { target, value });
            return Flow::Next(block);
        }
        let (value, block) = self.value(right, block);
        self.stmt(block, Statement::Assign { target, value });
        Flow::Next(block)
    }

    fn lower_augmented(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        // tree-sitter-python gives `augmented_assignment` no fields: the shape
        // is `left`, the operator token, `right`.
        let children = named_children(node);
        let all = {
            let mut cursor = node.walk();
            node.children(&mut cursor).collect::<Vec<_>>()
        };
        let (Some(left), Some(right)) = (children.first().copied(), children.last().copied())
        else {
            return Flow::Next(cur);
        };
        let operator = all
            .iter()
            .find(|c| !c.is_named() && c.start_byte() >= left.end_byte())
            .map_or_else(String::new, |o| node_text(*o, self.src));
        let (target, block) = self.lvalue(left, cur);
        let (right, block) = self.value(right, block);
        let Some(op) = map_binop(operator.trim_end_matches('=')) else {
            self.gap(
                GapReason::UnsupportedExpression,
                format!("unmapped augmented operator `{operator}`"),
                Some(node),
            );
            return Flow::Next(block);
        };
        let value = ValueExpr::Binary {
            op,
            lhs: Box::new(target.clone()),
            rhs: Box::new(right),
        };
        self.stmt(block, Statement::Assign { target, value });
        Flow::Next(block)
    }

    /// Left-hand side of an assignment. Names and attribute paths are values.
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

    /// `if_statement` and `elif_clause` share this shape: condition,
    /// consequence, alternative (an `elif_clause` or `else_clause`).
    fn lower_conditional(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
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
            None => (Some(ValueExpr::Null), cur),
        };
        // The value is read *before* any `finally` body runs: `return x` with a
        // `finally` that writes `x` returns the value `x` had here, so it is
        // stamped into a temporary first.
        let value = value.map(|value| self.stamped(block, value));
        match self.inline_finally(block) {
            Some(block) => {
                self.term(block, Terminator::Return { value });
                Flow::Diverges
            }
            // A `finally` body that returns or raises supersedes this
            // completion: it already terminated the path, and this `return`
            // must not be emitted at all.
            None => Flow::Diverges,
        }
    }

    fn lower_raise(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
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

    /// Inline every active `finally` body, innermost first, into `block`.
    ///
    /// Run exactly the `finally` clause of the `try` being lowered, if any: the
    /// cleanup of a completion that stays inside this `try` (its normal end, or
    /// an `except`/`else` arm that ends normally). Enclosing clauses are
    /// deliberately not run — they belong to their own `try` and run when it
    /// completes, or when a `return`/`raise` leaves it.
    ///
    /// `None` in, `None` out: a previous step already diverged. `None` out with
    /// a clause means the clause's own body diverged.
    fn run_finally(&mut self, clause: Option<Node<'a>>, block: Option<BlockId>) -> Option<BlockId> {
        let block = block?;
        let Some(clause) = clause else {
            return Some(block);
        };
        let Some(body) = suite_body(clause) else {
            return Some(block);
        };
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

    /// `Some(block)` is where normal completion continues. `None` means a
    /// `finally` body diverged: a `return` or `raise` inside it overrides the
    /// completion being carried, so the caller must not emit its own
    /// `return`/`goto`.
    fn inline_finally(&mut self, block: BlockId) -> Option<BlockId> {
        let saved = std::mem::take(&mut self.finally);
        let mut block = Some(block);
        for (i, clause) in saved.iter().enumerate().rev() {
            self.finally = saved[..i].to_vec();
            let Some(body) = suite_body(*clause) else {
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
        // `while ... else` runs only on normal exhaustion, which the loop exit
        // represents.
        self.with_else(node, exit)
    }

    fn lower_for(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        // The iterable is evaluated once, before the loop; the loop variable
        // takes its (unmodeled) element value on each iteration.
        let mut block = cur;
        if let Some(iterable) = node.child_by_field_name("right") {
            let (value, next) = self.value(iterable, block);
            if let Some(target) = node.child_by_field_name("left") {
                let target = self.lvalue_shape(target);
                if target == ValueExpr::Unknown {
                    self.gap(
                        GapReason::UnsupportedExpression,
                        "for-loop target is not a tracked name",
                        Some(target_node(node)),
                    );
                } else {
                    self.stmt(next, Statement::Assign { target, value });
                }
            }
            block = next;
        }
        let header = self.block(None);
        self.term(block, Terminator::Goto { next: header });
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
        self.with_else(node, exit)
    }

    /// Lower an `else` clause attached to a loop, if present.
    fn with_else(&mut self, node: Node<'a>, exit: BlockId) -> Flow {
        let mut exit = exit;
        if let Some(alternative) = node.child_by_field_name("alternative") {
            if let Flow::Next(end) = self.lower_stmt(alternative, exit) {
                exit = end;
            }
        }
        Flow::Next(exit)
    }

    /// The loop variable of a `for` — a name, or a tuple of names (untracked).
    fn lvalue_shape(&self, node: Node<'a>) -> ValueExpr {
        if node.kind() == "identifier" {
            ValueExpr::Symbolic {
                name: node_text(node, self.src),
            }
        } else {
            ValueExpr::Unknown
        }
    }

    fn lower_try(&mut self, node: Node<'a>, cur: BlockId) -> Flow {
        let mut cursor = node.walk();
        let children: Vec<Node<'a>> = node.children(&mut cursor).collect();
        let body = children
            .iter()
            .copied()
            .find(|c| c.kind() == "block")
            .or_else(|| node.child_by_field_name("body"));
        let handlers: Vec<Node<'a>> = children
            .iter()
            .copied()
            .filter(|c| {
                matches!(
                    c.kind(),
                    "except_clause" | "except_group_clause" | "else_clause"
                )
            })
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

        let after = self.block(None);
        let normal = match flow {
            Flow::Next(block) => match self.run_finally(finally, Some(block)) {
                Some(block) => {
                    self.term(block, Terminator::Goto { next: after });
                    true
                }
                // The `finally` body returned or raised: normal completion
                // never reaches the statement after the `try`.
                None => false,
            },
            Flow::Diverges => false,
        };

        // `except` / `else` dispatch is unmodeled: those bodies stay reachable
        // as *may* paths, so their calls are `Possible`, never `Confirmed`.
        let mut handler_reachable = false;
        for handler in handlers {
            let block = self.builder.as_mut().expect("builder").gap_block(
                self.alloc,
                GapReason::ExceptionDispatch,
                "except/else clause: which arm runs depends on a thrown value",
                Some(span_of(handler, self.file)),
                cur,
            );
            let end = match suite_body(handler) {
                Some(body) => match self.lower_stmt(body, block) {
                    Flow::Next(end) => Some(end),
                    Flow::Diverges => None,
                },
                None => Some(block),
            };
            // A handler that completes normally also runs *its own* `finally`
            // body; a `finally` that returns or raises supersedes that
            // completion. Enclosing clauses are not run here.
            let end = self.run_finally(finally, end);
            if let Some(end) = end {
                self.term(end, Terminator::Goto { next: after });
                handler_reachable = true;
            }
        }

        if finally.is_some() {
            self.finally.pop();
        }

        if normal || handler_reachable {
            Flow::Next(after)
        } else {
            Flow::Diverges
        }
    }

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

    /// Value-position gap: the continuation is a fresh block, and the
    /// construct's inner expressions are lowered into a block reachable only
    /// through the unmodeled mechanism, so their calls stay `Possible`.
    fn value_gap_container(
        &mut self,
        node: Node<'a>,
        cur: BlockId,
        reason: GapReason,
        detail: impl Into<String>,
    ) -> BlockId {
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
        for child in named_children(node) {
            let _ = self.value(child, gap_block);
        }
        self.term(gap_block, Terminator::Goto { next: after });
        after
    }

    // -- values -------------------------------------------------------------

    fn value(&mut self, node: Node<'a>, cur: BlockId) -> (ValueExpr, BlockId) {
        match node.kind() {
            "conditional_expression" => self.lower_ternary(node, cur),
            "boolean_operator" => self.lower_boolean(node, cur),
            "parenthesized_expression" => match first_named_child(node) {
                Some(inner) => self.value(inner, cur),
                None => (ValueExpr::Unknown, cur),
            },
            "list_comprehension" | "generator_expression" | "set_comprehension"
            | "dictionary_comprehension" => {
                let block = self.value_gap_container(
                    node,
                    cur,
                    GapReason::UnsupportedExpression,
                    "comprehension (0..N iterations unmodeled)",
                );
                (ValueExpr::Unknown, block)
            }
            _ => self.simple_value(node, cur),
        }
    }

    /// `A if B else C`.
    ///
    /// The Python grammar declares no field names on `conditional_expression`,
    /// so the three parts are taken positionally: the source order is
    /// `consequence if condition else alternative`.
    fn lower_ternary(&mut self, node: Node<'a>, cur: BlockId) -> (ValueExpr, BlockId) {
        let parts = named_children(node);
        let consequence = parts.first().copied();
        let condition_node = parts.get(1).copied();
        let alternative = parts.get(2).copied();
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
        for (arm, block) in [(consequence, then_block), (alternative, else_block)] {
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
            // nested conditional): the arm *exits* here, which is not the block
            // it entered. Terminating the entry instead overwrote the nested
            // branch and dropped the arm's value.
            exits.push(block);
        }
        let join = self.block(None);
        for exit in exits {
            self.term(exit, Terminator::Goto { next: join });
        }
        (temp, join)
    }

    fn lower_boolean(&mut self, node: Node<'a>, cur: BlockId) -> (ValueExpr, BlockId) {
        let operator = node
            .child_by_field_name("operator")
            .map_or_else(String::new, |o| node_text(o, self.src));
        let op = if operator == "or" {
            BinaryOp::Or
        } else {
            BinaryOp::And
        };
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
        // Python's `and`/`or` yield an operand: the short-circuit arm keeps the
        // left value, the other arm the right one.
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

    /// Python's chained comparison: `a < b < c` means `a < b and b < c`, with
    /// `b` evaluated once. tree-sitter-python puts the operands in unnamed
    /// fields and each operator under the repeated `operators` field.
    fn lower_comparison(&mut self, node: Node<'a>, cur: BlockId) -> (ValueExpr, BlockId) {
        let mut operands: Vec<Node<'a>> = Vec::new();
        let mut operators: Vec<String> = Vec::new();
        for i in 0..node.child_count() {
            let Some(child) = node.child(i) else {
                continue;
            };
            if node.field_name_for_child(i) == Some("operators") {
                operators.push(node_text(child, self.src));
            } else if child.is_named() {
                operands.push(child);
            }
        }
        if operands.len() < 2 || operators.len() + 1 != operands.len() {
            self.gap(
                GapReason::UnsupportedExpression,
                format!("unexpected comparison shape with {} operands", operands.len()),
                Some(node),
            );
            return (ValueExpr::Unknown, cur);
        }
        let mut block = cur;
        let mut values = Vec::with_capacity(operands.len());
        for operand in operands {
            let (value, next) = self.value(operand, block);
            values.push(value);
            block = next;
        }
        let mut pairs = Vec::with_capacity(operators.len());
        for (i, text) in operators.iter().enumerate() {
            // `is` / `is not` are identity tests; on scalars equality is a
            // sound abstraction, and it is the idiomatic `x is None` check.
            let op = match text.as_str() {
                "is" => Some(BinaryOp::Eq),
                "is not" => Some(BinaryOp::Ne),
                other => map_binop(other),
            };
            let Some(op) = op else {
                self.gap(
                    GapReason::UnsupportedExpression,
                    format!("unmapped comparison operator `{text}`"),
                    Some(node),
                );
                return (ValueExpr::Unknown, block);
            };
            pairs.push(ValueExpr::Binary {
                op,
                lhs: Box::new(values[i].clone()),
                rhs: Box::new(values[i + 1].clone()),
            });
        }
        let mut out = pairs.remove(0);
        for pair in pairs {
            out = ValueExpr::Binary {
                op: BinaryOp::And,
                lhs: Box::new(out),
                rhs: Box::new(pair),
            };
        }
        (out, block)
    }

    fn simple_value(&mut self, node: Node<'a>, cur: BlockId) -> (ValueExpr, BlockId) {
        match node.kind() {
            "identifier" => (
                ValueExpr::Symbolic {
                    name: node_text(node, self.src),
                },
                cur,
            ),
            "string" | "string_start" => (
                ValueExpr::Str {
                    value: unquote(&node_text(node, self.src)),
                },
                cur,
            ),
            "integer" => match node_text(node, self.src).replace('_', "").parse::<i64>() {
                Ok(value) => (ValueExpr::Int { value }, cur),
                Err(_) => {
                    self.gap(
                        GapReason::UnsupportedExpression,
                        format!("integer literal outside i64: `{}`", node_text(node, self.src)),
                        Some(node),
                    );
                    (ValueExpr::Unknown, cur)
                }
            },
            "float" => match node_text(node, self.src).replace('_', "").parse::<f64>() {
                Ok(value) => (ValueExpr::Float { value }, cur),
                Err(_) => {
                    self.gap(
                        GapReason::UnsupportedExpression,
                        format!("float literal outside f64: `{}`", node_text(node, self.src)),
                        Some(node),
                    );
                    (ValueExpr::Unknown, cur)
                }
            },
            "true" | "True" => (ValueExpr::Bool { value: true }, cur),
            "false" | "False" => (ValueExpr::Bool { value: false }, cur),
            "none" | "None" => (ValueExpr::Null, cur),
            "attribute" => {
                let (base, block) = match node.child_by_field_name("object") {
                    Some(object) => self.value(object, cur),
                    None => (ValueExpr::Unknown, cur),
                };
                let name = node
                    .child_by_field_name("attribute")
                    .map_or_else(String::new, |a| node_text(a, self.src));
                (
                    ValueExpr::Field {
                        base: Box::new(base),
                        name,
                    },
                    block,
                )
            }
            "call" => self.call_value(node, cur),
            "binary_operator" => {
                let (left, block) = match node.child_by_field_name("left") {
                    Some(left) => self.value(left, cur),
                    None => (ValueExpr::Unknown, cur),
                };
                let (right, block) = match node.child_by_field_name("right") {
                    Some(right) => self.value(right, block),
                    None => (ValueExpr::Unknown, block),
                };
                let operator = node
                    .child_by_field_name("operator")
                    .map_or_else(String::new, |o| node_text(o, self.src));
                match map_binop(&operator) {
                    Some(op) => (
                        ValueExpr::Binary {
                            op,
                            lhs: Box::new(left),
                            rhs: Box::new(right),
                        },
                        block,
                    ),
                    None => {
                        self.gap(
                            GapReason::UnsupportedExpression,
                            format!("unmapped binary operator `{operator}`"),
                            Some(node),
                        );
                        (ValueExpr::Unknown, block)
                    }
                }
            }
            "comparison_operator" => self.lower_comparison(node, cur),
            "unary_operator" | "not_operator" => {
                let (operand, block) = match node
                    .child_by_field_name("argument")
                    .or_else(|| named_children(node).into_iter().last())
                {
                    Some(operand) => self.value(operand, cur),
                    None => (ValueExpr::Unknown, cur),
                };
                let operator = if node.kind() == "not_operator" {
                    "not".to_owned()
                } else {
                    node_text(node, self.src)
                        .split_whitespace()
                        .next()
                        .unwrap_or_default()
                        .to_owned()
                };
                match operator.as_str() {
                    "not" | "!" => (
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
                    // `+x` / `~x`: the operand's calls are hoisted; the value
                    // is outside the supported subset.
                    _ => (ValueExpr::Unknown, block),
                }
            }
            "subscript" => {
                let mut block = cur;
                for part in [
                    node.child_by_field_name("value"),
                    node.child_by_field_name("subscript"),
                ]
                .into_iter()
                .flatten()
                {
                    let (_, next) = self.value(part, block);
                    block = next;
                }
                self.gap(
                    GapReason::UnsupportedExpression,
                    "container element state is not modeled",
                    Some(node),
                );
                (ValueExpr::Unknown, block)
            }
            "list" | "tuple" | "set" | "dictionary" | "argument_list" | "expression_list"
            | "parenthesized_list_splat" | "list_splat" | "dictionary_splat" => {
                let mut block = cur;
                for child in named_children(node) {
                    let (_, next) = self.value(child, block);
                    block = next;
                }
                (ValueExpr::Unknown, block)
            }
            "keyword_argument" => match node.child_by_field_name("value") {
                Some(value) => self.value(value, cur),
                None => (ValueExpr::Unknown, cur),
            },
            "lambda" => {
                self.gap(
                    GapReason::UnsupportedExpression,
                    "lambda body is not part of this body's control flow",
                    Some(node),
                );
                (ValueExpr::Unknown, cur)
            }
            "await" | "yield" => {
                let mut block = cur;
                for child in named_children(node) {
                    let (_, next) = self.value(child, block);
                    block = next;
                }
                self.gap(
                    GapReason::UnsupportedExpression,
                    format!("`{}` (suspension semantics unmodeled)", node.kind()),
                    Some(node),
                );
                (ValueExpr::Unknown, block)
            }
            other => {
                self.gap(
                    GapReason::UnsupportedExpression,
                    format!("unlowered Python expression `{other}`"),
                    Some(node),
                );
                (ValueExpr::Unknown, cur)
            }
        }
    }

    fn call_value(&mut self, node: Node<'a>, cur: BlockId) -> (ValueExpr, BlockId) {
        let mut block = cur;
        if let Some(function) = node.child_by_field_name("function") {
            if function.kind() == "attribute" {
                if let Some(object) = function.child_by_field_name("object") {
                    let (_, next) = self.value(object, block);
                    block = next;
                }
            }
        }
        if let Some(arguments) = node.child_by_field_name("arguments") {
            for child in named_children(arguments) {
                let (_, next) = self.value(child, block);
                block = next;
            }
        }
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
            None => {
                self.gap(
                    GapReason::UnresolvedCall,
                    "no call site registered for this call",
                    Some(node),
                );
                (ValueExpr::Unknown, block)
            }
        }
    }
}

/// The suite of a clause (`except`, `finally`, `else`).
///
/// tree-sitter-python does not give these clauses a `body` field: the suite is
/// an anonymous `block` child. A missing suite is not an error here — the
/// caller decides what that means.
fn suite_body(node: Node<'_>) -> Option<Node<'_>> {
    node.child_by_field_name("body")
        .or_else(|| named_children(node).into_iter().find(|c| c.kind() == "block"))
}

fn target_node(node: Node<'_>) -> Node<'_> {
    node
}

fn named_children(node: Node<'_>) -> Vec<Node<'_>> {
    let mut cursor = node.walk();
    let children: Vec<Node<'_>> = node.children(&mut cursor).collect();
    children.into_iter().filter(Node::is_named).collect()
}

fn first_named_child(node: Node<'_>) -> Option<Node<'_>> {
    named_children(node).into_iter().next()
}

/// Kinds that appear as children of a suite but are not statements.
fn is_non_statement(kind: &str) -> bool {
    matches!(
        kind,
        "comment" | "line_continuation" | "decorator" | "string"
    )
}
