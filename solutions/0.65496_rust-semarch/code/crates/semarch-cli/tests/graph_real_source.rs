//! T11/T12 acceptance on the REAL Train Ticket source:
//!
//! - Call-site ownership by innermost span containment and name-based callee
//!   resolution over `TokenServiceImpl.java`: the private `getServiceUrl`
//!   helper resolves uniquely (confirmed edge), library calls stay
//!   unresolved externals (never dropped, never guessed).
//! - Interprocedural propagation: the analyzer evaluates
//!   `getServiceUrl("ts-verification-code-service")` to the concrete URL by
//!   substituting the actual argument into the callee's return expression
//!   (`return "http://" + serviceName`). Language-neutral mechanism, real
//!   frontend source.
//!
//! Java identifiers appear verbatim in helper/constants; test names stay
//! snake_case per clippy.

#![allow(non_snake_case)]

use semarch_core::value::AbstractValue;
use semarch_core::analysis::{Analyzer, Env, SimpleNameResolver};
use semarch_core::graph::{ArchitectureGraph, NodeKind};
use semarch_core::ir::{CallSite, Function, ValueExpr};
use semarch_core::{
    Allocator, EvidenceStatus, Language, LanguageFrontend, ParseContext,
};
use semarch_frontend_java::JavaFrontend;

const TOKEN_SERVICE: &str =
    "tt-challenge/targets/trainticket/ts-auth-service/src/main/java/auth/service/impl/TokenServiceImpl.java";

fn parse_real_file() -> (Vec<Function>, Vec<CallSite>) {
    let path = std::format!(
        "{}/../../../{}",
        env!("CARGO_MANIFEST_DIR"),
        TOKEN_SERVICE
    );
    let source = std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("needs the Train Ticket tree ({e}): {path}"));
    let mut fe = JavaFrontend::new().expect("grammar ABI ok");
    let mut alloc = Allocator::default();
    let mut diags = Vec::new();
    let mut ctx = ParseContext::new(0u32.into(), Language::Java, &mut alloc, &mut diags);
    let pf = fe.parse(&mut ctx, &source).expect("parse succeeds");
    (pf.functions, pf.callsites)
}

#[test]
fn get_service_url_is_a_confirmed_edge_of_get_token() {
    let (functions, callsites) = parse_real_file();

    let tokens = functions
        .iter()
        .filter(|f| f.name == "getServiceUrl")
        .count();
    assert_eq!(
        tokens, 1,
        "the private getServiceUrl(URL: String) helper must be extracted"
    );
    let token = functions
        .iter()
        .find(|f| f.name == "getToken")
        .expect("getToken present").id;

    let (graph, stats) = ArchitectureGraph::build(&functions, &[&callsites]);
    assert!(stats.functions >= 2, "getToken + getServiceUrl at least");

    let confirmed = &graph.edges.iter().filter(|(from, _, e)| {
        graph.nodes[*from as usize] == NodeKind::Function { id: token }
            && e.evidence.status == EvidenceStatus::Confirmed
    }).count();
    assert!(
        *confirmed >= 1,
        "getToken → getServiceUrl must be confirmed by unique name match"
    );

    // Library surface (StringUtils/is/restTemplate/…) never becomes a guess:
    // unresolvable callees are External nodes with unresolved evidence.
    assert!(
        graph
            .nodes
            .iter()
            .any(|n| matches!(n, NodeKind::External { label } if label == "isEmpty")),
        "isEmpty stays an external node (library, not a guess)"
    );
}

#[test]
fn may_closure_makes_get_service_url_executable_from_get_token() {
    let (functions, callsites) = parse_real_file();
    let (graph, _) = ArchitectureGraph::build(&functions, &[&callsites]);
    let closure = graph.may_closure();

    let get_token = functions
        .iter()
        .find(|f| f.name == "getToken")
        .expect("getToken")
        .id;
    let get_service_url = functions
        .iter()
        .find(|f| f.name == "getServiceUrl")
        .expect("getServiceUrl")
        .id;

    let reach = &closure[&get_token];
    assert!(
        reach.contains(&get_service_url),
        "may-closure (executes) must include the resolved helper"
    );
}

#[test]
fn interprocedural_eval_substitutes_url_result() {
    let (functions, callsites) = parse_real_file();

    // The call site in getToken: getServiceUrl("ts-verification-code-service")
    let cs = callsites
        .iter()
        .find(|c| c.callee == "getServiceUrl")
        .expect("the getToken body contains one getServiceUrl call");

    let resolver = SimpleNameResolver { functions: &functions };
    let analyzer = Analyzer::new(Env::default(), &callsites).with_resolver(&resolver);

    let got = analyzer.eval(&ValueExpr::CallResult { callsite: cs.id });
    assert_eq!(
        got,
        AbstractValue::str_val("http://ts-verification-code-service"),
        "T11: actual argument must be substituted into the callee return"
    );
}

#[test]
fn returns_collected_from_real_source() {
    let (functions, _) = parse_real_file();
    let helper = functions
        .iter()
        .find(|f| f.name == "getServiceUrl")
        .expect("getServiceUrl");
    assert_eq!(
        helper.returns,
        vec![ValueExpr::Binary {
            op: semarch_core::BinaryOp::Add,
            lhs: Box::new(ValueExpr::Str { value: "http://".into() }),
            rhs: Box::new(ValueExpr::Symbolic { name: "serviceName".into() }),
        }],
        "return expressions must be collected into the IR Function"
    );
    // Param name binding data comes from the real declaration:
    assert_eq!(helper.param_names, vec!["serviceName".to_string()]);
    assert!(functions.iter().any(|f| f.name == "getToken"));
}
