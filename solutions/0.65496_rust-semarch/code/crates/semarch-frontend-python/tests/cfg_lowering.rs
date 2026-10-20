//! N03 acceptance on the Python frontend: the same orderd-IR contract as Java,
//! including the language-specific scalar rules (truthiness, `and`/`or` yielding
//! an operand, implicit `None`).
//!
//! The inputs are the plan's `branch_cases.py` shapes. Nothing is executed.

use std::collections::BTreeSet;

use semarch_core::analysis::analyze_body;
use semarch_core::ids::BlockId;
use semarch_core::ir::{FunctionBody, GapReason, Statement, Terminator, ValueExpr};
use semarch_core::lowering::{validate, BodyCheck};
use semarch_core::value::LanguageProfile;
use semarch_core::{
    Allocator, Effect, Env, Language, LanguageFrontend, ParseContext, ParsedFile,
};
use semarch_frontend_python::PythonFrontend;

fn parse(src: &str) -> ParsedFile {
    let mut fe = PythonFrontend::new().expect("grammar ABI ok");
    let mut alloc = Allocator::default();
    let mut diags = Vec::new();
    let mut ctx = ParseContext::new(0u32.into(), Language::Python, &mut alloc, &mut diags);
    let parsed = fe.parse(&mut ctx, src).expect("parse succeeds");
    assert!(diags.is_empty(), "unexpected diagnostics: {diags:?}");
    parsed
}

fn body<'a>(pf: &'a ParsedFile, name: &str) -> &'a FunctionBody {
    let function = pf
        .functions
        .iter()
        .find(|f| f.name == name)
        .unwrap_or_else(|| panic!("function `{name}` not found"));
    pf.bodies
        .iter()
        .find(|b| b.function == function.id)
        .unwrap_or_else(|| panic!("no lowered body for `{name}`"))
}

fn terminator(body: &FunctionBody, id: BlockId) -> &Terminator {
    &body
        .blocks
        .iter()
        .find(|b| b.id == id)
        .expect("block exists")
        .terminator
}

fn collect_callees(pf: &ParsedFile, value: &ValueExpr, out: &mut BTreeSet<String>) {
    match value {
        ValueExpr::CallResult { callsite } => {
            if let Some(cs) = pf.callsites.iter().find(|c| c.id == *callsite) {
                out.insert(cs.callee.clone());
            }
        }
        ValueExpr::Unary { operand, .. } => collect_callees(pf, operand, out),
        ValueExpr::Binary { lhs, rhs, .. } => {
            collect_callees(pf, lhs, out);
            collect_callees(pf, rhs, out);
        }
        ValueExpr::Field { base, .. } => collect_callees(pf, base, out),
        _ => {}
    }
}

fn callees_in(pf: &ParsedFile, body: &FunctionBody, id: BlockId) -> BTreeSet<String> {
    let mut out = BTreeSet::new();
    for block in &body.blocks {
        if block.id != id {
            continue;
        }
        for statement in &block.statements {
            let value = match statement {
                Statement::Eval { value } => value,
                Statement::Assign { value, .. } => value,
                Statement::Unsupported { .. } => continue,
            };
            collect_callees(pf, value, &mut out);
        }
    }
    out
}

fn analysis_callees(analysis: &semarch_core::analysis::BodyAnalysis) -> BTreeSet<String> {
    analysis
        .effects
        .iter()
        .filter_map(|(effect, _)| match effect {
            Effect::LocalCall { callee, .. } => Some(callee.clone()),
            _ => None,
        })
        .collect()
}

fn branch(body: &FunctionBody, id: BlockId) -> (BlockId, BlockId) {
    match terminator(body, id) {
        Terminator::Branch {
            then_block,
            else_block,
            ..
        } => (*then_block, *else_block),
        other => panic!("block {id:?} does not branch: {other:?}"),
    }
}

fn successors(body: &FunctionBody, id: BlockId) -> Vec<BlockId> {
    terminator(body, id).successors()
}

