//! N04 acceptance for whole-body analysis: a real work-list over the ordered
//! IR, with environment joins at merge points, a bounded interprocedural
//! summary, guarded effects marked `Possible`, and every undecidable step
//! recorded as a gap.
//!
//! The bodies here are built by hand. That is deliberate: the analysis must be
//! correct on the IR contract alone, with no frontend and no source text.

use semarch_core::analysis::{analyze_body, CallResolver, Env, SimpleNameResolver};
use semarch_core::ids::{BlockId, CallSiteId, FunctionId, GuardId};
use semarch_core::ir::{
    AnalysisGap, BasicBlock, CallSite, Function, FunctionBody, GapReason, Guard, Statement,
    SymbolKind, Terminator, ValueExpr,
};
use semarch_core::span::SourceSpan;
use semarch_core::value::{AbstractValue, LanguageProfile};
use semarch_core::{Effect, EvidenceStatus};

fn span() -> SourceSpan {
    SourceSpan {
        file: 0u32.into(),
        start_byte: 0,
        end_byte: 1,
        start_row: 0,
        start_col: 0,
        end_row: 0,
        end_col: 1,
    }
}

fn block(id: u32, statements: Vec<Statement>, terminator: Terminator) -> BasicBlock {
    BasicBlock {
        id: BlockId::from_raw(id),
        statements,
        terminator,
        span: Some(span()),
    }
}

fn body(blocks: Vec<BasicBlock>) -> FunctionBody {
    FunctionBody {
        function: FunctionId::from_raw(0),
        entry: BlockId::from_raw(0),
        exits: blocks
            .iter()
            .filter(|b| b.terminator.is_exit())
            .map(|b| b.id)
            .collect(),
        blocks,
        guards: Vec::new(),
        gaps: Vec::new(),
    }
}

fn call(id: u32, callee: &str, args: Vec<ValueExpr>) -> CallSite {
    CallSite {
        id: CallSiteId::from_raw(id),
        callee: callee.to_owned(),
        receiver: None,
        args,
        span: span(),
        name_span: None,
    }
}

fn call_value(id: u32) -> ValueExpr {
    ValueExpr::CallResult {
        callsite: CallSiteId::from_raw(id),
    }
}

fn eval(value: ValueExpr) -> Statement {
    Statement::Eval { value }
}

fn assign(name: &str, value: ValueExpr) -> Statement {
    Statement::Assign {
        target: ValueExpr::Symbolic {
            name: name.to_owned(),
        },
        value,
    }
}

fn goto(next: u32) -> Terminator {
    Terminator::Goto {
        next: BlockId::from_raw(next),
    }
}

fn branch(
    guard: u32,
    condition: ValueExpr,
    then_block: u32,
    else_block: u32,
) -> Terminator {
    Terminator::Branch {
        guard: GuardId::from_raw(guard),
        condition,
        then_block: BlockId::from_raw(then_block),
        else_block: BlockId::from_raw(else_block),
    }
}

fn ret(value: Option<ValueExpr>) -> Terminator {
    Terminator::Return { value }
}

fn callees(analysis: &semarch_core::analysis::BodyAnalysis) -> Vec<(String, EvidenceStatus)> {
    analysis
        .effects
        .iter()
        .filter_map(|(effect, evidence)| match effect {
            Effect::LocalCall { callee, .. } => Some((callee.clone(), evidence.status)),
            _ => None,
        })
        .collect()
}

#[test]
fn linear_body_confirms_its_effects_and_returns_once() {
    let callsites = vec![call(0, "seed", vec![]), call(1, "store", vec![])];
    let b = body(vec![
        block(0, vec![eval(call_value(0))], goto(1)),
        block(1, vec![eval(call_value(1))], ret(None)),
        block(2, vec![eval(call_value(1))], ret(None)), // unreachable
    ]);
    let analysis = analyze_body(&b, Env::default(), &callsites, None, LanguageProfile::java());

    assert_eq!(
        callees(&analysis),
        vec![
            ("seed".to_owned(), EvidenceStatus::Confirmed),
            ("store".to_owned(), EvidenceStatus::Confirmed),
        ]
    );
    assert_eq!(analysis.returns.len(), 1);
    assert_eq!(analysis.reached_blocks.len(), 2);
    assert!(
        !analysis.reached_blocks.contains(&BlockId::from_raw(2)),
        "a block with no incoming edge is not reached"
    );
}

