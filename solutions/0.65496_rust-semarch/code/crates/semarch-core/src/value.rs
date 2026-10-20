//! Abstract values and typed scalar semantics (N04).
//!
//! [`ValueExpr`] is the *expression syntax* a frontend produces; an
//! [`AbstractValue`] is what evaluating it yields. Keeping them apart is the
//! point of this module: `Unknown` is a value in the domain (no information),
//! not an expression, and it is **not** bottom.
//!
//! # Lattice
//!
//! ```text
//!            Unknown        (⊤: no information)
//!          /    |    \
//!   Bool  Int  Float  Str  Null
//!          \    |    /
//!          Unreachable     (⊥: no path reaches this point)
//! ```
//!
//! `join` keeps a concrete value when both sides agree, returns the other side
//! when one is `Unreachable`, and widens to `Unknown` otherwise. Nothing in the
//! module ever turns `Unknown` into a definite verdict.
//!
//! # Where the languages genuinely differ
//!
//! Two operations cannot be given one value for every language, so the profile
//! decides instead of guessing:
//!
//! * `/` between two integers is truncating integer division in Java/Go/C# and
//!   a float division in Python/JS ([`LanguageProfile::division_is_integral`]).
//! * `%` follows the dividend (Java) or the divisor (Python). When the operands
//!   disagree in sign the result is *not* computed: the operation reports
//!   `remainder_sign_differs_between_languages` and the caller records a gap.
//! * a non-boolean condition is a compile error in Java and a truthiness test
//!   in Python ([`LanguageProfile::falsy_values_decide`]).
//!
//! # Why a language profile
//!
//! Scalar semantics are not universal. `if (0)` is not a Java program, so the
//! Java profile may not read `Int { 0 }` as "false"; Python's `not x` always
//! yields a boolean, while Python's `and`/`or` yield an *operand*; Java's `&&`
//! yields a boolean. The profile makes these differences explicit instead of
//! hiding them behind one shared truthiness rule.

use serde::{Deserialize, Serialize};

use crate::ir::{BinaryOp, UnaryOp};
use crate::lang::Language;

/// What evaluating an expression produced. See the module docs for the lattice.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum AbstractValue {
    /// No information (top). Never treated as `false`.
    Unknown,
    /// No value: the program point is unreachable (bottom).
    Unreachable,
    Null,
    Bool { value: bool },
    Int { value: i64 },
    Float { value: f64 },
    Str { value: String },
}

impl AbstractValue {
    #[must_use]
    pub fn bool(value: bool) -> Self {
        Self::Bool { value }
    }
    #[must_use]
    pub fn int(value: i64) -> Self {
        Self::Int { value }
    }
    #[must_use]
    pub fn str_val(value: impl Into<String>) -> Self {
        Self::Str {
            value: value.into(),
        }
    }

    /// Whether this is the top element (no information).
    #[must_use]
    pub fn is_unknown(&self) -> bool {
        matches!(self, Self::Unknown)
    }

    /// Whether this is bottom (no path reaches the point).
    #[must_use]
    pub fn is_unreachable(&self) -> bool {
        matches!(self, Self::Unreachable)
    }

    /// Lattice join. Order-independent and monotone.
    #[must_use]
    pub fn join(&self, other: &Self) -> Self {
        match (self, other) {
            (Self::Unreachable, x) | (x, Self::Unreachable) => x.clone(),
            (a, b) if a == b => a.clone(),
            _ => Self::Unknown,
        }
    }

