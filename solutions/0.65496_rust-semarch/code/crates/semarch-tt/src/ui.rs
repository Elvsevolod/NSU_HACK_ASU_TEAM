//! UI text extraction (the "bound-pair" half of entry grounding).
//!
//! Scenario steps are written in the vocabulary of the *user interface*, while
//! handlers are named in the vocabulary of the *backend*. The web UI is the
//! bridge: an HTTP call site in client code is surrounded by the label,
//! function name and file name a user actually sees.
//!
//! This extractor is deliberately shallow and framework-agnostic: it locates
//! request paths as string literals in any JS/TS/HTML/Vue source. Around each
//! occurrence it keeps three *separately weighted* kinds of evidence, because
//! they answer different questions:
//!
//! * **page** vocabulary (the client file name) — which screen the user is on;
//! * **action** vocabulary (enclosing function, target element, local window)
//!   — which control on that screen sends the request;
//! * the request path itself, plus the HTTP verb when the call site states one.
//!
//! It does not parse JavaScript and never asserts what an endpoint *means*.

use std::path::{Path, PathBuf};

use crate::TtError;

/// How the UI call site is reached: from a user event, on page load, or
/// unknown. Recorded as diagnostic evidence; both kinds are legitimate entries
/// (a step may *be* a page-load lookup such as "view the food menu").
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Trigger {
    /// Bound to a click/submit/change handler.
    Action,
    /// Sent from a page-load hook (`$(document).ready`, `onload`, `mounted`).
    Load,
    /// No recognisable event binding nearby.
    Unknown,
}

impl Trigger {
    /// Stable name for reports.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Action => "action",
            Self::Load => "load",
            Self::Unknown => "unknown",
        }
    }
}

/// One request path occurrence with its surrounding UI text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UiFact {
    /// Path as written (`/api/v1/orderservice/order/refresh`).
    pub url: String,
    /// HTTP verb stated by the call site, when it says so.
    pub http: Option<String>,
    /// How the call site is triggered.
    pub trigger: Trigger,
    /// Retrieval tokens of the *control* that sends the request: the
    /// declaration the call site sits inside and the element the event is bound
    /// to. This is the strongest UI evidence — it names the action.
    pub action_tokens: Vec<String>,
    /// Retrieval tokens of the bounded text window around the call site. This
    /// is mostly the request's own payload and the field labels it writes to
    /// (`booking_new_contacts_name`), i.e. screen vocabulary, not action
    /// vocabulary — it is therefore weighted like the page, not like a control.
    pub context_tokens: Vec<String>,
    /// Retrieval tokens from the enclosing page (client file name).
    pub page_tokens: Vec<String>,
    /// Union of page, action, context and URL tokens (compatibility
    /// convenience; the entry index uses the separated fields).
    pub tokens: Vec<String>,
    /// Source file the fact came from (diagnostics).
    pub file: String,
}

const UI_EXTS: &[&str] = &["js", "ts", "jsx", "tsx", "vue", "html", "htm"];
/// Characters that terminate a bare path literal.
const URL_STOP: &[char] = &['"', '\'', '`', ' ', '\t', '\n', '\r', ')', ';', ',', '<', '>'];
/// How much local text before a request path counts as its action context.
const ACTION_WINDOW: usize = 240;
/// How far back to look for the declaration the call site sits inside.
const METHOD_LOOKBACK: usize = 8000;
/// Property names that describe *how* a callback fires, not what an action
/// does: they are skipped when looking for the enclosing method.
const CALLBACK_NAMES: &[&str] = &[
    "onconfirm",
    "oncancel",
    "onsubmit",
    "onclick",
    "success",
    "error",
    "complete",
    "done",
    "fail",
    "then",
    "catch",
    "finally",
    "callback",
    "ready",
    "mounted",
    "created",
    "foreach",
    "each",
    "map",
];
/// JavaScript keywords that look like a declaration head but are not one.
const JS_KEYWORDS: &[&str] = &[
    "if", "for", "while", "switch", "catch", "else", "return", "function", "new", "typeof", "do",
    "try", "case", "throw", "class", "var", "let", "const", "export", "import", "default", "async",
    "await", "delete", "in", "of", "instanceof", "void", "yield", "super", "this",
];