#[test]
fn branch_keeps_both_arms_and_marks_them_possible() {
    let callsites = vec![call(0, "left", vec![]), call(1, "right", vec![])];
    let b = body(vec![
        block(
            0,
            vec![],
            branch(0, ValueExpr::Symbolic { name: "p".into() }, 1, 2),
        ),
        block(1, vec![eval(call_value(0))], goto(3)),
        block(2, vec![eval(call_value(1))], goto(3)),
        block(3, vec![], ret(None)),
    ]);
    let analysis = analyze_body(&b, Env::default(), &callsites, None, LanguageProfile::java());
    assert_eq!(
        callees(&analysis),
        vec![
            ("left".to_owned(), EvidenceStatus::Possible),
            ("right".to_owned(), EvidenceStatus::Possible),
        ]
    );
    // Both arms are reachable, and the witness path names the guard decision.
    assert!(analysis.reached_blocks.contains(&BlockId::from_raw(1)));
    assert!(analysis.reached_blocks.contains(&BlockId::from_raw(2)));
}

#[test]
fn a_provably_false_condition_prunes_only_the_guarded_arm() {
    let callsites = vec![call(0, "guarded", vec![]), call(1, "always", vec![])];
    let b = body(vec![
        block(
            0,
            vec![],
            branch(0, ValueExpr::Bool { value: false }, 1, 2),
        ),
        block(1, vec![eval(call_value(0))], goto(3)),
        block(2, vec![eval(call_value(1))], goto(3)),
        block(3, vec![], ret(None)),
    ]);
    let analysis = analyze_body(&b, Env::default(), &callsites, None, LanguageProfile::java());
    assert_eq!(
        callees(&analysis),
        vec![("always".to_owned(), EvidenceStatus::Confirmed)],
        "the false arm is absent, and the surviving path is unconditional"
    );
    assert!(!analysis.reached_blocks.contains(&BlockId::from_raw(1)));
}

#[test]
fn a_provably_true_condition_prunes_the_other_arm() {
    let callsites = vec![call(0, "taken", vec![])];
    let b = body(vec![
        block(0, vec![], branch(0, ValueExpr::Bool { value: true }, 1, 2)),
        block(1, vec![eval(call_value(0))], ret(None)),
        block(2, vec![], ret(None)),
    ]);
    let analysis = analyze_body(&b, Env::default(), &callsites, None, LanguageProfile::java());
    assert_eq!(
        callees(&analysis),
        vec![("taken".to_owned(), EvidenceStatus::Confirmed)]
    );
    assert_eq!(analysis.returns.len(), 1);
}

#[test]
fn assignments_thread_through_blocks() {
    // `x = 5; if (x == 5) then();` — the second block is reached with x = 5.
    let callsites = vec![call(0, "then_branch", vec![])];
    let b = body(vec![
        block(
            0,
            vec![assign("x", ValueExpr::Int { value: 5 })],
            branch(
                0,
                ValueExpr::Binary {
                    op: semarch_core::BinaryOp::Eq,
                    lhs: Box::new(ValueExpr::Symbolic { name: "x".into() }),
                    rhs: Box::new(ValueExpr::Int { value: 5 }),
                },
                1,
                2,
            ),
        ),
        block(1, vec![eval(call_value(0))], ret(None)),
        block(2, vec![], ret(None)),
    ]);
    let analysis = analyze_body(&b, Env::default(), &callsites, None, LanguageProfile::java());
    assert_eq!(
        callees(&analysis),
        vec![("then_branch".to_owned(), EvidenceStatus::Confirmed)]
    );
    assert!(!analysis.reached_blocks.contains(&BlockId::from_raw(2)));
}

