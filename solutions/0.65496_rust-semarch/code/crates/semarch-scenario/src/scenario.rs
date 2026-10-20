//! Scenario text model (contest input format, `scenarios/S*.json`).
//!
//! The model intentionally carries *only* what an organizer scenario file
//! gives us: a scenario id, prose, and ordered user actions. It has no field
//! for addresses, handlers or answers — grounding is an adapter concern.

use serde::{Deserialize, Serialize};

/// One ordered user action. `n` is the contest's step number (1-based).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Step {
    pub n: u32,
    pub action: String,
}

/// A full scenario: prose plus ordered steps.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Scenario {
    pub project: String,
    pub id: String,
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub description: String,
    /// Input modality (`text`); kept for completeness of the contest format.
    #[serde(default)]
    pub input: String,
    #[serde(default)]
    pub steps: Vec<Step>,
}

impl Scenario {
    /// Parse a scenario JSON document.
    ///
    /// # Errors
    /// Propagates `serde_json` errors verbatim.
    pub fn from_json(text: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(text)
    }

    /// The retrieval query for one step: its action clause.
    ///
    /// The scenario title is *not* concatenated by default: it aggregates
    /// nouns from every step ("contacts, orders, luggage") and would make all
    /// steps rank the same handler. It is used only as a fallback when an
    /// action is too terse to retrieve anything. Payload and state clauses are
    /// dropped: a step's payload (`with assurance, food, luggage`) names the
    /// *contents* of the request, not the handler that serves it.
    #[must_use]
    pub fn query_for(&self, step: &Step) -> String {
        let action = crate::text::action_query(&step.action);
        let tokens = crate::text::tokenize(&action);
        if tokens.len() < 2 && !self.title.is_empty() {
            format!("{} {}", action, self.title)
        } else {
            action
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_contest_shape() {
        let json = r#"{
          "project": "trainticket", "id": "S0", "title": "My account",
          "description": "prose", "input": "text",
          "steps": [{"n": 1, "action": "Log in"}, {"n": 2, "action": "Open contacts"}]
        }"#;
        let s = Scenario::from_json(json).expect("valid");
        assert_eq!(s.steps.len(), 2);
        assert_eq!(s.steps[1].action, "Open contacts");
        assert_eq!(s.query_for(&s.steps[0]), "Log in My account");
        // a step with enough content tokens keeps only its own action
        assert_eq!(s.query_for(&s.steps[1]), "Open contacts");
    }
}
