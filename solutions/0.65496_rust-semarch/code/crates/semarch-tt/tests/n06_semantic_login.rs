//! N06 acceptance end to end on the contested project: the verify-code call.
//!
//! This test runs the *production* path — the same loader, entry grounding,
//! value binder, CFG analysis and exporter a submitted answer uses — over the
//! real Train Ticket checkout. It pins the one vertical slice the plan asks
//! for: the login request's verification code flows from prose, through the
//! JavaBeans accessor of the request DTO, into a local variable, and decides
//! the branch that guards the call to the verification-code service.
//!
//! Two cases must both hold:
//!
//! * the scenario says nothing about the code → the branch is open, the remote
//!   call is *possible* (never silently dropped, never claimed);
//! * the scenario states a code → the branch is *proved true* and the remote
//!   call is *confirmed*, with the guard decision as proof.
//!
//! Scope of this file, stated explicitly because the earlier revision
//! overclaimed it: these two cases are *generic* silence and a *stated*
//! value. They do **not** establish the Train Ticket default, where the task
//! package itself states "no verification code at login" (`context/README.md`,
//! `skeleton.context.account`). That default is a separate input and is
//! analysed in `review_b38_real_login.rs`; nothing here may be read as "real
//! empty is proven".
//!
//! The submission itself must remain byte-identical: the legacy answer is not
//! touched by this engine, and the test asserts that too.

use std::path::{Path, PathBuf};

use semarch_scenario::scenario::{Scenario, Step};
use semarch_tt::pipeline::{AnalyzerConfig, LoadOptions, TtAnalyzer};
use semarch_tt::request::{BoundField, BoundValue, FieldOrigin};
use semarch_tt::{export, Relation};

/// The contested workspace, relative to this crate.
fn challenge_root() -> PathBuf {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("..")
        .join("tt-challenge");
    assert!(
        root.join("skeleton").is_dir(),
        "the contested workspace must be checked out at {}",
        root.display()
    );
    root
}

fn analyzer() -> TtAnalyzer {
    TtAnalyzer::load_with(challenge_root(), &LoadOptions { require_sources: true })
        .expect("the contested project loads with its sources")
}

fn cfg() -> AnalyzerConfig {
    AnalyzerConfig {
        resolution: semarch_tt::ResolutionConfig::default(),
        entry_ratio: 0.95,
        max_candidates: 4,
        use_context: true,
    }
}

/// The same configuration with the task package's context *not* read.
///
/// This is the ablation the "generic silence" case needs: on the contested
/// project the package itself states that the pre-registered account has no
/// verification code at login, so silence only exists once that statement is
/// turned off.
fn cfg_without_context() -> AnalyzerConfig {
    AnalyzerConfig {
        use_context: false,
        ..cfg()
    }
}

fn scenario(id: &str, actions: &[&str]) -> Scenario {
    Scenario {
        project: "trainticket".to_owned(),
        id: id.to_owned(),
        title: String::new(),
        description: String::new(),
        input: "text".to_owned(),
        steps: actions
            .iter()
            .enumerate()
            .map(|(i, a)| Step {
                n: i as u32 + 1,
                action: (*a).to_owned(),
            })
            .collect(),
    }
}

/// The bound value of the request field whose name contains `needle`.
fn bound(analyzer: &TtAnalyzer, action: &str, needle: &str) -> BoundValue {
    bound_field(analyzer, action, needle).value.clone()
}

/// Where the bound value of that field came from.
fn origin_of(analyzer: &TtAnalyzer, action: &str, needle: &str) -> FieldOrigin {
    bound_field(analyzer, action, needle).origin
}

fn bound_field(analyzer: &TtAnalyzer, action: &str, needle: &str) -> BoundField {
    let scn = scenario("S-probe", &[action]);
    let outcome = analyzer.semantic_run(&scn, &cfg()).expect("semantic run");
    let step = &outcome.steps[0];
    step.bindings
        .iter()
        .flat_map(|b| &b.fields)
        .find(|f| f.name.to_ascii_lowercase().contains(needle))
        .unwrap_or_else(|| panic!("no bound field matching {needle:?}: {:?}", step.bindings))
        .clone()
}