/// Extract UI facts from a web-client directory (recursively).
///
/// # Errors
/// [`TtError::Io`] if the directory cannot be read. Unreadable individual
/// files are skipped rather than failing the whole run.
pub fn extract(root: impl AsRef<Path>) -> Result<Vec<UiFact>, TtError> {
    let mut facts = Vec::new();
    let mut stack = vec![root.as_ref().to_path_buf()];
    while let Some(dir) = stack.pop() {
        let entries = match std::fs::read_dir(&dir) {
            Ok(e) => e,
            Err(_) => continue,
        };
        for entry in entries.flatten() {
            let path: PathBuf = entry.path();
            let Ok(meta) = entry.metadata() else { continue };
            if meta.is_dir() {
                let name = path.file_name().and_then(|s| s.to_str()).unwrap_or("");
                // Vendored/minified trees carry no project vocabulary.
                if matches!(name, "node_modules" | ".git" | "target" | "dist" | "build") {
                    continue;
                }
                stack.push(path);
                continue;
            }
            let ext = path.extension().and_then(|s| s.to_str()).unwrap_or("");
            if !UI_EXTS.contains(&ext) {
                continue;
            }
            if let Ok(text) = std::fs::read_to_string(&path) {
                facts.extend(scan_file(&text, &path));
            }
        }
    }
    facts.sort_by_key(|f| (f.file.clone(), f.url.clone()));
    Ok(facts)
}

/// Scan one UI file for request-path literals.
#[must_use]
pub fn scan_file(text: &str, path: &Path) -> Vec<UiFact> {
    let stem = path
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or_default()
        .to_owned();
    let page_tokens = semarch_scenario::text::tokenize(&stem.replace(['-', '_', '.'], " "));
    let mut out = Vec::new();
    let bytes = text.as_bytes();
    let mut i = 0usize;
    // The previous request literal in this file bounds the action context: text
    // before it belongs to another call, not to this one.
    let mut prev_url_end = 0usize;
    while i < bytes.len() {
        // A path literal starts with '/' followed by an alphanumeric letter.
        if bytes[i] == b'/' && bytes.get(i + 1).is_some_and(u8::is_ascii_alphanumeric) {
            let mut j = i;
            while j < bytes.len() && !URL_STOP.contains(&(bytes[j] as char)) {
                j += 1;
            }
            let url = &text[i..j];
            if is_candidate_path(url) {
                let start = text[..i]
                    .char_indices()
                    .rev()
                    .nth(ACTION_WINDOW)
                    .map_or(0, |(b, _)| b)
                    .max(prev_url_end);
                let context_tokens =
                    semarch_scenario::text::tokenize(&text[start..i]);
                // The declaration the call sits inside names the control; the
                // element its event is bound to names the button. Both are
                // action vocabulary; the window above is payload and field
                // labels, i.e. screen vocabulary.
                let mut action_tokens = Vec::new();
                let method_start = prev_url_end.max(i.saturating_sub(METHOD_LOOKBACK));
                if let Some(func) = enclosing_method(&text[method_start..i]) {
                    action_tokens.extend(semarch_scenario::text::tokenize(&func));
                }
                if let Some(el) = last_element(&text[prev_url_end..i]) {
                    action_tokens.extend(semarch_scenario::text::tokenize(&el));
                }
                let mut tokens = page_tokens.clone();
                tokens.extend(action_tokens.iter().cloned());
                tokens.extend(context_tokens.iter().cloned());
                tokens.extend(semarch_scenario::text::tokenize(url));
                out.push(UiFact {
                    url: url.to_owned(),
                    http: last_http(text, i, prev_url_end),
                    trigger: last_trigger(&text[prev_url_end..i]),
                    action_tokens,
                    context_tokens,
                    page_tokens: page_tokens.clone(),
                    tokens,
                    file: path.display().to_string(),
                });
                prev_url_end = j;
            }
            i = j.max(i + 1);
            continue;
        }
        i += 1;
    }
    out
}

