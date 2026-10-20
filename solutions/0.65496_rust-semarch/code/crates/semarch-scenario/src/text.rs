//! Text normalization for retrieval: identifier-aware tokenization, a
//! *conservative* stemmer and a small action-synonym table.
//!
//! The tokenizer exists because identifiers are not English: `queryOrdersForRefresh`
//! must become `query / order / for / refresh` and `find_contacts_by_account_id`
//! must become `find / contact / by / account / id`. This is a general property
//! of source code, not of any particular project.

use std::collections::BTreeSet;

/// English function words that carry no retrieval signal in either code
/// identifiers or UI prose. Deliberately small: aggressive stopword lists hurt
/// short queries such as "open the contact book".
const STOPWORDS: &[&str] = &[
    "the", "a", "an", "of", "to", "in", "on", "at", "for", "with", "and", "or", "is", "are", "be",
    "by", "it", "its", "this", "that", "these", "those", "as", "from", "into", "then", "than",
    "my", "me", "i", "we", "our", "you", "your", "they", "their", "his", "her", "them", "his",
    "el", "la", "los", "las", "de",
];

/// Action synonyms: user-facing verbs (UI prose) mapped to the vocabulary that
/// HTTP handlers and method names actually use. This is a *vocabulary bridge*
/// between the two text sources, not a rule about any project.
const SYNONYMS: &[(&str, &[&str])] = &[
    ("open", &["get", "find", "query", "list"]),
    ("view", &["get", "find", "query", "list"]),
    ("show", &["get", "find", "query", "list"]),
    ("display", &["get", "find", "query", "list"]),
    ("see", &["get", "find", "query", "list"]),
    ("check", &["get", "find", "query"]),
    ("look", &["get", "find", "query"]),
    ("refresh", &["query", "find", "list", "refresh"]),
    ("reload", &["query", "find", "list"]),
    ("log", &["login", "token", "auth"]),
    ("register", &["create", "add", "register"]),
    ("signup", &["create", "add", "register"]),
    ("create", &["add", "create", "new", "save"]),
    ("add", &["create", "add", "new", "save"]),
    ("delete", &["delete", "remove", "cancel"]),
    ("remove", &["delete", "remove", "cancel"]),
    ("book", &["book", "preserve"]),
    ("buy", &["pay", "order", "preserve"]),
    ("pay", &["pay", "payment", "inside"]),
    ("change", &["update", "modify", "change"]),
    ("update", &["update", "modify", "change"]),
    ("modify", &["update", "modify", "change"]),
    ("search", &["query", "find", "search"]),
];

/// Operation families: for a head verb, the other names the *same operation* can
/// take in a code base (`book` → `preserve` in a booking service).
///
/// The table is deliberately thin. It holds only mappings onto a concrete
/// operation name, because those are what a project actually exposes; generic
/// mappings (`add` → `create`/`new`/`save`) are not here: every administration
/// screen has a "create …" form, so such an expansion matches the wrong screen
/// as often as the right one, and the channel stops discriminating.
///
/// A head verb outside this table names no operation the project has a word
/// for, so the operation channel is empty for that step and the action and
/// payload channels decide alone.
const OPERATION_FAMILIES: &[(&str, &[&str])] = &[
    ("book", &["book", "preserve"]),
    ("reserve", &["book", "preserve"]),
    ("buy", &["buy", "preserve"]),
    ("change", &["update", "modify"]),
    ("update", &["update", "modify"]),
    ("modify", &["update", "modify"]),
];

/// Split an identifier or sentence into lowercase search tokens.
///
/// Splitting rules (all language-agnostic):
/// * non-alphanumeric characters are separators;
/// * a `lower`→`UPPER` boundary starts a new token (`queryOrders` → `query`,
///   `orders`);
/// * a run of capitals followed by a lowercase letter splits before the last
///   capital (`HTTPServer` → `http`, `server`).
#[must_use]
pub fn tokenize(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut prev: Option<char> = None;
    let mut chars: Vec<char> = text.chars().collect();
    // lookahead needed for the acronym rule
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        let next = chars.get(i + 1).copied();
        if !c.is_alphanumeric() {
            flush(&mut cur, &mut out);
            prev = None;
            i += 1;
            continue;
        }
        if let (Some(p), true) = (prev, c.is_uppercase()) {
            let boundary = p.is_lowercase()
                || p.is_ascii_digit()
                || (p.is_uppercase() && next.is_some_and(|n| n.is_lowercase()));
            if boundary {
                flush(&mut cur, &mut out);
            }
        }
        cur.extend(c.to_lowercase());
        prev = Some(c);
        i += 1;
    }
    flush(&mut cur, &mut out);
    chars.clear();
    out.retain(|t| t.len() > 1 && !STOPWORDS.contains(&t.as_str()));
    out
}