    /// The type tag, for cross-type reasoning that is valid in both Java and
    /// Python (see [`Comparison`]).
    fn tag(&self) -> Tag {
        match self {
            Self::Unknown => Tag::Unknown,
            Self::Unreachable => Tag::Unreachable,
            Self::Null => Tag::Null,
            Self::Bool { .. } => Tag::Bool,
            Self::Int { .. } => Tag::Int,
            Self::Float { .. } => Tag::Float,
            Self::Str { .. } => Tag::Str,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Tag {
    Unknown,
    Unreachable,
    Null,
    Bool,
    Int,
    Float,
    Str,
}

/// Per-language scalar semantics. Construct with [`LanguageProfile::java`] or
/// [`LanguageProfile::python`]; [`LanguageProfile::for_language`] maps a
/// [`Language`] to the profile actually used (JS/TS follow Python's rules here,
/// Go/C# follow Java's).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LanguageProfile {
    pub language: Language,
}

impl LanguageProfile {
    #[must_use]
    pub fn java() -> Self {
        Self {
            language: Language::Java,
        }
    }

    #[must_use]
    pub fn python() -> Self {
        Self {
            language: Language::Python,
        }
    }

    /// The profile used for a language. Java and C# decide a condition only on
    /// a boolean; Python, JS and TS admit falsy values.
    #[must_use]
    pub fn for_language(language: Language) -> Self {
        Self { language }
    }

    /// Whether a value other than a boolean may decide a condition
    /// (`0`, `""`, `None` are false).
    #[must_use]
    pub fn falsy_values_decide(&self) -> bool {
        matches!(
            self.language,
            Language::Python | Language::JavaScript | Language::TypeScript
        )
    }

    /// Whether `&&`/`||` yield an operand rather than a boolean.
    #[must_use]
    pub fn logical_yields_operand(&self) -> bool {
        self.falsy_values_decide()
    }

    /// Whether `/` between two integers is integer division. Java, Go and C#
    /// truncate toward zero; Python and JavaScript divide into a float. The
    /// same expression therefore does not have the same value in both.
    #[must_use]
    pub fn division_is_integral(&self) -> bool {
        matches!(
            self.language,
            Language::Java | Language::Go | Language::CSharp
        )
    }

    /// Whether the language's standard property convention is a pair of
    /// accessor methods (`getX`/`isX`) over a field `x` — the JavaBeans
    /// contract. Java has it; Python attributes and C# properties are read
    /// directly, and Go has no such convention.
    #[must_use]
    pub fn bean_accessors(&self) -> bool {
        matches!(self.language, Language::Java)
    }

    /// Name used in evidence reasons.
    #[must_use]
    pub fn name(&self) -> &'static str {
        self.language.name()
    }
}

/// Property an accessor method name reads under the JavaBeans convention:
/// `getVerificationCode` → `verificationCode`, `isValid` → `valid`.
///
/// This is the platform convention (JavaBeans), not a project fact; callers
/// must additionally check that the language profile has accessors and that
/// the property is bound on the receiver.
#[must_use]
pub fn accessor_property(callee: &str) -> Option<String> {
    for prefix in ["get", "is"] {
        let Some(rest) = callee.strip_prefix(prefix) else {
            continue;
        };
        let mut chars = rest.chars();
        let first = chars.next()?;
        if !first.is_uppercase() {
            continue;
        }
        let mut out = String::with_capacity(rest.len());
        for (i, c) in rest.chars().enumerate() {
            if i == 0 {
                out.extend(c.to_lowercase());
            } else {
                out.push(c);
            }
        }
        return Some(out);
    }
    None
}

/// Truth of a value under a profile. Mirrors [`crate::cfg::GuardVerdict`]
/// without depending on it (the CFG module depends on this one).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Truth {
    True,
    False,
    Unknown,
}

impl Truth {
    #[must_use]
    pub fn negate(self) -> Self {
        match self {
            Truth::True => Truth::False,
            Truth::False => Truth::True,
            Truth::Unknown => Truth::Unknown,
        }
    }

    #[must_use]
    pub fn is_decided(self) -> bool {
        !matches!(self, Truth::Unknown)
    }
}

impl AbstractValue {
    /// Truth under a language profile. This is the only place truthiness is
    /// decided, so the `unknown != false` invariant has one home.
    #[must_use]
    pub fn truth(&self, profile: &LanguageProfile) -> Truth {
        match self {
            AbstractValue::Bool { value } => {
                if *value {
                    Truth::True
                } else {
                    Truth::False
                }
            }
            AbstractValue::Unreachable => Truth::Unknown,
            AbstractValue::Unknown => Truth::Unknown,
            // Only languages that admit falsy values may decide here. In Java
            // `if (0)` is not a program, so reading an integer as a condition
            // would be a claim about a program that cannot exist.
            other => {
                if !profile.falsy_values_decide() {
                    return Truth::Unknown;
                }
                match other {
                    AbstractValue::Null => Truth::False,
                    AbstractValue::Int { value } => bool_truth(*value != 0),
                    AbstractValue::Float { value } => bool_truth(*value != 0.0),
                    AbstractValue::Str { value } => bool_truth(!value.is_empty()),
                    AbstractValue::Bool { .. }
                    | AbstractValue::Unknown
                    | AbstractValue::Unreachable => Truth::Unknown,
                }
            }
        }
    }

