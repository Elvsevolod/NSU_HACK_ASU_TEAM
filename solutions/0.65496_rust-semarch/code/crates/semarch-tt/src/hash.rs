//! Deterministic content hashing for run manifests.
//!
//! FNV-1a (64-bit) — algorithm provenance: Fowler–Noll–Vo, placed in the public
//! domain by its authors (Glenn Fowler, Landon Curt Noll, Kiem-Phong Vo).
//!
//! This is **not** a cryptographic hash. It exists only to fingerprint the exact
//! inputs of one analysis run so two runs can be compared for equality, and the
//! emitted label (`fnv1a64:<hex>`) says so. Cryptographic verification of the
//! *answer* belongs to the release tooling (`scripts/reproduce_rust.py` hashes
//! the two output files with sha256); the manifest deliberately does not pretend
//! to that strength.

const OFFSET_BASIS: u64 = 0xcbf2_9ce4_8422_2325;
const PRIME: u64 = 0x0000_0100_0000_01b3;

/// FNV-1a 64-bit hash of a byte slice.
#[must_use]
pub fn fnv1a64(bytes: &[u8]) -> u64 {
    let mut hash = OFFSET_BASIS;
    for &b in bytes {
        hash ^= u64::from(b);
        hash = hash.wrapping_mul(PRIME);
    }
    hash
}

/// Lowercase hex of an FNV-1a 64-bit hash, labelled with the algorithm.
///
/// The label is part of the value on purpose: a reader must never mistake a
/// 64-bit fingerprint for the sha256 the release tooling reports.
#[must_use]
pub fn content_hash(bytes: &[u8]) -> String {
    format!("fnv1a64:{:016x}", fnv1a64(bytes))
}

/// Hash a set of `(name, content)` pairs order-independently: the pairs are
/// sorted by name first, so a directory listing order never leaks into the
/// fingerprint.
#[must_use]
pub fn set_hash<'a>(items: impl IntoIterator<Item = (&'a str, &'a [u8])>) -> String {
    let mut pairs: Vec<(&str, &[u8])> = items.into_iter().collect();
    pairs.sort_by(|a, b| a.0.cmp(b.0));
    let mut blob = Vec::new();
    for (name, content) in pairs {
        blob.extend_from_slice(name.as_bytes());
        blob.push(0);
        blob.extend_from_slice(content);
        blob.push(b'\n');
    }
    content_hash(&blob)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fnv1a_matches_the_reference_vectors() {
        // Reference values for FNV-1a 64-bit from the algorithm's public test
        // vectors.
        assert_eq!(fnv1a64(b""), 0xcbf2_9ce4_8422_2325);
        assert_eq!(fnv1a64(b"a"), 0xaf63_dc4c_8601_ec8c);
        assert_eq!(fnv1a64(b"foobar"), 0x85944171f73967e8);
    }

    #[test]
    fn set_hash_is_order_independent() {
        let a = set_hash([("x", b"1".as_slice()), ("y", b"2".as_slice())]);
        let b = set_hash([("y", b"2".as_slice()), ("x", b"1".as_slice())]);
        assert_eq!(a, b);
        assert!(a.starts_with("fnv1a64:"));
    }
}