/// The HTTP verb and event trigger stated by the call site nearest before or
/// after the path literal.
///
/// A literal may precede its own options (`url: path` built from a variable, so
/// the `type:` line comes later) or follow them; a *symmetric* window with
/// nearest-wins handles both, and a stale `type:` from an unrelated call far
/// away is ignored.
fn last_http(text: &str, at: usize, lo_bound: usize) -> Option<String> {
    const HTTP_WINDOW: usize = 800;
    let start = text[..at]
        .char_indices()
        .rev()
        .nth(HTTP_WINDOW)
        .map_or(0, |(b, _)| b)
        .max(lo_bound);
    let end = text[at..]
        .char_indices()
        .nth(HTTP_WINDOW)
        .map_or(text.len(), |(b, _)| at + b);
    let (lo, hi) = (start, end);
    let win = &text[lo..hi];
    let low = win.to_ascii_lowercase();
    let rel = at - lo;
    let mut best: Option<(usize, String)> = None;
    let consider = |pos: usize, verb: String, best: &mut Option<(usize, String)>| {
        let d = pos.abs_diff(rel);
        if best.as_ref().is_none_or(|(bd, _)| d < *bd) {
            *best = Some((d, verb));
        }
    };
    let bytes = low.as_bytes();
    for key in ["type:", "method:"] {
        let mut from = 0usize;
        while let Some(pos) = low[from..].find(key) {
            let abs = from + pos;
            let before_ok =
                abs == 0 || !(bytes[abs - 1].is_ascii_alphanumeric() || bytes[abs - 1] == b'_');
            if before_ok {
                if let Some(v) = read_quoted_word(&win[abs + key.len()..]) {
                    let v = v.to_ascii_uppercase();
                    if matches!(v.as_str(), "GET" | "POST" | "PUT" | "DELETE" | "PATCH") {
                        consider(abs, v, &mut best);
                    }
                }
            }
            from = abs + key.len();
        }
    }
    for (pat, verb) in [
        ("$.post", "POST"),
        ("$.getjson", "GET"),
        ("$.get", "GET"),
        ("axios.post", "POST"),
        ("axios.put", "PUT"),
        ("axios.delete", "DELETE"),
        ("axios.get", "GET"),
    ] {
        let mut from = 0usize;
        while let Some(pos) = low[from..].find(pat) {
            consider(from + pos, verb.to_owned(), &mut best);
            from += pos + pat.len();
        }
    }
    best.map(|(_, v)| v)
}

/// Read the first quoted word after `s` (`"post"` → `post`).
fn read_quoted_word(s: &str) -> Option<String> {
    let mut chars = s.char_indices();
    let (_, quote) = chars.find(|(_, c)| !c.is_whitespace())?;
    if quote != '"' && quote != '\'' {
        return None;
    }
    let start = s.find(quote)? + 1;
    let rest = &s[start..];
    let end = rest.find(quote)?;
    Some(rest[..end].to_owned())
}

/// The event binding nearest before the call site.
fn last_trigger(pre: &str) -> Trigger {
    let low = pre.to_ascii_lowercase();
    let action = [
        ".click(",
        ".submit(",
        ".change(",
        "addEventListener(\"click\"",
        "addEventListener('click'",
        "onclick",
        "@click",
        "v-on:click",
    ];
    let load = [
        "$(document).ready",
        "$(function",
        ".onload",
        ".ready(",
        "mounted(",
        "created(",
        "window.onload",
    ];
    let nearest = |pats: &[&str], tag: Trigger| {
        pats.iter()
            .filter_map(|p| low.rfind(p).map(|i| (i, tag)))
            .max_by_key(|(i, _)| *i)
    };
    match (nearest(&action, Trigger::Action), nearest(&load, Trigger::Load)) {
        (Some(a), Some(l)) => {
            if a.0 >= l.0 {
                a.1
            } else {
                l.1
            }
        }
        (Some(a), None) => a.1,
        (None, Some(l)) => l.1,
        (None, None) => Trigger::Unknown,
    }
}

