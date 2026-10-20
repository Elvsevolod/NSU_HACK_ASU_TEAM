//! R04/R05 gate (own tests, not from the review package).
//!
//! Three properties the prepared `review_975_continuations` fixture cannot
//! reach in one file:
//!
//! * a callee whose body *assigns a local* before `return <local>` — the flat
//!   "substitute the actuals into the return expression" shortcut sees only an
//!   unknown local there, so this only passes if the callee body was walked;
//! * two calls to the same helper with different arguments get their own
//!   result, not one joined summary;
//! * two same-named helpers in *different files* do not share a body, so the
//!   helper the caller declares is the one used.
//!
//! Source-only two-service pipeline tests; seed remote wiring, no live HTTP.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use semarch_scenario::scenario::{Scenario, Step};
use semarch_tt::engine::ScenarioOutcome;
use semarch_tt::pipeline::{AnalyzerConfig, LoadOptions, TtAnalyzer};
use serde_json::{json, Value};

const FILE: &str = "caller/src/main/java/a/Ctl.java";
const DTO: &str = "caller/src/main/java/a/Dto.java";
const RF: &str = "remote/src/main/java/a/Verifier.java";
const ENTRY: &str = "method:caller:a.Ctl#login(a.Dto)";
const HELPER: &str = "method:caller:a.Ctl#helper(java.lang.String)";
const REMOTE_HELPER: &str = "method:remote:a.Verifier#helper(java.lang.String)";
const REMOTE: &str = "method:remote:a.Verifier#verify()";
const SEND: &str = "restTemplate.exchange(\"http://remote/verify\", HttpMethod.GET, null, 1);";
const PREDICATE: &str =
    "public boolean helper(String code){ return !StringUtils.isEmpty(code); }";

static SEQ: AtomicU64 = AtomicU64::new(0);

struct Fixture {
    root: PathBuf,
}

impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.root);
    }
}

fn write(root: &Path, rel: &str, contents: &str) {
    let path = root.join(rel);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).expect("create fixture directory");
    }
    std::fs::write(&path, contents).expect("write fixture file");
}

fn pos(s: &str, i: usize) -> (u32, u32) {
    let t = &s[..i];
    (
        (t.bytes().filter(|&x| x == b'\n').count() + 1) as u32,
        (t.rfind('\n').map_or(i + 1, |n| i - n)) as u32,
    )
}

fn method(name: &str, desc: &str, file: &str, line: u32, module: &str, owner: &str) -> Value {
    json!({"kind":"method","owner":owner,"name":name,"descriptor":desc,"module":module,"file":file,"line":line})
}

/// Build a two-service fixture. `caller_helper` is declared in the caller file
/// (and is the only `helper` the caller may use); `remote_helper` is a second
/// helper with the same name and arity, in a different file.
fn fixture(caller_body: &str, caller_helper: &str, remote_helper: Option<&str>) -> Fixture {
    let root = std::env::temp_dir().join(format!(
        "semarch-gater-{}-{}",
        std::process::id(),
        SEQ.fetch_add(1, Ordering::SeqCst)
    ));
    assert!(!root.exists());

    let caller_body = caller_body.replace("SEND", SEND);
    let src = format!(
        "package a;\nimport org.springframework.util.StringUtils;\nimport org.springframework.web.bind.annotation.PostMapping;\nimport org.springframework.web.client.RestTemplate;\nimport org.springframework.http.HttpMethod;\npublic class Ctl {{\n RestTemplate restTemplate;\n @PostMapping(path=\"/login\")\n public void login(Dto dto) {{\n {caller_body}\n }}\n {caller_helper}\n}}\n"
    );
    let remote_helper = remote_helper.unwrap_or("");
    let rsrc = format!(
        "package a;\nimport org.springframework.util.StringUtils;\npublic class Verifier {{\n {remote_helper}\n public boolean verify(){{return true;}}\n}}\n"
    );

    write(&root, &format!("targets/probe/{FILE}"), &src);
    write(
        &root,
        &format!("targets/probe/{DTO}"),
        "package a;\npublic class Dto {\n public String verificationCode;\n public String getVerificationCode(){return verificationCode;}\n}\n",
    );
    write(&root, &format!("targets/probe/{RF}"), &rsrc);
    write(
        &root,
        "targets/probe/probe-ui/client.js",
        "$.ajax({url:'/login',type:'POST'});\n",
    );

    let mut n = serde_json::Map::new();
    let mut es = vec![];
    for (id, fqn, module) in [
        ("type:caller:a.Ctl", "a.Ctl", "caller"),
        ("type:caller:a.Dto", "a.Dto", "caller"),
        ("type:remote:a.Verifier", "a.Verifier", "remote"),
    ] {
        n.insert(
            id.into(),
            json!({"kind":"type","fqn":fqn,"type_kind":"class","module":module}),
        );
    }
    n.insert("field:caller:a.Dto.verificationCode".into(), json!({"kind":"field","owner":"type:caller:a.Dto","name":"verificationCode","type_raw":"String","type":"java.lang.String","module":"caller","file":DTO,"line":3}));
    let mut entry = method("login", "a.Dto", FILE, 9, "caller", "type:caller:a.Ctl");
    entry["annotations"] = json!([{"name":"PostMapping","args":"(path=\"/login\")"}]);
    entry["params_as_written"] = json!(["Dto"]);
    n.insert(ENTRY.into(), entry);
    n.insert(REMOTE.into(), method("verify", "", RF, 3, "remote", "type:remote:a.Verifier"));

    let ch = src.find("public boolean helper").expect("caller helper present");
    n.insert(
        HELPER.into(),
        method(
            "helper",
            "java.lang.String",
            FILE,
            pos(&src, ch).0,
            "caller",
            "type:caller:a.Ctl",
        ),
    );
    if let Some(rh) = rsrc.find("public boolean helper") {
        n.insert(
            REMOTE_HELPER.into(),
            method(
                "helper",
                "java.lang.String",
                RF,
                pos(&rsrc, rh).0,
                "remote",
                "type:remote:a.Verifier",
            ),
        );
    }
    for (offset, _) in src.match_indices("exchange(\"http://remote/verify\"") {
        let (line, col) = pos(&src, offset);
        let id = format!("call:{ENTRY}@{line}:{col}");
        n.insert(id.clone(), json!({"kind":"call_site","method":ENTRY,"callee":"exchange","receiver":"restTemplate","receiver_type":"org.springframework.web.client.RestTemplate","arg_count":4,"args_text":"(\"http://remote/verify\", HttpMethod.GET, null, 1)","module":"caller","file":FILE,"line":line,"col":col}));
        es.push(json!({"source":id,"type":"remote_call","target":REMOTE}));
    }
    write(
        &root,
        "skeleton/probe.json",
        &serde_json::to_string_pretty(&json!({"project":"probe","schema":"review","nodes":n,"edges":es})).unwrap(),
    );
    write(
        &root,
        "scenarios/S1.json",
        r#"{"project":"probe","id":"S1","title":"login","description":"","input":"text","steps":[{"n":1,"action":"Log in"}]}"#,
    );
    Fixture { root }
}