fn reaches(body: &FunctionBody, from: BlockId, target: BlockId) -> bool {
    let mut seen = BTreeSet::new();
    let mut stack = vec![from];
    while let Some(id) = stack.pop() {
        if id == target {
            return true;
        }
        if !seen.insert(id) {
            continue;
        }
        stack.extend(successors(body, id));
    }
    false
}

fn blocks_with(pf: &ParsedFile, body: &FunctionBody, callee: &str) -> Vec<BlockId> {
    body.blocks
        .iter()
        .filter(|block| callees_in(pf, body, block.id).contains(callee))
        .map(|block| block.id)
        .collect()
}

fn assert_valid(body: &FunctionBody) {
    match validate(body) {
        BodyCheck::Valid { .. } => {}
        BodyCheck::Invalid { problems } => panic!("invalid body: {problems:?}"),
    }
}

fn run<'a>(pf: &'a ParsedFile, b: &'a FunctionBody) -> semarch_core::analysis::BodyAnalysis {
    analyze_body(b, Env::default(), &pf.callsites, None, LanguageProfile::python())
}

#[test]
fn early_return_leaves_the_rest_reachable() {
    let pf = parse("def early(stop):\n    if stop:\n        return\n    remote()\n");
    let b = body(&pf, "early");
    assert_valid(b);

    let (then_block, else_block) = branch(b, b.entry);
    assert!(matches!(
        terminator(b, then_block),
        Terminator::Return { value: Some(ValueExpr::Null) }
    ));
    let remote = blocks_with(&pf, b, "remote");
    assert_eq!(remote.len(), 1);
    assert!(reaches(b, else_block, remote[0]));
    assert!(!reaches(b, then_block, remote[0]));
}

#[test]
fn implicit_none_is_an_explicit_return() {
    let pf = parse("def tail():\n    step()\n");
    let b = body(&pf, "tail");
    assert_valid(b);
    let returns: Vec<&Terminator> = b
        .blocks
        .iter()
        .filter(|block| matches!(block.terminator, Terminator::Return { .. }))
        .map(|block| &block.terminator)
        .collect();
    assert_eq!(returns.len(), 1, "exactly one synthetic return: {returns:?}");
    assert!(matches!(
        returns[0],
        Terminator::Return { value: Some(ValueExpr::Null) }
    ));
}

#[test]
fn finally_runs_on_return_and_on_the_normal_path() {
    let pf = parse(
        "def finally_case(stop):\n    try:\n        if stop:\n            return\n        remote()\n    finally:\n        audit()\n",
    );
    let b = body(&pf, "finally_case");
    assert_valid(b);

    // The return inside `try` carries the inlined cleanup.
    let guarded_return = b
        .blocks
        .iter()
        .find(|block| {
            matches!(block.terminator, Terminator::Return { .. })
                && callees_in(&pf, b, block.id).contains("audit")
        })
        .expect("the return path runs the finally body");
    assert!(b.exits.contains(&guarded_return.id));

    // The normal path runs it too, before leaving the construct.
    let with_audit = blocks_with(&pf, b, "audit");
    assert!(with_audit.len() >= 2, "return and normal path: {with_audit:?}");
}

#[test]
fn conditional_expression_retains_both_arms() {
    let pf = parse("def conditional(flag):\n    return first() if flag else second()\n");
    let b = body(&pf, "conditional");
    assert_valid(b);

    // The arms are separate control-flow paths whichever way the flat walk
    // registers their calls: each arm writes the materialized temp, then both
    // converge on the single `return`.
    let (then_block, else_block) = branch(b, b.entry);
    assert_ne!(then_block, else_block);
    let then_join = match terminator(b, then_block) {
        Terminator::Goto { next } => *next,
        other => panic!("arm must fall through, got {other:?}"),
    };
    let else_join = match terminator(b, else_block) {
        Terminator::Goto { next } => *next,
        other => panic!("arm must fall through, got {other:?}"),
    };
    assert_eq!(then_join, else_join, "both arms converge on one return");
    assert!(matches!(
        terminator(b, then_join),
        Terminator::Return { value: Some(_) }
    ));
}

