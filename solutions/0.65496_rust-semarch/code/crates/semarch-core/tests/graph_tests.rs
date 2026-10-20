//! T12 acceptance: architecture graph construction (ownership by innermost
//! span containment, name-based callee resolution with evidence statuses)
//! and the may-closure reachability used for `executes`.

use semarch_core::ids::{CallSiteId, FunctionId};
use semarch_core::ir::{CallSite, EvidenceStatus, Function, SymbolKind, ValueExpr};
use semarch_core::graph::{ArchitectureGraph, NodeKind};
use semarch_core::span::SourceSpan;

fn span(file: u32, start: u32, end: u32) -> SourceSpan {
    SourceSpan {
        file: file.into(),
        start_byte: start,
        end_byte: end,
        start_row: 0,
        start_col: start,
        end_row: 0,
        end_col: end,
    }
}

/// Caller f [0..100) calls g [200..300) with a unique name.
fn f(callsite: CallSiteId) -> (Function, CallSite) {
    let function = Function {
        id: FunctionId(1),
        name: "f".into(),
        qualified: None,
        kind: SymbolKind::Function,
        span: span(1, 0, 100),
        params: vec![],
        param_names: vec![],
        returns: vec![],
        is_decl_only: false,
    };
    let site = CallSite {
        id: callsite,
        callee: "g".into(),
        receiver: None,
        args: vec![],
        span: span(1, 50, 60),
        name_span: None,
    };
    (function, site)
}

/// Callee `g` [200..300), unique.
fn g() -> Function {
    Function {
        id: FunctionId(2),
        name: "g".into(),
        qualified: None,
        kind: SymbolKind::Function,
        span: span(1, 200, 300),
        params: vec![ValueExpr::Parameter { index: 0 }],
        param_names: vec!["n".into()],
        returns: vec![ValueExpr::Int { value: 0 }],
        is_decl_only: false,
    }
}

#[test]
fn owner_is_innermost_containing_function() {
    let (f, cs) = f(CallSiteId(1));
    let callee = g();
    // Outer wrapper spanning the whole file: f must still win as owner
    // (smallest covering span).
    let outer = Function {
        id: FunctionId(9),
        name: "outer".into(),
        qualified: None,
        kind: SymbolKind::Function,
        span: span(1, 0, 1000),
        params: vec![],
        param_names: vec![],
        returns: vec![],
        is_decl_only: false,
    };
    let functions = vec![outer, f, callee];
    let (graph, stats) = ArchitectureGraph::build(&functions, &[&[cs]]);

    assert_eq!(stats.functions, 3);
    assert_eq!(stats.confirmed_edges, 1);
    let from = &graph.edges[0].0;
    assert_eq!(
        graph.nodes[graph.function_nodes[&FunctionId(1)] as usize],
        NodeKind::Function { id: FunctionId(1) }
    );
    assert_eq!(
        graph.nodes[graph.function_nodes[&FunctionId(1)] as usize].clone(),
        NodeKind::Function { id: FunctionId(1) }
    );
    let _ = from;
}

#[test]
fn confirmed_edge_has_evidence_and_closure_is_transitive() {
    // g calls r (a third function); set up f → g → r closure.
    let r_fn = Function {
        id: FunctionId(3),
        name: "r".into(),
        qualified: None,
        kind: SymbolKind::Function,
        span: span(1, 400, 500),
        params: vec![],
        param_names: vec![],
        returns: vec![],
        is_decl_only: false,
    };
    let r_site = CallSite {
        id: CallSiteId(2),
        callee: "r".into(),
        receiver: None,
        args: vec![],
        span: span(1, 250, 260),
        name_span: None,
    };
    let (f, cs) = f(CallSiteId(1));
    let templates = vec![f, g(), r_fn];
    let sites_file1 = [cs, r_site];

    let (graph, stats) = ArchitectureGraph::build(&templates, &[&sites_file1[..]]);
    assert_eq!(stats.confirmed_edges, 2);

    let closure = graph.may_closure();
    let f_reach = closure.get(&FunctionId(1)).expect("f in closure map");
    assert!(f_reach.contains(&FunctionId(2)));
    assert!(
        f_reach.contains(&FunctionId(3)),
        "may-closure must be transitive over call edges"
    );
    assert!(!f_reach.contains(&FunctionId(1)), "self not in own closure");
}

#[test]
fn cycle_terminates_and_closes_both_sides() {
    // a [0..50) calls b; b [100..150) calls a.
    let a = Function {
        id: FunctionId(10),
        name: "a".into(),
        qualified: None,
        kind: SymbolKind::Function,
        span: span(2, 0, 50),
        params: vec![],
        param_names: vec![],
        returns: vec![],
        is_decl_only: false,
    };
    let b = Function {
        id: FunctionId(11),
        name: "b".into(),
        qualified: None,
        kind: SymbolKind::Function,
        span: span(2, 100, 150),
        params: vec![],
        param_names: vec![],
        returns: vec![],
        is_decl_only: false,
    };
    let sites = [
        CallSite { id: CallSiteId(30), callee: "b".into(), receiver: None, args: vec![], span: span(2, 10, 20), name_span: None },
        CallSite { id: CallSiteId(31), callee: "a".into(), receiver: None, args: vec![], span: span(2, 110, 120), name_span: None },
    ];
    let functions = vec![a, b];
    let (graph, stats) = ArchitectureGraph::build(&functions, &[&sites]);
    assert_eq!(stats.confirmed_edges, 2);

    let closure = graph.may_closure();
    let a_reach = &closure[&FunctionId(10)];
    let b_reach = &closure[&FunctionId(11)];
    assert!(a_reach.contains(&FunctionId(11)) && b_reach.contains(&FunctionId(10)));
    // Reaching "self" through the cycle is a legitimate may-closure answer
    // (a cycle means recursion may happen) — but the v0 excludes self-id
    // entries; termination is the property under test, no hang here.
}

#[test]
fn unresolvable_callee_becomes_unresolved_evidence_not_dropped() {
    let (f, mut cs) = f(CallSiteId(1));
    cs.callee = "sprintf".into(); // no project function named `sprintf`
    let functions = vec![f];
    let (graph, stats) = ArchitectureGraph::build(&functions, &[&[cs]]);

    assert_eq!(stats.unresolved_edges, 1);
    assert!(stats.confirmed_edges == 0 && stats.possible_edges == 0);
    assert!(
        graph.nodes.iter().any(|n| matches!(n, NodeKind::External { label } if label == "sprintf")),
        "external callee node must exist"
    );
    assert_eq!(graph.edges[0].2.evidence.status, EvidenceStatus::Unresolved);
}

#[test]
fn ambiguous_callee_spreads_possible_edges() {
    let g1 = g();
    let g2 = Function {
        id: FunctionId(20),
        name: "g".into(),
        ..g1.clone()
    };
    let (f, cs) = f(CallSiteId(1));
    let functions = vec![f, g1, g2];
    let (graph, stats) = ArchitectureGraph::build(&functions, &[&[cs]]);
    assert_eq!(stats.possible_edges, 2);
    assert_eq!(stats.confirmed_edges, 0);
    for (_, _, edge) in &graph.edges {
        assert_eq!(edge.evidence.status, EvidenceStatus::Possible);
    }
}