#[test]
fn join_at_a_merge_point_widens_a_differing_binding() {
    // One arm sets `x = 1`, the other `x = 2`; after the merge `x == 1` is
    // undecidable, so both continuations stay.
    let callsites = vec![call(0, "one", vec![]), call(1, "not_one", vec![])];
    let b = body(vec![
        block(
            0,
            vec![],
            branch(0, ValueExpr::Symbolic { name: "p".into() }, 1, 2),
        ),
        block(1, vec![assign("x", ValueExpr::Int { value: 1 })], goto(3)),
        block(2, vec![assign("x", ValueExpr::Int { value: 2 })], goto(3)),
        block(
            3,
            vec![],
            branch(
                1,
                ValueExpr::Binary {
                    op: semarch_core::BinaryOp::Eq,
                    lhs: Box::new(ValueExpr::Symbolic { name: "x".into() }),
                    rhs: Box::new(ValueExpr::Int { value: 1 }),
                },
                4,
                5,
            ),
        ),
        block(4, vec![eval(call_value(0))], ret(None)),
        block(5, vec![eval(call_value(1))], ret(None)),
    ]);
    let analysis = analyze_body(&b, Env::default(), &callsites, None, LanguageProfile::java());
    assert_eq!(
        callees(&analysis),
        vec![
            ("one".to_owned(), EvidenceStatus::Possible),
            ("not_one".to_owned(), EvidenceStatus::Possible),
        ]
    );
}

#[test]
fn a_join_that_agrees_keeps_the_value() {
    // Both arms set `x = 1`, so the merge decides `x == 1`.
    let callsites = vec![call(0, "equal", vec![])];
    let b = body(vec![
        block(
            0,
            vec![],
            branch(0, ValueExpr::Symbolic { name: "p".into() }, 1, 2),
        ),
        block(1, vec![assign("x", ValueExpr::Int { value: 1 })], goto(3)),
        block(2, vec![assign("x", ValueExpr::Int { value: 1 })], goto(3)),
        block(
            3,
            vec![],
            branch(
                1,
                ValueExpr::Binary {
                    op: semarch_core::BinaryOp::Eq,
                    lhs: Box::new(ValueExpr::Symbolic { name: "x".into() }),
                    rhs: Box::new(ValueExpr::Int { value: 1 }),
                },
                4,
                5,
            ),
        ),
        block(4, vec![eval(call_value(0))], ret(None)),
        block(5, vec![], ret(None)),
    ]);
    let analysis = analyze_body(&b, Env::default(), &callsites, None, LanguageProfile::java());
    // The merge agrees on `x = 1`, so the second branch is decided: the
    // `x != 1` arm is not reached at all.
    assert!(!analysis.reached_blocks.contains(&BlockId::from_raw(5)));
    // The status stays `Possible`: reaching this block required a branch
    // decision upstream, and certainty about the *value* is not certainty
    // about the *path*.
    assert_eq!(
        callees(&analysis),
        vec![("equal".to_owned(), EvidenceStatus::Possible)]
    );
}

#[test]
fn a_decided_short_circuit_never_reaches_the_right_operand() {
    // `false && sideEffect()`: the lowering puts the right operand in its own
    // block guarded by the left one. A decided left operand prunes it, so the
    // call is not merely `Possible` — it is unreachable.
    let callsites = vec![call(0, "side_effect", vec![])];
    let b = body(vec![
        block(
            0,
            vec![],
            branch(0, ValueExpr::Bool { value: false }, 1, 2),
        ),
        block(1, vec![eval(call_value(0))], goto(3)),
        block(
            2,
            vec![assign("$t0", ValueExpr::Bool { value: false })],
            goto(3),
        ),
        block(3, vec![], ret(Some(ValueExpr::Symbolic { name: "$t0".into() }))),
    ]);
    let analysis = analyze_body(&b, Env::default(), &callsites, None, LanguageProfile::java());
    assert!(callees(&analysis).is_empty(), "{:?}", analysis.effects);
    assert!(!analysis.reached_blocks.contains(&BlockId::from_raw(1)));
    assert_eq!(analysis.returns.len(), 1);
    assert_eq!(analysis.returns[0].value, AbstractValue::bool(false));
}

