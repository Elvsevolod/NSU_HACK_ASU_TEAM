//! End-to-end Train Ticket pipeline: project inputs → per-scenario prediction.
//!
//! ```text
//!   skeleton/*.json.gz ─┐
//!   targets/…/ui ───────┼─► TtGraph ─┐
//!   routes (in skeleton) ┘           ├─► Prediction ─► export::Submission
//!   scenarios/S*.json ──► EntryIndex ┘
//! ```
//!
//! The analyzer never reads `gold/`: the builder must stay independent of the
//! scored oracle (only our own measurement scripts may touch it).

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};
use std::sync::{Arc, OnceLock};

use semarch_scenario::bm25;
use semarch_scenario::scenario::Scenario;

use crate::bodies::BodyIndex;
use crate::engine::{ScenarioEngine, ScenarioOutcome, ShadowDiff};
use crate::entry::{EntryIndex, StepRanking};
use crate::graph::{Prediction, ResolutionConfig, TtGraph};
use crate::guards::{GuardIndex, scenario_features};
use crate::manifest::Diagnostic;
use crate::skeleton::Skeleton;
use crate::ui::UiOption;
use crate::{ui, TtError};

/// Tunables for one analysis run.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct AnalyzerConfig {
    /// Mechanism switches for edge resolution.
    pub resolution: ResolutionConfig,
    /// Keep entry candidates scoring at least `entry_ratio × best`.
    pub entry_ratio: f64,
    /// Hard cap on entry candidates considered per step.
    pub max_candidates: usize,
    /// Read the task package's statements about the starting point
    /// (`skeleton.context`) into the binding.
    ///
    /// On by default, because the package's context *is* an input. Off, the
    /// engine sees only the step's own prose — the mode used to show that
    /// generic silence is not absence.
    pub use_context: bool,
}

impl Default for AnalyzerConfig {
    fn default() -> Self {
        Self {
            resolution: ResolutionConfig::default(),
            entry_ratio: 0.95,
            max_candidates: 4,
            use_context: true,
        }
    }
}

/// Options that control how a project is loaded.
///
/// The only option is deliberately about *honesty*: whether a missing project
/// checkout (which silently removes optional-feature guard knowledge) is a hard
/// error or an explicit degradation recorded in [`TtAnalyzer::diagnostics`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct LoadOptions {
    /// Fail instead of degrading when project sources cannot be read, so the
    /// optional-feature guards (G6) would be unknown.
    pub require_sources: bool,
}

/// A loaded, index-ready Train Ticket project.
pub struct TtAnalyzer {
    pub skeleton: Skeleton,
    pub graph: TtGraph,
    pub entries: EntryIndex,
    /// Number of UI facts folded into the entry index (diagnostics).
    pub ui_facts: usize,
    /// UI source directory used (diagnostics).
    pub ui_root: PathBuf,
    /// Static UI option values (`<select>` options), used by the value binder.
    pub ui_options: Vec<UiOption>,
    /// Lowered bodies of the project sources, built on first semantic use.
    bodies: OnceLock<Arc<BodyIndex>>,
    /// Project checkout the skeleton paths are relative to (diagnostics).
    pub target_root: PathBuf,
    /// Skeleton file that was loaded (input fingerprint for the run manifest).
    pub skeleton_path: PathBuf,
    /// Content fingerprint of the Java sources behind the G6 guard knowledge;
    /// empty when the sources were unavailable.
    pub source_hash: String,
    /// Non-fatal degradations the loader had to accept.
    pub diagnostics: Vec<Diagnostic>,
    /// Challenge root the analyzer was loaded from.
    base: PathBuf,
}

impl TtAnalyzer {
    /// Load a contest workspace (`tt-challenge/`): skeleton, targets, UI.
    ///
    /// Equivalent to [`TtAnalyzer::load_with`] with [`LoadOptions::default`]:
    /// a missing project checkout degrades to "no guard knowledge" and is
    /// recorded in [`TtAnalyzer::diagnostics`].
    ///
    /// # Errors
    /// [`TtError::Missing`] when the skeleton or scenario inputs are absent;
    /// propagates IO/JSON errors from the loaders.
    pub fn load(challenge_root: impl AsRef<Path>) -> Result<Self, TtError> {
        Self::load_with(challenge_root, &LoadOptions::default())
    }