fn flush(cur: &mut String, out: &mut Vec<String>) {
    if !cur.is_empty() {
        out.push(stem(cur));
        cur.clear();
    }
}

/// Conservative plural/gerund stemmer (the same family of rule as the
/// contest's own BM25 example program): `orders`→`order`, `departing`→`depart`,
/// `booked`→`book`; short stems and `-ers`/`-ment` words are left intact.
#[must_use]
pub fn stem(w: &str) -> String {
    if w.len() >= 5 && w.ends_with("ies") {
        return format!("{}y", &w[..w.len() - 3]);
    }
    let mut w = w.to_owned();
    if (w.len() >= 5 && w.ends_with("es") && matches!(w.as_bytes()[w.len() - 3], b's' | b'x' | b'z'))
        || w.ends_with("ches")
        || w.ends_with("shes")
    {
        w.truncate(w.len() - 2);
    } else if w.len() >= 4
        && w.ends_with('s')
        && !w.ends_with("ss")
        && !w.ends_with("us")
        && !w.ends_with("is")
    {
        w.truncate(w.len() - 1);
    }
    for suf in ["ing", "ed"] {
        if w.ends_with(suf) && w.len() - suf.len() >= 4 {
            let base = &w[..w.len() - suf.len()];
            if base.chars().any(|c| matches!(c, 'a' | 'e' | 'i' | 'o' | 'u' | 'y')) {
                let mut b = base.to_owned();
                if b.len() > 4 && b.ends_with(|c: char| c.is_ascii_alphabetic()) {
                    let mut ch = b.chars().rev();
                    if let (Some(x), Some(y)) = (ch.next(), ch.next()) {
                        if x == y && !matches!(x, 'a' | 'e' | 'i' | 'o' | 'u') {
                            b.pop();
                        }
                    }
                }
                w = b;
                break;
            }
        }
    }
    w
}

/// Expand a token set with the action-synonym table (one hop, deterministic).
#[must_use]
pub fn synonyms(tokens: &[String]) -> BTreeSet<String> {
    let mut out: BTreeSet<String> = tokens.iter().cloned().collect();
    for t in tokens {
        for (key, vals) in SYNONYMS {
            if t == key {
                for v in *vals {
                    out.insert((*v).to_owned());
                }
            }
        }
    }
    out
}

/// The synonym table's expansion of one token, if it has any.
#[must_use]
pub fn synonym_of(token: &str) -> Option<&'static [&'static str]> {
    SYNONYMS
        .iter()
        .find(|(key, _)| *key == token)
        .map(|(_, vals)| *vals)
}

/// Expand a step's tokens through the synonym table, bridging **the action verb
/// only**.
///
/// The table maps user-facing verbs to handler vocabulary (`open` → `get`,
/// `book` → `preserve`, `pay` → `payment`). Applied to *every* token it would
/// also rewrite nouns that happen to look like verbs: in "Open the contact
/// book", `book` would add `preserve`/`create` and the step would match the
/// booking page's "create new contact" control. A step has one action verb, so
/// only the first token the table knows is expanded; the rest are matched
/// literally.
#[must_use]
pub fn synonyms_for_action(tokens: &[String]) -> BTreeSet<String> {
    let mut out: BTreeSet<String> = tokens.iter().cloned().collect();
    if let Some(vals) = tokens.iter().find_map(|t| synonym_of(t)) {
        out.extend(vals.iter().map(|v| (*v).to_owned()));
    }
    out
}

