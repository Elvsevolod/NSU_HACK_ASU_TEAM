//! Rename independence: every mechanism must derive from language semantics or
//! a public framework contract, never from a project's own vocabulary.
//!
//! The test builds one toy project twice. The second copy renames *everything*:
//! the module, every type, every method, the entity, the table, the filter, the
//! principal, the scenario id, and the prose that grounds the step. If any
//! mechanism depended on a name, the two runs would diverge.
//!
//! The toy project is deliberately not Train Ticket. It exercises the same
//! contracts:
//!
//! | mechanism | toy shape |
//! |---|---|
//! | entry grounding | one `@PostMapping` handler + one UI call literal |
//! | G3 repository proxy | `interface XRepo extends CrudRepository` |
//! | G4 ORM materialization | `ArrayList<Entity>` return type |
//! | G5 framework callbacks | `implements Filter`, `implements UserDetailsService` |
//! | G6 optional features | `if (!isEmpty(flag)) { … }` |
//! | G7 static receiver | `Kind.PRIMARY.code()` |
//!
//! Every run also goes through the contest exporter, so the test doubles as a
//! contract check: no id may be invented, for any vocabulary.

// The fixture skeleton is one large `serde_json::json!` literal; the macro
// expands per element and needs headroom.
#![recursion_limit = "512"]

use std::collections::HashSet;
use std::path::{Path, PathBuf};

use semarch_tt::pipeline::{AnalyzerConfig, TtAnalyzer};
use semarch_tt::{export, Prediction, ResolutionConfig};

/// Every project-level name the toy project uses, so a whole vocabulary can be
/// swapped out in one place.
#[derive(Clone, Copy)]
struct Names {
    module: &'static str,
    class: &'static str,
    action: &'static str,
    entity: &'static str,
    repo: &'static str,
    repo_field: &'static str,
    aux: &'static str,
    aux_field: &'static str,
    kind: &'static str,
    table: &'static str,
    filter: &'static str,
    users: &'static str,
    person: &'static str,
    scenario: &'static str,
    /// Prose that grounds the step (must contain the action and the module).
    step: &'static str,
}

/// Vocabulary A.
fn alpha() -> Names {
    Names {
        module: "svc",
        class: "Ctrl",
        action: "act",
        entity: "Widget",
        repo: "WidgetRepo",
        repo_field: "widgetRepo",
        aux: "Aux",
        aux_field: "aux",
        kind: "Kind",
        table: "widget_table",
        filter: "Gate",
        users: "Users",
        person: "Person",
        scenario: "S9",
        step: "act on the svc",
    }
}

/// Vocabulary B: the same program, everything renamed.
fn beta() -> Names {
    Names {
        module: "mod",
        class: "Handler",
        action: "run",
        entity: "Gadget",
        repo: "GadgetStore",
        repo_field: "store",
        aux: "Helper",
        aux_field: "helper",
        kind: "Sort",
        table: "gadget_table",
        filter: "Screen",
        users: "People",
        person: "Human",
        scenario: "T1",
        step: "run on the mod",
    }
}

/// The Java source of the toy handler, parameterized by vocabulary.
fn handler_source(n: &Names) -> String {
    format!(
        r#"package a;

import java.util.ArrayList;

public class {class} {{
    private {repo} {repo_field};
    private {aux} {aux_field};

    @PostMapping(path = "/{action}")
    public void {action}(String {feature}) {{
        ArrayList<{entity}> rows = {repo_field}.findOne("id");
        if (!isEmpty({feature})) {{
            {aux_field}.help();
        }}
        int code = {kind}.PRIMARY.code();
        save(rows, code);
    }}

    private void save(ArrayList<{entity}> rows, int code) {{
        rows.size();
    }}
}}
"#,
        class = n.class,
        repo = n.repo,
        repo_field = n.repo_field,
        aux = n.aux,
        aux_field = n.aux_field,
        action = n.action,
        feature = feature_param(n),
        entity = n.entity,
        kind = n.kind,
    )
}