    /// Load with explicit options. See [`LoadOptions`].
    ///
    /// # Errors
    /// As [`TtAnalyzer::load`]; additionally a [`TtError`] when
    /// `opts.require_sources` is set and the project checkout cannot be read.
    pub fn load_with(
        challenge_root: impl AsRef<Path>,
        opts: &LoadOptions,
    ) -> Result<Self, TtError> {
        let root = challenge_root.as_ref();
        let sk_path = find_skeleton(root)?;
        let skeleton = Skeleton::load(&sk_path)?;
        let target_root = find_target_root(root, &skeleton.project);
        let mut diagnostics: Vec<Diagnostic> = Vec::new();
        // Project sources give the optional-feature guards (G6). A missing
        // checkout is never a silent success: either it is a hard error
        // (strict mode) or an explicit degradation.
        let mut source_hash = String::new();
        let graph = match GuardIndex::build(&target_root) {
            Ok(guards) => {
                source_hash = guards.source_hash.clone();
                TtGraph::build(&skeleton).with_guards(guards)
            }
            Err(e) => {
                if opts.require_sources {
                    return Err(e);
                }
                diagnostics.push(Diagnostic::degraded(
                    "guard_sources_unavailable",
                    format!(
                        "project sources under {} could not be read ({}); optional-feature guards (G6) are unknown for this run",
                        target_root.display(),
                        e
                    ),
                ));
                TtGraph::build(&skeleton)
            }
        };
        let ui_root = find_ui_root(&target_root);
        let facts = if ui_root.is_dir() {
            ui::extract(&ui_root)?
        } else {
            Vec::new()
        };
        if facts.is_empty() {
            diagnostics.push(Diagnostic::info(
                "ui_evidence_absent",
                format!(
                    "no UI request facts under {}; entry grounding falls back to route and scenario vocabulary alone",
                    ui_root.display()
                ),
            ));
        }
        let options = if ui_root.is_dir() {
            ui::extract_options(&ui_root)?
        } else {
            Vec::new()
        };
        let entries = EntryIndex::build(&skeleton, &graph, &facts);
        Ok(Self {
            skeleton,
            graph,
            entries,
            ui_facts: facts.len(),
            ui_root,
            ui_options: options,
            bodies: OnceLock::new(),
            target_root,
            skeleton_path: sk_path,
            source_hash,
            diagnostics,
            base: root.to_path_buf(),
        })
    }

    /// Challenge root the analyzer was loaded from.
    #[must_use]
    pub fn root(&self) -> &Path {
        &self.base
    }

    /// Predict the execution subgraph of one scenario.
    #[must_use]
    pub fn analyze(&self, scenario: &Scenario, cfg: &AnalyzerConfig) -> Prediction {
        let rankings = self.entries.rank_scenario(scenario);
        let entries = self.entries.select_scenario(
            scenario,
            &rankings,
            cfg.entry_ratio,
            cfg.max_candidates,
        );
        let engaged = scenario_features(scenario);
        self.graph.predict(&entries, cfg.resolution, &engaged)
    }

    /// Lowered bodies of the project sources, built once on first use.
    ///
    /// Parsing the whole checkout is only needed by the semantic engine, so
    /// the contest path never pays for it.
    ///
    /// # Errors
    /// Propagates discovery/parse failures when the sources cannot be read.
    pub fn bodies(&self) -> Result<&Arc<BodyIndex>, TtError> {
        if let Some(b) = self.bodies.get() {
            return Ok(b);
        }
        let built = Arc::new(BodyIndex::build(&self.target_root)?);
        Ok(self.bodies.get_or_init(|| built))
    }

    /// Resolution switches the semantic engine uses.
    ///
    /// The engine decides call sites by *value*, so the lexical feature
    /// pruning (G6) is off: a call site behind an optional feature stays live
    /// unless the bound request proves it dead.
    #[must_use]
    pub fn semantic_resolution(&self, cfg: &AnalyzerConfig) -> ResolutionConfig {
        ResolutionConfig {
            feature_guards: false,
            ..cfg.resolution
        }
    }