#[test]
fn the_login_request_field_exists_and_is_bound_from_the_step() {
    let analyzer = analyzer();
    // The step says nothing about the code. That silence is *not* absence by
    // itself — but the task package states the starting point ("no
    // verification code at login"): the field is not sent, and the binding
    // records that it came from the package, not from the step.
    assert_eq!(
        bound(&analyzer, "Log in with username and password", "code"),
        BoundValue::Absent
    );
    let origin = origin_of(&analyzer, "Log in with username and password", "code");
    assert_eq!(origin, FieldOrigin::Context);
    // A step that states a value still wins over the package default.
    assert_eq!(
        bound(&analyzer, "Log in with username admin and verification code 4578", "code"),
        BoundValue::Literal("4578".to_owned())
    );
    let origin = origin_of(
        &analyzer,
        "Log in with username admin and verification code 4578",
        "code",
    );
    assert_eq!(origin, FieldOrigin::Payload);
}

#[test]
fn a_stated_code_confirms_the_remote_call_and_proves_the_guard() {
    let analyzer = analyzer();
    let scn = scenario(
        "S-code",
        &["Log in with username admin and verification code 4578"],
    );
    let outcome = analyzer.semantic_run(&scn, &cfg()).expect("semantic run");
    let step = &outcome.steps[0];

    let remotes: Vec<&semarch_tt::EffectEvent> = step
        .effects
        .iter()
        .filter(|e| e.relation == Relation::Remote)
        .collect();
    assert!(
        !remotes.is_empty(),
        "the bound code must keep the verify-code call: {:?}",
        step.effects
    );
    let verify = remotes
        .iter()
        .find(|e| e.targets.iter().any(|t| t.contains("VerifyCodeController")))
        .expect("the verification-code service is the remote target");
    assert_eq!(verify.status, "confirmed", "a stated value proves the branch");
    assert!(
        step.decisions
            .iter()
            .any(|d| d.method == verify.method && d.verdict == "proves_true"),
        "the guard that guards the call must be decided true: {:?}",
        step.decisions
    );

    // Through the production exporter: the edge is whitelisted, so the answer
    // never carries an invented id.
    let (submission, reports) = export::build(
        &analyzer.skeleton.project,
        &[(scn.id.clone(), outcome.prediction.clone())],
        &analyzer.graph.method_ids,
        &analyzer.graph.table_ids,
    );
    assert!(
        reports[&scn.id].rejected.is_empty(),
        "no edge may be rejected: {:?}",
        reports[&scn.id].rejected
    );
    let block = &submission.scenarios[&scn.id];
    assert!(
        block
            .edges
            .iter()
            .any(|e| e.relation == "remote" && e.target.contains("VerifyCodeController")),
        "the exported block carries the remote edge: {:?}",
        block.edges
    );
}

#[test]
fn silence_keeps_the_branch_open_and_the_remote_possible() {
    let analyzer = analyzer();
    // The real scenario S0 says exactly this: username and password, nothing
    // about a verification code. The task package's own statement ("no
    // verification code at login") is turned off here: this test is about
    // *generic* silence, where nothing at all has been stated — the case the
    // package's default must not be confused with.
    let scn = scenario("S-silent", &["Log in with username and password"]);
    let outcome = analyzer
        .semantic_run(&scn, &cfg_without_context())
        .expect("semantic run");
    let step = &outcome.steps[0];

    let verify = step
        .effects
        .iter()
        .find(|e| {
            e.relation == Relation::Remote
                && e.targets.iter().any(|t| t.contains("VerifyCodeController"))
        })
        .expect("silence is not absence: the call stays possible");
    assert_eq!(verify.status, "possible");
    assert!(
        step.decisions.iter().any(|d| d.verdict == "unknown"),
        "an undecided guard is recorded as unknown: {:?}",
        step.decisions
    );
}