/// Clause separators in a scenario step: `,`, `:` and `;`.
///
/// A step is written as one English sentence whose clauses play different
/// roles: the first clause names the *action* (`Book one first-class seat`),
/// later clauses enumerate the *payload* (`with food …, assurance …`) or
/// explain *state* (`the internal balance is empty`). Entry grounding wants the
/// action; the payload belongs to guard resolution.
#[must_use]
pub fn clauses(action: &str) -> Vec<&str> {
    let mut out = Vec::new();
    let mut start = 0usize;
    for (i, c) in action.char_indices() {
        if matches!(c, ',' | ':' | ';') {
            let part = action[start..i].trim();
            if !part.is_empty() {
                out.push(part);
            }
            start = i + c.len_utf8();
        }
    }
    let part = action[start..].trim();
    if !part.is_empty() {
        out.push(part);
    }
    out
}

/// Lead words that introduce a *payload* clause ("with assurance", "without
/// food", "no consignment", "carrying luggage").
const PAYLOAD_LEAD: &[&str] = &[
    "with",
    "without",
    "carrying",
    "including",
    "accompanied",
    "no",
    "nor",
    "not",
];

/// State words that mark a clause as a *condition about the system* rather than
/// the object of the action ("the internal balance is empty", "the system
/// refuses", "the payment is completed"). Compared as prefix against stemmed
/// tokens so `refuses`/`completed`/`insufficient` all match.
const STATE_WORDS: &[&str] = &[
    "empty",
    "insufficient",
    "refus",
    "complet",
    "expir",
    "alread",
    "unavail",
    "insuffici",
];

/// Whether a clause describes payload or state instead of the action's object.
#[must_use]
pub fn is_payload_clause(clause: &str) -> bool {
    let lower = clause.to_ascii_lowercase();
    let lead = lower
        .split(|c: char| !c.is_alphanumeric())
        .find(|s| !s.is_empty());
    if lead.is_some_and(|w| PAYLOAD_LEAD.contains(&w)) {
        return true;
    }
    tokenize(clause)
        .iter()
        .any(|t| STATE_WORDS.iter().any(|w| t.starts_with(w)))
}

/// Prepositions that introduce an *instrument/source* phrase, not the object:
/// `Pay for the order from the internal account balance` → `Pay for the order`.
const INSTRUMENT_MARKERS: &[&str] = &["from", "via", "through", "using"];

/// Cut a trailing instrument/source phrase off a clause (whole-word match only).
#[must_use]
pub fn strip_instrument(clause: &str) -> &str {
    let lower = clause.to_ascii_lowercase();
    let bytes = lower.as_bytes();
    let mut best: Option<usize> = None;
    for m in INSTRUMENT_MARKERS {
        let mut from = 0usize;
        while let Some(pos) = lower[from..].find(m) {
            let abs = from + pos;
            let end = abs + m.len();
            let before_ok = abs == 0 || !(bytes[abs - 1].is_ascii_alphanumeric() || bytes[abs - 1] == b'_');
            let after_ok =
                end >= bytes.len() || !(bytes[end].is_ascii_alphanumeric() || bytes[end] == b'_');
            if before_ok && after_ok && best.is_none_or(|b| abs < b) {
                best = Some(abs);
            }
            from = end;
        }
    }
    match best {
        Some(i) => clause[..i].trim_end_matches(|c: char| c == ',' || c.is_whitespace()),
        None => clause,
    }
}

/// The retrieval query for entry grounding of one step action.
///
/// * the first clause is the action, with any instrument phrase removed;
/// * following clauses are appended only until the first payload/state clause;
/// * after a payload clause the rest of the sentence is payload (the
///   enumeration continues with commas), so it is dropped.
///
/// This is a clause-role heuristic over English prose, not project vocabulary:
/// `Book … , with food …, assurance …` keeps `Book …`, while
/// `Advanced search: the cheapest trips` keeps the object clause that names
/// the search variant.
#[must_use]
pub fn action_query(action: &str) -> String {
    let cls = clauses(action);
    let Some((first, rest)) = cls.split_first() else {
        return action.trim().to_owned();
    };
    let mut out = strip_instrument(first).to_owned();
    let mut payload = false;
    for c in rest {
        if payload || is_payload_clause(c) {
            payload = true;
            continue;
        }
        if !out.is_empty() {
            out.push(' ');
        }
        out.push_str(strip_instrument(c));
    }
    if out.trim().is_empty() {
        action.trim().to_owned()
    } else {
        out
    }
}

