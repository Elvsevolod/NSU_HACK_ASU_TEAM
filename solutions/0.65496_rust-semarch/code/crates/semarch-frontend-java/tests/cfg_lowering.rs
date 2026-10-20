//! N03 acceptance on the Java frontend: the lowered `FunctionBody` must express
//! real control flow, and the flat facts must be untouched by lowering.
//!
//! Inputs are the plan's property fixtures (`BranchCases.java` shapes). The
//! calls are intentionally unresolved: what is asserted is control/effect
//! placement, not Train Ticket semantics.

use std::collections::BTreeSet;

use semarch_core::analysis::analyze_body;
use semarch_core::ids::BlockId;
use semarch_core::ir::{FunctionBody, GapReason, Statement, Terminator, ValueExpr};
use semarch_core::lowering::{validate, BodyCheck};
use semarch_core::value::LanguageProfile;
use semarch_core::{Allocator, Env, Effect, EvidenceStatus, Language, LanguageFrontend, ParseContext, ParsedFile};
use semarch_frontend_java::JavaFrontend;

fn parse(src: &str) -> ParsedFile {
    let mut fe = JavaFrontend::new().expect("grammar ABI ok");
    let mut alloc = Allocator::default();
    let mut diags = Vec::new();
    let mut ctx = ParseContext::new(0u32.into(), Language::Java, &mut alloc, &mut diags);
    let parsed = fe.parse(&mut ctx, src).expect("parse succeeds");
    assert!(diags.is_empty(), "unexpected diagnostics: {diags:?}");
    parsed
}

/// The lowered body of the unique method named `name`.
fn body<'a>(pf: &'a ParsedFile, name: &str) -> &'a FunctionBody {
    let function = pf
        .functions
        .iter()
        .find(|f| f.name == name)
        .unwrap_or_else(|| panic!("method `{name}` not found"));
    pf.bodies
        .iter()
        .find(|b| b.function == function.id)
        .unwrap_or_else(|| panic!("no lowered body for `{name}`"))
}

fn block(body: &FunctionBody, id: BlockId) -> &semarch_core::ir::BasicBlock {
    body.blocks
        .iter()
        .find(|b| b.id == id)
        .expect("block exists")
}

fn terminator(body: &FunctionBody, id: BlockId) -> &Terminator {
    &block(body, id).terminator
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

/// Callees of the calls the block's own statements evaluate.
fn callees_in(pf: &ParsedFile, body: &FunctionBody, id: BlockId) -> BTreeSet<String> {
    let mut out = BTreeSet::new();
    for statement in &block(body, id).statements {
        let value = match statement {
            Statement::Eval { value } => value,
            Statement::Assign { value, .. } => value,
            Statement::Unsupported { .. } => continue,
        };
        collect_callees(pf, value, &mut out);
    }
    out
}

/// Callees of the calls in the branch condition that ends `id`.
fn condition_callees(pf: &ParsedFile, body: &FunctionBody, id: BlockId) -> BTreeSet<String> {
    match terminator(body, id) {
        Terminator::Branch { condition, .. } => {
            let mut out = BTreeSet::new();
            collect_callees(pf, condition, &mut out);
            out
        }
        other => panic!("block {id:?} does not branch: {other:?}"),
    }
}

fn callees(body: &FunctionBody, analysis: &semarch_core::analysis::BodyAnalysis) -> BTreeSet<String> {
    let _ = body;
    analysis
        .effects
        .iter()
        .filter_map(|(effect, _)| match effect {
            Effect::LocalCall { callee, .. } => Some(callee.clone()),
            _ => None,
        })
        .collect()
}

fn is_goto(body: &FunctionBody, id: BlockId) -> Option<BlockId> {
    match terminator(body, id) {
        Terminator::Goto { next } => Some(*next),
        _ => None,
    }
}

fn successors(body: &FunctionBody, id: BlockId) -> Vec<BlockId> {
    terminator(body, id).successors()
}

/// Whether `target` is reachable from `from` (including `from == target`).
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

fn assert_valid(body: &FunctionBody) {
    match validate(body) {
        BodyCheck::Valid { .. } => {}
        BodyCheck::Invalid { problems } => panic!("invalid body: {problems:?}"),
    }
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

#[test]
fn false_branch_is_not_always_the_function_exit() {
    let pf = parse(
        r#"class BranchCases {
            void negative() { if (!hasFood()) audit(); else food(); }
        }"#,
    );
    let b = body(&pf, "negative");
    assert_valid(b);

    let (then_block, else_block) = branch(b, b.entry);
    assert!(
        matches!(
            terminator(b, b.entry),
            Terminator::Branch {
                condition: ValueExpr::Unary { .. },
                ..
            }
        ),
        "the condition keeps its `!`"
    );
    assert_ne!(then_block, else_block);
    assert_eq!(callees_in(&pf, b, then_block), ["audit".to_owned()].into());
    assert_eq!(callees_in(&pf, b, else_block), ["food".to_owned()].into());

    // Both arms fall through to one join and the `else` arm is therefore not
    // the function exit.
    let then_next = is_goto(b, then_block).expect("then falls through");
    let else_next = is_goto(b, else_block).expect("else falls through");
    assert_eq!(then_next, else_next, "both arms join at one block");
    assert!(matches!(terminator(b, then_next), Terminator::Return { .. }));
    assert!(!terminator(b, else_block).is_exit());
}

#[test]
fn early_return_leaves_a_reachable_rest() {
    let pf = parse(
        r#"class BranchCases {
            void early(boolean stop) { if (stop) return; remote(); }
        }"#,
    );
    let b = body(&pf, "early");
    assert_valid(b);

    let (then_block, else_block) = branch(b, b.entry);
    // The `then` arm returns without a value, so it is an exit.
    assert!(matches!(
        terminator(b, then_block),
        Terminator::Return { value: None }
    ));
    assert!(b.exits.contains(&then_block));

    // The code after the `if` is still reachable from the fall-through arm.
    let with_remote: Vec<BlockId> = b
        .blocks
        .iter()
        .filter(|block| callees_in(&pf, b, block.id).contains("remote"))
        .map(|block| block.id)
        .collect();
    assert_eq!(with_remote.len(), 1, "remote appears once");
    assert!(
        reaches(b, else_block, with_remote[0]),
        "the early return must not make `remote()` unreachable"
    );
    assert!(!reaches(b, then_block, with_remote[0]));
}