#[test]
fn the_semantic_engine_loses_nothing_the_legacy_answer_derives() {
    let analyzer = analyzer();
    let scn = scenario("S-silent", &["Log in with username and password"]);
    let diff = analyzer.shadow_run(&scn, &cfg()).expect("shadow run");

    // This is a *superset* claim, not equality: the earlier name of this test
    // ("reproduces the legacy answer exactly") claimed more than the assertion
    // checks. Nothing the legacy flood derives is lost; the engine additionally
    // refuses to prune by scenario vocabulary, which is what the diffs record.
    assert!(diff.only_legacy.is_empty(), "{diff:#?}");
    assert!(diff.only_legacy_executes.is_empty(), "{diff:#?}");
    assert!(
        diff.only_semantic
            .iter()
            .all(|e| e.explanation.contains("scenario vocabulary")
                || e.explanation.contains("value decisions")
                || e.explanation.contains("did not expand")),
        "every added edge carries its explanation: {:#?}",
        diff.only_semantic
    );
    // The verify-code remote is *not* claimed for this request. The legacy path
    // also drops it, but on scenario vocabulary; here the drop is a value proof:
    // the task package states the pre-registered account has no code, so the
    // bound `verificationCode` is absent, the guard is proved false and the
    // block is cut off with a certificate naming that decision. Turning the
    // context off brings the remote back as possible — which is what makes the
    // drop the proof and not the vocabulary.
    let with_context = analyzer.semantic_run(&scn, &cfg()).expect("semantic run");
    let without = analyzer
        .semantic_run(&scn, &cfg_without_context())
        .expect("ablation run");
    let verify_present = |outcome: &semarch_tt::engine::ScenarioOutcome| {
        outcome
            .prediction
            .remote
            .iter()
            .any(|(_, t)| t.contains("VerifyCode"))
    };
    assert!(
        !verify_present(&with_context),
        "the package's stated absence proves the guard false: {:?}",
        with_context.prediction.remote
    );
    assert!(
        verify_present(&without),
        "generic silence keeps the call possible: {:?}",
        without.prediction.remote
    );
}

#[test]
fn a_static_option_binds_but_a_runtime_fetched_list_does_not() {
    let analyzer = analyzer();
    // A control with static options is a value the project itself states.
    assert!(
        analyzer
            .ui_options
            .iter()
            .any(|o| o.field == "preserve_food_type" && o.label == "Train Food" && o.value == "1"),
        "the booking page offers a static food-type option"
    );
    // `assurance` is filled from `/assurance/getAllAssuranceType` at runtime:
    // no static `<option>` exists, so no value may be invented for it.
    assert!(
        !analyzer
            .ui_options
            .iter()
            .any(|o| o.field.contains("assurance")),
        "the assurance list is fetched at runtime, so it has no source value"
    );

    // The picked option binds; the unpicked list does not.
    let scn = scenario("S-option", &["Book a ticket with train food"]);
    let outcome = analyzer.semantic_run(&scn, &cfg()).expect("semantic run");
    let food = outcome.steps[0]
        .bindings
        .iter()
        .flat_map(|b| &b.fields)
        .find(|f| f.name.eq_ignore_ascii_case("foodType"));
    if let Some(food) = food {
        assert_eq!(
            food.value,
            BoundValue::Literal("1".to_owned()),
            "the picked option's value is bound: {food:?}"
        );
        assert_eq!(food.origin, semarch_tt::FieldOrigin::UiOption);
    }
    // A step that names no option leaves every option-carrying field unknown.
    let scn = scenario("S-plain", &["Book a ticket"]);
    let outcome = analyzer.semantic_run(&scn, &cfg()).expect("semantic run");
    assert!(
        outcome.steps[0]
            .bindings
            .iter()
            .flat_map(|b| &b.fields)
            .all(|f| f.origin != semarch_tt::FieldOrigin::UiOption),
        "an unpicked control must not bind a value"
    );
}

#[test]
fn the_submitted_answer_is_byte_identical_to_the_legacy_run() {
    let analyzer = analyzer();
    let all = analyzer
        .analyze_all(&cfg())
        .expect("every scenario is analyzed");
    let predictions: Vec<(String, semarch_tt::Prediction)> = all
        .iter()
        .map(|(id, p, _)| (id.clone(), p.clone()))
        .collect();
    let (submission, _) = export::build(
        &analyzer.skeleton.project,
        &predictions,
        &analyzer.graph.method_ids,
        &analyzer.graph.table_ids,
    );
    let json = export::to_json(&submission).expect("json");
    // The fingerprint of the released answer; a change here is a change of the
    // submitted artifact and must be a deliberate, separately reviewed commit.
    // The released artifact's SHA-256 is pinned by the reproduction harness
    // (`scripts/reproduce_rust.py`, `ea3c7ca2…`); this test pins the same bytes
    // with the crate's own deterministic fingerprint, so a change to the
    // submitted answer fails a unit test as well as the release gate.
    let digest = semarch_tt::hash::set_hash([("submission.json", json.as_bytes())]);
    assert_eq!(
        digest, "fnv1a64:4145150f03aec303",
        "the contest answer changed; if that is intended, pin it in its own commit"
    );
}
