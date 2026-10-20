//! The engine's [`CallTargetProvider`]: it turns a callee *name written in a
//! file* into that file's lowered body (R05).
//!
//! The provider is deliberately narrow. It answers only for a name declared in
//! the same project file the call is written in, at the declared arity; a name
//! with several same-arity bodies in that file is left unresolved rather than
//! guessed, because entering the wrong overload would resume the caller with
//! another method's values. "Not resolved" is an [`Unknown`](semarch_core::invocation::CallOutcome)
//! outcome, never a proof that the callee does not return.

use semarch_core::invocation::{CallTargetProvider, CalleeBody};
use semarch_core::value::LanguageProfile;

use crate::bodies::BodyIndex;

/// Adapter over a built [`BodyIndex`].
pub struct BodyProvider<'a> {
    bodies: &'a BodyIndex,
}

impl<'a> BodyProvider<'a> {
    #[must_use]
    pub fn new(bodies: &'a BodyIndex) -> Self {
        Self { bodies }
    }
}

impl CallTargetProvider for BodyProvider<'_> {
    fn body_of(&self, caller_file: &str, callee: &str, arity: usize) -> Option<CalleeBody<'_>> {
        // Line 0 never matches a declared line, so a same-name same-arity
        // overload set in one file resolves to `Ambiguous` and yields `None`
        // instead of a guess.
        let slot = self.bodies.resolve(caller_file, callee, arity, 0).into_slot()?;
        Some(CalleeBody {
            body: &slot.body,
            callsites: &slot.unit.callsites,
            param_names: &slot.param_names,
            file: &slot.unit.file,
            profile: LanguageProfile::for_language(slot.unit.language),
        })
    }
}
