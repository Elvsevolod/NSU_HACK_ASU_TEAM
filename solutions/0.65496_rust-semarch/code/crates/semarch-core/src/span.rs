//! Source spans. Byte offsets plus tree-sitter row/col (both 0-based, byte
//! columns) so spans can be re-checked against the original source without
//! keeping token offsets.

use crate::ids::FileId;
use serde::{Deserialize, Serialize};

#[derive(
    Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize,
)]
pub struct SourceSpan {
    pub file: FileId,
    /// UTF-8 byte offset of the first byte.
    pub start_byte: u32,
    /// UTF-8 byte offset one past the last byte.
    pub end_byte: u32,
    /// 0-based row of the start.
    pub start_row: u32,
    /// 0-based byte column of the start.
    pub start_col: u32,
    /// 0-based row just past the end.
    pub end_row: u32,
    /// 0-based byte column just past the end.
    pub end_col: u32,
}

impl SourceSpan {
    /// `file@row+1:col+1[-row+1:col+1[:end_byte]]`-style anchor that can always
    /// be verified byte-wise against the original source.
    pub fn anchor(&self) -> String {
        if self.start_byte >= self.end_byte {
            format_span(self, self.start_byte)
        } else {
            format_span(self, self.end_byte)
        }
    }
}

fn format_span(s: &SourceSpan, byte: u32) -> String {
    if s.start_row == s.end_row {
        format!(
            "f{}@{}:{}:{}",
            s.file.raw(),
            s.start_row + 1,
            s.start_col + 1,
            byte
        )
    } else {
        format!(
            "f{}@{}:{}[-{}:{}]:{}",
            s.file.raw(),
            s.start_row + 1,
            s.start_col + 1,
            s.end_row + 1,
            s.end_col + 1,
            byte
        )
    }
}
