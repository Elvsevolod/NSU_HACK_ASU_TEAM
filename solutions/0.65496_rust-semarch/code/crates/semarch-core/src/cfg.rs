//! Minimal CFG construction and guard policy.
//!
//! v0 policy: a guard is a condition with two outgoing arms. The analysis of
//! *which* arm is taken (branch truth) is a scenario decision producing a
//! [`GuardVerdict`]; "unknown" is a verdict, never silently "false". A
//! `ProvesFalse` verdict on a path marks the guarded effects `Excluded` with
//! evidence — the only legal way to turn an effect off.
//!
//! [`linear_cfg`] is the legacy flat builder: it exists for the old API and is
//! superseded by the ordered bodies of [`crate::ir::FunctionBody`] built with
//! [`crate::lowering::BodyBuilder`], where a false arm is a real block rather
//! than the function exit.

use serde::{Deserialize, Serialize};

use crate::ir::{Action, Cfg, CfgBlock, Effect, Evidence, EvidenceStatus, Guard};
use crate::ids::BlockId;
use crate::value::{AbstractValue, LanguageProfile, Truth};

/// Verdict of a guard on a concrete path.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GuardVerdict {
    /// Condition provably holds on this path (e.g. constant literal).
    ProvesTrue,
    /// Condition provably does not hold on this path. The guarded branch's
    /// semantic effects are excluded with evidence, not deleted.
    ProvesFalse,
    /// No decision (`unknown != false`).
    Unknown,
}

/// Build a minimal straight-line CFG: `entry -> g0 -> .. -> body -> exit`,
/// every guard block branching its `false` arm to `exit` (v0: no structural
/// if/loop graphs yet — guard facts stay attached to their blocks).
#[must_use]
pub fn linear_cfg(function: crate::ids::FunctionId, guards: Vec<Guard>) -> Cfg {
    let mut cfg = Cfg {
        function,
        ..Cfg::default()
    };
    let n_guards = guards.len() as u32;
    let body = BlockId::from_raw(n_guards); // body block after all guard blocks
    let exit = BlockId::from_raw(n_guards + 1);

    cfg.entry = if n_guards == 0 { Some(body) } else { Some(BlockId::from_raw(0)) };
    for (i, g) in guards.into_iter().enumerate() {
        let i = i as u32;
        let next = if i + 1 < n_guards { BlockId::from_raw(i + 1) } else { body };
        cfg.blocks.push(CfgBlock {
            id: BlockId::from_raw(i),
            guard: Some(g.id),
            true_succ: Some(next),
            false_succ: Some(exit),
            actions: Vec::new(),
        });
    }
    cfg.guards = Vec::new(); // guards stay attached to their blocks in v0
    cfg.blocks.push(CfgBlock {
        id: body,
        guard: None,
        true_succ: Some(exit),
        false_succ: None,
        actions: vec![Action::Return { value: None }],
    });
    cfg.blocks.push(CfgBlock { id: exit, guard: None, true_succ: None, false_succ: None, actions: Vec::new() });
    cfg.exit = Some(exit);
    cfg
}

/// Evaluate what a condition value proves under a language profile.
///
/// Only the profile's own truthiness rules decide; everything else is
/// [`GuardVerdict::Unknown`]. In particular the Java profile decides only on a
/// boolean, because `if (0)` is not a Java program and reading it as "false"
/// would be a claim about a program that cannot exist.
#[must_use]
pub fn evaluate_condition(value: &AbstractValue, profile: &LanguageProfile) -> GuardVerdict {
    value.truth(profile).into()
}

impl From<Truth> for GuardVerdict {
    fn from(t: Truth) -> Self {
        match t {
            Truth::True => GuardVerdict::ProvesTrue,
            Truth::False => GuardVerdict::ProvesFalse,
            Truth::Unknown => GuardVerdict::Unknown,
        }
    }
}

/// Apply a guard verdict to semantic effects: `ProvesFalse` on the effect's
/// guarding path turns it into an *excluded* evidence record; other verdicts
/// leave status untouched.
pub fn apply_verdict(
    effects: &mut [(Effect, Evidence)],
    predicate: impl Fn(&Effect) -> bool,
    verdict: GuardVerdict,
    reason: &str,
) {
    match verdict {
        GuardVerdict::ProvesFalse => {
            for (effect, ev) in effects.iter_mut() {
                if predicate(effect) && ev.status != EvidenceStatus::Excluded {
                    *ev = Evidence::excluded(reason.to_owned());
                }
            }
        }
        GuardVerdict::ProvesTrue => {
            for (effect, ev) in effects.iter_mut() {
                if predicate(effect) && ev.status == EvidenceStatus::Unresolved {
                    *ev = Evidence::possible("guard_holds_on_path");
                }
            }
        }
        GuardVerdict::Unknown => {
            // unknown != false: no change.
        }
    }
}