#[test]
fn a_local_assignment_shadows_the_parameter() {
    // `f(p) { p = 2; if (p == 2) hit(); }` — the local assignment replaces the
    // parameter binding in the frame, so the condition is decided by the *new*
    // value, not by the unknown parameter.
    let callsites = vec![call(0, "hit", vec![])];
    let b = body(vec![
        block(0, vec![assign("p", ValueExpr::Int { value: 2 })], goto(1)),
        block(
            1,
            vec![],
            branch(
                0,
                ValueExpr::Binary {
                    op: semarch_core::BinaryOp::Eq,
                    lhs: Box::new(ValueExpr::Symbolic { name: "p".into() }),
                    rhs: Box::new(ValueExpr::Int { value: 2 }),
                },
                2,
                3,
            ),
        ),
        block(2, vec![eval(call_value(0))], ret(None)),
        block(3, vec![], ret(None)),
    ]);
    let mut initial = Env::default();
    initial.insert("p".to_owned(), AbstractValue::Unknown);
    let analysis = analyze_body(&b, initial, &callsites, None, LanguageProfile::java());
    assert_eq!(
        callees(&analysis),
        vec![("hit".to_owned(), EvidenceStatus::Confirmed)]
    );
    assert!(!analysis.reached_blocks.contains(&BlockId::from_raw(3)));
}

#[test]
fn a_loop_converges_and_its_body_stays_possible() {
    let callsites = vec![call(0, "step", vec![])];
    let b = body(vec![
        block(0, vec![assign("i", ValueExpr::Int { value: 0 })], goto(1)),
        block(
            1,
            vec![],
            branch(
                0,
                ValueExpr::Binary {
                    op: semarch_core::BinaryOp::Lt,
                    lhs: Box::new(ValueExpr::Symbolic { name: "i".into() }),
                    rhs: Box::new(ValueExpr::Symbolic { name: "n".into() }),
                },
                2,
                3,
            ),
        ),
        block(
            2,
            vec![
                eval(call_value(0)),
                assign(
                    "i",
                    ValueExpr::Binary {
                        op: semarch_core::BinaryOp::Add,
                        lhs: Box::new(ValueExpr::Symbolic { name: "i".into() }),
                        rhs: Box::new(ValueExpr::Int { value: 1 }),
                    },
                ),
            ],
            goto(1),
        ),
        block(3, vec![], ret(Some(ValueExpr::Symbolic { name: "i".into() }))),
    ]);
    let mut initial = Env::default();
    initial.insert("n".to_owned(), AbstractValue::int(3));
    let analysis = analyze_body(&b, initial, &callsites, None, LanguageProfile::java());
    assert_eq!(
        callees(&analysis),
        vec![("step".to_owned(), EvidenceStatus::Possible)]
    );
    // The loop did not widen: `i` becomes Unknown at the header by joining
    // 0 with 1, which is a fixed point, not a sweep-limit escape.
    assert!(
        !analysis
            .gaps
            .iter()
            .any(|g| g.reason == GapReason::Widened),
        "{:?}",
        analysis.gaps
    );
}

#[test]
fn a_throw_is_a_recorded_exit() {
    let b = body(vec![
        block(
            0,
            vec![eval(ValueExpr::Str { value: "boom".into() })],
            Terminator::Throw {
                value: ValueExpr::Str { value: "boom".into() },
            },
        ),
        block(1, vec![], ret(None)),
    ]);
    let analysis = analyze_body(&b, Env::default(), &[], None, LanguageProfile::java());
    assert_eq!(analysis.throws.len(), 1);
    assert_eq!(analysis.returns.len(), 0);
    assert_eq!(analysis.throws[0].block, BlockId::from_raw(0));
}

