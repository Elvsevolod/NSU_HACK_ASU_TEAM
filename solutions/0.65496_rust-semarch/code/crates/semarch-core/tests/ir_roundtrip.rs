//! Serde round-trip tests for the Common IR (T02 acceptance: `Debug`,
//! `PartialEq`, serde — serialize → deserialize → equal).

use semarch_core::{
    roundtrip_json, Action, BinaryOp, CallSite, Capability, Cfg, CfgBlock, Effect,
    Evidence, EvidenceStatus, Function, FunctionSummary, Guard, GuardCondition, Language,
    ModuleDecl, ParsedFile, SourceSpan, SymbolKind, UnaryOp, ValueExpr,
};

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

fn sample_function(file: u32) -> Function {
    Function {
        id: 7u32.into(),
        name: "getToken".into(),
        qualified: Some("TokenServiceImpl.getToken".into()),
        kind: SymbolKind::Method,
        span: span(file, 100, 250),
        params: vec![ValueExpr::Parameter { index: 0 }, ValueExpr::Parameter { index: 1 }],
        param_names: vec!["userId".into(), "verifyCode".into()],
        returns: vec![ValueExpr::Symbolic { name: "token".into() }],
        is_decl_only: false,
    }
}

fn sample_callsite(file: u32) -> CallSite {
    CallSite {
        id: 3u32.into(),
        callee: "verifyCode".into(),
        receiver: Some(ValueExpr::Symbolic { name: "verifyCodeService".into() }),
        args: vec![
            ValueExpr::Symbolic { name: "verifyCode".into() },
            ValueExpr::Parameter { index: 1 },
        ],
        span: span(file, 67, 78),
        name_span: None,
    }
}

#[test]
fn function_roundtrips() {
    let f = sample_function(12);
    assert_eq!(roundtrip_json(&f).unwrap(), f);
}

#[test]
fn callsite_roundtrips_with_nested_receiver() {
    let c = sample_callsite(12);
    assert_eq!(roundtrip_json(&c).unwrap(), c);
}

#[test]
fn value_expr_all_variants_roundtrip() {
    let variants = vec![
        ValueExpr::Unknown,
        ValueExpr::Null,
        ValueExpr::Bool { value: true },
        ValueExpr::Int { value: -5 },
        ValueExpr::Float { value: 2.5 },
        ValueExpr::Str { value: "abc".into() },
        ValueExpr::Symbolic { name: "x".into() },
        ValueExpr::Parameter { index: 2 },
        ValueExpr::Field {
            base: Box::new(ValueExpr::Symbolic { name: "order".into() }),
            name: "status".into(),
        },
        ValueExpr::Unary {
            op: UnaryOp::Not,
            operand: Box::new(ValueExpr::Bool { value: false }),
        },
        ValueExpr::Binary {
            op: BinaryOp::Eq,
            lhs: Box::new(ValueExpr::Str { value: "".into() }),
            rhs: Box::new(ValueExpr::CallResult { callsite: 3u32.into() }),
        },
        ValueExpr::CallResult { callsite: 9u32.into() },
    ];
    for v in variants {
        assert_eq!(roundtrip_json(&v).unwrap(), v);
    }
}

#[test]
fn evidence_status_serializes_snake_case() {
    for (status, expected) in [
        (EvidenceStatus::Confirmed, "confirmed"),
        (EvidenceStatus::Possible, "possible"),
        (EvidenceStatus::Excluded, "excluded"),
        (EvidenceStatus::Unresolved, "unresolved"),
    ] {
        let json = serde_json::to_string(&status).unwrap();
        assert_eq!(json, format!("{expected:?}"));
    }
}

