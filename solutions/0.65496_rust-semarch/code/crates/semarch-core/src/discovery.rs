//! Project discovery: walk a source tree `.gitignore`-aware and classify
//! files by language extension. Never runs analyzed applications; only reads
//! files.

use std::path::{Path, PathBuf};

use crate::lang::Language;

/// One discovered source file candidate.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DiscoveredFile {
    pub path: PathBuf,
    pub language: Language,
}

/// Walker over a project root.
#[derive(Debug, Clone)]
pub struct ProjectDiscovery {
    root: PathBuf,
    /// Extra glob filters to accept besides language extensions (e.g.
    /// `*.proto` for a later phase). Empty by default.
    extra_extensions: Vec<String>,
}

impl ProjectDiscovery {
    #[must_use]
    pub fn new(root: impl AsRef<Path>) -> Self {
        Self {
            root: root.as_ref().to_path_buf(),
            extra_extensions: Vec::new(),
        }
    }

    pub fn with_extra_extension(mut self, ext: impl Into<String>) -> Self {
        self.extra_extensions.push(ext.into());
        self
    }

    /// Walk the tree respecting `.gitignore`/`.ignore`, returning files that
    /// map to a Tier-A language.
    ///
    /// Order is deterministic (sorted by path). Hidden files are skipped
    /// unless they are regular language sources (`foo.java`).
    ///
    /// # Errors
    /// Fails when the root cannot be walked at all (missing directory).
    pub fn discover(&self) -> crate::Result<Vec<DiscoveredFile>> {
        let root = self
            .root
            .canonicalize()
            .map_err(|e| crate::Error::Discovery(format!("root {}: {e}", self.root.display())))?;

        let mut out = Vec::new();
        for entry in ignore::WalkBuilder::new(&root)
            .hidden(false)
            .git_ignore(true)
            .git_global(true)
            .ignore(true)
            .require_git(false) // honor .gitignore even without a .git dir
            .parents(true)
            .build()
        {
            let entry = entry
                .map_err(|e| crate::Error::Discovery(format!("walk: {e}")))?;
            if !entry.file_type().is_some_and(|t| t.is_file()) {
                continue;
            }
            let path = entry.into_path();
            let Some(ext) = path.extension().and_then(|e| e.to_str()) else {
                continue;
            };
            if self.extra_extensions.iter().any(|x| x == ext) {
                out.push(DiscoveredFile {
                    path: path.clone(),
                    // Extra extensions are protocol/config candidates; the
                    // language is undecided here.
                    language: Language::from_extension(ext)
                        .ok_or(crate::Error::Discovery(format!(
                            "extra extension {ext} must map to a language"
                        )))?,
                });
                continue;
            }
            if let Some(language) = Language::from_extension(ext) {
                out.push(DiscoveredFile { path, language });
            }
        }
        out.sort_by(|a, b| a.path.cmp(&b.path));
        Ok(out)
    }
}