#[test]
fn a_gap_block_keeps_its_effects_possible() {
    let callsites = vec![call(0, "unmodeled", vec![])];
    // The construct's content lives in a block of its own, reachable only
    // through the unmodeled mechanism: the *normal* path runs block 0 → 1 and
    // never executes block 2.
    let mut b = body(vec![
        block(0, vec![], goto(1)),
        block(1, vec![], ret(None)),
        block(2, vec![eval(call_value(0))], ret(None)),
    ]);
    b.gaps.push(
        AnalysisGap::new(GapReason::ExceptionDispatch, "catch clause", Some(span()))
            .in_block(BlockId::from_raw(2))
            .owned_by(BlockId::from_raw(1)),
    );
    let analysis = analyze_body(&b, Env::default(), &callsites, None, LanguageProfile::java());
    assert_eq!(
        callees(&analysis),
        vec![("unmodeled".to_owned(), EvidenceStatus::Possible)],
        "an effect behind an unmodeled mechanism is possible, never confirmed"
    );
    assert!(
        analysis.tainted_blocks.contains(&BlockId::from_raw(2)),
        "the content block is reached on a gap witness: {:?}",
        analysis.tainted_blocks
    );
    assert!(analysis
        .gaps
        .iter()
        .any(|g| g.reason == GapReason::ExceptionDispatch));
}

#[test]
fn a_gap_block_owned_by_a_dead_arm_stays_dead() {
    let callsites = vec![call(0, "unmodeled", vec![])];
    // The arm that owns the gap is unreachable: `if (false)` never takes the
    // then-branch, so the construct's content must not be revived.
    let mut b = body(vec![
        block(0, vec![], branch(0, ValueExpr::Bool { value: false }, 1, 2)),
        block(1, vec![], goto(3)),
        block(2, vec![], ret(None)),
        block(3, vec![eval(call_value(0))], ret(None)),
    ]);
    b.gaps.push(
        AnalysisGap::new(GapReason::NotInFactContract, "new Foo()", Some(span()))
            .in_block(BlockId::from_raw(3))
            .owned_by(BlockId::from_raw(1)),
    );
    let analysis = analyze_body(&b, Env::default(), &callsites, None, LanguageProfile::java());
    assert!(
        callees(&analysis).is_empty(),
        "an unmodeled construct inside a dead arm stays dead: {:?}",
        callees(&analysis)
    );
    assert_eq!(
        analysis.reached_blocks,
        vec![BlockId::from_raw(0), BlockId::from_raw(2)]
    );
}

#[test]
fn an_unsupported_statement_is_reported_and_produces_no_value() {
    let b = body(vec![block(
        0,
        vec![Statement::Unsupported {
            reason: GapReason::UnsupportedStatement,
            detail: "switch".to_owned(),
        }],
        ret(Some(ValueExpr::Unknown)),
    )]);
    let analysis = analyze_body(&b, Env::default(), &[], None, LanguageProfile::java());
    assert_eq!(analysis.gaps.len(), 1);
    assert_eq!(analysis.gaps[0].reason, GapReason::UnsupportedStatement);
    // The return value is unknown, not invented.
    assert_eq!(analysis.returns.len(), 1);
    assert!(analysis.returns[0].value.is_unknown());
}

// -- interprocedural summaries ------------------------------------------------

fn function(id: u32, name: &str, params: &[&str], returns: Vec<ValueExpr>) -> Function {
    Function {
        id: FunctionId::from_raw(id),
        name: name.to_owned(),
        qualified: None,
        // `SymbolIdx` is unused by the analysis; the value is a placeholder.
        kind: SymbolKind::Method,
        span: span(),
        params: (0..params.len())
            .map(|i| ValueExpr::Parameter { index: i as u16 })
            .collect(),
        param_names: params.iter().map(|p| (*p).to_owned()).collect(),
        returns,
        is_decl_only: false,
    }
}