/// The optional-feature parameter name (renamed with the vocabulary).
fn feature_param(n: &Names) -> &'static str {
    match n.module {
        "svc" => "sprocket",
        _ => "flange",
    }
}

/// 1-based line of the first line containing `needle`.
fn line_of(source: &str, needle: &str) -> u32 {
    source
        .lines()
        .position(|l| l.contains(needle))
        .map(|i| i as u32 + 1)
        .expect("marker present in fixture source")
}

/// Write one toy project (skeleton + scenario + sources + UI) under `root`.
fn write_fixture(root: &Path, n: &Names) {
    let module = n.module;
    let file_rel = format!("{module}/src/main/java/a/{}.java", n.class);
    let source = handler_source(n);
    let write = |rel: &str, body: &str| {
        let path = root.join(rel);
        std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
        std::fs::write(path, body).expect("write");
    };
    write(&format!("targets/toy/{file_rel}"), &source);

    let repo_line = line_of(&source, &format!("{}.findOne(", n.repo_field));
    let aux_line = line_of(&source, &format!("{}.help()", n.aux_field));
    let kind_line = line_of(&source, ".PRIMARY.code()");
    let decl_line = line_of(&source, &format!("public void {}", n.action));

    // The UI names the endpoint in a click handler; this is the only evidence
    // that binds prose to the route besides the route itself.
    write(
        &format!("targets/toy/{module}-ui/static/client.js"),
        &format!(
            "$(\"#go_{action}\").click(function () {{ $.ajax({{ url: \"/{module}/{action}\" }}); }});\n",
            action = n.action,
            module = module
        ),
    );

    let id = |s: &str| s.to_owned();
    let handler = id(&format!("method:{module}:a.{}#{}", n.class, n.action));
    let repo_method = id(&format!("method:{module}:a.{}#findOne", n.repo));
    let entity_ctor = id(&format!("method:{module}:a.{}#<init>()", n.entity));
    let aux_method = id(&format!("method:{module}:a.{}#help()", n.aux));
    let kind_method = id(&format!("method:{module}:a.{}#code()", n.kind));
    let filter_method = id(&format!("method:{module}:a.{}#doFilterInternal()", n.filter));
    let users_method = id(&format!("method:{module}:a.{}#loadUserByUsername", n.users));
    let person_getter = id(&format!("method:{module}:a.{}#getPassword()", n.person));
    let table_id = id(&format!("data_resource:{module}:{}", n.table));

    let repo_cs = format!("call:{handler}@{repo_line}:9");
    let aux_cs = format!("call:{handler}@{aux_line}:13");
    let kind_cs = format!("call:{handler}@{kind_line}:20");

    let call_site = |callee: &str, receiver: &str, receiver_type: Option<&str>, line: u32| {
        let mut v = serde_json::json!({
            "kind": "call_site", "method": handler, "callee": callee,
            "receiver": receiver, "arg_count": 0,
            "module": module, "file": file_rel, "line": line, "col": 9,
        });
        if let Some(t) = receiver_type {
            v["receiver_type"] = serde_json::json!(format!("a.{t}"));
        }
        v
    };

    let skeleton = serde_json::json!({
        "project": "toy",
        "schema": "test",
        "nodes": {
            format!("type:{module}:a.{}", n.class): {
                "kind": "type", "fqn": format!("a.{}", n.class), "type_kind": "class",
                "module": module,
                "annotations": [{"name": "RequestMapping", "args": format!("(\"/{module}\")")}],
            },
            handler.clone(): {
                "kind": "method", "owner": format!("type:{module}:a.{}", n.class),
                "name": n.action, "descriptor": "java.lang.String", "module": module,
                "file": file_rel, "line": decl_line,
                "annotations": [{"name": "PostMapping", "args": format!("(path = \"/{}\")", n.action)}],
            },
            format!("type:{module}:a.{}", n.repo): {
                "kind": "type", "fqn": format!("a.{}", n.repo), "type_kind": "interface",
                "extends_raw": ["CrudRepository"], "module": module,
            },
            repo_method.clone(): {
                "kind": "method", "owner": format!("type:{module}:a.{}", n.repo),
                "name": "findOne", "descriptor": "java.lang.String",
                "return_raw": format!("ArrayList<{}>", n.entity),
                "abstract": true, "module": module,
            },
            format!("type:{module}:a.{}", n.entity): {
                "kind": "type", "fqn": format!("a.{}", n.entity), "type_kind": "class",
                "module": module,
            },
            entity_ctor.clone(): {
                "kind": "method", "owner": format!("type:{module}:a.{}", n.entity),
                "name": "<init>", "descriptor": "", "module": module,
            },
            format!("type:{module}:a.{}", n.aux): {
                "kind": "type", "fqn": format!("a.{}", n.aux), "type_kind": "class",
                "module": module,
            },
            aux_method.clone(): {
                "kind": "method", "owner": format!("type:{module}:a.{}", n.aux),
                "name": "help", "descriptor": "", "module": module,
            },
            format!("type:{module}:a.{}", n.kind): {
                "kind": "type", "fqn": format!("a.{}", n.kind), "type_kind": "class",
                "module": module,
            },
            kind_method.clone(): {
                "kind": "method", "owner": format!("type:{module}:a.{}", n.kind),
                "name": "code", "descriptor": "", "module": module,
            },
            format!("type:{module}:a.{}", n.filter): {
                "kind": "type", "fqn": format!("a.{}", n.filter), "type_kind": "class",
                "implements_raw": ["Filter"], "module": module,
            },
            filter_method.clone(): {
                "kind": "method", "owner": format!("type:{module}:a.{}", n.filter),
                "name": "doFilterInternal", "descriptor": "", "module": module,
            },
            format!("type:{module}:a.{}", n.users): {
                "kind": "type", "fqn": format!("a.{}", n.users), "type_kind": "class",
                "implements_raw": ["UserDetailsService"], "module": module,
            },
            users_method.clone(): {
                "kind": "method", "owner": format!("type:{module}:a.{}", n.users),
                "name": "loadUserByUsername", "descriptor": "java.lang.String",
                "return_raw": "UserDetails", "module": module,
            },
            format!("type:{module}:a.{}", n.person): {
                "kind": "type", "fqn": format!("a.{}", n.person), "type_kind": "class",
                "implements_raw": ["UserDetails"], "module": module,
            },
            person_getter.clone(): {
                "kind": "method", "owner": format!("type:{module}:a.{}", n.person),
                "name": "getPassword", "descriptor": "", "module": module,
            },
            repo_cs.clone(): call_site("findOne", n.repo_field, Some(n.repo), repo_line),
            aux_cs.clone(): call_site("help", n.aux_field, Some(n.aux), aux_line),
            kind_cs.clone(): call_site("code", &format!("{}.PRIMARY", n.kind), None, kind_line),
            table_id.clone(): {"kind": "data_resource", "resource_kind": "table", "name": n.table},
        },
        "edges": [
            {"source": repo_cs, "type": "calls", "target": repo_method},
            {"source": repo_cs, "type": "data_access", "target": table_id},
            {"source": aux_cs, "type": "calls", "target": aux_method},
        ],
    });

    write(
        "skeleton/toy.json",
        &serde_json::to_string_pretty(&skeleton).expect("skeleton json"),
    );

    let feature = feature_param(n);
    for (id_suffix, step_text) in [
        // Both steps ground the same handler; only the second one mentions the
        // optional input, which is exactly the G6 switch.
        ("absent", n.step.to_owned()),
        ("present", format!("{} with {feature}", n.step)),
    ] {
        let scenario = serde_json::json!({
            "project": "toy",
            "id": format!("{}-{id_suffix}", n.scenario),
            "title": format!("{} flow", n.action),
            "description": step_text,
            "input": "text",
            "steps": [{"n": 1, "action": step_text}],
        });
        write(
            &format!("scenarios/{}-{id_suffix}.json", n.scenario),
            &serde_json::to_string_pretty(&scenario).expect("scenario json"),
        );
    }
}