    /// Run the scenario state engine over one scenario.
    ///
    /// # Errors
    /// Propagates source parsing failures.
    pub fn semantic_run(
        &self,
        scn: &Scenario,
        cfg: &AnalyzerConfig,
    ) -> Result<ScenarioOutcome, TtError> {
        let bodies = self.bodies()?;
        let rankings = self.entries.rank_scenario(scn);
        let selections =
            self.entries
                .select_per_step(scn, &rankings, cfg.entry_ratio, cfg.max_candidates);
        let engine = ScenarioEngine::new(
            &self.graph,
            bodies,
            &self.skeleton,
            &self.ui_options,
            self.semantic_resolution(cfg),
            cfg.use_context,
        );
        Ok(engine.run(scn, &rankings, &selections, &self.entries))
    }

    /// The semantic prediction of one scenario, in the answer's own shape.
    ///
    /// # Errors
    /// Propagates source parsing failures.
    pub fn semantic_predict(
        &self,
        scn: &Scenario,
        cfg: &AnalyzerConfig,
    ) -> Result<Prediction, TtError> {
        Ok(self.semantic_run(scn, cfg)?.prediction)
    }

    /// Diff the legacy answer and the semantic engine for one scenario.
    ///
    /// # Errors
    /// Propagates source parsing failures.
    pub fn shadow_run(&self, scn: &Scenario, cfg: &AnalyzerConfig) -> Result<ShadowDiff, TtError> {
        let legacy = self.analyze(scn, cfg);
        let bodies = self.bodies()?;
        let rankings = self.entries.rank_scenario(scn);
        let selections =
            self.entries
                .select_per_step(scn, &rankings, cfg.entry_ratio, cfg.max_candidates);
        let engine = ScenarioEngine::new(
            &self.graph,
            bodies,
            &self.skeleton,
            &self.ui_options,
            self.semantic_resolution(cfg),
            cfg.use_context,
        );
        let outcome = engine.run(scn, &rankings, &selections, &self.entries);
        let engaged = scenario_features(scn);
        Ok(engine.shadow(scn, &legacy, &outcome, &engaged))
    }

    /// Shadow diffs of every scenario file, sorted by scenario id.
    ///
    /// # Errors
    /// Propagates the same errors as [`Self::analyze_all`].
    pub fn shadow_all(&self, cfg: &AnalyzerConfig) -> Result<Vec<ShadowDiff>, TtError> {
        let mut out = Vec::new();
        for (_, _, scn) in self.analyze_all(cfg)? {
            out.push(self.shadow_run(&scn, cfg)?);
        }
        Ok(out)
    }

    /// Predict from an explicit entry set (used by gates and ablations).
    #[must_use]
    pub fn predict_from_entries(
        &self,
        entries: &[String],
        engaged: &std::collections::HashSet<String>,
        cfg: &AnalyzerConfig,
    ) -> Prediction {
        self.graph.predict(entries, cfg.resolution, engaged)
    }

    /// Per-step entry ranking, for explainability and gate tests.
    #[must_use]
    pub fn rank(&self, scenario: &Scenario) -> Vec<StepRanking> {
        self.entries.rank_scenario(scenario)
    }

    /// Analyze every scenario file in `scenarios/` (sorted by id).
    ///
    /// # Errors
    /// [`TtError::Missing`] if the directory has no scenario files.
    pub fn analyze_all(&self, cfg: &AnalyzerConfig) -> Result<Vec<(String, Prediction, Scenario)>, TtError> {
        let dir = self
            .scenarios_dir()
            .ok_or_else(|| TtError::Missing("scenarios/".to_owned()))?;
        let mut files: Vec<PathBuf> = std::fs::read_dir(&dir)
            .map_err(TtError::Io)?
            .flatten()
            .map(|e| e.path())
            .filter(|p| p.extension().is_some_and(|e| e == "json"))
            .collect();
        files.sort();
        if files.is_empty() {
            return Err(TtError::Missing(format!("{}/ contains no scenarios", dir.display())));
        }
        let mut out = Vec::new();
        for f in files {
            let text = std::fs::read_to_string(&f).map_err(TtError::Io)?;
            let scn = Scenario::from_json(&text)?;
            let pred = self.analyze(&scn, cfg);
            out.push((scn.id.clone(), pred, scn));
        }
        Ok(out)
    }

