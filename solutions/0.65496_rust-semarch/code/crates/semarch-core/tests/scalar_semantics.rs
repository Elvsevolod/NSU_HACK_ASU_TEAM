//! N04 acceptance: typed scalar semantics over the abstract-value domain.
//!
//! These are the properties the *analysis* relies on, stated without any
//! frontend: exact integers (no float round-trip), no invented values on
//! overflow/division by zero, `Unknown` never deciding, and the places where
//! Java and Python genuinely differ being decided by the profile rather than
//! guessed.

use semarch_core::value::{AbstractValue, LanguageProfile, Truth};
use semarch_core::{BinaryOp, Language, UnaryOp};

fn java() -> LanguageProfile {
    LanguageProfile::java()
}

fn python() -> LanguageProfile {
    LanguageProfile::python()
}

fn int(v: i64) -> AbstractValue {
    AbstractValue::int(v)
}

fn bin(
    op: BinaryOp,
    lhs: &AbstractValue,
    rhs: &AbstractValue,
    profile: &LanguageProfile,
) -> AbstractValue {
    AbstractValue::binary(op, lhs, rhs, profile).expect("operation is supported")
}

#[test]
fn integer_arithmetic_is_exact_above_the_float_limit() {
    // `1 + 1 == 2`.
    assert_eq!(
        bin(BinaryOp::Add, &int(1), &int(1), &java()),
        int(2)
    );

    // 2^53 + 1 and 2^53 are distinct integers but the same f64. An analysis
    // that round-tripped through f64 would claim them equal.
    let a = int(9_007_199_254_740_993);
    let b = int(9_007_199_254_740_992);
    assert_eq!(
        bin(BinaryOp::Eq, &a, &b, &java()),
        AbstractValue::bool(false)
    );
    assert_eq!(
        bin(BinaryOp::Add, &int(i64::MAX - 1), &int(1), &java()),
        int(i64::MAX)
    );
}

#[test]
fn overflow_and_division_by_zero_produce_a_reason_not_a_value() {
    assert_eq!(
        AbstractValue::binary(BinaryOp::Add, &int(i64::MAX), &int(1), &java()),
        Err("integer_overflow")
    );
    assert_eq!(
        AbstractValue::binary(BinaryOp::Div, &int(1), &int(0), &java()),
        Err("integer_division_by_zero")
    );
    assert_eq!(
        AbstractValue::binary(BinaryOp::Rem, &int(1), &int(0), &java()),
        Err("integer_remainder_by_zero")
    );
    assert_eq!(
        AbstractValue::binary(
            BinaryOp::Div,
            &AbstractValue::Float { value: 1.0 },
            &AbstractValue::Float { value: 0.0 },
            &java()
        ),
        Err("floating_division_by_zero")
    );
    // The minimum integer has no positive counterpart.
    assert_eq!(
        AbstractValue::unary(UnaryOp::Negate, &int(i64::MIN), &java()),
        Err("integer_overflow")
    );
}

#[test]
fn division_follows_the_language() {
    // Java: truncating integer division.
    assert_eq!(bin(BinaryOp::Div, &int(7), &int(2), &java()), int(3));
    assert_eq!(bin(BinaryOp::Div, &int(-7), &int(2), &java()), int(-3));
    // Python: true division, always a float.
    assert_eq!(
        bin(BinaryOp::Div, &int(7), &int(2), &python()),
        AbstractValue::Float { value: 3.5 }
    );
    // `%` agrees when the operands agree in sign, and is refused otherwise.
    assert_eq!(bin(BinaryOp::Rem, &int(7), &int(2), &java()), int(1));
    assert_eq!(
        AbstractValue::binary(BinaryOp::Rem, &int(-7), &int(2), &java()),
        Err("remainder_sign_differs_between_languages")
    );
}

#[test]
fn string_concatenation_is_add() {
    assert_eq!(
        bin(
            BinaryOp::Add,
            &AbstractValue::str_val("verify"),
            &AbstractValue::str_val("-code"),
            &java()
        ),
        AbstractValue::str_val("verify-code")
    );
    // A number on the other side is not concatenated into a string by guess.
    assert_eq!(
        AbstractValue::binary(
            BinaryOp::Add,
            &AbstractValue::str_val("a"),
            &int(1),
            &java()
        ),
        Err("arithmetic_on_non_number")
    );
}

