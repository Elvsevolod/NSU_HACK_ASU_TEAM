//! Interning arena: the canonical home of all semantic entities.
//!
//! Functions, call sites and related facts are appended in deterministic
//! frontend order; every derived graph then references them by id, so the
//! whole index serializes to a stable byte stream (serde round-trip tests
//! guard this).

use crate::lang::Language;
use crate::{Error, FrontendError, ParsedFile, Result};

#[derive(Debug, Default)]
pub struct SemanticIndex {
    files: Vec<FileEntry>,
    pub parsed: Vec<ParsedFile>,
    pub diagnostics: Vec<FrontendError>,
    alloc: crate::Allocator,
}

#[derive(Debug, Clone)]
pub struct FileEntry {
    pub path: String,
    pub language: Language,
}

impl SemanticIndex {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Register a file (path + language) and return its dense `FileId` raw
    /// value; the id is handed to the frontend through `ParseContext`.
    pub fn add_file(&mut self, path: impl Into<String>, language: Language) -> u32 {
        let raw = self.files.len() as u32;
        self.files.push(FileEntry {
            path: path.into(),
            language,
        });
        raw
    }

    pub fn file(&self, id: u32) -> Option<&FileEntry> {
        self.files.get(id as usize)
    }

    pub fn file_path(&self, id: u32) -> Option<&str> {
        self.files.get(id as usize).map(|f| f.path.as_str())
    }

    pub fn files(&self) -> &[FileEntry] {
        &self.files
    }

    /// Parse `source` with `frontend`, integrating the result into the index.
    /// The frontend builds every span with the `FileId` carried by
    /// `ParseContext`, so no post-hoc span fixup is needed.
    ///
    /// # Errors
    /// Fails only on real parse errors. Per-source diagnostics are
    /// accumulated into `self.diagnostics`, never dropped silently.
    pub fn parse_with(
        &mut self,
        frontend: &mut dyn crate::LanguageFrontend,
        source: &str,
    ) -> Result<u32> {
        let lang = frontend.language();
        let file_raw = self.add_file("", lang);
        let mut diagnostics = Vec::new();
        let mut alloc = self.alloc;
        let mut ctx = crate::ParseContext::new(file_raw.into(), lang, &mut alloc, &mut diagnostics);
        let parsed = frontend.parse(&mut ctx, source)?;
        self.parsed.push(parsed);
        self.diagnostics.append(&mut diagnostics);
        self.alloc = alloc;
        Ok(file_raw)
    }

    /// Attach the file path after external discovery (e.g. when the frontend
    /// was fed from a fixture string without a path).
    pub fn set_file_path(&mut self, id: u32, path: impl Into<String>) {
        let slot = &mut self.files[id as usize];
        slot.path = path.into();
    }

    /// Mutable allocator (e.g. CFG block ids allocated during analysis).
    pub fn alloc_mut(&mut self) -> &mut crate::Allocator {
        &mut self.alloc
    }

    /// Snapshot of allocator counters (for deterministic round-trip checks).
    pub const fn alloc(&self) -> crate::Allocator {
        self.alloc
    }
}

/// Round-trip a serde type through JSON (T02 acceptance helper).
///
/// # Errors
/// Serialization of IR types must not fail; a failure is a bug.
pub fn roundtrip_json<T: serde::Serialize + serde::de::DeserializeOwned>(
    value: &T,
) -> Result<T> {
    let text = serde_json::to_vec(value).map_err(Error::Json)?;
    serde_json::from_slice(&text).map_err(Error::Json)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::lang::Language;

    #[test]
    fn add_file_ids_are_dense_and_lookup_works() {
        let mut idx = SemanticIndex::new();
        let a = idx.add_file("a.java", Language::Java);
        let b = idx.add_file("b.py", Language::Python);
        assert_eq!(a, 0);
        assert_eq!(b, 1);
        assert_eq!(idx.file_path(1), Some("b.py"));
        assert_eq!(idx.file(0).map(|f| f.language), Some(Language::Java));
    }
}
