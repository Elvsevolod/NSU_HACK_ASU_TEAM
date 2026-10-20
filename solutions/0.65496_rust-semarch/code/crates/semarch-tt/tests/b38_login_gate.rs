//! The login gate of the B38 increment, end to end on the contest project.
//!
//! The `review_b38_*` suites are the review package's specification; this file
//! is the increment's own regression pin. It walks the whole chain the
//! increment claims, on the real `tt-challenge` checkout, and fails loudly if
//! any link of it moves:
//!
//! ```text
//! scenario step
//!   -> grounded entry (which handler the step is about)
//!   -> bound request field (what value the request carries, and why)
//!   -> guard decision (which branch that value proves)
//!   -> excluded call sites (each with the decision that proves it dead)
//!   -> the answer's edge set (the remote call is gone, or present)
//! ```
//!
//! Nothing here is a simulation: the loader, the entry grounder, the request
//! binder, the Java frontend, the CFG analysis and the scenario engine are the
//! production ones, and `--require-sources` semantics are on (a missing source
//! tree is an error, not a quiet degradation).
//!
//! Scope, stated because the increment's earlier revisions overclaimed it: this
//! proves the *login* slice. It says nothing about the other scenarios, and it
//! does not establish that the semantic answer is more precise than the legacy
//! one — on this scenario the two agree edge for edge (see
//! `semarch/docs/B38_INCREMENT.md`, B38-05).

use std::path::{Path, PathBuf};

use semarch_scenario::scenario::{Scenario, Step};
use semarch_tt::engine::ScenarioOutcome;
use semarch_tt::pipeline::{AnalyzerConfig, LoadOptions, TtAnalyzer};
use semarch_tt::request::{BoundValue, FieldOrigin};

/// The login handler of the real project, as the answer's own id space spells
/// it.
const LOGIN_HANDLER: &str = "method:ts-auth-service:auth.controller.UserController#getToken(auth.dto.BasicAuthDto,org.springframework.http.HttpHeaders)";
/// The handler the guard lives in, one call away.
const TOKEN_SERVICE: &str = "method:ts-auth-service:auth.service.impl.TokenServiceImpl#getToken(auth.dto.BasicAuthDto,org.springframework.http.HttpHeaders)";
/// Callees of the three call sites the guard decision proves unreachable.
const EXCLUDED: [&str; 3] = ["exchange", "getBody", "info"];

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../..")
        .join("tt-challenge")
}

fn analyzer() -> TtAnalyzer {
    let root = root();
    assert!(
        root.join("sources.json").is_file() || root.join("targets").is_dir(),
        "the real contest checkout is required: {}",
        root.display()
    );
    TtAnalyzer::load_with(&root, &LoadOptions { require_sources: true }).expect("real sources")
}

fn scenario(actions: &[&str]) -> Scenario {
    Scenario {
        project: "trainticket".to_owned(),
        id: "B38-login-gate".to_owned(),
        title: String::new(),
        description: String::new(),
        input: "text".to_owned(),
        steps: actions
            .iter()
            .enumerate()
            .map(|(i, action)| Step {
                n: u32::try_from(i + 1).expect("step index"),
                action: (*action).to_owned(),
            })
            .collect(),
    }
}

fn run_with(actions: &[&str], cfg: &AnalyzerConfig) -> ScenarioOutcome {
    analyzer()
        .semantic_run(&scenario(actions), cfg)
        .expect("semantic pipeline")
}

fn run(actions: &[&str]) -> ScenarioOutcome {
    run_with(actions, &AnalyzerConfig::default())
}

/// Whether the answer's own edge set carries a call to the verification-code
/// service.
fn verify_remote(outcome: &ScenarioOutcome) -> bool {
    outcome
        .prediction
        .remote
        .iter()
        .any(|(_, target)| target.contains("VerifyCode"))
}

#[test]
fn the_login_step_grounds_on_the_login_handler() {
    let outcome = run(&["Log in with username and password"]);
    let step = &outcome.steps[0];
    assert_eq!(
        step.entries,
        vec![LOGIN_HANDLER.to_owned()],
        "the step is about one handler, and it is the login handler"
    );
    assert_eq!(step.bindings.len(), 1, "{:#?}", step.bindings);
    assert_eq!(step.bindings[0].endpoint, "/api/v1/users/login");
    assert_eq!(step.bindings[0].method, LOGIN_HANDLER);
}

#[test]
fn the_package_context_makes_the_verification_code_absent() {
    let outcome = run(&["Log in with username and password"]);
    let request = &outcome.steps[0].bindings[0];
    let field = |name: &str| {
        request
            .fields
            .iter()
            .find(|f| f.name == name)
            .unwrap_or_else(|| panic!("{name} is a declared field of the login DTO"))
    };

    // The step names these two and gives no value: they stay open.
    for name in ["username", "password"] {
        assert_eq!(field(name).value, BoundValue::Unknown, "{name}");
        assert_eq!(field(name).origin, FieldOrigin::Payload, "{name}");
    }
    // The task package states the pre-registered account has no code at login,
    // and the step does not contradict it: the field is *absent*, not unknown,
    // and the provenance names the clause that decided it.
    let code = field("verificationCode");
    assert_eq!(code.value, BoundValue::Absent);
    assert_eq!(code.origin, FieldOrigin::Context);
    assert!(
        code.provenance.to_lowercase().contains("verification code"),
        "the provenance names the statement: {}",
        code.provenance
    );
}