/// A vocabulary-independent summary of one prediction.
#[derive(Debug, PartialEq, Eq)]
struct Behavior {
    executes: usize,
    calls: usize,
    remote: usize,
    data: usize,
    /// The handler grounded as an entry.
    endpoint: bool,
    /// `executes` contains the repository proxy (it must not).
    repo_proxy: bool,
    /// The ORM-materialized entity constructor (G4).
    entity_ctor: bool,
    /// The guarded helper call survived (G6).
    guarded_helper: bool,
    /// The static-receiver call resolved (G7).
    static_receiver: bool,
    /// The servlet filter ran (G5).
    filter: bool,
    /// The principal's member was read by the auth machinery (G5).
    details_member: bool,
    /// SQL credited to the handler (G3).
    table: bool,
}

impl Behavior {
    fn of(pred: &Prediction, n: &Names, id: &str) -> Self {
        let m = |name_suffix: &str| format!("method:{}:a.{name_suffix}", n.module);
        let handler = format!("method:{}:a.{}#{}", n.module, n.class, n.action);
        let table = format!("data_resource:{}:{}", n.module, n.table);
        Self {
            executes: pred.executes.len(),
            calls: pred.calls.len(),
            remote: pred.remote.len(),
            data: pred.data.len(),
            endpoint: pred.executes.contains(&handler),
            repo_proxy: pred
                .executes
                .iter()
                .any(|e| e.contains(&format!("a.{}#", n.repo))),
            entity_ctor: pred.executes.contains(&m(&format!("{}#<init>()", n.entity))),
            guarded_helper: pred
                .calls
                .iter()
                .any(|(_, t)| *t == m(&format!("{}#help()", n.aux))),
            static_receiver: pred
                .calls
                .iter()
                .any(|(_, t)| *t == m(&format!("{}#code()", n.kind))),
            filter: pred
                .executes
                .contains(&m(&format!("{}#doFilterInternal()", n.filter))),
            details_member: pred.executes.contains(&m(&format!("{}#getPassword()", n.person))),
            table: pred.data.iter().any(|(_, t)| *t == table),
        }
        .tap(id)
    }