#[test]
fn boolean_operator_guards_its_right_operand() {
    let pf = parse("def short(stop):\n    if stop and remote_predicate():\n        food()\n");
    let b = body(&pf, "short");
    assert_valid(b);

    let (rhs_block, short_block) = branch(b, b.entry);
    assert_eq!(callees_in(&pf, b, rhs_block), ["remote_predicate".to_owned()].into());
    assert!(callees_in(&pf, b, short_block).is_empty());

    // Python's `and` yields an operand: the short-circuit arm assigns the left
    // value itself rather than a coerced boolean.
    let short_assign = b
        .blocks
        .iter()
        .find(|block| block.id == short_block)
        .and_then(|block| {
            block.statements.iter().find_map(|s| match s {
                Statement::Assign { value, .. } => Some(value.clone()),
                _ => None,
            })
        })
        .expect("the short arm materializes its operand");
    assert_eq!(short_assign, ValueExpr::Symbolic { name: "stop".to_owned() });

    let analysis = run(&pf, b);
    assert!(
        analysis.effects.iter().any(|(effect, ev)| matches!(
            effect, Effect::LocalCall { callee, .. } if callee == "remote_predicate"
        ) && ev.status == semarch_core::EvidenceStatus::Possible),
        "a call behind a condition is possible, not confirmed"
    );
}

#[test]
fn python_truthiness_decides_zero_height_and_empty() {
    let pf = parse(
        "def falsy():\n    if 0:\n        never()\n    if '':\n        also_never()\n    done()\n",
    );
    let b = body(&pf, "falsy");
    assert_valid(b);
    let analysis = run(&pf, b);
    let calls = analysis_callees(&analysis);
    assert!(!calls.contains("never"), "{calls:?}");
    assert!(!calls.contains("also_never"), "{calls:?}");
    assert!(calls.contains("done"), "{calls:?}");
}

#[test]
fn not_yields_a_boolean_only_under_the_python_profile() {
    // `not 0` is `True` in Python and not even a program in Java. The same IR
    // must therefore be decided by one profile and left open by the other.
    let pf = parse("def negate():\n    if not 0:\n        yes()\n");
    let b = body(&pf, "negate");
    assert_valid(b);

    let python = run(&pf, b);
    let yes_python = python
        .effects
        .iter()
        .find(|(effect, _)| matches!(effect, Effect::LocalCall { callee, .. } if callee == "yes"))
        .expect("the call is reached");
    assert_eq!(yes_python.1.status, semarch_core::EvidenceStatus::Confirmed);
    // The guard proved the condition true, so the `else` arm is dead.
    let (_, else_block) = branch(b, b.entry);
    assert!(
        !python.reached_blocks.contains(&else_block),
        "the false arm must stay unreached: {:?}",
        python.reached_blocks
    );

    let java = analyze_body(b, Env::default(), &pf.callsites, None, LanguageProfile::java());
    let yes_java = java
        .effects
        .iter()
        .find(|(effect, _)| matches!(effect, Effect::LocalCall { callee, .. } if callee == "yes"))
        .expect("the call is still recorded");
    assert_eq!(
        yes_java.1.status,
        semarch_core::EvidenceStatus::Possible,
        "Java mode may not read an integer condition as a boolean"
    );
}

#[test]
fn loop_with_else_reaches_both_back_edge_and_else_body() {
    let pf = parse(
        "def scan(items):\n    for item in items:\n        step(item)\n    else:\n        empty()\n    tail()\n",
    );
    let b = body(&pf, "scan");
    assert_valid(b);

    // A back edge exists (the CFG is cyclic), and the `else` clause is a
    // distinct path that still reaches the code after the loop.
    let cyclic = b.blocks.iter().any(|block| {
        successors(b, block.id)
            .iter()
            .any(|next| reaches(b, *next, block.id))
    });
    assert!(cyclic, "the for-loop must have a back edge");

    let calls = analysis_callees(&run(&pf, b));
    assert!(calls.contains("step"), "{calls:?}");
    assert!(calls.contains("empty"), "{calls:?}");
    assert!(calls.contains("tail"), "{calls:?}");
}