/// The nearest declaration the call site sits inside: `collectTicket(orderId) {`,
/// `function queryOrders()`, `refresh: function (...)`, `pay = (id) => {`.
///
/// Event-callback property names (`onConfirm`, `success`, `error`) are skipped
/// because they describe *how* the call fires, not what the action is; the
/// enclosing method is the control's handler and names the action.
fn enclosing_method(ctx: &str) -> Option<String> {
    for line in ctx.lines().rev() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let Some(name) = method_decl_name(line) else {
            continue;
        };
        let lower = name.to_ascii_lowercase();
        if CALLBACK_NAMES.contains(&lower.as_str()) || JS_KEYWORDS.contains(&lower.as_str()) {
            continue;
        }
        return Some(name);
    }
    None
}

/// The name declared by one code line, if it declares a function/method.
fn method_decl_name(line: &str) -> Option<String> {
    let ident = |s: &str| -> String {
        s.chars()
            .take_while(|c| c.is_alphanumeric() || *c == '_' || *c == '$')
            .collect()
    };
    let mut rest = line;
    if let Some(r) = rest.strip_prefix("async ") {
        rest = r.trim_start();
    }
    if let Some(r) = rest.strip_prefix("function") {
        let r = r.trim_start();
        let name = ident(r);
        if !name.is_empty() && r[name.len()..].trim_start().starts_with('(') {
            return Some(name);
        }
    }
    let name = ident(line);
    if name.is_empty() || name == "$" || name.chars().next().is_some_and(|c| c.is_ascii_digit()) {
        return None;
    }
    let tail = line[name.len()..].trim_start();
    if tail.starts_with('(') && line.trim_end().ends_with('{') {
        return Some(name);
    }
    if let Some(t) = tail.strip_prefix(':').or_else(|| tail.strip_prefix('=')) {
        let t = t.trim_start();
        let t = t.strip_prefix("async ").unwrap_or(t).trim_start();
        if t.starts_with("function") || (t.starts_with('(') && t.contains("=>")) {
            return Some(name);
        }
    }
    None
}

/// The nearest element selector (`#id`) or id attribute (`id="id"`) before the
/// call site: the control the user interacts with.
fn last_element(pre: &str) -> Option<String> {
    let sel = pre.rfind('#').map(|i| (&pre[i + 1..], i));
    let attr = pre.rfind("id=").map(|i| {
        let rest = &pre[i + 3..];
        let rest = rest.trim_start_matches(['"', '\'', ' ']);
        (rest, i)
    });
    let (rest, _) = match (sel, attr) {
        (Some(s), Some(a)) => {
            if s.1 >= a.1 {
                s
            } else {
                a
            }
        }
        (Some(s), None) => s,
        (None, Some(a)) => a,
        (None, None) => return None,
    };
    let name: String = rest
        .chars()
        .take_while(|c| c.is_alphanumeric() || *c == '_' || *c == '-')
        .collect();
    (!name.is_empty()).then_some(name)
}

/// A path is a candidate if it is an API route or has at least two segments.
fn is_candidate_path(url: &str) -> bool {
    if url.starts_with("/api/") {
        return true;
    }
    let segs = url.split('/').filter(|s| !s.is_empty()).count();
    segs >= 2 && !url.contains(".min.") && !url.contains("//")
}