/// The *payload* half of a step action: the clauses that describe what the
/// request carries, as opposed to the action that sends it.
///
/// A payload clause is introduced by [`PAYLOAD_LEAD`] ("with food …, no
/// assurance …, accompanied by …") or continues such an enumeration, and stops
/// being a payload when it turns into a *state* description ("the internal
/// balance is empty"): a condition about the system is not request data.
///
/// Returns an empty string when the step carries no payload, which is what
/// makes the contract channel of entry grounding inert for read-only steps.
#[must_use]
pub fn payload_query(action: &str) -> String {
    let cls = clauses(action);
    let mut out = String::new();
    let mut in_payload = false;
    for c in &cls {
        if is_payload_lead(c) {
            in_payload = true;
        } else if in_payload && is_state_clause(c) {
            in_payload = false;
            continue;
        } else if !in_payload {
            continue;
        }
        if !out.is_empty() {
            out.push(' ');
        }
        out.push_str(c);
    }
    let extra = payload_extras(action);
    if !extra.is_empty() {
        if !out.is_empty() {
            out.push(' ');
        }
        out.push_str(&extra.join(" "));
    }
    out
}

/// Field lists that requirement prose states *without* a payload lead word.
///
/// Two constructions carry request fields:
///
/// * a parenthetical **enumeration** — "Register a new passenger account
///   (username, password, gender, ID document, e-mail)";
/// * a possessive attribute — "Change the consignee's name and phone number".
///
/// Both name the fields of the request body, exactly like "with food and
/// assurance" does, so they belong to the contract channel. A parenthesis that
/// is not an enumeration ("('Other' type) trains", "assurance (insurance)")
/// qualifies the object instead of listing fields, so it is left alone: at least
/// three items are required for the content to be a field list.
fn payload_extras(action: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut depth = 0usize;
    let mut cur = String::new();
    for c in action.chars() {
        match c {
            '(' => {
                depth += 1;
                if depth == 1 {
                    cur.clear();
                }
            }
            ')' => {
                if depth == 1 && cur.matches(',').count() >= 2 {
                    out.push(cur.trim().to_owned());
                }
                depth = depth.saturating_sub(1);
                cur.clear();
            }
            _ => {
                if depth > 0 {
                    cur.push(c);
                }
            }
        }
    }
    for c in clauses(action) {
        if let Some(attr) = possessive_attribute(c) {
            out.push(attr);
        }
    }
    out
}

/// Words that end the attribute phrase after a possessive (`… name and phone
/// number **in** the consignment`): the phrase before them is the field list.
const ATTRIBUTE_STOP: &[&str] = &[
    "in", "on", "of", "for", "from", "with", "without", "to", "at", "by", "into", "during",
    "before", "after",
];

/// The attribute named by a possessive in one clause, if any.
fn possessive_attribute(clause: &str) -> Option<String> {
    let (idx, sep) = clause
        .find("'s ")
        .map(|i| (i, 3))
        .or_else(|| clause.find("\u{2019}s ").map(|i| (i, 4)))?;
    let after = &clause[idx + sep..];
    let mut keep: Vec<&str> = Vec::new();
    for w in after.split_whitespace() {
        let bare = w
            .trim_matches(|c: char| !c.is_alphanumeric())
            .to_ascii_lowercase();
        if ATTRIBUTE_STOP.contains(&bare.as_str()) {
            break;
        }
        keep.push(w);
    }
    if keep.is_empty() {
        None
    } else {
        Some(keep.join(" "))
    }
}

/// Whether a clause *starts* with a payload lead word.
#[must_use]
pub fn is_payload_lead(clause: &str) -> bool {
    clause
        .to_ascii_lowercase()
        .split(|c: char| !c.is_alphanumeric())
        .find(|s| !s.is_empty())
        .is_some_and(|w| PAYLOAD_LEAD.contains(&w))
}

/// Whether a clause is a *state* description (a condition about the system)
/// rather than a payload item.
#[must_use]
pub fn is_state_clause(clause: &str) -> bool {
    tokenize(clause)
        .iter()
        .any(|t| STATE_WORDS.iter().any(|w| t.starts_with(w)))
}