    /// Negation under a profile. Java's `!` requires a boolean; Python's `not`
    /// always yields a boolean, so it is defined for any falsy value.
    #[must_use]
    pub fn not(&self, profile: &LanguageProfile) -> AbstractValue {
        match self.truth(profile) {
            Truth::True => AbstractValue::bool(false),
            Truth::False => AbstractValue::bool(true),
            // An unknown truth still yields a boolean for Python (`not x` is
            // `bool`), but its *value* is unknown.
            Truth::Unknown => AbstractValue::Unknown,
        }
    }

    /// Unary operation with an explicit failure reason.
    ///
    /// # Errors
    /// Returns a reason when the operation is outside the supported semantics
    /// (e.g. negating a string); the caller records a gap and yields `Unknown`.
    pub fn unary(op: UnaryOp, operand: &Self, profile: &LanguageProfile) -> Result<Self, &'static str> {
        // Bottom is not a value: no path reaches this point, so no operation on
        // it has a result.
        if operand.is_unreachable() {
            return Ok(Self::Unreachable);
        }
        match op {
            UnaryOp::Not => Ok(operand.not(profile)),
            UnaryOp::Negate => match operand {
                // Negating `i64::MIN` overflows: refuse instead of wrapping.
                AbstractValue::Int { value } => value
                    .checked_neg()
                    .map(AbstractValue::int)
                    .ok_or("integer_overflow"),
                AbstractValue::Float { value } => Ok(AbstractValue::Float { value: -value }),
                AbstractValue::Unknown => Ok(AbstractValue::Unknown),
                AbstractValue::Unreachable => Ok(AbstractValue::Unreachable),
                _ => Err("negation_of_non_number"),
            },
        }
    }

    /// Binary operation with an explicit failure reason.
    ///
    /// # Errors
    /// Returns a reason for operations outside the supported semantics
    /// (integer overflow, division by zero, ordering of non-numbers, string
    /// arithmetic). Callers record a gap; they never invent a value.
    pub fn binary(
        op: BinaryOp,
        lhs: &Self,
        rhs: &Self,
        profile: &LanguageProfile,
    ) -> Result<Self, &'static str> {
        if lhs.is_unreachable() || rhs.is_unreachable() {
            return Ok(Self::Unreachable);
        }
        match op {
            BinaryOp::And | BinaryOp::Or => Ok(logical(op, lhs, rhs, profile)),
            BinaryOp::Eq | BinaryOp::Ne => Ok(equality(op, lhs, rhs)),
            BinaryOp::Lt | BinaryOp::Le | BinaryOp::Gt | BinaryOp::Ge => compare(op, lhs, rhs),
            BinaryOp::Add | BinaryOp::Sub | BinaryOp::Mul | BinaryOp::Div | BinaryOp::Rem => {
                arithmetic(op, lhs, rhs, profile)
            }
        }
    }

    /// Textual rendering used in evidence detail strings.
    #[must_use]
    pub fn describe(&self) -> String {
        match self {
            AbstractValue::Unknown => "unknown".to_owned(),
            AbstractValue::Unreachable => "unreachable".to_owned(),
            AbstractValue::Null => "null".to_owned(),
            AbstractValue::Bool { value } => value.to_string(),
            AbstractValue::Int { value } => value.to_string(),
            AbstractValue::Float { value } => value.to_string(),
            AbstractValue::Str { value } => format!("{value:?}"),
        }
    }
}

fn bool_truth(value: bool) -> Truth {
    if value {
        Truth::True
    } else {
        Truth::False
    }
}