#[test]
fn call_in_a_condition_is_evaluated_on_the_predicate_path() {
    let pf = parse(
        r#"class BranchCases {
            void sameLine() { if (hasFood()) food(); audit(); }
        }"#,
    );
    let b = body(&pf, "sameLine");
    assert_valid(b);

    // The call inside the predicate belongs to the branch point, not to the
    // `then` body: excluding the branch cannot silently delete it.
    assert_eq!(
        condition_callees(&pf, b, b.entry),
        ["hasFood".to_owned()].into()
    );
    let (then_block, else_block) = branch(b, b.entry);
    assert_eq!(callees_in(&pf, b, then_block), ["food".to_owned()].into());

    // `audit()` runs after either arm, from the same join.
    let with_audit: Vec<BlockId> = b
        .blocks
        .iter()
        .filter(|block| callees_in(&pf, b, block.id).contains("audit"))
        .map(|block| block.id)
        .collect();
    assert_eq!(with_audit.len(), 1);
    assert!(reaches(b, then_block, with_audit[0]));
    assert!(reaches(b, else_block, with_audit[0]));
}

#[test]
fn ternary_retains_both_candidate_calls() {
    let src = r#"class A {
        int choose(boolean p) {
            int x = p ? left() : right();
            return x;
        }
    }"#;
    let pf = parse(src);

    // Flat facts stay complete: both candidates are still registered.
    assert!(pf.callsites.iter().any(|c| c.callee == "left"));
    assert!(pf.callsites.iter().any(|c| c.callee == "right"));

    let b = body(&pf, "choose");
    assert_valid(b);
    let (then_block, else_block) = branch(b, b.entry);
    assert_eq!(callees_in(&pf, b, then_block), ["left".to_owned()].into());
    assert_eq!(callees_in(&pf, b, else_block), ["right".to_owned()].into());

    // Both arms write one generated temp, then join.
    let then_target = first_assign_target(b, then_block);
    let else_target = first_assign_target(b, else_block);
    assert_eq!(then_target, else_target, "both arms write one temp");
    let join = is_goto(b, then_block).expect("then falls through");
    assert_eq!(join, is_goto(b, else_block).expect("else falls through"));

    let ValueExpr::Symbolic { name } = then_target else {
        panic!("the ternary temp is a symbolic name");
    };
    assert!(name.starts_with('$'), "generated temp, got {name}");
}

fn first_assign_target(body: &FunctionBody, id: BlockId) -> ValueExpr {
    block(body, id)
        .statements
        .iter()
        .find_map(|statement| match statement {
            Statement::Assign { target, .. } => Some(target.clone()),
            _ => None,
        })
        .unwrap_or_else(|| panic!("no assignment in {id:?}"))
}

