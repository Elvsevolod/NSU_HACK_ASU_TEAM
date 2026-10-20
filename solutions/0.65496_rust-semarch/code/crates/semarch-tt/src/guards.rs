//! Scenario-conditioned optional features.
//!
//! # Why this exists
//!
//! Train Ticket handlers switch *optional* capabilities on with a flag taken
//! from the request: a verification code, a food order, an assurance, a
//! consignment, a date-range filter. The body of such a branch only runs when
//! the flag arrives set. A static answer that ignores the flag over-approximates
//! every scenario with every optional feature.
//!
//! The scenario is the specification of what the user asked for, so the rule is
//! a vocabulary match: **a guarded region whose condition tests one feature
//! executes only if the scenario mentions that feature.**
//!
//! # What counts as the guarded region
//!
//! The region is the condition's `then` body, never the whole construct:
//!
//! * the **predicate** is evaluated before the branch decision, so a call site
//!   inside it always runs and must not be pruned;
//! * the **`else` branch** runs when the predicate does *not* hold; "feature not
//!   engaged" is not "feature absent" (`unknown != false`), so it is left alone;
//! * a **`do { … } while (…)` body** runs at least once, so its condition
//!   guards nothing.
//!
//! The region is a *line* range because that is what the skeleton gives for a
//! call site. When the body's first row is also the predicate's last row (the
//! usual `if (cond) {`), that shared row is excluded: a call there cannot be
//! placed in the body from the line alone. This trades a hypothetical one-line
//! `if (cond) call();` prune for never killing a live predicate call.
//!
//! # Deliberate narrowness
//!
//! Only *single* predicate leaves are treated as feature tests:
//!
//! * a call to a boolean-looking predicate (`isEnableFood()`, `hasFood()`);
//! * an emptiness/nullity test over one value (`!isEmpty(verifyCode)`,
//!   `x != null` where `x` is not a getter);
//!
//! and combinations of the above with `!` or a literal comparison. A condition
//! that compares *business state* (`order.getStatus() == 1`), a disjunction of
//! several independent flags (a filter composition, true whenever any one flag
//! is set) or a bare variable is left alone: the scenario does not say which
//! way such a condition resolves, so the analysis stays conservative. Each of
//! those shapes is a real possibility in the code base, and pruning them would
//! trade honest unknowns for wrong answers.

use std::collections::{HashMap, HashSet};
use std::path::Path;

use semarch_core::ids::CallSiteId;
use semarch_core::{
    Allocator, BinaryOp, CallSite, Language, LanguageFrontend, ParseContext, UnaryOp, ValueExpr,
};
use semarch_frontend_java::JavaFrontend;
use semarch_scenario::text;
use semarch_scenario::scenario::Scenario;

use crate::TtError;

/// A guarded line range that is only live when one of its features is engaged.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FeatureGuard {
    /// 1-based first line of the guarded body (`then` branch only).
    pub start_line: u32,
    /// 1-based last line of the guarded body (`then` branch only).
    pub end_line: u32,
    /// Normalized feature tokens named by the condition (non-empty).
    pub features: Vec<String>,
}

/// Feature guards of a project, keyed by project-relative source file.
#[derive(Debug, Clone, Default)]
pub struct GuardIndex {
    by_file: HashMap<String, Vec<FeatureGuard>>,
    /// Diagnostics: conditions that *looked* like feature tests, for auditing.
    pub source_files: usize,
    /// Order-free content fingerprint of every Java source file that was read.
    /// Empty when the index is built by hand (tests); the loader fills it so a
    /// run manifest can name the exact sources behind the guard knowledge.
    pub source_hash: String,
}