/// Kleene `and`/`or` for boolean-yielding languages; operand selection for
/// languages where `and`/`or` return one of their operands.
fn logical(op: BinaryOp, lhs: &AbstractValue, rhs: &AbstractValue, profile: &LanguageProfile) -> AbstractValue {
    let lt = lhs.truth(profile);
    let rt = rhs.truth(profile);
    if profile.logical_yields_operand() {
        // Python/JS: `a and b` is `a` when `a` is falsy, else `b`; `a or b` is
        // `a` when `a` is truthy, else `b`.
        return match (op, lt) {
            (BinaryOp::And, Truth::False) => lhs.clone(),
            (BinaryOp::And, Truth::True) => rhs.clone(),
            (BinaryOp::Or, Truth::True) => lhs.clone(),
            (BinaryOp::Or, Truth::False) => rhs.clone(),
            _ => AbstractValue::Unknown,
        };
    }
    match (op, lt, rt) {
        (BinaryOp::And, Truth::False, _) | (BinaryOp::And, _, Truth::False) => {
            AbstractValue::bool(false)
        }
        (BinaryOp::And, Truth::True, Truth::True) => AbstractValue::bool(true),
        (BinaryOp::Or, Truth::True, _) | (BinaryOp::Or, _, Truth::True) => AbstractValue::bool(true),
        (BinaryOp::Or, Truth::False, Truth::False) => AbstractValue::bool(false),
        _ => AbstractValue::Unknown,
    }
}

/// Equality. Two concrete values of *different* tags are unequal, which is
/// true both in Java (where such a comparison cannot even be written) and in
/// Python (`None == 0`, `1 == "a"` are `False`). `Int`/`Float` compare
/// numerically, as both languages promote.
fn equality(op: BinaryOp, lhs: &AbstractValue, rhs: &AbstractValue) -> AbstractValue {
    let (a, b) = (lhs, rhs);
    if a.is_unreachable() || b.is_unreachable() {
        return AbstractValue::Unreachable;
    }
    if a.is_unknown() || b.is_unknown() {
        return AbstractValue::Unknown;
    }
    let equal = match (a.tag(), b.tag()) {
        (Tag::Null, Tag::Null) => true,
        (Tag::Null, _) | (_, Tag::Null) => false,
        (Tag::Int, Tag::Int) => match (a, b) {
            (AbstractValue::Int { value: x }, AbstractValue::Int { value: y }) => x == y,
            _ => unreachable!("tag matched"),
        },
        (Tag::Float, Tag::Float) => match (a, b) {
            (AbstractValue::Float { value: x }, AbstractValue::Float { value: y }) => x == y,
            _ => unreachable!("tag matched"),
        },
        (Tag::Bool, Tag::Bool) => match (a, b) {
            (AbstractValue::Bool { value: x }, AbstractValue::Bool { value: y }) => x == y,
            _ => unreachable!("tag matched"),
        },
        (Tag::Str, Tag::Str) => match (a, b) {
            (AbstractValue::Str { value: x }, AbstractValue::Str { value: y }) => x == y,
            _ => unreachable!("tag matched"),
        },
        // Java and Python both define `1 == 1.0`.
        (Tag::Int, Tag::Float) | (Tag::Float, Tag::Int) => match (as_f64(a), as_f64(b)) {
            (Some(x), Some(y)) => x == y,
            _ => return AbstractValue::Unknown,
        },
        // Different concrete tags: not equal.
        _ => false,
    };
    AbstractValue::bool(if op == BinaryOp::Eq { equal } else { !equal })
}

/// Ordering. Numeric for numbers, lexicographic for strings; anything else is
/// outside the supported semantics (Java forbids it, Python raises at runtime),
/// so the caller records a gap rather than inventing a result.
fn compare(op: BinaryOp, lhs: &AbstractValue, rhs: &AbstractValue) -> Result<AbstractValue, &'static str> {
    if lhs.is_unreachable() || rhs.is_unreachable() {
        return Ok(AbstractValue::Unreachable);
    }
    if lhs.is_unknown() || rhs.is_unknown() {
        return Ok(AbstractValue::Unknown);
    }
    if let (AbstractValue::Str { value: a }, AbstractValue::Str { value: b }) = (lhs, rhs) {
        return Ok(AbstractValue::bool(match op {
            BinaryOp::Lt => a < b,
            BinaryOp::Le => a <= b,
            BinaryOp::Gt => a > b,
            BinaryOp::Ge => a >= b,
            _ => return Err("unsupported_ordering"),
        }));
    }
    let (Some(a), Some(b)) = (as_f64(lhs), as_f64(rhs)) else {
        return Err("ordering_of_non_number");
    };
    Ok(AbstractValue::bool(match op {
        BinaryOp::Lt => a < b,
        BinaryOp::Le => a <= b,
        BinaryOp::Gt => a > b,
        BinaryOp::Ge => a >= b,
        _ => return Err("unsupported_ordering"),
    }))
}