#[test]
fn unknown_is_not_false() {
    // The invariant is structural: Unknown is its own variant, distinct from
    // Bool(false), with no implicit conversion API anywhere in the core.
    assert_ne!(ValueExpr::Unknown, ValueExpr::Bool { value: false });
    let json = serde_json::to_string(&ValueExpr::Unknown).unwrap();
    assert_eq!(json, r#"{"kind":"unknown"}"#);
}

#[test]
fn cfg_roundtrips_with_guards() {
    let cfg = Cfg {
        function: 1u32.into(),
        entry: Some(0u32.into()),
        exit: Some(3u32.into()),
        blocks: vec![
            CfgBlock {
                id: 0u32.into(),
                guard: Some(0u32.into()),
                true_succ: Some(1u32.into()),
                false_succ: Some(3u32.into()),
                actions: vec![],
            },
            CfgBlock {
                id: 1u32.into(),
                guard: None,
                true_succ: Some(3u32.into()),
                false_succ: None,
                actions: vec![
                    Action::Assign {
                        target: ValueExpr::Symbolic { name: "x".into() },
                        value: ValueExpr::Int { value: 1 },
                    },
                    Action::Return {
                        value: Some(ValueExpr::Symbolic { name: "x".into() }),
                    },
                ],
            },
        ],
        guards: vec![Guard {
            id: 0u32.into(),
            condition: ValueExpr::Binary {
                op: BinaryOp::Eq,
                lhs: Box::new(ValueExpr::Str { value: "".into() }),
                rhs: Box::new(ValueExpr::Str { value: "".into() }),
            },
            span: span(2, 40, 60),
        }],
    };
    assert_eq!(roundtrip_json(&cfg).unwrap(), cfg);
}

#[test]
fn function_summary_with_evidence_roundtrips() {
    let s = FunctionSummary {
        function: 5u32.into(),
        executes: vec![(9u32.into(), Evidence::confirmed("direct_call"))],
        calls: vec![(3u32.into(), Some(9u32.into()), Evidence::confirmed("call_edge"))],
        effects: vec![(
            Effect::HttpCall {
                url: "http://verify-service:15679/verifycode".into(),
            },
            Evidence::possible("framework_mapping"),
        )],
    };
    assert_eq!(roundtrip_json(&s).unwrap(), s);
}

#[test]
fn parsed_file_roundtrips() {
    let pf = ParsedFile {
        file: 3u32.into(),
        language: Language::Java,
        module: Some(ModuleDecl {
            id: 2u32.into(),
            path: "com.example".into(),
        }),
        imports: vec![],
        annotations: vec![],
        functions: vec![sample_function(3)],
        callsites: vec![sample_callsite(3)],
        bodies: vec![],
        guard_conditions: vec![GuardCondition {
            condition: ValueExpr::Binary {
                op: BinaryOp::Or,
                lhs: Box::new(ValueExpr::Null),
                rhs: Box::new(ValueExpr::Str { value: String::new() }),
            },
            span: span(3, 10, 20),
            then_span: Some(span(3, 11, 20)),
            else_span: None,
            body_span: Some(span(3, 10, 22)),
            body_always_runs: false,
        }],
    };
    assert_eq!(roundtrip_json(&pf).unwrap(), pf);
}

#[test]
fn capabilities_cover_the_normalized_facts() {
    use Capability::*;
    let required = [
        Declarations, Parameters, CallSites, Literals, MemberAccess, Assignments,
        IfElse, ReturnThrow, BasicLoops, AnnotationsDecorators, Imports, SourceSpans,
    ];
    for c in required {
        // Exhaustive match over Capability, so adding a variant breaks this
        // test and every frontend must consciously extend its matrix.
        let shown = match c {
            Declarations => "declarations",
            Parameters => "parameters",
            CallSites => "call_sites",
            Literals => "literals",
            MemberAccess => "member_access",
            Assignments => "assignments",
            IfElse => "if_else",
            ReturnThrow => "return_throw",
            BasicLoops => "basic_loops",
            AnnotationsDecorators => "annotations",
            Imports => "imports",
            SourceSpans => "source_spans",
        };
        assert!(!shown.is_empty());
    }
}