    /// Human-readable explanation of the entry grounding for one scenario.
    #[must_use]
    pub fn explain(&self, scenario: &Scenario, cfg: &AnalyzerConfig) -> String {
        let mut out = String::new();
        let rankings = self.entries.rank_scenario(scenario);
        for r in &rankings {
            out.push_str(&format!("step {} ({}):\n", r.step, action_of(scenario, r.step)));
            for c in r.ranked.iter().take(5) {
                let e = &self.entries.endpoints[c.doc];
                out.push_str(&format!(
                    "    {:.3} [{}] {} {} ({})\n",
                    c.score, e.http, e.class, e.path, e.module
                ));
            }
        }
        let entries = self.entries.select_scenario(
            scenario,
            &rankings,
            cfg.entry_ratio,
            cfg.max_candidates,
        );
        out.push_str(&format!("selected entries: {}\n", entries.len()));
        for e in &entries {
            out.push_str(&format!("  {e}\n"));
        }
        let engaged = scenario_features(scenario);
        out.push_str(&format!(
            "scenario features: {}\n",
            {
                let mut f: Vec<&str> = engaged.iter().map(String::as_str).collect();
                f.sort_unstable();
                f.join(" ")
            }
        ));
        let pred = self.graph.predict(&entries, cfg.resolution, &engaged);
        out.push_str(&format!(
            "prediction: executes={} calls={} remote={} data={}\n",
            pred.executes.len(),
            pred.calls.len(),
            pred.remote.len(),
            pred.data.len()
        ));
        out
    }

    /// Distinct method ids in the prediction that are *not* skeleton vertices.
    #[must_use]
    pub fn unknown_ids(&self, pred: &Prediction) -> BTreeSet<String> {
        let mut out = BTreeSet::new();
        for m in &pred.executes {
            if !self.graph.method_ids.contains(m) {
                out.insert(m.clone());
            }
        }
        out
    }

    /// BM25 ranking of endpoints for arbitrary query text (tests/diagnostics).
    #[must_use]
    pub fn search(&self, query: &str) -> Vec<bm25::Ranked> {
        let q = semarch_scenario::text::synonyms(&semarch_scenario::text::tokenize(query))
            .into_iter()
            .collect::<Vec<_>>();
        self.entries.rank_query(&q)
    }

    fn scenarios_dir(&self) -> Option<PathBuf> {
        let d = self.base.join("scenarios");
        d.is_dir().then_some(d)
    }
}

fn action_of(scn: &Scenario, n: u32) -> String {
    scn.steps
        .iter()
        .find(|s| s.n == n)
        .map(|s| s.action.clone())
        .unwrap_or_default()
}

/// Locate `skeleton/*.json(.gz)` under a challenge root.
fn find_skeleton(root: &Path) -> Result<PathBuf, TtError> {
    let dir = root.join("skeleton");
    let mut candidates: Vec<PathBuf> = std::fs::read_dir(&dir)
        .map_err(|_| TtError::Missing(format!("{}/skeleton", root.display())))?
        .flatten()
        .map(|e| e.path())
        .filter(|p| {
            let n = p.file_name().and_then(|s| s.to_str()).unwrap_or("");
            n.contains("json")
        })
        .collect();
    candidates.sort();
    candidates
        .into_iter()
        .next()
        .ok_or_else(|| TtError::Missing(format!("{}/skeleton has no JSON skeleton", root.display())))
}

/// Locate the project checkout the skeleton's `file` fields are relative to:
/// `targets/<skeleton project>`, falling back to the only subdirectory there.
fn find_target_root(root: &Path, project: &str) -> PathBuf {
    let targets = root.join("targets");
    let named = targets.join(project);
    if !project.is_empty() && named.is_dir() {
        return named;
    }
    if let Ok(entries) = std::fs::read_dir(&targets) {
        let mut dirs: Vec<PathBuf> = entries
            .flatten()
            .map(|e| e.path())
            .filter(|p| p.is_dir())
            .collect();
        dirs.sort();
        if let Some(first) = dirs.into_iter().next() {
            return first;
        }
    }
    targets
}

/// Locate the web-client root inside the project checkout (any directory
/// whose name mentions `ui`).
fn find_ui_root(target_root: &Path) -> PathBuf {
    if let Ok(entries) = std::fs::read_dir(target_root) {
        for e in entries.flatten() {
            let name = e.file_name().to_string_lossy().into_owned();
            if name.contains("ui") && e.path().is_dir() {
                return e.path();
            }
        }
    }
    target_root.to_path_buf()
}