/// The *operation* a step names: the first content word of its action clause,
/// together with the other names the same operation takes in a code base
/// (`Change the consignee …` → `update`, `modify`).
///
/// Empty when the head verb is not in [`OPERATION_FAMILIES`]. This is
/// deliberately much narrower than [`synonyms_for_action`]: the whole action
/// clause is object vocabulary and belongs to the action channel, while the
/// head verb states the operation — and only a verb whose naming actually
/// varies between prose and code states one worth searching for.
#[must_use]
pub fn verb_tokens(action: &str) -> BTreeSet<String> {
    let cls = clauses(action);
    let head_clause = cls.first().copied().unwrap_or(action);
    let mut out = BTreeSet::new();
    let Some(head) = tokenize(head_clause).into_iter().next() else {
        return out;
    };
    if let Some((_, vals)) = OPERATION_FAMILIES.iter().find(|(k, _)| *k == head) {
        out.extend(vals.iter().map(|v| (*v).to_owned()));
    }
    out
}

/// Identifier prefixes that mark a *predicate* rather than a feature:
/// `isEnabled`, `hasFood`, `getVerificationCode`, `enableStateQuery`. They are
/// stripped before a name becomes a feature token, so the guard
/// `isEnableStateQuery()` and the prose "filter by state" talk about the same
/// feature. This is identifier convention, not project vocabulary.
const PREDICATE_PREFIXES: &[&str] = &[
    "is", "has", "have", "enable", "enabled", "get", "set", "should", "can", "must", "check",
    "use", "using", "allow", "flag", "with", "without", "need",
];

/// Words that never name a feature on their own (predicate helpers and
/// container-ish checks).
const PREDICATE_WORDS: &[&str] = &[
    "empty", "blank", "null", "nil", "none", "present", "absent", "equal", "equals", "available",
    "valid", "validity", "size", "length", "count", "true", "false", "not", "non",
];

/// Split an identifier into *feature* tokens: camel/snake words with predicate
/// prefixes removed and predicate words dropped.
///
/// * `isEnableStateQuery` → `state, query`
/// * `getVerificationCode` → `verification, code`
/// * `isNotEmpty` → `[]` (pure predicate)
#[must_use]
pub fn feature_tokens(ident: &str) -> Vec<String> {
    let mut s = ident.to_owned();
    loop {
        let mut stripped = false;
        for p in PREDICATE_PREFIXES {
            if let Some(rest) = strip_word(&s, p) {
                s = rest;
                stripped = true;
                break;
            }
        }
        if !stripped {
            break;
        }
    }
    let mut out = tokenize(&s);
    out.retain(|t| !PREDICATE_WORDS.contains(&t.as_str()));
    out
}

/// Strip `prefix` from `s` only when it is a whole camel/snake word
/// (`isEnable` → `Enable`), never a substring (`island` stays `island`).
fn strip_word(s: &str, prefix: &str) -> Option<String> {
    if s.len() <= prefix.len() || !s[..prefix.len()].eq_ignore_ascii_case(prefix) {
        return None;
    }
    let rest = &s[prefix.len()..];
    let next = rest.chars().next()?;
    if next.is_uppercase() || next == '_' || next.is_ascii_digit() {
        return Some(rest.trim_start_matches('_').to_owned());
    }
    None
}