fn run(f: &Fixture) -> ScenarioOutcome {
    let a = TtAnalyzer::load_with(&f.root, &LoadOptions { require_sources: true }).unwrap();
    let s = Scenario {
        project: "probe".into(),
        id: "gater".into(),
        title: String::new(),
        description: String::new(),
        input: "text".into(),
        steps: vec![Step {
            n: 1,
            action: "Log in".into(),
        }],
    };
    let o = a.semantic_run(&s, &AnalyzerConfig::default()).unwrap();
    assert_eq!(
        o.steps[0].entries,
        vec![ENTRY.to_owned()],
        "entry precondition: a grounded single entry, not an empty graph"
    );
    o
}

fn remote(o: &ScenarioOutcome) -> bool {
    o.prediction.remote.iter().any(|(_, t)| t == REMOTE)
}

/// The callee assigns a local before returning it. The flat-return shortcut
/// substitutes the actuals into `return ok;` and sees an unknown local, which
/// would leave the remote possible; only walking the callee body proves `ok`
/// is `false` for `code = ""`.
#[test]
fn a_local_assignment_inside_the_callee_is_not_a_flat_return() {
    let f = fixture(
        "boolean ok=helper(\"\"); if(!ok) return; SEND",
        "public boolean helper(String code){ boolean ok = !StringUtils.isEmpty(code); return ok; }",
        None,
    );
    assert!(
        !remote(&run(&f)),
        "the callee's local assignment must decide the caller's guard"
    );
}

/// Two calls of the same helper with different arguments: the first is true and
/// the second is false, so the second prunes. A single joined summary would
/// make both unknown and keep the remote.
#[test]
fn repeated_helper_calls_keep_their_own_arguments() {
    let f = fixture(
        "boolean a=helper(\"X\"); boolean b=helper(\"\"); if(!a) return; if(!b) return; SEND",
        PREDICATE,
        None,
    );
    assert!(
        !remote(&run(&f)),
        "each call must be summarized with its own actual arguments"
    );
}

/// The caller's helper returns `false`; a same-named helper in another file
/// returns `true`. The caller's own file must win: the guard is proved false
/// and the remote is pruned.
#[test]
fn a_same_named_helper_in_another_file_is_not_the_callee() {
    let f = fixture(
        "if(helper(\"\")) { SEND }",
        "public boolean helper(String code){ return false; }",
        Some("public boolean helper(String code){ return true; }"),
    );
    assert!(
        !remote(&run(&f)),
        "the callee is the helper of the caller's file, not a look-alike elsewhere"
    );
}

/// The same fixture with the caller's helper returning `true` keeps the remote:
/// the previous test's prune is caused by the *caller's* body, not by an
/// unresolved callee.
#[test]
fn the_callers_helper_return_value_is_what_decides() {
    let f = fixture(
        "if(helper(\"\")) { SEND }",
        "public boolean helper(String code){ return true; }",
        Some("public boolean helper(String code){ return false; }"),
    );
    assert!(
        remote(&run(&f)),
        "the caller's helper decides, and a true guard keeps the remote"
    );
}