/// A static option of a UI control: the value a form can actually send.
///
/// Only *static* options are extracted. A `<select>` filled from a remote
/// endpoint at runtime has no value in the source, and the binder must keep
/// that field unknown rather than invent the option the user is supposed to
/// pick.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UiOption {
    /// `name`/`id` of the `<select>` that owns the option.
    pub field: String,
    /// Visible label of the option.
    pub label: String,
    /// `value` the control submits.
    pub value: String,
    /// Source file (diagnostics).
    pub file: String,
}

/// Extract static `<select>` options of every HTML-like source under `root`.
///
/// # Errors
/// Propagates IO failures while walking the tree.
pub fn extract_options(root: impl AsRef<Path>) -> Result<Vec<UiOption>, TtError> {
    let mut out = Vec::new();
    let mut stack = vec![root.as_ref().to_path_buf()];
    let options = HtmlOptions;
    while let Some(dir) = stack.pop() {
        let entries = match std::fs::read_dir(&dir) {
            Ok(e) => e,
            Err(_) => continue,
        };
        for entry in entries.flatten() {
            let path = entry.path();
            let Ok(meta) = entry.metadata() else { continue };
            if meta.is_dir() {
                let name = path.file_name().and_then(|n| n.to_str()).unwrap_or_default();
                if !name.starts_with('.') && name != "node_modules" && name != "target" {
                    stack.push(path);
                }
                continue;
            }
            let ext = path.extension().and_then(|e| e.to_str()).unwrap_or_default();
            if !matches!(ext, "html" | "htm" | "vue") {
                continue;
            }
            let Ok(text) = std::fs::read_to_string(&path) else { continue };
            let file = path
                .strip_prefix(root.as_ref())
                .unwrap_or(&path)
                .to_string_lossy()
                .replace('\\', "/");
            options.scan(&text, &file, &mut out);
        }
    }
    out.sort_by(|a, b| (&a.file, &a.field, &a.value).cmp(&(&b.file, &b.field, &b.value)));
    out.dedup();
    Ok(out)
}

/// Scanner for `<select>`/`<option>` blocks (no HTML parser dependency).
struct HtmlOptions;

impl HtmlOptions {
    fn scan(&self, text: &str, file: &str, out: &mut Vec<UiOption>) {
        let lower = text.to_ascii_lowercase();
        let mut at = 0usize;
        while let Some(rel) = lower[at..].find("<select") {
            let start = at + rel;
            let Some(tag_end_rel) = lower[start..].find('>') else { break };
            let tag = &text[start..start + tag_end_rel];
            let field = attr(tag, "name").or_else(|| attr(tag, "id")).unwrap_or_default();
            let body_start = start + tag_end_rel + 1;
            let body_end = lower[body_start..]
                .find("</select>")
                .map_or(text.len(), |i| body_start + i);
            if !field.is_empty() {
                let body = &text[body_start..body_end];
                self.options(body, file, &field, out);
            }
            at = body_end.max(body_start);
        }
    }

    fn options(&self, body: &str, file: &str, field: &str, out: &mut Vec<UiOption>) {
        let lower = body.to_ascii_lowercase();
        let mut at = 0usize;
        while let Some(rel) = lower[at..].find("<option") {
            let start = at + rel;
            let Some(tag_end_rel) = lower[start..].find('>') else { break };
            let tag = &body[start..start + tag_end_rel];
            let value = attr(tag, "value").unwrap_or_default();
            let label_start = start + tag_end_rel + 1;
            let label_end = lower[label_start..]
                .find("</option>")
                .map_or(body.len(), |i| label_start + i);
            let label = strip_tags(&body[label_start..label_end]);
            if !value.is_empty() && !label.is_empty() {
                out.push(UiOption {
                    field: field.to_owned(),
                    label,
                    value,
                    file: file.to_owned(),
                });
            }
            at = label_end.max(label_start);
        }
    }
}

