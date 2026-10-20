//! Provided project skeleton (`skeleton/*.json.gz`): typed loader + indexes.
//!
//! The skeleton is an organizer-provided artifact of the *contested project*,
//! not part of our analyzer's semantics. It is loaded here, in the Train
//! Ticket adapter crate, and never leaks into `semarch-core`: the core stays
//! project-agnostic, while this crate may hold project-specific bindings.

use std::collections::HashMap;
use std::io::Read;
use std::path::Path;

use serde::Deserialize;

use crate::TtError;

/// A skeleton vertex. The schema is deliberately *open*: every field is
/// optional and unknown fields are ignored, so a schema bump does not break
/// loading. Callers use accessors rather than pattern-matching the raw shape.
#[derive(Debug, Clone, Default, Deserialize)]
pub struct Node {
    #[serde(default)]
    pub kind: String,
    pub name: Option<String>,
    /// Owning `type:` id (methods, fields) or owning `method:` id (call sites,
    /// parameters).
    pub owner: Option<String>,
    /// Method descriptor: comma-joined *fully qualified* parameter types.
    pub descriptor: Option<String>,
    /// Method parameters as written in source (simple type names).
    #[serde(default)]
    pub params_as_written: Vec<String>,
    /// Resolved return type of a method.
    #[serde(rename = "return")]
    pub return_type: Option<String>,
    /// Return type as written in source (`Response<ArrayList<Order>>`).
    pub return_raw: Option<String>,
    #[serde(rename = "abstract", default)]
    pub is_abstract: bool,
    #[serde(default)]
    pub unresolved: bool,
    pub module: Option<String>,
    pub file: Option<String>,
    pub line: Option<u32>,
    /// 1-based **byte** column of the token the skeleton tool reports for this
    /// node. Measured against the contested project: for a method invocation it
    /// is the callee name, for a constructor call it is the `new` keyword; on
    /// the 22 source lines with non-ASCII text the four call sites whose
    /// character and byte columns differ (e.g. `TravelServiceImpl.java:451`)
    /// match the byte convention, so the skeleton column is byte-based and is
    /// converted from Tree-sitter's 0-based byte column by `+1`.
    pub col: Option<u32>,
    pub end: Option<u32>,
    #[serde(default)]
    pub annotations: Vec<Annotation>,
    // ---- call_site ----
    pub callee: Option<String>,
    pub receiver: Option<String>,
    pub receiver_type: Option<String>,
    pub arg_count: Option<u32>,
    /// Argument text. The contested skeleton writes a single string
    /// (`"(AdminBasicInfoApplication.class, args)"`); an alternate shape writes
    /// the arguments as an array, which is accepted and normalised here so a
    /// fixture skeleton can be used without weakening the loader.
    #[serde(default, deserialize_with = "string_or_seq")]
    pub args_text: Option<String>,
    #[serde(default)]
    pub string_args: Vec<String>,
    /// Owner method id of a call site, or of a parameter.
    pub method: Option<String>,
    /// Declared (fully qualified) type of a `parameter` node.
    #[serde(rename = "type")]
    pub type_: Option<String>,
    /// 0-based position of a `parameter` node in its method's parameter list.
    pub index: Option<u32>,
    #[serde(default)]
    pub method_ref: bool,
    // ---- field ----
    /// Declared type of a field as written in source (`String`, `int`).
    pub type_raw: Option<String>,
    /// Initializer as written, `null` when the field has none. Evidence for the
    /// "an omitted field is `null`" rule: a field with an initializer does not
    /// become `null` just because the request omitted it.
    #[serde(default)]
    pub init_literal: Option<String>,
    // ---- type ----
    pub fqn: Option<String>,
    pub type_kind: Option<String>,
    #[serde(default)]
    pub extends_raw: Vec<String>,
    #[serde(default)]
    pub implements_raw: Vec<String>,
    // ---- data_resource ----
    pub resource_kind: Option<String>,
    pub schema: Option<String>,
    // ---- config_entry ----
    pub key: Option<String>,
    pub value: Option<String>,
    pub doc: Option<u32>,
    pub value_type: Option<String>,
    // ---- file / module ----
    pub path: Option<String>,
    pub artifact_id: Option<String>,
    #[serde(default)]
    pub deployment_units: Vec<String>,
}

/// Annotation occurrence attached to a declaration.
#[derive(Debug, Clone, Default, Deserialize)]
pub struct Annotation {
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub args: String,
}

/// A skeleton edge (`source`, `type`, `target`).
#[derive(Debug, Clone, Deserialize)]
pub struct Edge {
    pub source: String,
    #[serde(rename = "type")]
    pub type_: String,
    pub target: String,
}

/// The task package's own statement of the scenario's starting point.
///
/// This is *input* to the semantic engine, not prose to be ignored: the package
/// says what the account, the clock and the choices are before every scenario,
/// and a step that leaves a request field open must be read against it.
#[derive(Debug, Clone, Default, Deserialize, serde::Serialize)]
pub struct Context {
    #[serde(default)]
    pub initial_state: String,
    #[serde(default)]
    pub account: String,
    #[serde(default)]
    pub date: String,
    #[serde(default)]
    pub choices: String,
    #[serde(default)]
    pub profile: String,
}