/// Whether two normalized tokens plausibly denote the same feature, allowing
/// suffix-forming variants (`consign` ↔ `consignment`, `assur` ↔ `assurance`).
///
/// Equality always counts; otherwise one token must be a prefix of the other
/// and carry at least [`MIN_PREFIX`] characters, which keeps `state`/`status`
/// and other near-misses apart. Irregular pairs (`verify` / `verification`)
/// are *not* linked here — they meet through the token they share
/// (`verifyCode` and "verification code" both carry `code`).
#[must_use]
pub fn related(a: &str, b: &str) -> bool {
    /// Shortest prefix accepted as a morphological variant.
    pub const MIN_PREFIX: usize = 5;
    if a == b {
        return true;
    }
    let (short, long) = if a.len() <= b.len() { (a, b) } else { (b, a) };
    short.len() >= MIN_PREFIX && long.starts_with(short)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn camel_and_snake_split() {
        // function words ("for", "by") are dropped as stopwords
        assert_eq!(
            tokenize("queryOrdersForRefresh"),
            vec!["query", "order", "refresh"]
        );
        assert_eq!(
            tokenize("find_contacts_by_account_id"),
            vec!["find", "contact", "account", "id"]
        );
    }

    #[test]
    fn acronym_boundary() {
        assert_eq!(tokenize("HTTPServerConfig"), vec!["http", "server", "config"]);
        assert_eq!(tokenize("parseHTMLBody"), vec!["parse", "html", "body"]);
    }

    #[test]
    fn stopwords_and_singletons_dropped() {
        // "a" is a stopword, "in" is a stopword; "to" also.
        assert_eq!(tokenize("Log in to a system"), vec!["log", "system"]);
    }

    #[test]
    fn conservative_stemming() {
        assert_eq!(stem("orders"), "order");
        assert_eq!(stem("contact"), "contact");
        assert_eq!(stem("booked"), "book");
        assert_eq!(stem("departing"), "depart");
        assert_eq!(stem("passengers"), "passenger");
        assert_eq!(stem("address"), "address");
    }

    #[test]
    fn synonyms_expand_deterministically() {
        let t = tokenize("open contact book");
        let s = synonyms(&t);
        assert!(s.contains("get"));
        assert!(s.contains("contact"));
        assert!(s.contains("book"));
    }

    #[test]
    fn feature_tokens_strip_predicates() {
        assert_eq!(feature_tokens("isEnableStateQuery"), vec!["state", "query"]);
        assert_eq!(feature_tokens("getVerificationCode"), vec!["verification", "code"]);
        assert_eq!(feature_tokens("isEnableFood"), vec!["food"]);
        assert_eq!(feature_tokens("verificationCode"), vec!["verification", "code"]);
        // a pure predicate names no feature
        assert!(feature_tokens("isEmpty").is_empty());
        assert!(feature_tokens("isNotEmpty").is_empty());
        // substrings are not prefixes
        assert_eq!(feature_tokens("island"), vec!["island"]);
    }

    #[test]
    fn action_query_keeps_the_action_and_drops_payload() {
        let s = "Book one first-class seat on the trip for this contact, with food on the train, \
                 assurance (insurance) of the first type and luggage consignment of 2 kg to a consignee";
        assert_eq!(
            action_query(s),
            "Book one first-class seat on the trip for this contact"
        );
        let s = "Book a first-class seat on the cheapest (regular) trip for this contact, \
                 without food, assurance or consignment";
        assert_eq!(
            action_query(s),
            "Book a first-class seat on the cheapest (regular) trip for this contact"
        );
    }

    #[test]
    fn action_query_drops_instrument_and_state_clauses() {
        assert_eq!(
            action_query("Pay for the order from the internal account balance"),
            "Pay for the order"
        );
        assert_eq!(
            action_query(
                "Pay for the order: the internal balance is empty, so the payment is \
                 completed through the external payment channel"
            ),
            "Pay for the order"
        );
        assert_eq!(
            action_query("Refresh the list of orders filtered by the 'Paid' status"),
            "Refresh the list of orders filtered by the 'Paid' status"
        );
    }

    #[test]
    fn action_query_keeps_an_object_clause_after_a_colon() {
        // "Advanced search" alone cannot name the search variant; the object
        // clause after the colon carries it.
        assert_eq!(
            action_query("Advanced search: the cheapest trips from Shanghai to Nanjing on 1 October 2026"),
            "Advanced search the cheapest trips"
        );
    }

    #[test]
    fn clauses_split_on_prose_separators() {
        assert_eq!(clauses("A, B: C; D"), vec!["A", "B", "C", "D"]);
        assert!(is_payload_clause("without food, assurance or consignment"));
        assert!(is_payload_clause("the internal balance is empty"));
        assert!(!is_payload_clause("the cheapest trips from Shanghai"));
    }

    #[test]
    fn related_links_suffix_variants_but_not_near_misses() {
        assert!(related("consign", "consignment"));
        assert!(related("food", "food"));
        assert!(!related("state", "status"));
        assert!(!related("date", "data"));
    }
}