impl GuardIndex {
    /// Parse every Java source under `root` and collect feature guards.
    ///
    /// `root` must be the directory the skeleton's `file` fields are relative
    /// to (the project checkout). Only syntax facts are read; nothing is run.
    ///
    /// # Errors
    /// Propagates IO failures and frontend failures (a broken grammar must be
    /// loud, never a silent empty index).
    pub fn build(root: &Path) -> Result<Self, TtError> {
        let root = root.canonicalize().map_err(TtError::Io)?;
        let files = semarch_core::ProjectDiscovery::new(&root).discover()?;
        let mut frontend = JavaFrontend::new()?;
        let mut index = Self::default();
        let mut hashed: Vec<(String, Vec<u8>)> = Vec::new();
        for f in files {
            if f.language != Language::Java {
                continue;
            }
            let Ok(rel) = f.path.strip_prefix(&root) else {
                continue;
            };
            let rel = rel.to_string_lossy().replace('\\', "/");
            let source = std::fs::read_to_string(&f.path).map_err(TtError::Io)?;
            hashed.push((rel.clone(), source.clone().into_bytes()));
            let mut alloc = Allocator::default();
            let mut diagnostics = Vec::new();
            let mut ctx = ParseContext::new(
                semarch_core::ids::FileId::from_raw(0),
                Language::Java,
                &mut alloc,
                &mut diagnostics,
            );
            let parsed = frontend.parse(&mut ctx, &source)?;
            index.source_files += 1;
            index.absorb(&rel, &parsed);
        }
        let pairs: Vec<(&str, &[u8])> =
            hashed.iter().map(|(n, b)| (n.as_str(), b.as_slice())).collect();
        index.source_hash = crate::hash::set_hash(pairs);
        Ok(index)
    }

    fn absorb(&mut self, rel: &str, parsed: &semarch_core::ParsedFile) {
        if parsed.guard_conditions.is_empty() {
            return;
        }
        let sites: HashMap<CallSiteId, &CallSite> =
            parsed.callsites.iter().map(|c| (c.id, c)).collect();
        let mut guards = Vec::new();
        for g in &parsed.guard_conditions {
            // Only a delimited *guarded body* (`then` branch) can be a
            // protected region. The predicate is evaluated before the branch
            // decision, and the `else` branch runs when the predicate does not
            // hold, so neither is protected by this condition. A `do { … }
            // while` body always runs at least once, so it has no `then_span`.
            let Some(body) = g.then_span else {
                continue;
            };
            let Some(features) = feature_test(&g.condition, &sites) else {
                continue;
            };
            if features.is_empty() {
                continue;
            }
            guards.push(FeatureGuard {
                start_line: guarded_first_row(&g.span, body),
                end_line: body.end_row + 1,
                features,
            });
        }
        if !guards.is_empty() {
            guards.sort_by_key(|g| (g.start_line, g.end_line));
            self.by_file.insert(rel.to_owned(), guards);
        }
    }

    /// Whether a call site at `file:line` is protected by a feature the
    /// scenario does not engage.
    ///
    /// A nested guard that is *engaged* does not rescue a call site from an
    /// outer guard that is not: both conditions must hold for the statement to
    /// run, so one disabled feature is enough to make it dead.
    #[must_use]
    pub fn blocks(&self, file: &str, line: u32, engaged: &HashSet<String>) -> bool {
        !self.blocking_features(file, line, engaged).is_empty()
    }

    /// Feature sets of the guards that kill `file:line` for this scenario.
    ///
    /// Empty when the call site runs. Reports *which* features would revive it,
    /// which is what the audit trail needs to explain a missing edge.
    #[must_use]
    pub fn blocking_features(
        &self,
        file: &str,
        line: u32,
        engaged: &HashSet<String>,
    ) -> Vec<Vec<String>> {
        let Some(guards) = self.by_file.get(file) else {
            return Vec::new();
        };
        guards
            .iter()
            .filter(|g| line >= g.start_line && line <= g.end_line)
            .filter(|g| {
                !g.features
                    .iter()
                    .any(|f| engaged.iter().any(|e| text::related(f, e)))
            })
            .map(|g| g.features.clone())
            .collect()
    }

    /// Total number of guards (diagnostics).
    #[must_use]
    pub fn len(&self) -> usize {
        self.by_file.values().map(Vec::len).sum()
    }

