//! Explicit call outcomes (R04): what an invocation can complete as.
//!
//! The IR hoists every call into a statement or terminator expression with its
//! own [`CallSiteId`](crate::ids::CallSiteId), so the call point is already
//! explicit: the call-site id *is* the result slot, the block's successor is
//! the normal continuation, and any `throw` the analysis reaches is the
//! exceptional one. What was missing is the *outcome* — whether the callee
//! returns a value, returns nothing, never returns normally, or is simply not
//! known. [`CallOutcome`] makes that distinction explicit so a caller's
//! continuation is only cut by a proven absence of a normal return, never by
//! an unresolved callee (which is `Unknown`, not "no normal").
//!
//! A callee body is entered through [`CallTargetProvider`]: a flat list of
//! `return` expressions cannot describe a local assignment, a branch, or a
//! `throw`, so the callee is analyzed as its own ordered body, with its own
//! call-site arena, in the caller's argument environment.

use crate::ir::{CallSite, FunctionBody};
use crate::value::{AbstractValue, LanguageProfile};

/// How a callee can complete, as the *caller* must see it.
#[derive(Debug, Clone, PartialEq)]
pub enum CallOutcome {
    /// At least one normal path returns this value.
    Returns(AbstractValue),
    /// Every normal path returns without a value (`void`).
    Void,
    /// No normal path at all: every path throws, or no exit is reachable. The
    /// caller's normal continuation after the call is unreachable.
    NoNormal,
    /// The body is not available (unresolved callee, unsupported shape, an
    /// overload that could not be identified): the call may return anything and
    /// may throw. This is **not** `NoNormal`.
    Unknown,
    /// A recursion/budget cut-off: the summary is not a proof of absence.
    Cutoff,
}

impl CallOutcome {
    /// The value the call site evaluates to. A call with no normal completion
    /// is the bottom value, which cuts the caller's path.
    #[must_use]
    pub fn value(&self) -> AbstractValue {
        match self {
            Self::Returns(value) => value.clone(),
            Self::Void | Self::Unknown | Self::Cutoff => AbstractValue::Unknown,
            Self::NoNormal => AbstractValue::Unreachable,
        }
    }

    /// Whether the caller's normal continuation is reachable after the call.
    #[must_use]
    pub fn may_return_normally(&self) -> bool {
        !matches!(self, Self::NoNormal)
    }

    /// A short stable label for reports and tests.
    #[must_use]
    pub fn describe(&self) -> &'static str {
        match self {
            Self::Returns(_) => "returns",
            Self::Void => "void",
            Self::NoNormal => "no_normal_return",
            Self::Unknown => "unknown_body",
            Self::Cutoff => "recursion_cutoff",
        }
    }

    /// Join two visits to the same call point into the outcome a reporter must
    /// show: the same outcome when they agree, and "may return anything" when
    /// they do not. The *guarding* use is always the per-visit outcome; this
    /// join must never turn a returning visit into a proven absence.
    #[must_use]
    pub fn join(&self, other: &Self) -> Self {
        if self == other {
            return self.clone();
        }
        match (self, other) {
            (Self::Returns(a), Self::Returns(b)) => Self::Returns(a.join(b)),
            _ => Self::Unknown,
        }
    }
}

/// One project-local callee body the analyzer may enter.
///
/// `file` is the callee's own project-relative file: a nested call is resolved
/// in *that* file, not in the caller's, so two same-named helpers in different
/// files never share a body.
pub struct CalleeBody<'a> {
    pub body: &'a FunctionBody,
    pub callsites: &'a [CallSite],
    pub param_names: &'a [String],
    pub file: &'a str,
    pub profile: LanguageProfile,
}

/// Resolve a callee name *written in `caller_file`* to its lowered body.
///
/// Returning `None` means "no body available here", which the analyzer records
/// as [`CallOutcome::Unknown`]: not a proof that the callee does not return.
pub trait CallTargetProvider {
    fn body_of(&self, caller_file: &str, callee: &str, arity: usize) -> Option<CalleeBody<'_>>;
}