#[test]
fn equality_holds_across_tags_where_both_languages_define_it() {
    let eq = |lhs: &AbstractValue, rhs: &AbstractValue| {
        bin(BinaryOp::Eq, lhs, rhs, &java())
    };
    assert_eq!(eq(&int(1), &AbstractValue::Float { value: 1.0 }), AbstractValue::bool(true));
    assert_eq!(eq(&AbstractValue::Null, &AbstractValue::Null), AbstractValue::bool(true));
    // `None == 0`, `"" == 0`, `"" == None` are all false in both languages.
    assert_eq!(eq(&AbstractValue::Null, &int(0)), AbstractValue::bool(false));
    assert_eq!(
        eq(&AbstractValue::str_val(""), &int(0)),
        AbstractValue::bool(false)
    );
    assert_eq!(
        bin(BinaryOp::Ne, &AbstractValue::str_val("a"), &AbstractValue::str_val("b"), &java()),
        AbstractValue::bool(true)
    );
}

#[test]
fn unknown_never_decides_anything() {
    let unknown = AbstractValue::Unknown;
    for op in [BinaryOp::Eq, BinaryOp::Ne, BinaryOp::Lt, BinaryOp::Add] {
        assert_eq!(
            bin(op, &unknown, &int(0), &java()),
            unknown,
            "{op:?} with an unknown operand is unknown, never false"
        );
    }
    assert_eq!(
        bin(BinaryOp::Eq, &int(0), &unknown, &java()),
        AbstractValue::Unknown
    );
    // Two unknowns do not prove equality *or* inequality.
    assert_eq!(
        bin(BinaryOp::Ne, &unknown, &unknown, &java()),
        AbstractValue::Unknown
    );
    assert_eq!(unknown.truth(&java()), Truth::Unknown);
    assert_eq!(unknown.truth(&python()), Truth::Unknown);
}

#[test]
fn bottom_absorbs_operations() {
    let bottom = AbstractValue::Unreachable;
    assert_eq!(bin(BinaryOp::Add, &bottom, &int(1), &java()), bottom);
    assert_eq!(bin(BinaryOp::Eq, &int(1), &bottom, &java()), bottom);
    assert_eq!(
        AbstractValue::unary(UnaryOp::Not, &bottom, &java()),
        Ok(bottom.clone()),
        "an operation on bottom stays bottom"
    );
    assert_eq!(
        AbstractValue::unary(UnaryOp::Negate, &bottom, &java()),
        Ok(bottom)
    );
}

#[test]
fn java_requires_a_boolean_condition() {
    let profile = java();
    assert_eq!(AbstractValue::bool(true).truth(&profile), Truth::True);
    assert_eq!(AbstractValue::bool(false).truth(&profile), Truth::False);
    for value in [
        int(0),
        int(1),
        AbstractValue::Null,
        AbstractValue::str_val(""),
        AbstractValue::str_val("x"),
    ] {
        assert_eq!(
            value.truth(&profile),
            Truth::Unknown,
            "`if ({value:?})` is not a Java program"
        );
    }
}

#[test]
fn python_admits_falsy_conditions() {
    let profile = python();
    assert_eq!(int(0).truth(&profile), Truth::False);
    assert_eq!(int(-1).truth(&profile), Truth::True);
    assert_eq!(AbstractValue::Float { value: 0.0 }.truth(&profile), Truth::False);
    assert_eq!(AbstractValue::Null.truth(&profile), Truth::False);
    assert_eq!(AbstractValue::str_val("").truth(&profile), Truth::False);
    assert_eq!(AbstractValue::str_val("0").truth(&profile), Truth::True);
}

#[test]
fn the_profile_follows_the_language_family() {
    assert!(!LanguageProfile::for_language(Language::Java).falsy_values_decide());
    assert!(!LanguageProfile::for_language(Language::Go).falsy_values_decide());
    assert!(LanguageProfile::for_language(Language::Python).falsy_values_decide());
    assert!(LanguageProfile::for_language(Language::JavaScript).falsy_values_decide());
    assert!(LanguageProfile::for_language(Language::TypeScript).falsy_values_decide());
    assert!(LanguageProfile::for_language(Language::Java).division_is_integral());
    assert!(!LanguageProfile::for_language(Language::Python).division_is_integral());
}