    /// Whether the index holds no guard at all.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

/// First 0-based row that belongs to the guarded body.
///
/// `body` is the consequence block (it starts at `{`, usually on the predicate's
/// own row). A call site is located by line only, so a row shared with the
/// predicate cannot be attributed to the body: it is skipped.
fn guarded_first_row(predicate: &semarch_core::SourceSpan, body: semarch_core::SourceSpan) -> u32 {
    let after_predicate = predicate.end_row + 1;
    // 1-based line of the first row that is unambiguously inside the body.
    body.start_row.max(after_predicate) + 1
}

/// The feature tokens a *single-predicate* guard tests, or `None` when the
/// condition is not a feature test in the sense documented above.
fn feature_test(
    expr: &ValueExpr,
    sites: &HashMap<CallSiteId, &CallSite>,
) -> Option<Vec<String>> {
    match expr {
        ValueExpr::Unary {
            op: UnaryOp::Not,
            operand,
        } => feature_test(operand, sites),
        // One flag compared against a literal (`x != null`, `flag == true`).
        ValueExpr::Binary {
            op: BinaryOp::Eq | BinaryOp::Ne,
            lhs,
            rhs,
        } => {
            let lhs_lit = is_literal(lhs);
            let rhs_lit = is_literal(rhs);
            match (lhs_lit, rhs_lit) {
                (false, true) => feature_test(lhs, sites),
                (true, false) => feature_test(rhs, sites),
                _ => None,
            }
        }
        ValueExpr::CallResult { callsite } => predicate_feature(sites.get(callsite).copied()?),
        // A disjunction/conjunction mixes independent flags into a filter
        // composition; see the module docs.
        _ => None,
    }
}

fn is_literal(e: &ValueExpr) -> bool {
    matches!(
        e,
        ValueExpr::Bool { .. }
            | ValueExpr::Null
            | ValueExpr::Int { .. }
            | ValueExpr::Str { .. }
            | ValueExpr::Float { .. }
    )
}

/// Feature tokens named by one predicate call site.
fn predicate_feature(cs: &CallSite) -> Option<Vec<String>> {
    let name = cs.callee.rsplit('.').next().unwrap_or(&cs.callee);
    if name.is_empty() || !has_predicate_prefix(name) {
        return None;
    }
    let own = text::feature_tokens(name);
    if !own.is_empty() {
        // `isEnableFood()` / `hasFood()`: the flag names its feature.
        return Some(own);
    }
    // `isEmpty(x)` / `isNull(x)`: the tested value names the feature.
    let mut idents = Vec::new();
    for a in &cs.args {
        collect_idents(a, &mut idents);
    }
    let mut toks: Vec<String> = idents.iter().flat_map(|i| text::feature_tokens(i)).collect();
    toks.sort();
    toks.dedup();
    (!toks.is_empty()).then_some(toks)
}

/// Whether the name starts with a boolean *predicate* word (`is`, `has`,
/// `enable`) — getters are excluded: `getStatus()` returns business state, not
/// a capability flag.
fn has_predicate_prefix(name: &str) -> bool {
    ["is", "has", "have", "enable", "should", "can", "must"].iter().any(|p| {
        name.len() > p.len()
            && name[..p.len()].eq_ignore_ascii_case(p)
            && name[p.len()..]
                .chars()
                .next()
                .is_some_and(|c| c.is_uppercase())
    })
}

fn collect_idents(e: &ValueExpr, out: &mut Vec<String>) {
    match e {
        ValueExpr::Symbolic { name } => out.push(name.clone()),
        ValueExpr::Field { base, name } => {
            out.push(name.clone());
            collect_idents(base, out);
        }
        _ => {}
    }
}

/// Feature tokens a scenario engages.
///
/// The whole scenario is used, not one step: the scenario is the user's intent
/// for the session, and an optional capability engaged anywhere in it is
/// described in the prose that surrounds the step that uses it.
#[must_use]
pub fn scenario_features(scn: &Scenario) -> HashSet<String> {
    let mut blob = String::new();
    blob.push_str(&scn.title);
    blob.push(' ');
    blob.push_str(&scn.description);
    for s in &scn.steps {
        blob.push(' ');
        blob.push_str(&s.action);
    }
    let tokens = text::tokenize(&blob);
    text::synonyms(&tokens).into_iter().collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use semarch_core::SourceSpan;

    fn span() -> SourceSpan {
        SourceSpan {
            file: semarch_core::ids::FileId::from_raw(0),
            start_byte: 0,
            end_byte: 0,
            start_row: 0,
            start_col: 0,
            end_row: 0,
            end_col: 0,
        }
    }

    fn call(callee: &str, args: Vec<ValueExpr>) -> CallSite {
        CallSite {
            id: CallSiteId::from_raw(1),
            callee: callee.to_owned(),
            receiver: None,
            args,
            span: span(),
            name_span: None,
        }
    }

    #[test]
    fn emptiness_test_is_a_feature() {
        let cs = call("isEmpty", vec![ValueExpr::symbolic("verifyCode")]);
        let sites = HashMap::from([(cs.id, &cs)]);
        let cond = ValueExpr::Unary {
            op: UnaryOp::Not,
            operand: Box::new(ValueExpr::CallResult { callsite: cs.id }),
        };
        assert_eq!(
            feature_test(&cond, &sites),
            Some(vec!["code".to_owned(), "verify".to_owned()])
        );
    }

    #[test]
    fn boolean_getter_names_its_feature() {
        let cs = call("isEnableStateQuery", vec![]);
        let sites = HashMap::from([(cs.id, &cs)]);
        let cond = ValueExpr::CallResult { callsite: cs.id };
        assert_eq!(
            feature_test(&cond, &sites),
            Some(vec!["state".to_owned(), "query".to_owned()])
        );
    }

    #[test]
    fn business_state_and_flag_disjunctions_stay_unpruned() {
        let a = call("isEnableStateQuery", vec![]);
        let b = call("isEnableBoughtDateQuery", vec![]);
        let sites = HashMap::from([(a.id, &a), (b.id, &b)]);
        let disjunction = ValueExpr::Binary {
            op: BinaryOp::Or,
            lhs: Box::new(ValueExpr::CallResult { callsite: a.id }),
            rhs: Box::new(ValueExpr::CallResult { callsite: b.id }),
        };
        assert_eq!(feature_test(&disjunction, &sites), None);

        let status = call("getStatus", vec![]);
        let sites = HashMap::from([(status.id, &status)]);
        let compare = ValueExpr::Binary {
            op: BinaryOp::Eq,
            lhs: Box::new(ValueExpr::CallResult { callsite: status.id }),
            rhs: Box::new(ValueExpr::Int { value: 1 }),
        };
        assert_eq!(feature_test(&compare, &sites), None);

        let bare = ValueExpr::symbolic("hasPermission");
        assert_eq!(feature_test(&bare, &sites), None);
    }

    #[test]
    fn blocks_only_when_the_feature_is_absent() {
        let mut index = GuardIndex::default();
        index.by_file.insert(
            "svc/A.java".to_owned(),
            vec![FeatureGuard {
                start_line: 10,
                end_line: 20,
                features: vec!["verify".to_owned(), "code".to_owned()],
            }],
        );
        let absent: HashSet<String> = ["login".to_owned(), "contact".to_owned()]
            .into_iter()
            .collect();
        assert!(index.blocks("svc/A.java", 15, &absent));
        // "verification code" engages the guard: the two vocabularies meet on
        // the token they share even though `verify` is not a prefix of
        // `verification`
        let present: HashSet<String> = ["verification".to_owned(), "code".to_owned()]
            .into_iter()
            .collect();
        assert!(!index.blocks("svc/A.java", 15, &present));
        // honest boundary: prose that names the concept with an irregular
        // variant only ("verification" alone) is not linked to `verifyCode`
        let oblique: HashSet<String> = ["verification".to_owned()].into_iter().collect();
        assert!(index.blocks("svc/A.java", 15, &oblique));
        // outside the guarded range nothing is pruned
        assert!(!index.blocks("svc/A.java", 21, &absent));
        assert!(!index.blocks("other/B.java", 15, &absent));
    }

    #[test]
    fn scenario_features_come_from_the_whole_scenario() {
        let scn = Scenario {
            project: "p".into(),
            id: "S".into(),
            title: "My account".into(),
            description: "Nothing is searched".into(),
            input: "text".into(),
            steps: vec![semarch_scenario::scenario::Step {
                n: 1,
                action: "Log in with username and password".into(),
            }],
        };
        let f = scenario_features(&scn);
        assert!(f.contains("login"));
        assert!(f.contains("username"));
        assert!(!f.contains("food"));
    }
}