/// The whole skeleton document.
#[derive(Debug, Clone, Deserialize)]
pub struct Skeleton {
    #[serde(default)]
    pub project: String,
    pub schema: Option<String>,
    /// Task-package context block (see [`Context`]); dropped before B38-02.
    #[serde(default)]
    pub context: Option<Context>,
    #[serde(default)]
    pub nodes: HashMap<String, Node>,
    #[serde(default)]
    pub edges: Vec<Edge>,
}

impl Skeleton {
    /// Load a skeleton from a `.json` or `.json.gz` path (magic-byte sniffed,
    /// so a mislabeled extension cannot silently produce garbage).
    ///
    /// # Errors
    /// [`TtError::Io`] on unreadable files, [`TtError::Json`] on malformed
    /// documents, [`TtError::Gzip`] on a corrupt compressed stream.
    pub fn load(path: impl AsRef<Path>) -> Result<Self, TtError> {
        let bytes = std::fs::read(path).map_err(TtError::Io)?;
        Self::parse(&bytes)
    }

    /// Parse in-memory bytes, transparently inflating gzip.
    ///
    /// # Errors
    /// Same as [`Skeleton::load`].
    pub fn parse(bytes: &[u8]) -> Result<Self, TtError> {
        if bytes.starts_with(&[0x1f, 0x8b]) {
            let mut decoder = flate2::read::MultiGzDecoder::new(bytes);
            let mut text = Vec::new();
            decoder
                .read_to_end(&mut text)
                .map_err(|e| TtError::Gzip(e.to_string()))?;
            Ok(serde_json::from_slice(&text).map_err(TtError::Json)?)
        } else {
            Ok(serde_json::from_slice(bytes).map_err(TtError::Json)?)
        }
    }

    /// Count nodes of a given `kind` (diagnostics/tests).
    #[must_use]
    pub fn count_kind(&self, kind: &str) -> usize {
        self.nodes.values().filter(|n| n.kind == kind).count()
    }

    /// Count edges of a given `type` (diagnostics/tests).
    #[must_use]
    pub fn count_edge(&self, type_: &str) -> usize {
        self.edges.iter().filter(|e| e.type_ == type_).count()
    }

    /// All ids of a given node kind.
    pub fn ids_of_kind<'a>(&'a self, kind: &'a str) -> impl Iterator<Item = &'a str> + 'a {
        self.nodes
            .iter()
            .filter(move |(_, n)| n.kind == kind)
            .map(|(id, _)| id.as_str())
    }
}

/// Accept an argument text written either as one string or as a list of
/// argument texts, normalising both to the string shape the skeleton uses.
fn string_or_seq<'de, D>(deserializer: D) -> Result<Option<String>, D::Error>
where
    D: serde::Deserializer<'de>,
{
    #[derive(Deserialize)]
    #[serde(untagged)]
    enum Shape {
        One(String),
        Many(Vec<String>),
    }
    Ok(match Option::<Shape>::deserialize(deserializer)? {
        None => None,
        Some(Shape::One(text)) => Some(text),
        Some(Shape::Many(parts)) => Some(parts.join(", ")),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    const SKELETON: &str = r#"{
      "project": "demo", "schema": "v6-skeleton/2.1",
      "nodes": {
        "type:svc:a.B": {"kind":"type","fqn":"a.B","type_kind":"class","implements_raw":["UserDetailsService"]},
        "method:svc:a.B#run()": {"kind":"method","owner":"type:svc:a.B","name":"run","descriptor":"",
            "abstract":false,"annotations":[{"name":"GetMapping","args":"(path = \"/x\")"}]},
        "call:method:svc:a.B#run()@1:2": {"kind":"call_site","method":"method:svc:a.B#run()","callee":"f",
            "receiver_type":"a.C","arg_count":0}
      },
      "edges": [
        {"source":"call:method:svc:a.B#run()@1:2","type":"calls","target":"method:svc:a.C#f()"}
      ]
    }"#;

    #[test]
    fn parses_typed_nodes_and_edges() {
        let sk = Skeleton::parse(SKELETON.as_bytes()).expect("valid");
        assert_eq!(sk.project, "demo");
        assert_eq!(sk.nodes.len(), 3);
        assert_eq!(sk.edges.len(), 1);
        assert_eq!(sk.count_kind("method"), 1);
        assert_eq!(sk.count_edge("calls"), 1);
        let m = &sk.nodes["method:svc:a.B#run()"];
        assert_eq!(m.name.as_deref(), Some("run"));
        assert_eq!(m.annotations[0].name, "GetMapping");
        let t = &sk.nodes["type:svc:a.B"];
        assert_eq!(t.implements_raw, vec!["UserDetailsService"]);
        assert_eq!(sk.edges[0].type_, "calls");
    }

    #[test]
    fn gzip_roundtrip_is_transparent() {
        use flate2::write::GzEncoder;
        use std::io::Write as _;
        let mut enc = GzEncoder::new(Vec::new(), flate2::Compression::fast());
        enc.write_all(SKELETON.as_bytes()).unwrap();
        let gz = enc.finish().unwrap();
        assert!(gz.starts_with(&[0x1f, 0x8b]));
        let sk = Skeleton::parse(&gz).expect("gzip");
        assert_eq!(sk.nodes.len(), 3);
    }

    #[test]
    fn malformed_json_is_an_error_not_a_panic() {
        assert!(matches!(
            Skeleton::parse(b"{not json"),
            Err(TtError::Json(_))
        ));
    }
}