#[test]
fn while_with_else_is_lowered() {
    let pf = parse(
        "def wait(flag):\n    while flag:\n        tick()\n    else:\n        settled()\n    done()\n",
    );
    let b = body(&pf, "wait");
    assert_valid(b);
    let calls = analysis_callees(&run(&pf, b));
    assert!(calls.contains("tick"), "{calls:?}");
    assert!(calls.contains("settled"), "{calls:?}");
    assert!(calls.contains("done"), "{calls:?}");
}

#[test]
fn augmented_assignment_is_an_assignment() {
    let pf = parse("def bump(n):\n    i = 0\n    while i < n:\n        step()\n        i += 1\n    return i\n");
    let b = body(&pf, "bump");
    assert_valid(b);
    // Some block assigns `i + 1` to `i`: the update is a real assignment, so
    // the analysis can see the loop make progress.
    assert!(
        b.blocks.iter().any(|block| block.statements.iter().any(|s| matches!(
            s,
            Statement::Assign { target: ValueExpr::Symbolic { name }, value: ValueExpr::Binary { .. } }
                if name == "i"
        ))),
        "the `i += 1` must be lowered as an assignment"
    );
}

#[test]
fn unsupported_with_statement_is_recorded_and_its_body_kept() {
    let pf = parse(
        "def load(path):\n    with open(path) as f:\n        read(f)\n    tail()\n",
    );
    let b = body(&pf, "load");
    assert_valid(b);
    assert!(
        b.gaps
            .iter()
            .any(|g| g.reason == GapReason::UnsupportedStatement),
        "{:?}",
        b.gaps
    );
    let calls = analysis_callees(&run(&pf, b));
    assert!(calls.contains("read"), "the body is kept as may-execute: {calls:?}");
    assert!(calls.contains("tail"), "{calls:?}");
}

#[test]
fn assert_statement_is_a_recorded_gap() {
    let pf = parse("def check(x):\n    assert x\n    tail()\n");
    let b = body(&pf, "check");
    assert_valid(b);
    assert!(b.gaps.iter().any(|g| g.reason == GapReason::UnsupportedStatement));
    let calls = analysis_callees(&run(&pf, b));
    assert!(calls.contains("tail"), "{calls:?}");
}

#[test]
fn nested_defs_are_lowered_too() {
    let pf = parse("def outer():\n    def inner():\n        leaf()\n    inner()\n");
    let outer = body(&pf, "outer");
    assert_valid(outer);
    let inner = body(&pf, "inner");
    assert_valid(inner);
    assert_eq!(callees_in(&pf, inner, inner.entry), ["leaf".to_owned()].into());
}

#[test]
fn raise_terminates_the_path() {
    let pf = parse("def boom(msg):\n    raise ValueError(msg)\n    unreachable()\n");
    let b = body(&pf, "boom");
    assert_valid(b);
    let throws = b
        .blocks
        .iter()
        .filter(|block| matches!(block.terminator, Terminator::Throw { .. }))
        .count();
    assert_eq!(throws, 1);
    let calls = analysis_callees(&run(&pf, b));
    assert!(!calls.contains("unreachable"), "{calls:?}");
}

#[test]
fn guard_references_resolve_and_match_the_condition_count() {
    let pf = parse(
        "def f(a, b):\n    if a:\n        x()\n    elif b:\n        y()\n    while a and b:\n        w()\n",
    );
    let b = body(&pf, "f");
    assert_valid(b);
    for block in &b.blocks {
        if let Terminator::Branch { guard, .. } = &block.terminator {
            assert!(b.guards.iter().any(|g| g.id == *guard));
        }
    }
    assert!(b.guards.len() >= 3, "{}", b.guards.len());
}