/// Arithmetic. Integer operations stay in `i64` (no float round-trip, which
/// would silently lose precision above 2^53) and are checked; `/` between two
/// integers is integer division, as in Java.
fn arithmetic(
    op: BinaryOp,
    lhs: &AbstractValue,
    rhs: &AbstractValue,
    profile: &LanguageProfile,
) -> Result<AbstractValue, &'static str> {
    if lhs.is_unreachable() || rhs.is_unreachable() {
        return Ok(AbstractValue::Unreachable);
    }
    if lhs.is_unknown() || rhs.is_unknown() {
        return Ok(AbstractValue::Unknown);
    }
    // `+` with a string on either side concatenates, in both Java and Python.
    if op == BinaryOp::Add {
        if let (Some(a), Some(b)) = (as_text(lhs), as_text(rhs)) {
            return Ok(AbstractValue::str_val(format!("{a}{b}")));
        }
    }
    match (lhs, rhs) {
        (AbstractValue::Int { value: a }, AbstractValue::Int { value: b }) => {
            let (a, b) = (*a, *b);
            let out = match op {
                BinaryOp::Add => a.checked_add(b),
                BinaryOp::Sub => a.checked_sub(b),
                BinaryOp::Mul => a.checked_mul(b),
                BinaryOp::Div => {
                    if b == 0 {
                        return Err("integer_division_by_zero");
                    }
                    if !profile.division_is_integral() {
                        // Python/JS: `7 / 2` is `3.5`, not `3`.
                        return Ok(AbstractValue::Float {
                            value: a as f64 / b as f64,
                        });
                    }
                    a.checked_div(b)
                }
                BinaryOp::Rem => {
                    if b == 0 {
                        return Err("integer_remainder_by_zero");
                    }
                    // `%` follows the dividend in Java and the divisor in
                    // Python, so the sign of the result differs unless the
                    // operands agree in sign. Refusing is honest; guessing is
                    // a claim about one language applied to the other.
                    if a != 0 && (a < 0) != (b < 0) {
                        return Err("remainder_sign_differs_between_languages");
                    }
                    a.checked_rem(b)
                }
                _ => return Err("unsupported_integer_operator"),
            };
            out.map(AbstractValue::int).ok_or("integer_overflow")
        }
        (a, b) => {
            let (Some(x), Some(y)) = (as_f64(a), as_f64(b)) else {
                return Err("arithmetic_on_non_number");
            };
            match op {
                BinaryOp::Add => Ok(AbstractValue::Float { value: x + y }),
                BinaryOp::Sub => Ok(AbstractValue::Float { value: x - y }),
                BinaryOp::Mul => Ok(AbstractValue::Float { value: x * y }),
                BinaryOp::Div if y != 0.0 => Ok(AbstractValue::Float { value: x / y }),
                BinaryOp::Rem if y != 0.0 => Ok(AbstractValue::Float { value: x % y }),
                BinaryOp::Div | BinaryOp::Rem => Err("floating_division_by_zero"),
                _ => Err("unsupported_float_operator"),
            }
        }
    }
}

fn as_f64(v: &AbstractValue) -> Option<f64> {
    match v {
        AbstractValue::Int { value } => Some(*value as f64),
        AbstractValue::Float { value } => Some(*value),
        _ => None,
    }
}

fn as_text(v: &AbstractValue) -> Option<String> {
    match v {
        AbstractValue::Str { value } => Some(value.clone()),
        _ => None,
    }
}