/// Value of an HTML attribute, single- or double-quoted, case-insensitive name.
fn attr(tag: &str, name: &str) -> Option<String> {
    let lower = tag.to_ascii_lowercase();
    let mut at = 0usize;
    while let Some(rel) = lower[at..].find(name) {
        let start = at + rel;
        let before_ok = start == 0 || !lower.as_bytes()[start - 1].is_ascii_alphanumeric();
        let after = lower[start + name.len()..].trim_start();
        if before_ok {
            if let Some(rest) = after.strip_prefix('=') {
                let rest = rest.trim_start();
                let quote = rest.chars().next()?;
                if quote == '"' || quote == '\'' {
                    let body = &rest[1..];
                    let end = body.find(quote)?;
                    return Some(body[..end].to_owned());
                }
                let end = rest.find(|c: char| c.is_whitespace() || c == '>').unwrap_or(rest.len());
                return Some(rest[..end].to_owned());
            }
        }
        at = start + name.len();
    }
    None
}

fn strip_tags(text: &str) -> String {
    let mut out = String::new();
    let mut inside = false;
    for c in text.chars() {
        match c {
            '<' => inside = true,
            '>' => inside = false,
            c if !inside => out.push(c),
            _ => {}
        }
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_api_path_and_keeps_context() {
        let text = r##"
            $("#refresh_booking_contacts_button").click(function () { refresh_booking_contacts(); });
            function refresh_booking_contacts() {
                $.ajax({ url: "/api/v1/contactservice/contacts/account/" + sessionStorage.getItem("client_id") });
            }
        "##;
        let facts = scan_file(text, Path::new("/ui/client_ticket_book.js"));
        assert_eq!(facts.len(), 1, "{facts:?}");
        assert_eq!(facts[0].url, "/api/v1/contactservice/contacts/account/");
        assert_eq!(facts[0].trigger, Trigger::Action);
        let t = &facts[0].tokens;
        assert!(t.contains(&"contact".to_owned()), "{t:?}");
        // "booking" and "contacts" stem to "book" / "contact"
        assert!(t.contains(&"book".to_owned()), "{t:?}");
        // file name tokens are folded in as evidence
        assert!(t.contains(&"ticket".to_owned()), "{t:?}");
        // the enclosing function name is action evidence, not page evidence
        assert!(facts[0].action_tokens.contains(&"refresh".to_owned()), "{:?}", facts[0].action_tokens);
        assert!(facts[0].page_tokens.contains(&"book".to_owned()));
    }

    #[test]
    fn reads_http_verb_and_trigger() {
        let text = r##"
            $("#pay_button").click(function () {
                $.ajax({ type: "post", contentType: "application/json", url: "/api/v1/inside_pay_service/inside_payment" });
            });
            $(document).ready(function () {
                $.get("/api/v1/inside_pay_service/inside_payment/account");
            });
        "##;
        let facts = scan_file(text, Path::new("/ui/client_order_list.js"));
        let post = facts.iter().find(|f| f.url.ends_with("inside_payment")).expect("post fact");
        assert_eq!(post.http.as_deref(), Some("POST"));
        assert_eq!(post.trigger, Trigger::Action);
        assert_eq!(post.page_tokens, vec!["client", "order", "list"]);
        let get = facts.iter().find(|f| f.url.ends_with("account")).expect("get fact");
        assert_eq!(get.trigger, Trigger::Load);
    }

    #[test]
    fn ignores_non_paths_and_relative_noise() {
        let facts = scan_file(r#"var a = 1/2; var b = "a/b"; css: url(/img/x.png)"#, Path::new("a.js"));
        assert!(facts.iter().all(|f| !f.url.contains("1/2")));
    }

    #[test]
    fn concatenated_url_keeps_static_prefix() {
        let facts = scan_file("url: '/api/v1/consignservice/consigns/account/' + id", Path::new("x.js"));
        assert_eq!(facts[0].url, "/api/v1/consignservice/consigns/account/");
    }
}
