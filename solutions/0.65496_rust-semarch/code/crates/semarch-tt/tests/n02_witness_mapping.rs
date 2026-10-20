//! N02 acceptance for the evidence mapping: a predicted edge either has one
//! checkable witness, or several — in which case the report must say so instead
//! of presenting the first call site as *the* reason.
//!
//! The fixture is a source-less skeleton (only the graph is exercised): one
//! method calls the same callee twice (the `@65`/`@67` shape), another calls it
//! once.

use semarch_tt::graph::TtGraph;
use semarch_tt::skeleton::Skeleton;

const CALLER: &str = "method:svc:a.Svc#caller()";
const SINGLE: &str = "method:svc:a.Svc#single()";
const DUP: &str = "method:svc:a.Svc#dup()";
const FILE: &str = "svc/src/main/java/a/Svc.java";

fn skeleton() -> Skeleton {
    let doc = serde_json::json!({
        "project": "toy",
        "nodes": {
            "type:svc:a.Svc": {"kind": "type", "fqn": "a.Svc", "type_kind": "class", "module": "svc"},
            CALLER: {"kind": "method", "owner": "type:svc:a.Svc", "name": "caller", "descriptor": "", "module": "svc", "file": FILE, "line": 60},
            SINGLE: {"kind": "method", "owner": "type:svc:a.Svc", "name": "single", "descriptor": "", "module": "svc", "file": FILE, "line": 60},
            DUP: {"kind": "method", "owner": "type:svc:a.Svc", "name": "dup", "descriptor": "", "module": "svc", "file": FILE, "line": 20},
            "call:svc:1": {"kind": "call_site", "method": CALLER, "callee": "dup", "receiver": "svc",
                "receiver_type": "a.Svc", "arg_count": 0, "args_text": "()",
                "file": FILE, "line": 65, "end": 65},
            "call:svc:2": {"kind": "call_site", "method": CALLER, "callee": "dup", "receiver": "svc",
                "receiver_type": "a.Svc", "arg_count": 0, "args_text": "()",
                "file": FILE, "line": 67, "end": 67},
            "call:svc:3": {"kind": "call_site", "method": SINGLE, "callee": "dup", "receiver": "svc",
                "receiver_type": "a.Svc", "arg_count": 0, "args_text": "()",
                "file": FILE, "line": 70, "end": 70}
        },
        "edges": [
            {"source": "call:svc:1", "type": "calls", "target": DUP},
            {"source": "call:svc:2", "type": "calls", "target": DUP},
            {"source": "call:svc:3", "type": "calls", "target": DUP}
        ]
    });
    Skeleton::parse(serde_json::to_string(&doc).unwrap().as_bytes()).expect("skeleton parses")
}

#[test]
fn two_call_sites_for_one_edge_are_reported_as_ambiguous() {
    let graph = TtGraph::build(&skeleton());
    let ev = graph.evidence_for("calls", CALLER, DUP);

    assert_eq!(ev.mapping, "ambiguous");
    assert!(ev.call_site.is_none(), "no single site may be presented as the witness");
    assert_eq!(ev.basis, "calls");
    assert_eq!(ev.witnesses.len(), 2, "both call sites are named");
    let lines: Vec<Option<u32>> = ev.witnesses.iter().map(|w| w.line).collect();
    assert_eq!(lines, vec![Some(65), Some(67)], "@65 and @67 are distinguished");
    assert!(
        ev.note.contains("65") && ev.note.contains("67"),
        "the reason names both places: {}",
        ev.note
    );
    assert!(ev.witnesses.iter().all(|w| w.receiver_type.as_deref() == Some("a.Svc")));
}

#[test]
fn one_call_site_is_a_unique_checkable_witness() {
    let graph = TtGraph::build(&skeleton());
    let ev = graph.evidence_for("calls", SINGLE, DUP);

    assert_eq!(ev.mapping, "unique");
    assert_eq!(ev.call_site.as_deref(), Some("call:svc:3"));
    assert_eq!(ev.line, Some(70));
    assert_eq!(ev.file.as_deref(), Some(FILE));
    assert_eq!(ev.receiver_type.as_deref(), Some("a.Svc"));
    assert_eq!(ev.args_text.as_deref(), Some("()"));
    assert_eq!(ev.witnesses.len(), 1);
}

#[test]
fn an_edge_without_a_call_site_is_a_contract() {
    let graph = TtGraph::build(&skeleton());
    let ev = graph.evidence_for("calls", DUP, CALLER);
    assert_eq!(ev.mapping, "contract");
    assert_eq!(ev.basis, "framework");
    assert!(ev.witnesses.is_empty());
}