/// The plan's fixture uses `return p ? a() : b()`. The v0 flat walk visits only
/// the ternary's first child through `expression()`, so the arm call sites are
/// not registered. The lowering must *record* that instead of silently
/// producing an arm with no call.
#[test]
fn ternary_arm_without_a_flat_call_site_is_recorded_not_dropped() {
    let pf = parse(
        r#"class A { Object choose(boolean p) { return p ? left() : right(); } }"#,
    );
    assert!(
        !pf.callsites.iter().any(|c| c.callee == "left"),
        "precondition: the flat walk does not visit the arms of a returned ternary"
    );
    let b = body(&pf, "choose");
    assert_valid(b);
    assert!(
        b.gaps
            .iter()
            .any(|g| g.reason == GapReason::UnresolvedCall),
        "the missing arm call sites are recorded: {:?}",
        b.gaps
    );
    // Both arms still exist as separate control-flow paths.
    let (then_block, else_block) = branch(b, b.entry);
    assert_ne!(then_block, else_block);
}

#[test]
fn short_circuit_right_hand_side_is_guarded() {
    let pf = parse(
        r#"class BranchCases {
            void shortCircuit(boolean stop) { if (stop && remotePredicate()) food(); }
        }"#,
    );
    let b = body(&pf, "shortCircuit");
    assert_valid(b);

    // The `&&` itself branches; the right-hand call lives in the then-arm of
    // that branch, so it is reached only when the left operand holds.
    let (rhs_block, short_block) = branch(b, b.entry);
    assert_eq!(
        callees_in(&pf, b, rhs_block),
        ["remotePredicate".to_owned()].into()
    );
    assert!(callees_in(&pf, b, short_block).is_empty());

    // A second branch point decides `food()` on the materialized temp.
    let join = is_goto(b, rhs_block).expect("rhs falls through");
    assert_eq!(some_join(b, short_block), Some(join));
    let (food_block, _) = branch(b, join);
    assert_eq!(callees_in(&pf, b, food_block), ["food".to_owned()].into());

    // The analysis keeps the guarded call *possible* rather than deleting it.
    let analysis = analyze_body(b, Env::default(), &pf.callsites, None, LanguageProfile::java());
    assert!(callees(b, &analysis).contains("remotePredicate"), "{:?}", callees(b, &analysis));
    assert!(
        analysis.effects.iter().any(
            |(effect, ev)| matches!(effect, Effect::LocalCall { callee, .. } if callee == "remotePredicate")
                && ev.status == EvidenceStatus::Possible
        ),
        "a call behind a branch is possible, never confirmed"
    );
}

/// The block a short-circuit arm falls through to.
fn some_join(body: &FunctionBody, id: BlockId) -> Option<BlockId> {
    let mut next = id;
    for _ in 0..4 {
        let branch = match terminator(body, next) {
            Terminator::Goto { next } => *next,
            _ => return None,
        };
        if branch != id {
            return Some(branch);
        }
        next = branch;
    }
    None
}

#[test]
fn do_while_runs_its_body_before_testing() {
    let pf = parse(
        r#"class BranchCases {
            void firstDo() { do { remote(); } while (false); }
        }"#,
    );
    let b = body(&pf, "firstDo");
    assert_valid(b);

    // Entry jumps straight into the body: the first iteration is unconditional.
    let body_block = is_goto(b, b.entry).expect("entry falls into the body");
    assert_eq!(callees_in(&pf, b, body_block), ["remote".to_owned()].into());
    // The condition is tested after the body, and its false arm exits.
    match terminator(b, body_block) {
        Terminator::Branch { condition, .. } => {
            assert_eq!(*condition, ValueExpr::Bool { value: false });
        }
        other => panic!("the body must end in the loop test, got {other:?}"),
    }
}

#[test]
fn loop_zero_one_and_n_paths() {
    for (src, name) in [
        (
            r#"class L { void zero() { while (false) { never(); } after(); } }"#,
            "zero",
        ),
        (
            r#"class L { void one() { int i = 0; while (i < 1) { once(); i = 1; } after(); } }"#,
            "one",
        ),
        (
            r#"class L { void many(int n) { int i = 0; while (i < n) { step(); i = i + 1; } after(); } }"#,
            "many",
        ),
    ] {
        let pf = parse(src);
        let b = body(&pf, name);
        assert_valid(b);

        let analysis = analyze_body(b, Env::default(), &pf.callsites, None, LanguageProfile::java());
        assert!(!analysis.reached_blocks.is_empty());
        let calls = callees(b, &analysis);
        assert!(calls.contains("after"), "{name}: {calls:?}");

        // The loop body has a back edge into the header: the CFG is cyclic, not
        // a straight line through the body.
        let cyclic = b.blocks.iter().any(|block| {
            successors(b, block.id)
                .iter()
                .any(|next| reaches(b, *next, block.id))
        });
        assert!(cyclic, "{name}: the loop must have a back edge");

        if name == "zero" {
            // `while (false)` is decided by the Java profile on a boolean
            // literal, so the body stays unreached.
            assert!(!calls.contains("never"), "{calls:?}");
        }
    }
}

