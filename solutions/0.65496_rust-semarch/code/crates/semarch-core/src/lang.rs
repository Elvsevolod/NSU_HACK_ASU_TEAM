//! Language identifier and capability matrix.
//!
//! Language support is a dense set of per-language capability flags, not a
//! "?" | "?" boolean: languages participate in analysis to the depth their
//! frontend supports.

use serde::{Deserialize, Serialize};

#[derive(
    Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub enum Language {
    Java,
    Python,
    Go,
    JavaScript,
    TypeScript,
    CSharp,
}

/// Normalized semantic fact kinds every frontend is expected to emit when the
/// language construct exists. Missing capability == fact is never emitted,
/// never silently `false`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Capability {
    Declarations,
    Parameters,
    CallSites,
    Literals,
    MemberAccess,
    Assignments,
    IfElse,
    ReturnThrow,
    BasicLoops,
    AnnotationsDecorators,
    Imports,
    SourceSpans,
}

impl Language {
    /// Stable lowercase name used in `language` serialized fields.
    pub const fn name(self) -> &'static str {
        match self {
            Language::Java => "java",
            Language::Python => "python",
            Language::Go => "go",
            Language::JavaScript => "javascript",
            Language::TypeScript => "typescript",
            Language::CSharp => "c_sharp",
        }
    }

    /// Source-file extension mapping used by ProjectDiscovery. Type of
    /// extension may map to one language only in v0 (`.h` C/C++ is out of tier).
    pub fn from_extension(ext: &str) -> Option<Language> {
        match ext {
            "java" => Some(Language::Java),
            "py" => Some(Language::Python),
            "go" => Some(Language::Go),
            "js" | "mjs" | "cjs" => Some(Language::JavaScript),
            "ts" => Some(Language::TypeScript),
            "tsx" => Some(Language::TypeScript), // tsx grammar added at T23
            "cs" => Some(Language::CSharp),
            _ => None,
        }
    }
}