#[test]
fn the_absent_code_is_the_guard_that_proves_the_remote_call_dead() {
    let outcome = run(&["Log in with username and password"]);
    let step = &outcome.steps[0];

    // The decision: one branch, in the token service, proved false by the
    // absence of the code.
    let decision = step
        .decisions
        .iter()
        .find(|d| d.method == TOKEN_SERVICE && d.verdict == "proves_false")
        .unwrap_or_else(|| panic!("no proves_false decision in the token service: {:#?}", step.decisions));
    assert_eq!(decision.guard, "g0");
    assert_eq!(decision.line, Some(65));
    assert!(
        decision.symbols.iter().any(|s| s == "verifyCode"),
        "the decision is attributed to the code: {:?}",
        decision.symbols
    );
    assert!(
        decision.path.is_empty(),
        "the branch is reached unconditionally, so the verdict is not about a gap: {:?}",
        decision.path
    );

    // The three call sites that decision excludes, each with the certificate:
    // the same guard, line, verdict and dead blocks.
    assert_eq!(step.suppressed.len(), step.suppressions.len());
    assert_eq!(step.suppressions.len(), 3, "{:#?}", step.suppressions);
    let mut callees: Vec<&str> = step
        .suppressions
        .iter()
        .map(|s| s.callee.as_str())
        .collect();
    callees.sort_unstable();
    assert_eq!(callees, EXCLUDED, "{:#?}", step.suppressions);
    for suppression in &step.suppressions {
        let cert = &suppression.certificate;
        assert_eq!(cert.guard, decision.guard, "{}", suppression.call_site);
        assert_eq!(cert.line, decision.line, "{}", suppression.call_site);
        assert_eq!(cert.verdict, "proves_false", "{}", suppression.call_site);
        assert_eq!(cert.blocks, vec![2, 4, 5, 6], "{}", suppression.call_site);
        assert!(
            cert.blocks.contains(&cert.block),
            "the certificate's own block is one of the blocks it proves dead"
        );
    }

    // Every dropped site in this step has a certificate; nothing was dropped
    // because the method happened to contain an unmodeled construct.
    assert!(
        step.suppressions
            .iter()
            .any(|s| s.callee == "exchange" && s.call_site.ends_with("@67:55")),
        "the REST call this slice is about is among the certified drops: {:#?}",
        step.suppressions
    );
    assert_eq!(step.sites.suppressed, 3);
    assert_eq!(
        step.sites.kept.keys().collect::<Vec<_>>(),
        vec![&"skeleton_site_absent_from_lowered_body".to_owned()],
        "the whole-method veto cause is gone: {:?}",
        step.sites.kept
    );

    // And the answer itself: the code service is not called.
    assert!(
        !verify_remote(&outcome),
        "the proved-false guard removes the call: {:?}",
        outcome.prediction.remote
    );

    println!(
        "witness: entry {LOGIN_HANDLER}\n  binding: verificationCode = absent (context)\n  decision: {} {} line {:?} path {:?}\n  excluded: {}",
        decision.guard,
        decision.verdict,
        decision.line,
        decision.path,
        step.suppressions
            .iter()
            .map(semarch_tt::engine::Suppression::describe)
            .collect::<Vec<_>>()
            .join("; ")
    );
}

#[test]
fn turning_the_package_context_off_brings_the_remote_call_back() {
    let off = AnalyzerConfig {
        use_context: false,
        ..AnalyzerConfig::default()
    };
    let outcome = run_with(&["Log in with username and password"], &off);
    let request = &outcome.steps[0].bindings[0];
    let code = request
        .fields
        .iter()
        .find(|f| f.name == "verificationCode")
        .expect("declared field");
    assert_eq!(
        code.value,
        BoundValue::Unknown,
        "without the package's statement silence is only silence"
    );
    assert!(
        verify_remote(&outcome),
        "an unmentioned field must not be read as absence: the call stays possible"
    );
}

#[test]
fn a_stated_code_keeps_the_remote_call() {
    let outcome = run(&["Log in with username and password and verification code 4578"]);
    assert!(
        verify_remote(&outcome),
        "the positive case must survive a negative-only fix: {:?}",
        outcome.prediction.remote
    );
    let decision = outcome.steps[0]
        .decisions
        .iter()
        .find(|d| d.method == TOKEN_SERVICE && d.verdict == "proves_true");
    assert!(
        decision.is_some(),
        "a stated code proves the branch true: {:#?}",
        outcome.steps[0].decisions
    );
}
