//! N05/N06 acceptance on a fixture project: a bound request decides a branch.
//!
//! The fixture is deliberately *not* Train Ticket: one `@PostMapping` handler
//! whose body reads a request field through the JavaBeans accessor, tests it
//! with `StringUtils.isEmpty` and calls a remote handler when it is non-empty.
//!
//! The point of the test is the whole chain, not the guard:
//!
//! ```text
//!   step prose → bound field (typed) → accessor → local binding
//!              → guard verdict → call site live/dead → edge with proof
//! ```
//!
//! Four step wordings cover the distinctions the engine must keep apart:
//! a stated value, an explicitly empty value, an explicitly absent field, and
//! silence (unknown — which is *not* absence).

use std::collections::HashSet;
use std::path::{Path, PathBuf};

use semarch_scenario::scenario::Scenario;
use semarch_tt::pipeline::{AnalyzerConfig, TtAnalyzer};
use semarch_tt::request::BoundValue;
use semarch_tt::{Relation, TtError};

const HANDLER: &str = "shop/src/main/java/a/Ctl.java";
const DTO: &str = "shop/src/main/java/a/BasicDto.java";
const VERIFY: &str = "shop/src/main/java/a/Verify.java";

const HANDLER_SRC: &str = r#"package a;

import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

public class Ctl {
    @PostMapping(path = "/login")
    public void login(@RequestBody BasicDto dto) {
        String code = dto.getVerificationCode();
        if (!StringUtils.isEmpty(code)) {
            send();
        }
        audit();
    }
}
"#;

const DTO_SRC: &str = r#"package a;

public class BasicDto {
    private String verificationCode;

    public String getVerificationCode() {
        return verificationCode;
    }
}
"#;

const VERIFY_SRC: &str = r#"package a;

public class Verify {
    public void send() {
    }

    public void audit() {
    }
}
"#;

fn temp_root(tag: &str) -> PathBuf {
    let root = std::env::temp_dir().join(format!(
        "semarch-n05-{tag}-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.subsec_nanos())
            .unwrap_or(0)
    ));
    let _ = std::fs::remove_dir_all(&root);
    std::fs::create_dir_all(&root).expect("create temp root");
    root
}

fn line_of(source: &str, needle: &str) -> u32 {
    let hits: Vec<usize> = source
        .lines()
        .enumerate()
        .filter(|(_, l)| l.contains(needle))
        .map(|(i, _)| i + 1)
        .collect();
    assert_eq!(hits.len(), 1, "`{needle}` must be unambiguous: {hits:?}");
    hits[0] as u32
}

/// Write the fixture project: sources, skeleton, UI evidence, one scenario.
fn write_fixture(root: &Path) {
    let write = |rel: &str, body: &str| {
        let path = root.join(rel);
        std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
        std::fs::write(path, body).expect("write");
    };
    write(&format!("targets/shop/{HANDLER}"), HANDLER_SRC);
    write(&format!("targets/shop/{DTO}"), DTO_SRC);
    write(&format!("targets/shop/{VERIFY}"), VERIFY_SRC);
    write(
        "targets/shop/shop-ui/static/client.js",
        "$(\"#login\").click(function () { $.ajax({ url: \"/login\" }); });\n",
    );

    let decl = line_of(HANDLER_SRC, "public void login");
    let accessor = line_of(HANDLER_SRC, "dto.getVerificationCode()");
    let send = line_of(HANDLER_SRC, "send();");
    let audit = line_of(HANDLER_SRC, "audit();");

    let handler = "method:shop:a.Ctl#login(a.BasicDto)".to_owned();
    let send_cs = format!("call:{handler}@{send}:13");
    let audit_cs = format!("call:{handler}@{audit}:9");
    let accessor_cs = format!("call:{handler}@{accessor}:23");
    let verify_method = "method:shop:a.Verify#send()".to_owned();
    let audit_method = "method:shop:a.Verify#audit()".to_owned();

    let call_site = |callee: &str, receiver: serde_json::Value, line: u32| {
        serde_json::json!({
            "kind": "call_site", "method": handler, "callee": callee,
            "receiver": receiver, "arg_count": 0,
            "module": "shop", "file": HANDLER, "line": line, "col": 9,
        })
    };

    let skeleton = serde_json::json!({
        "project": "shop",
        "schema": "test",
        "nodes": {
            "type:shop:a.Ctl": {
                "kind": "type", "fqn": "a.Ctl", "type_kind": "class", "module": "shop",
            },
            handler.clone(): {
                "kind": "method", "owner": "type:shop:a.Ctl", "name": "login",
                "descriptor": "a.BasicDto", "params_as_written": ["BasicDto"],
                "module": "shop", "file": HANDLER, "line": decl,
                "annotations": [{"name": "PostMapping", "args": "(path = \"/login\")"}],
            },
            "type:shop:a.BasicDto": {
                "kind": "type", "fqn": "a.BasicDto", "type_kind": "class", "module": "shop",
            },
            "field:shop:a.BasicDto.verificationCode": {
                "kind": "field", "owner": "type:shop:a.BasicDto",
                "name": "verificationCode", "type": "java.lang.String", "type_raw": "String",
                "module": "shop", "file": DTO, "line": 4,
            },
            format!("param:{handler}#0"): {
                "kind": "parameter", "method": handler, "index": 0, "name": "dto",
                "type": "a.BasicDto", "type_raw": "BasicDto",
                "annotations": [{"name": "RequestBody", "args": ""}],
                "module": "shop",
            },
            "type:shop:a.Verify": {
                "kind": "type", "fqn": "a.Verify", "type_kind": "class", "module": "shop",
            },
            verify_method.clone(): {
                "kind": "method", "owner": "type:shop:a.Verify", "name": "send",
                "descriptor": "", "module": "shop", "file": VERIFY,
                "line": line_of(VERIFY_SRC, "public void send"),
            },
            audit_method.clone(): {
                "kind": "method", "owner": "type:shop:a.Verify", "name": "audit",
                "descriptor": "", "module": "shop", "file": VERIFY,
                "line": line_of(VERIFY_SRC, "public void audit"),
            },
            accessor_cs.clone(): call_site("getVerificationCode", serde_json::json!("dto"), accessor),
            send_cs.clone(): call_site("send", serde_json::Value::Null, send),
            audit_cs.clone(): call_site("audit", serde_json::Value::Null, audit),
        },
        "edges": [
            {"source": accessor_cs, "type": "calls", "target": "method:shop:a.BasicDto#getVerificationCode()"},
            {"source": send_cs, "type": "remote_call", "target": verify_method},
            {"source": audit_cs, "type": "calls", "target": audit_method},
        ],
    });
    write(
        "skeleton/shop.json",
        &serde_json::to_string_pretty(&skeleton).expect("skeleton json"),
    );
    write(
        "scenarios/S1-baseline.json",
        r#"{"project":"shop","id":"S1-baseline","title":"login","description":"Log in.","input":"text","steps":[{"n":1,"action":"Log in with username passenger"}]}"#,
    );
}

