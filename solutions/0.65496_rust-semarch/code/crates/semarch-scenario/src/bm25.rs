//! Okapi BM25 over caller-supplied documents.
//!
//! Deterministic, dependency-free, single-pass index. Scores are returned
//! raw; callers normalize when they need cross-query comparability (the
//! contest's own baseline normalizes by the best score within one query).
//!
//! Provenance: Okapi BM25 (Robertson & Walker, 1994); the two-stage
//! retrieval framing (cheap lexical ranker, optional learned reranker) follows
//! the TOSS line of work. Implemented from the formula, no code borrowed.

use std::collections::HashMap;

/// Default term-frequency saturation.
pub const K1: f64 = 1.2;
/// Default length-normalization strength.
pub const B: f64 = 0.75;

/// One ranked document with its raw BM25 score.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Ranked {
    /// Index into the document slice handed to [`Bm25Index::build`].
    pub doc: usize,
    pub score: f64,
}

/// Immutable BM25 index over a document corpus.
#[derive(Debug, Clone)]
pub struct Bm25Index {
    /// document length in tokens
    lens: Vec<usize>,
    avg_len: f64,
    /// term -> (document -> term frequency)
    postings: HashMap<String, HashMap<usize, u32>>,
    n_docs: usize,
}

impl Bm25Index {
    /// Build an index from `(document_id, tokens)` pairs. `document_id` is
    /// opaque and echoed back in [`Ranked::doc`] as the position in `docs`.
    #[must_use]
    pub fn build<'a, I>(docs: I) -> Self
    where
        I: IntoIterator<Item = &'a [String]>,
    {
        let mut postings: HashMap<String, HashMap<usize, u32>> = HashMap::new();
        let mut lens = Vec::new();
        for (i, tokens) in docs.into_iter().enumerate() {
            lens.push(tokens.len());
            for t in tokens {
                *postings
                    .entry(t.clone())
                    .or_default()
                    .entry(i)
                    .or_insert(0) += 1;
            }
        }
        #[allow(clippy::cast_precision_loss)]
        let avg_len = if lens.is_empty() {
            0.0
        } else {
            lens.iter().sum::<usize>() as f64 / lens.len() as f64
        };
        Self {
            n_docs: lens.len(),
            lens,
            avg_len,
            postings,
        }
    }

    /// Rank documents against a query token set. Ties are broken by document
    /// index so the result is fully deterministic.
    #[must_use]
    pub fn search(&self, query: &[String]) -> Vec<Ranked> {
        let mut scores: HashMap<usize, f64> = HashMap::new();
        let mut seen = std::collections::HashSet::new();
        for q in query {
            if !seen.insert(q.as_str()) {
                continue;
            }
            let Some(plist) = self.postings.get(q) else {
                continue;
            };
            let df = plist.len() as f64;
            let n = self.n_docs as f64;
            let idf = (1.0 + (n - df + 0.5) / (df + 0.5)).ln();
            for (&doc, &tf) in plist {
                let tf = f64::from(tf);
                let dl = self.lens[doc] as f64;
                let denom = tf + K1 * (1.0 - B + B * dl / self.avg_len.max(1.0));
                *scores.entry(doc).or_insert(0.0) += idf * tf * (K1 + 1.0) / denom;
            }
        }
        let mut out: Vec<Ranked> = scores
            .into_iter()
            .map(|(doc, score)| Ranked { doc, score })
            .collect();
        out.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then(a.doc.cmp(&b.doc))
        });
        out
    }

    /// Number of indexed documents.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.n_docs
    }

    /// Whether the index is empty.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.n_docs == 0
    }
}

/// Normalize raw scores so the best document scores `1.0`.
#[must_use]
pub fn normalize(mut ranked: Vec<Ranked>) -> Vec<Ranked> {
    let max = ranked.first().map_or(0.0, |r| r.score);
    if max > 0.0 {
        for r in &mut ranked {
            r.score /= max;
        }
    }
    ranked
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::text;

    fn docs() -> Vec<Vec<String>> {
        vec![
            text::tokenize("find contacts by account id contact book"),
            text::tokenize("query orders for refresh order list"),
            text::tokenize("look up luggage consignments consign record"),
        ]
    }

    #[test]
    fn ranks_relevant_document_first() {
        let d = docs();
        let idx = Bm25Index::build(d.iter().map(Vec::as_slice));
        let q = text::tokenize("open the contact book");
        let r = Bm25Index::search(&idx, &q);
        assert_eq!(r[0].doc, 0, "expected the contacts document: {r:?}");
    }

    #[test]
    fn consign_query_prefers_consign_document() {
        let d = docs();
        let idx = Bm25Index::build(d.iter().map(Vec::as_slice));
        let q = text::tokenize("luggage consignments");
        let r = Bm25Index::search(&idx, &q);
        assert_eq!(r[0].doc, 2, "expected the consign document: {r:?}");
    }

    #[test]
    fn deterministic_and_normalized() {
        let d = docs();
        let idx = Bm25Index::build(d.iter().map(Vec::as_slice));
        let q = text::tokenize("orders refresh");
        let a = normalize(Bm25Index::search(&idx, &q));
        let b = normalize(Bm25Index::search(&idx, &q));
        assert_eq!(a, b);
        assert!((a[0].score - 1.0).abs() < 1e-12);
    }

    #[test]
    fn unknown_terms_yield_no_hits() {
        let d = docs();
        let idx = Bm25Index::build(d.iter().map(Vec::as_slice));
        assert!(Bm25Index::search(&idx, &["zzz".to_owned()]).is_empty());
    }
}