#[test]
fn logical_operators_are_kleene_in_java() {
    let profile = java();
    let t = AbstractValue::bool(true);
    let f = AbstractValue::bool(false);
    let u = AbstractValue::Unknown;
    // Java's `&&`/`||` are boolean operators: a decided operand decides.
    assert_eq!(bin(BinaryOp::And, &f, &u, &profile), f);
    assert_eq!(bin(BinaryOp::And, &u, &f, &profile), f);
    assert_eq!(bin(BinaryOp::Or, &t, &u, &profile), t);
    assert_eq!(bin(BinaryOp::And, &t, &u, &profile), u);
    assert_eq!(bin(BinaryOp::Or, &f, &u, &profile), u);
}

#[test]
fn a_decided_left_operand_makes_the_right_one_irrelevant() {
    // `false && sideEffect()` is `false`: the value of the right operand — and
    // therefore any effect it would have — cannot change the result. This is a
    // *value* statement; that the call is also never reached is the CFG
    // property checked in `body_analysis.rs`.
    let profile = java();
    let f = AbstractValue::bool(false);
    let t = AbstractValue::bool(true);
    let call = AbstractValue::Unknown; // stands for `sideEffect()`
    assert_eq!(bin(BinaryOp::And, &f, &call, &profile), f);
    assert_eq!(bin(BinaryOp::Or, &t, &call, &profile), t);
    // The mirror image is *not* decidable: `true && x` is `x`.
    assert_eq!(bin(BinaryOp::And, &t, &call, &profile), call);
    assert_eq!(bin(BinaryOp::Or, &f, &call, &profile), call);
}

#[test]
fn logical_operators_yield_an_operand_in_python() {
    let profile = python();
    // `0 and f()` is `0`, not `False`.
    assert_eq!(
        bin(BinaryOp::And, &int(0), &AbstractValue::Unknown, &profile),
        int(0)
    );
    // `"" or "default"` is `"default"`.
    assert_eq!(
        bin(
            BinaryOp::Or,
            &AbstractValue::str_val(""),
            &AbstractValue::str_val("default"),
            &profile
        ),
        AbstractValue::str_val("default")
    );
    // `1 and 2` is `2`.
    assert_eq!(bin(BinaryOp::And, &int(1), &int(2), &profile), int(2));
}

#[test]
fn not_is_a_boolean_in_python_and_strict_in_java() {
    assert_eq!(
        AbstractValue::unary(UnaryOp::Not, &int(0), &python()),
        Ok(AbstractValue::bool(true))
    );
    assert_eq!(
        AbstractValue::unary(UnaryOp::Not, &AbstractValue::str_val(""), &python()),
        Ok(AbstractValue::bool(true))
    );
    // The same input has no Java value: `!0` does not compile.
    assert_eq!(
        AbstractValue::unary(UnaryOp::Not, &int(0), &java()),
        Ok(AbstractValue::Unknown)
    );
    // Negating a string is outside both languages' scalar semantics.
    assert_eq!(
        AbstractValue::unary(UnaryOp::Negate, &AbstractValue::str_val("x"), &java()),
        Err("negation_of_non_number")
    );
}

#[test]
fn ordering_of_non_numbers_is_refused() {
    assert_eq!(
        AbstractValue::binary(
            BinaryOp::Lt,
            &int(1),
            &AbstractValue::str_val("2"),
            &java()
        ),
        Err("ordering_of_non_number")
    );
    // Strings order lexicographically in both languages.
    assert_eq!(
        bin(
            BinaryOp::Lt,
            &AbstractValue::str_val("a"),
            &AbstractValue::str_val("b"),
            &java()
        ),
        AbstractValue::bool(true)
    );
}

#[test]
fn join_is_a_lattice() {
    let u = AbstractValue::Unknown;
    let bottom = AbstractValue::Unreachable;
    let one = int(1);
    let two = int(2);
    assert_eq!(bottom.join(&one), one);
    assert_eq!(one.join(&bottom), one);
    assert_eq!(one.join(&one), one);
    assert_eq!(one.join(&two), u);
    assert_eq!(one.join(&u), u);
    assert_eq!(u.join(&bottom), u);
    // Commutative and associative on the interesting pairs.
    assert_eq!(one.join(&two), two.join(&one));
    assert_eq!(one.join(&two).join(&one), one.join(&two.join(&one)));
}

#[test]
fn describe_is_the_evidence_vocabulary() {
    assert_eq!(AbstractValue::Unknown.describe(), "unknown");
    assert_eq!(AbstractValue::Unreachable.describe(), "unreachable");
    assert_eq!(AbstractValue::Null.describe(), "null");
    assert_eq!(int(7).describe(), "7");
    assert_eq!(AbstractValue::bool(false).describe(), "false");
    assert_eq!(AbstractValue::str_val("").describe(), "\"\"");
}