    /// Assert the contract that must hold for *any* vocabulary.
    fn tap(self, scenario: &str) -> Self {
        assert!(
            self.endpoint,
            "{scenario}: the mapped handler must be grounded as an entry"
        );
        assert!(
            !self.repo_proxy,
            "{scenario}: a container-generated repository proxy never executes"
        );
        assert!(
            self.entity_ctor,
            "{scenario}: reading an entity materializes it (JPA no-arg constructor)"
        );
        assert!(self.filter, "{scenario}: a servlet filter runs per request");
        assert!(
            self.details_member,
            "{scenario}: the auth machinery reads the principal's members"
        );
        assert!(
            self.static_receiver,
            "{scenario}: a call on a type-named receiver is that type's method"
        );
        assert!(self.table, "{scenario}: the repository's SQL is credited to the caller");
        self
    }
}

fn temp_root(tag: &str) -> PathBuf {
    let root = std::env::temp_dir().join(format!(
        "semarch-generality-{tag}-{}-{}",
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

fn run_fixture(root: &Path, n: &Names) -> Vec<(Behavior, usize)> {
    let analyzer = TtAnalyzer::load(root).expect("analyzer loads the toy project");
    let cfg = AnalyzerConfig::default();
    let scenarios = analyzer.analyze_all(&cfg).expect("scenarios run");
    assert_eq!(scenarios.len(), 2, "both fixture scenarios are analyzed");

    let mut out = Vec::new();
    for (id, pred, _) in &scenarios {
        // the contest exporter must accept every predicted id verbatim
        let predictions = vec![(id.clone(), pred.clone())];
        let (submission, reports) = export::build(
            &analyzer.skeleton.project,
            &predictions,
            &analyzer.graph.method_ids,
            &analyzer.graph.table_ids,
        );
        assert_eq!(reports.len(), 1);
        let report = reports.get(id).expect("one report per scenario");
        assert!(
            report.rejected.is_empty(),
            "{id}: no id may be invented, got {:?}",
            report.rejected
        );
        assert_eq!(submission.scenarios.len(), 1);
        out.push((Behavior::of(pred, n, id), report.emitted));
    }
    out
}

#[test]
fn mechanisms_are_rename_independent() {
    let alpha_root = temp_root("alpha");
    let beta_root = temp_root("beta");
    let a = alpha();
    let b = beta();
    write_fixture(&alpha_root, &a);
    write_fixture(&beta_root, &b);

    let a_runs = run_fixture(&alpha_root, &a);
    let b_runs = run_fixture(&beta_root, &b);

    // Scenarios are sorted by id, so "absent" precedes "present".
    let (a_absent, a_absent_edges) = &a_runs[0];
    let (b_absent, b_absent_edges) = &b_runs[0];
    let (a_present, a_present_edges) = &a_runs[1];
    let (b_present, b_present_edges) = &b_runs[1];

    // G6: the optional branch is dead when the scenario omits the feature …
    assert!(
        !a_absent.guarded_helper,
        "a step that never mentions the feature must not execute its branch"
    );
    // … and alive when the scenario engages it.
    assert!(
        a_present.guarded_helper,
        "naming the feature must keep its branch alive"
    );
    assert!(
        a_present.executes > a_absent.executes && a_present.calls > a_absent.calls,
        "engaging the feature must add exactly its call and its vertex"
    );

    // Rename independence: identical structure under a different vocabulary …
    assert_eq!(a_absent, b_absent, "vocabulary must not change the outcome");
    assert_eq!(a_present, b_present, "vocabulary must not change the outcome");
    assert_eq!(a_absent_edges, b_absent_edges);
    assert_eq!(a_present_edges, b_present_edges);

    let _ = std::fs::remove_dir_all(&alpha_root);
    let _ = std::fs::remove_dir_all(&beta_root);
}

/// The engine's mechanisms are *switchable*: turning G6 off must restore the
/// branch regardless of the scenario text, which is what makes the ablation
/// evidence on the contested project meaningful.
#[test]
fn ablations_are_observable_on_the_toy_project() {
    let root = temp_root("ablate");
    let n = alpha();
    write_fixture(&root, &n);
    let analyzer = TtAnalyzer::load(&root).expect("loads");

    let scenario_text =
        std::fs::read_to_string(root.join("scenarios/S9-absent.json")).expect("scenario");
    let scn = semarch_scenario::scenario::Scenario::from_json(&scenario_text).expect("parses");
    // ground the entry through the analyzer itself
    let cfg = AnalyzerConfig::default();
    let pred = analyzer.analyze(&scn, &cfg);
    assert!(!Behavior::of(&pred, &n, "S9-absent").guarded_helper);

    let off = ResolutionConfig {
        feature_guards: false,
        ..ResolutionConfig::default()
    };
    let cfg_off = AnalyzerConfig {
        resolution: off,
        ..cfg
    };
    let pred_off = analyzer.analyze(&scn, &cfg_off);
    assert!(
        Behavior::of(&pred_off, &n, "S9-absent").guarded_helper,
        "with G6 disabled the branch is reported again (the ablation is real)"
    );

    let _ = std::fs::remove_dir_all(&root);
}

/// Guard extraction itself must not depend on the vocabulary either.
#[test]
fn guard_index_sees_a_renamed_feature() {
    let root = temp_root("guards");
    let n = beta();
    write_fixture(&root, &n);
    let guards = semarch_tt::guards::GuardIndex::build(&root.join("targets/toy")).expect("build");
    assert_eq!(guards.len(), 1, "one feature guard in the toy project");

    let absent: HashSet<String> = ["run".to_owned(), "mod".to_owned()].into_iter().collect();
    let file = format!("{}/src/main/java/a/{}.java", n.module, n.class);
    let source = handler_source(&n);
    let guarded = line_of(&source, &format!("{}.help()", n.aux_field));
    assert!(guards.blocks(&file, guarded, &absent));

    let present: HashSet<String> = [feature_param(&n).to_owned(), "run".to_owned()]
        .into_iter()
        .collect();
    assert!(!guards.blocks(&file, guarded, &present));

    let _ = std::fs::remove_dir_all(&root);
}