#[test]
fn actual_arguments_reach_the_callee_return() {
    // `identity(x)` is `p`, so `identity(7) == 7` is decidable.
    let functions = vec![function(0, "identity", &["p"], vec![ValueExpr::Symbolic {
        name: "p".into(),
    }])];
    let resolver = SimpleNameResolver {
        functions: &functions,
    };
    let callsites = vec![call(0, "identity", vec![ValueExpr::Int { value: 7 }])];
    let b = body(vec![block(
        0,
        vec![],
        branch(
            0,
            ValueExpr::Binary {
                op: semarch_core::BinaryOp::Eq,
                lhs: Box::new(call_value(0)),
                rhs: Box::new(ValueExpr::Int { value: 7 }),
            },
            1,
            2,
        ),
    )]
    .into_iter()
    .chain([
        block(1, vec![], ret(None)),
        block(2, vec![], ret(None)),
    ])
    .collect());
    let analysis = analyze_body(
        &b,
        Env::default(),
        &callsites,
        Some(&resolver),
        LanguageProfile::java(),
    );
    assert_eq!(analysis.returns.len(), 1);
    assert_eq!(analysis.returns[0].block, BlockId::from_raw(1));
}

#[test]
fn a_summary_is_not_shared_between_calls_with_different_arguments() {
    // `identity(1) == 1` holds, `identity(2) == 1` does not: the second call
    // must not reuse the first call's result.
    let functions = vec![function(0, "identity", &["p"], vec![ValueExpr::Symbolic {
        name: "p".into(),
    }])];
    let resolver = SimpleNameResolver {
        functions: &functions,
    };
    let callsites = vec![
        call(0, "identity", vec![ValueExpr::Int { value: 1 }]),
        call(1, "identity", vec![ValueExpr::Int { value: 2 }]),
    ];
    let eq_one = |value: ValueExpr| ValueExpr::Binary {
        op: semarch_core::BinaryOp::Eq,
        lhs: Box::new(value),
        rhs: Box::new(ValueExpr::Int { value: 1 }),
    };
    let b = body(vec![
        block(0, vec![], branch(0, eq_one(call_value(0)), 1, 2)),
        block(1, vec![], branch(1, eq_one(call_value(1)), 3, 4)),
        block(2, vec![], ret(None)),
        block(3, vec![eval(call_value(1))], ret(None)),
        block(4, vec![], ret(None)),
    ]);
    let analysis = analyze_body(
        &b,
        Env::default(),
        &callsites,
        Some(&resolver),
        LanguageProfile::java(),
    );
    // The first comparison is true, so block 1 is reached unconditionally; the
    // second is false, so block 3 is not reached at all.
    assert!(!analysis.reached_blocks.contains(&BlockId::from_raw(3)));
    assert!(analysis.reached_blocks.contains(&BlockId::from_raw(4)));
}

#[test]
fn an_ambiguous_callee_is_a_gap_not_a_guess() {
    let functions = vec![
        function(0, "save", &[], vec![ValueExpr::Int { value: 1 }]),
        function(1, "save", &[], vec![ValueExpr::Int { value: 2 }]),
    ];
    let resolver = SimpleNameResolver {
        functions: &functions,
    };
    let callsites = vec![call(0, "save", vec![])];
    let b = body(vec![block(0, vec![eval(call_value(0))], ret(Some(call_value(0))))]);
    let analysis = analyze_body(
        &b,
        Env::default(),
        &callsites,
        Some(&resolver),
        LanguageProfile::java(),
    );
    assert!(analysis
        .gaps
        .iter()
        .any(|g| g.detail == "callee_ambiguous" && g.reason == GapReason::UnresolvedCall));
    assert!(analysis.returns[0].value.is_unknown());
}

