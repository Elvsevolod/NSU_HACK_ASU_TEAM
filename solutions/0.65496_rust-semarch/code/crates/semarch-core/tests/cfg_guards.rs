//! Minimal CFG + guard policy fixtures (T08 acceptance): `ProvesFalse` on a
//! concrete path excludes the guarded effect *explicitly*, with evidence;
//! `Unknown` never changes status (unknown != false).
//!
//! N04 addition: truth is decided per *language profile*, so this file records
//! the counterexample that motivated the split — an integer condition is not a
//! Java program, so the Java profile must stay `Unknown` where Python's falsy
//! rule proves `false`.

use semarch_core::cfg::{apply_verdict, evaluate_condition, GuardVerdict, linear_cfg};
use semarch_core::value::{AbstractValue, LanguageProfile};
use semarch_core::{Effect, Evidence, EvidenceStatus, Guard, SourceSpan, ValueExpr};

fn empty_span() -> SourceSpan {
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

#[test]
fn java_profile_decides_only_on_booleans() {
    // Counterexample (recorded): the pre-N04 code read `Int { 0 }`, `Null` and
    // `Str { "" }` as `ProvesFalse` for *every* language. `if (0)` is not a
    // Java program, so a Java-profile decision there would be a claim about a
    // program that cannot exist. Only a boolean decides.
    let java = LanguageProfile::java();
    for (v, expected) in [
        (AbstractValue::bool(true), GuardVerdict::ProvesTrue),
        (AbstractValue::bool(false), GuardVerdict::ProvesFalse),
        (AbstractValue::int(0), GuardVerdict::Unknown),
        (AbstractValue::int(7), GuardVerdict::Unknown),
        (AbstractValue::Null, GuardVerdict::Unknown),
        (AbstractValue::str_val(""), GuardVerdict::Unknown),
        (AbstractValue::str_val("code"), GuardVerdict::Unknown),
        (AbstractValue::Unknown, GuardVerdict::Unknown),
        (AbstractValue::Unreachable, GuardVerdict::Unknown),
    ] {
        assert_eq!(evaluate_condition(&v, &java), expected, "java {v:?}");
    }
}

#[test]
fn python_profile_admits_falsy_conditions() {
    let python = LanguageProfile::python();
    for (v, expected) in [
        (AbstractValue::bool(true), GuardVerdict::ProvesTrue),
        (AbstractValue::bool(false), GuardVerdict::ProvesFalse),
        (AbstractValue::int(0), GuardVerdict::ProvesFalse),
        (AbstractValue::int(7), GuardVerdict::ProvesTrue),
        (AbstractValue::Float { value: 0.0 }, GuardVerdict::ProvesFalse),
        (AbstractValue::Null, GuardVerdict::ProvesFalse),
        (AbstractValue::str_val(""), GuardVerdict::ProvesFalse),
        (AbstractValue::str_val("code"), GuardVerdict::ProvesTrue),
        // `unknown != false` holds in every profile.
        (AbstractValue::Unknown, GuardVerdict::Unknown),
    ] {
        assert_eq!(evaluate_condition(&v, &python), expected, "python {v:?}");
    }
}

#[test]
fn proves_false_excludes_guarded_effect_with_evidence() {
    let mut effects = vec![
        (
            Effect::HttpCall {
                url: "http://verify-service:15679/verifycode".into(),
            },
            Evidence::possible("framework_mapping"),
        ),
        (
            Effect::DataRead {
                resource: 1u32.into(),
                table: None,
            },
            Evidence::confirmed("direct_write"),
        ),
    ];
    apply_verdict(
        &mut effects,
        |e| matches!(e, Effect::HttpCall { .. }),
        GuardVerdict::ProvesFalse,
        "guard_evaluates_false@67:55",
    );
    assert_eq!(effects[0].1.status, EvidenceStatus::Excluded);
    assert_eq!(effects[0].1.reason, "guard_evaluates_false@67:55");
    // The DataRead effect is untouched.
    assert_eq!(effects[1].1.status, EvidenceStatus::Confirmed);
}

#[test]
fn unknown_verdict_never_flips_status() {
    let mut effects = vec![(
        Effect::HttpCall { url: "http://x".into() },
        Evidence::possible("framework_mapping"),
    )];
    apply_verdict(&mut effects, |e| {
        matches!(e, Effect::HttpCall { .. })
    }, GuardVerdict::Unknown, "no_decision");
    assert_eq!(effects[0].1.status, EvidenceStatus::Possible);
    assert_eq!(effects[0].1.reason, "framework_mapping");
}

#[test]
fn linear_cfg_chains_guards_to_exit() {
    let guards = vec![
        Guard {
            id: 0u32.into(),
            condition: ValueExpr::Unknown,
            span: empty_span(),
        },
        Guard {
            id: 1u32.into(),
            condition: ValueExpr::Unknown,
            span: empty_span(),
        },
    ];
    let cfg = linear_cfg(5u32.into(), guards.clone());
    assert_eq!(cfg.blocks.len(), 4); // 2 guards + body + exit
    assert_eq!(cfg.entry, Some(0u32.into()));
    assert_eq!(cfg.exit, Some(3u32.into()));
    // Guard blocks branch false-arm to exit; true-arm to the next guard/body.
    assert_eq!(cfg.blocks[0].false_succ, Some(3u32.into()));
    assert_eq!(cfg.blocks[0].true_succ, Some(1u32.into()));
    assert_eq!(cfg.blocks[1].false_succ, Some(3u32.into()));
    assert_eq!(cfg.blocks[1].true_succ, Some(2u32.into()));
    // Body terminates with a return action into exit.
    assert_eq!(cfg.blocks[2].actions.len(), 1);
    assert_eq!(cfg.blocks[2].true_succ, Some(3u32.into()));
    // Guard ids are carried on their blocks.
    assert_eq!(cfg.blocks[0].guard, guards[0].id.into());
    let _: semarch_core::ids::GuardId = guards[0].id;
}
