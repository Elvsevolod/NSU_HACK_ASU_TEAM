//! R04: the explicit call outcome, and the one property every consumer relies
//! on — only a *proven* absence of a normal return may cut the caller's
//! continuation. An unresolved body and a budget cut-off must not.

use semarch_core::invocation::CallOutcome;
use semarch_core::AbstractValue;

#[test]
fn only_no_normal_return_cuts_the_caller_continuation() {
    assert!(CallOutcome::NoNormal.value().is_unreachable());
    assert!(!CallOutcome::NoNormal.may_return_normally());
    for outcome in [
        CallOutcome::Void,
        CallOutcome::Unknown,
        CallOutcome::Cutoff,
        CallOutcome::Returns(AbstractValue::bool(false)),
    ] {
        assert!(
            outcome.may_return_normally(),
            "{outcome:?} is not a proof of absence"
        );
        assert!(
            !outcome.value().is_unreachable(),
            "{outcome:?} must not cut the caller"
        );
    }
}

#[test]
fn an_unknown_body_is_not_a_proven_absence() {
    // A callee whose body was not available may return anything and may throw;
    // conflating it with "never returns" is the mistake this variant prevents.
    assert_ne!(CallOutcome::Unknown, CallOutcome::NoNormal);
    assert_eq!(CallOutcome::Unknown.value(), AbstractValue::Unknown);
    assert_eq!(CallOutcome::Cutoff.value(), AbstractValue::Unknown);
}

#[test]
fn a_returns_outcome_carries_its_value() {
    let value = CallOutcome::Returns(AbstractValue::str_val("X"));
    assert_eq!(value.value(), AbstractValue::Str { value: "X".into() });
    assert_eq!(value.describe(), "returns");
    assert_eq!(CallOutcome::Void.describe(), "void");
    assert_eq!(CallOutcome::NoNormal.describe(), "no_normal_return");
    assert_eq!(CallOutcome::Unknown.describe(), "unknown_body");
    assert_eq!(CallOutcome::Cutoff.describe(), "recursion_cutoff");
}

#[test]
fn joining_visits_never_turns_a_return_into_an_absence() {
    let joined = CallOutcome::NoNormal.join(&CallOutcome::Returns(AbstractValue::bool(true)));
    assert!(joined.may_return_normally(), "{joined:?}");
    assert_eq!(CallOutcome::Void.join(&CallOutcome::Void), CallOutcome::Void);
    assert_eq!(
        CallOutcome::Void.join(&CallOutcome::Returns(AbstractValue::bool(true))),
        CallOutcome::Unknown
    );
    assert_eq!(
        CallOutcome::Returns(AbstractValue::bool(true))
            .join(&CallOutcome::Returns(AbstractValue::bool(false))),
        CallOutcome::Returns(AbstractValue::Unknown)
    );
}