fn load(root: &Path) -> TtAnalyzer {
    let mut last: Option<TtError> = None;
    for _ in 0..3 {
        match TtAnalyzer::load(root) {
            Ok(a) => return a,
            Err(e) => last = Some(e),
        }
    }
    panic!("load failed: {:?}", last.expect("error"));
}

fn scenario(id: &str, action: &str) -> Scenario {
    Scenario {
        project: "shop".to_owned(),
        id: id.to_owned(),
        title: String::new(),
        description: String::new(),
        input: "text".to_owned(),
        steps: vec![semarch_scenario::scenario::Step {
            n: 1,
            action: action.to_owned(),
        }],
    }
}

fn cfg() -> AnalyzerConfig {
    AnalyzerConfig {
        resolution: semarch_tt::ResolutionConfig::default(),
        entry_ratio: 0.95,
        max_candidates: 4,
        use_context: true,
    }
}

/// The value one step bound to the fixture's single request field.
fn bound_value(analyzer: &TtAnalyzer, action: &str) -> BoundValue {
    let scn = scenario("S-probe", action);
    let outcome = analyzer.semantic_run(&scn, &cfg()).expect("semantic run");
    let step = &outcome.steps[0];
    let binding = step.bindings.first().expect("one bound request per entry");
    assert_eq!(binding.method, "method:shop:a.Ctl#login(a.BasicDto)");
    binding
        .fields
        .iter()
        .find(|f| f.name == "verificationCode")
        .expect("the handler's request field is bound")
        .value
        .clone()
}

fn step_remotes(step: &semarch_tt::StepOutcome) -> Vec<(String, String)> {
    step.effects
        .iter()
        .filter(|e| e.relation == Relation::Remote)
        .map(|e| (e.status.clone(), e.proof.join(" ")))
        .collect()
}

fn remote_effects(outcome: &semarch_tt::ScenarioOutcome) -> Vec<(String, String)> {
    step_remotes(&outcome.steps[0])
}