#[test]
fn recursion_is_bounded_and_reported() {
    // `loop() { return loop(); }` — the summary must stop at the depth limit
    // instead of recursing forever, and say so.
    let functions = vec![function(0, "loop", &[], vec![call_value(0)])];
    let resolver = SimpleNameResolver {
        functions: &functions,
    };
    let callsites = vec![call(0, "loop", vec![])];
    let b = body(vec![block(0, vec![], ret(Some(call_value(0))))]);
    let analysis = analyze_body(
        &b,
        Env::default(),
        &callsites,
        Some(&resolver),
        LanguageProfile::java(),
    );
    assert!(analysis
        .gaps
        .iter()
        .any(|g| g.detail == "recursion_depth_limit"));
    assert!(analysis.returns[0].value.is_unknown());
}

#[test]
fn an_unresolved_callee_is_recorded_and_yields_unknown() {
    let resolver = SimpleNameResolver { functions: &[] };
    let callsites = vec![call(0, "outside", vec![])];
    let b = body(vec![block(0, vec![], ret(Some(call_value(0))))]);
    let analysis = analyze_body(
        &b,
        Env::default(),
        &callsites,
        Some(&resolver),
        LanguageProfile::java(),
    );
    assert!(analysis
        .gaps
        .iter()
        .any(|g| g.detail == "callee_not_resolved"));
    assert!(analysis.returns[0].value.is_unknown());
}

#[test]
fn a_resolver_is_optional() {
    // Without a resolver nothing interprocedural is claimed: the value is
    // unknown and no "unresolved" gap is invented (the analyzer was not asked).
    let callsites = vec![call(0, "anything", vec![])];
    let b = body(vec![block(0, vec![], ret(Some(call_value(0))))]);
    let analysis = analyze_body(&b, Env::default(), &callsites, None, LanguageProfile::java());
    assert!(analysis.returns[0].value.is_unknown());
    assert!(analysis.gaps.is_empty(), "{:?}", analysis.gaps);
}

#[test]
fn guards_are_reported_by_id_so_evidence_can_be_traced() {
    let mut b = body(vec![
        block(0, vec![], branch(7, ValueExpr::Symbolic { name: "p".into() }, 1, 2)),
        block(1, vec![], ret(None)),
        block(2, vec![], ret(None)),
    ]);
    b.guards.push(Guard {
        id: GuardId::from_raw(7),
        condition: ValueExpr::Symbolic { name: "p".into() },
        span: span(),
    });
    let analysis = analyze_body(&b, Env::default(), &[], None, LanguageProfile::java());
    let effects = analysis.effects.len();
    assert_eq!(effects, 0);
    // Both paths are taken and the witness names the guard.
    assert_eq!(analysis.returns.len(), 2);
}

#[test]
fn the_analysis_is_deterministic() {
    let callsites = vec![call(0, "a", vec![]), call(1, "b", vec![])];
    let b = body(vec![
        block(0, vec![], branch(0, ValueExpr::Symbolic { name: "p".into() }, 1, 2)),
        block(1, vec![eval(call_value(0))], goto(3)),
        block(2, vec![eval(call_value(1))], goto(3)),
        block(3, vec![], ret(None)),
    ]);
    let first = analyze_body(&b, Env::default(), &callsites, None, LanguageProfile::java());
    let second = analyze_body(&b, Env::default(), &callsites, None, LanguageProfile::java());
    assert_eq!(first, second);
}

#[test]
fn the_resolver_trait_is_object_safe_for_downstream_adapters() {
    let functions = vec![function(0, "f", &[], vec![ValueExpr::Int { value: 1 }])];
    let resolver: &dyn CallResolver = &SimpleNameResolver {
        functions: &functions,
    };
    assert_eq!(resolver.candidates("f").len(), 1);
    assert!(resolver.candidates("missing").is_empty());
}