#[test]
fn unsupported_statements_are_recorded_as_gaps_not_dropped() {
    let pf = parse(
        r#"class G {
            void withSwitch(int x) {
                switch (x) { case 1: one(); break; default: two(); }
                tail();
            }
        }"#,
    );
    let b = body(&pf, "withSwitch");
    assert_valid(b);

    let gap_terminators = b
        .blocks
        .iter()
        .filter(|block| matches!(block.terminator, Terminator::Gap { .. }))
        .count();
    assert!(gap_terminators >= 1, "the switch is recorded as a gap");
    assert!(
        b.gaps
            .iter()
            .any(|g| g.reason == GapReason::UnsupportedStatement),
        "the gap keeps its reason: {:?}",
        b.gaps
    );
    // The statements inside the gap container stay reachable as *may* paths.
    let analysis = analyze_body(b, Env::default(), &pf.callsites, None, LanguageProfile::java());
    let calls = callees(b, &analysis);
    assert!(calls.contains("one"), "case body kept: {calls:?}");
    assert!(calls.contains("two"), "default body kept: {calls:?}");
    assert!(calls.contains("tail"), "code after the switch kept: {calls:?}");
}

#[test]
fn try_finally_runs_on_the_return_path() {
    let pf = parse(
        r#"class BranchCases {
            void finallyCase(boolean stop) {
                try { if (stop) return; remote(); } finally { audit(); }
            }
        }"#,
    );
    let b = body(&pf, "finallyCase");
    assert_valid(b);

    // The `return` inside the `try` carries the inlined `finally` body, so the
    // exit block itself evaluates `audit()` before returning.
    let returns: Vec<BlockId> = b
        .blocks
        .iter()
        .filter(|block| matches!(block.terminator, Terminator::Return { .. }))
        .map(|block| block.id)
        .collect();
    let guarded_return = returns
        .iter()
        .copied()
        .find(|id| callees_in(&pf, b, *id).contains("audit"))
        .expect("the return path runs the finally body");
    assert!(
        b.exits.contains(&guarded_return),
        "the finally-carrying return is an exit"
    );

    // The normal path also runs it before continuing.
    let with_audit: BTreeSet<BlockId> = b
        .blocks
        .iter()
        .filter(|block| callees_in(&pf, b, block.id).contains("audit"))
        .map(|block| block.id)
        .collect();
    assert!(with_audit.len() >= 2, "return path and normal path: {with_audit:?}");
}

#[test]
fn a_try_with_catch_keeps_the_handlers_reachable_and_records_the_gap() {
    let pf = parse(
        r#"class C {
            void guarded() {
                try { risky(); } catch (RuntimeException e) { recover(); }
            }
        }"#,
    );
    let b = body(&pf, "guarded");
    assert_valid(b);
    assert!(
        b.gaps
            .iter()
            .any(|g| g.reason == GapReason::ExceptionDispatch),
        "catch dispatch is recorded: {:?}",
        b.gaps
    );
    let analysis = analyze_body(b, Env::default(), &pf.callsites, None, LanguageProfile::java());
    let calls = callees(b, &analysis);
    assert!(calls.contains("risky"), "{calls:?}");
    assert!(calls.contains("recover"), "the handler stays reachable: {calls:?}");
}

#[test]
fn constructor_bodies_are_lowered_and_valid() {
    let pf = parse(
        r#"class D {
            static int shared = seed();
            int field;
            D() { init(); }
        }"#,
    );
    for b in &pf.bodies {
        assert_valid(b);
    }
    let constructor = pf
        .functions
        .iter()
        .find(|f| f.name == "D")
        .expect("constructor");
    let b = body(&pf, constructor.name.as_str());
    assert_eq!(callees_in(&pf, b, b.entry), ["init".to_owned()].into());
    // A field initializer is not a `FunctionBody`: there is exactly one body
    // here (the constructor). The static initializer is a documented hole in
    // the flat walk as well, so nothing in the lowering pretends to model it.
    assert_eq!(pf.bodies.len(), 1, "constructor only, got {}", pf.bodies.len());
    assert!(!pf.callsites.iter().any(|c| c.callee == "seed"));
}

#[test]
fn guard_references_always_resolve() {
    let pf = parse(
        r#"class E {
            void f(boolean a, boolean b) {
                if (a) { x(); } else if (b) { y(); } else { z(); }
                while (a && b) { w(); }
            }
        }"#,
    );
    let b = body(&pf, "f");
    assert_valid(b);
    for block in &b.blocks {
        if let Terminator::Branch { guard, .. } = &block.terminator {
            assert!(
                b.guards.iter().any(|g| g.id == *guard),
                "guard {guard:?} referenced but not registered"
            );
        }
    }
    assert!(b.guards.len() >= 3, "at least three conditions were tested");
}