#[test]
fn value_from_prose_reaches_the_guard_and_keeps_the_remote() {
    let root = temp_root("known");
    write_fixture(&root);
    let analyzer = load(&root);

    let scn = scenario("S-code", "Log in with verification code 4578");
    let outcome = analyzer.semantic_run(&scn, &cfg()).expect("semantic run");
    let step = &outcome.steps[0];

    assert_eq!(
        bound_value(&analyzer, "Log in with verification code 4578"),
        BoundValue::Literal("4578".to_owned())
    );
    assert!(
        step.decisions
            .iter()
            .any(|d| d.verdict == "proves_true" && d.symbols.iter().any(|s| s == "code")),
        "the guard must be decided true by the bound value: {:?}",
        step.decisions
    );
    let remotes = remote_effects(&outcome);
    assert_eq!(remotes.len(), 1, "one remote edge: {remotes:?}");
    assert_eq!(remotes[0].0, "confirmed", "the path is certain");
    // The sibling call that is *not* behind the guard still runs.
    assert!(outcome.prediction.calls.iter().any(|(_, t)| t.ends_with("#audit()")));

    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn empty_absent_and_unknown_are_three_different_things() {
    let root = temp_root("three");
    write_fixture(&root);
    let analyzer = load(&root);

    // Stated empty: the branch is proved false, the remote does not run.
    assert_eq!(
        bound_value(&analyzer, "Log in with an empty verification code"),
        BoundValue::Empty
    );
    // Stated absent: the field is not sent. It is `null` only because the body
    // is deserialized (`@RequestBody`) and the field declares no initializer —
    // the model evidence the fixture now carries.
    assert_eq!(
        bound_value(&analyzer, "Log in without a verification code"),
        BoundValue::Absent
    );
    // Silence: no statement about the field is no statement that it is empty.
    assert_eq!(
        bound_value(&analyzer, "Log in with username passenger"),
        BoundValue::Unknown
    );

    for (action, verdict_marker) in [
        ("Log in with an empty verification code", "proves_false"),
        ("Log in without a verification code", "proves_false"),
    ] {
        let scn = scenario("S-dead", action);
        let outcome = analyzer.semantic_run(&scn, &cfg()).expect("semantic run");
        let step = &outcome.steps[0];
        assert_eq!(
            remote_effects(&outcome),
            Vec::new(),
            "{action}: the remote call must not run"
        );
        assert!(
            step.decisions.iter().any(|d| d.verdict == verdict_marker),
            "{action}: expected {verdict_marker}: {:?}",
            step.decisions
        );
        assert!(
            step.suppressed
                .iter()
                .any(|s| s.contains("remote") || s.contains("send")),
            "{action}: the dead call site must be recorded as suppressed: {:?}",
            step.suppressed
        );
    }
}

#[test]
fn silence_leaves_the_branch_open_and_the_remote_possible() {
    let root = temp_root("unknown");
    write_fixture(&root);
    let analyzer = load(&root);

    let scn = scenario("S-silent", "Log in with username passenger");
    let outcome = analyzer.semantic_run(&scn, &cfg()).expect("semantic run");
    let remotes = remote_effects(&outcome);
    assert_eq!(remotes.len(), 1, "an open branch keeps the edge: {remotes:?}");
    assert_eq!(remotes[0].0, "possible", "unknown is not false");

    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn the_legacy_answer_is_unchanged_and_the_diff_explains_itself() {
    let root = temp_root("shadow");
    write_fixture(&root);
    let analyzer = load(&root);

    // A step whose words name the feature: the legacy engine keeps the call
    // site, and the two engines agree.
    let scn = scenario("S-agree", "Log in with verification code 4578");
    let diff = analyzer.shadow_run(&scn, &cfg()).expect("shadow run");
    assert!(diff.only_legacy.is_empty(), "legacy has nothing extra: {diff:?}");
    assert!(diff.only_semantic.is_empty(), "and semantic adds nothing: {diff:?}");

    // A step that states the field is empty: the legacy engine cannot know
    // (its pruning is lexical), the semantic engine proves the branch false.
    let scn = scenario("S-diff", "Log in with an empty verification code");
    let legacy = analyzer.analyze(&scn, &cfg());
    let diff = analyzer.shadow_run(&scn, &cfg()).expect("shadow run");
    assert!(
        !diff.only_legacy.is_empty(),
        "the semantic engine dropped the remote the legacy flood keeps: {diff:?}"
    );
    assert_eq!(diff.semantic.remote, 0);
    assert!(!legacy.remote.is_empty(), "the legacy answer is untouched");

    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn a_later_step_never_rewrites_an_earlier_one() {
    let root = temp_root("order");
    write_fixture(&root);
    let analyzer = load(&root);

    let mut scn = scenario("S-two", "Log in with an empty verification code");
    scn.steps.push(semarch_scenario::scenario::Step {
        n: 2,
        action: "Log in again with verification code 4578".to_owned(),
    });

    let outcome = analyzer.semantic_run(&scn, &cfg()).expect("semantic run");
    assert_eq!(outcome.steps.len(), 2);
    // Step 1 keeps its own binding and its own dead branch.
    assert_eq!(outcome.steps[0].bindings[0].fields[0].value, BoundValue::Empty);
    assert!(step_remotes(&outcome.steps[0]).is_empty());
    // Step 2 states a value and takes the branch.
    assert_eq!(
        outcome.steps[1].bindings[0].fields[0].value,
        BoundValue::Literal("4578".to_owned())
    );

    // The union of the two steps has the remote edge once.
    let remote_edges: HashSet<&(String, String)> = outcome.prediction.remote.iter().collect();
    assert_eq!(remote_edges.len(), 1);

    let _ = std::fs::remove_dir_all(&root);
}
