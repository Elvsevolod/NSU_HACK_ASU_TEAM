//! Tree-sitter based parser for Python source into semarch-core IR.
//!
//! The frontend has no knowledge of Flask or any framework. It exposes
//! syntax-level facts: imports, decorators, functions/methods, call sites,
//! member access, literals, and if/while guard conditions. All spans point
//! into the original source so anchors stay byte-verified.

#![deny(clippy::correctness)]
#![warn(clippy::suspicious, clippy::complexity, clippy::perf)]

use semarch_core::ids::FileId;
use semarch_core::{
    AnnotationFact, BinaryOp, CallSite, Capability, FrontendError, Function,
    GuardCondition, ImportFact, Language, LanguageFrontend, ParsedFile, ParseContext,
    Result, SourceSpan, SymbolKind, UnaryOp, ValueExpr,
};
use tree_sitter::{Node, Parser};

pub mod lowering;

/// The v0 capability matrix: facts emitted whenever the construct exists.
/// Assignments, branches, returns and loops are all materialized by the
/// lowering pass, so they are claimed (mirrors the Java matrix for parity).
pub const CAPABILITIES: &[Capability] = &[
    Capability::Declarations,
    Capability::Parameters,
    Capability::CallSites,
    Capability::Literals,
    Capability::MemberAccess,
    Capability::Assignments,
    Capability::IfElse,
    Capability::ReturnThrow,
    Capability::BasicLoops,
    Capability::AnnotationsDecorators,
    Capability::Imports,
    Capability::SourceSpans,
];

/// Python frontend over the pinned `tree-sitter-python` grammar.
pub struct PythonFrontend {
    parser: Parser,
}

impl PythonFrontend {
    /// Construct the frontend (grammar is loaded once and reused).
    ///
    /// # Errors
    /// Fails if the pinned grammar refuses the pinned runtime (ABI
    /// mismatch); this is exactly the spike failure mode recorded in
    /// `docs/adr/0002-grammar-pin.md`.
    pub fn new() -> Result<Self> {
        let mut parser = Parser::new();
        parser.set_language(&tree_sitter_python::LANGUAGE.into()).map_err(
            |e| FrontendError {
                language: Language::Python,
                message: format!("grammar/runtime ABI mismatch: {e}"),
                span: None,
            },
        )?;
        Ok(Self { parser })
    }
}

/// Per-file accumulation, mirroring the Java frontend's `Out`.
#[derive(Default)]
struct Out {
    imports: Vec<ImportFact>,
    decorators: Vec<AnnotationFact>,
    functions: Vec<Function>,
    callsites: Vec<CallSite>,
    guards: Vec<GuardCondition>,
    /// Return expressions collected during the walk; the owning function is
    /// resolved afterwards by innermost-span containment (same rule as the
    /// Java frontend).
    returns: Vec<(ValueExpr, SourceSpan)>,
}

fn walk(
    node: Node<'_>,
    stack: &mut Vec<String>,
    in_body: bool,
    ctx: &mut ParseContext<'_>,
    out: &mut Out,
    src: &str,
) {
    match node.kind() {
        "module" | "block" | "suite" | "class_definition_body" => {
            for_each_child(node, stack, in_body, ctx, out, src);
        }
        "import_statement" => {
            let mut cur = node.walk();
            for child in node.children(&mut cur) {
                match child.kind() {
                    "dotted_name" => {
                        out.imports.push(ImportFact {
                            path: node_text(child, src),
                            alias: None,
                            span: span_of(child, ctx.file),
                        });
                    }
                    "aliased_import" => {
                        let name =
                            child.child_by_field_name("name").map(|n| node_text(n, src));
                        let alias =
                            child.child_by_field_name("alias").map(|n| node_text(n, src));
                        out.imports.push(ImportFact {
                            path: name.unwrap_or_default(),
                            alias,
                            span: span_of(child, ctx.file),
                        });
                    }
                    _ => {}
                }
            }
        }
        "import_from_statement" => {
            // `from module import name [as alias]` → one fact per imported
            // name, path joined as `module.name`.
            let module_node = node.child_by_field_name("module_name");
            let module = module_node
                .map(|m| {
                    if m.kind() == "relative_import" {
                        normalize_relative(&node_text(m, src))
                    } else {
                        node_text(m, src)
                    }
                })
                .unwrap_or_default();
            let mut cur = node.walk();
            for child in node.children(&mut cur) {
                if child == module_node.unwrap_or(child) && module_node.is_some() {
                    continue; // module path is not an imported name
                }
                match child.kind() {
                    "dotted_name" | "aliased_import" => {
                        let (name, alias) = match child.kind() {
                            "dotted_name" => (Some(node_text(child, src)), None),
                            _ => (
                                child.child_by_field_name("name").map(|n| node_text(n, src)),
                                child.child_by_field_name("alias").map(|n| node_text(n, src)),
                            ),
                        };
                        let mut path = module.clone();
                        if !path.is_empty() {
                            path.push('.');
                        }
                        path.push_str(&name.unwrap_or_default());
                        out.imports.push(ImportFact {
                            path,
                            alias,
                            span: span_of(child, ctx.file),
                        });
                    }
                    "wildcard_import" => {
                        out.imports.push(ImportFact {
                            path: format!("{module}.*"),
                            alias: None,
                            span: span_of(child, ctx.file),
                        });
                    }
                    _ => {}
                }
            }
        }
        "decorated_definition" => {
            // Decorators attach to the following (single) definition.
            let children: Vec<Node<'_>> = {
                let mut cur = node.walk();
                node.children(&mut cur).collect()
            };
            let decorators: Vec<Node<'_>> = children
                .iter()
                .copied()
                .filter(|n| n.kind() == "decorator")
                .collect();
            let definition = children.iter().copied().find(|n| {
                n.kind() == "function_definition" || n.kind() == "class_definition"
            });
            if definition.is_none() {
                ctx.diagnose(
                    "decorator without attached definition",
                    Some(span_of(node, ctx.file)),
                );
                return;
            }
            for_each_child(node, stack, in_body, ctx, out, src);
            // Decorators of *functions* are captured after the definition is
            // walked, so annotation order is definition-stable (class
            // decorators are not claimed in v0).
            if matches!(definition.map(|d| d.kind()), Some("function_definition")) {
                for d in decorators {
                    let name = decorator_name(d, src);
                    let args = decorator_args(d, src);
                    out.decorators.push(AnnotationFact {
                        name,
                        args,
                        span: span_of(d, ctx.file),
                    });
                }
            }
        }
        "class_definition" => {
            let Some(name) = field_name(node, src) else {
                ctx.diagnose("class without a name", Some(span_of(node, ctx.file)));
                return;
            };
            stack.push(name);
            for_each_child(node, stack, in_body, ctx, out, src);
            stack.pop();
        }
        "function_definition" => {
            let Some(name) = field_name(node, src) else {
                ctx.diagnose("function without a name", Some(span_of(node, ctx.file)));
                return;
            };
            let param_names = match node.child_by_field_name("parameters") {
                Some(p) => {
                    let mut names = Vec::new();
                    let mut cur = p.walk();
                    for ch in p.children(&mut cur) {
                        if ch.kind() == "identifier" && names.len() < usize::from(u16::MAX) {
                            names.push(node_text(ch, src));
                        }
                    }
                    names
                }
                None => Vec::new(),
            };
            let params = param_names.len().min(u16::MAX as usize) as u16;
            out.functions.push(Function {
                id: ctx.alloc.next_function(),
                qualified: if stack.is_empty() { Some(name.clone()) } else { Some(stack.join(".")) },
                name,
                kind: if stack.is_empty() {
                    SymbolKind::Function
                } else {
                    SymbolKind::Method
                },
                span: span_of(node, ctx.file),
                params: (0..params)
                    .map(|i| ValueExpr::Parameter { index: i })
                    .collect(),
                param_names,
                // Filled by the span-containment post-pass after the walk.
                returns: Vec::new(),
                is_decl_only: false,
            });
            if let Some(body) = node.child_by_field_name("body") {
                for_each_child(body, stack, true, ctx, out, src);
            }
        }
        "call" if in_body => {
            collect_callsite(node, ctx, out, src);
        }
        "if_statement" => {
            let cond = node.child_by_field_name("condition");
            if let Some(cond) = cond {
                let condition = expression(cond, ctx, out, src);
                out.guards.push(GuardCondition {
                    condition,
                    span: span_of(cond, ctx.file),
                    then_span: node
                        .child_by_field_name("consequence")
                        .map(|c| span_of(c, ctx.file)),
                    else_span: node
                        .child_by_field_name("alternative")
                        .map(|a| span_of(a, ctx.file)),
                    body_span: Some(span_of(node, ctx.file)),
                    body_always_runs: false,
                });
            }
            skip_child_walk(node, cond, stack, ctx, out, src);
        }
        "elif_clause" => {
            let cond = node.child_by_field_name("condition");
            if let Some(cond) = cond {
                let condition = expression(cond, ctx, out, src);
                out.guards.push(GuardCondition {
                    condition,
                    span: span_of(cond, ctx.file),
                    then_span: node
                        .child_by_field_name("consequence")
                        .map(|c| span_of(c, ctx.file)),
                    else_span: None,
                    body_span: Some(span_of(node, ctx.file)),
                    body_always_runs: false,
                });
            }
            skip_child_walk(node, cond, stack, ctx, out, src);
        }
        "while_statement" => {
            let cond = node.child_by_field_name("condition");
            if let Some(cond) = cond {
                let condition = expression(cond, ctx, out, src);
                out.guards.push(GuardCondition {
                    condition,
                    span: span_of(cond, ctx.file),
                    // A `while` body runs only while the condition holds.
                    then_span: node.child_by_field_name("body").map(|b| span_of(b, ctx.file)),
                    else_span: None,
                    body_span: Some(span_of(node, ctx.file)),
                    body_always_runs: false,
                });
            }
            skip_child_walk(node, cond, stack, ctx, out, src);
        }
        "return_statement" => {
            // Children: `return` keyword, optional expression.
            let mut cursor = node.walk();
            let expr_node = node
                .children(&mut cursor)
                .find(|c| c.kind() != "return");
            if let Some(e) = expr_node {
                let value = expression(e, ctx, out, src);
                out.returns.push((value, span_of(e, ctx.file)));
            }
        }
        "comment" => {}
        "ERROR" => {
            ctx.diagnose(
                "unparsed fragment (tree-sitter ERROR node)",
                Some(span_of(node, ctx.file)),
            );
        }
        _ => for_each_child(node, stack, in_body, ctx, out, src),
    }
}

fn for_each_child<'c>(
    node: Node<'_>,
    stack: &mut Vec<String>,
    in_body: bool,
    ctx: &mut ParseContext<'c>,
    out: &mut Out,
    src: &str,
) {
    let mut cursor = node.walk();
    let children: Vec<Node<'_>> = node.children(&mut cursor).collect();
    for child in children {
        walk(child, stack, in_body, ctx, out, src);
    }
}

/// Walk all children except one (used to avoid re-registered guard
/// condition subtrees).
fn skip_child_walk<'c>(
    node: Node<'_>,
    skip: Option<Node<'_>>,
    stack: &mut Vec<String>,
    ctx: &mut ParseContext<'c>,
    out: &mut Out,
    src: &str,
) {
    let mut cursor = node.walk();
    let children: Vec<Node<'_>> = node.children(&mut cursor).collect();
    for child in children {
        if let Some(skip) = skip {
            if child == skip {
                continue;
            }
        }
        walk(child, stack, true, ctx, out, src);
    }
}

pub(crate) fn field_name(node: Node<'_>, src: &str) -> Option<String> {
    node.child_by_field_name("name")
        .and_then(|n| n.utf8_text(src.as_bytes()).ok())
        .map(str::to_owned)
}

pub(crate) fn node_text(node: Node<'_>, src: &str) -> String {
    node.utf8_text(src.as_bytes()).unwrap_or_default().to_owned()
}

pub(crate) fn span_of(node: Node<'_>, file: FileId) -> SourceSpan {
    SourceSpan {
        file,
        start_byte: node.start_byte() as u32,
        end_byte: node.end_byte() as u32,
        start_row: node.start_position().row as u32,
        start_col: node.start_position().column as u32,
        end_row: node.end_position().row as u32,
        end_col: node.end_position().column as u32,
    }
}

fn normalize_relative(text: &str) -> String {
    // `..foo` → `RELATIVE(..).foo`-style marker kept raw for v0.
    text.trim().to_owned()
}

fn decorator_name(node: Node<'_>, src: &str) -> String {
    // decorator node: child 0 == "@", child 1 == expression
    // (identifier/attribute/call). Dotted name of the function part.
    let Some(inner) = node.child(1) else {
        return String::new();
    };
    match inner.kind() {
        "identifier" | "attribute" => dotted_name(inner, src),
        "call" => inner
            .child_by_field_name("function")
            .map(|f| dotted_name(f, src))
            .unwrap_or_default(),
        _ => node_text(inner, src),
    }
}

/// Raw decorator arguments as written (inside the parentheses), `None` when
/// there are none.
fn decorator_args(node: Node<'_>, src: &str) -> Option<String> {
    let inner = node.child(1)?;
    if inner.kind() != "call" {
        return None;
    }
    let arglist = inner.child_by_field_name("arguments")?;
    let text = node_text(arglist, src);
    let stripped = text
        .trim()
        .strip_prefix('(')
        .and_then(|t| t.strip_suffix(')'))
        .map(str::trim)
        .unwrap_or(text.as_str());
    if stripped.is_empty() {
        None
    } else {
        Some(stripped.to_owned())
    }
}

fn dotted_name(node: Node<'_>, src: &str) -> String {
    match node.kind() {
        "identifier" => node_text(node, src),
        "attribute" => {
            let base = node.child_by_field_name("object").map(|o| dotted_name(o, src));
            let attr = node
                .child_by_field_name("attribute")
                .map(|a| node_text(a, src))
                .unwrap_or_default();
            match base {
                Some(b) if !b.is_empty() => format!("{b}.{attr}"),
                _ => attr,
            }
        }
        _ => node_text(node, src),
    }
}

fn collect_callsite(node: Node<'_>, ctx: &mut ParseContext<'_>, out: &mut Out, src: &str) {
    // Fields: `function`, `arguments`.
    let Some(fun) = node.child_by_field_name("function") else {
        ctx.diagnose("call without function", Some(span_of(node, ctx.file)));
        return;
    };
    let (callee, receiver, name_span) = match fun.kind() {
        "identifier" => (node_text(fun, src), None, Some(span_of(fun, ctx.file))),
        "attribute" => {
            let name_node = fun.child_by_field_name("attribute");
            let callee = name_node.map(|a| node_text(a, src)).unwrap_or_default();
            let receiver = fun
                .child_by_field_name("object")
                .map(|o| expression(o, ctx, out, src));
            (callee, receiver, name_node.map(|a| span_of(a, ctx.file)))
        }
        k => {
            ctx.diagnose(
                format!("callee `{k}` is not a plain name/attribute (dynamic call)"),
                Some(span_of(node, ctx.file)),
            );
            (String::new(), None, None)
        }
    };
    let mut args = Vec::new();
    if let Some(arglist) = node.child_by_field_name("arguments") {
        let mut cur = arglist.walk();
        for a in arglist.children(&mut cur) {
            if matches!(a.kind(), "(" | ")" | "," | "comment") {
                continue;
            }
            if a.kind() == "keyword_argument" {
                ctx.diagnose(
                    "keyword argument ignored in v0 (dynamic call shape)",
                    Some(span_of(a, ctx.file)),
                );
                continue;
            }
            args.push(expression(a, ctx, out, src));
        }
    }
    let id = ctx.alloc.next_callsite();
    out.callsites.push(CallSite {
        id,
        callee,
        receiver,
        args,
        span: span_of(node, ctx.file),
        name_span,
    });
}

/// Map an expression node to `ValueExpr`; calls encountered here are
/// registered as call sites (inner-first), mirroring the Java frontend.
fn expression(
    node: Node<'_>,
    ctx: &mut ParseContext<'_>,
    out: &mut Out,
    src: &str,
) -> ValueExpr {
    match node.kind() {
        "identifier" => ValueExpr::Symbolic { name: node_text(node, src) },
        "string" | "string_start" => ValueExpr::Str { value: unquote(&node_text(node, src)) },
        "integer" => match node_text(node, src).replace('_', "").parse::<i64>() {
            Ok(v) => ValueExpr::Int { value: v },
            Err(_) => {
                ctx.diagnose(
                    format!("unparsed integer literal `{}`", node_text(node, src)),
                    Some(span_of(node, ctx.file)),
                );
                ValueExpr::Unknown
            }
        },
        "float" => match node_text(node, src).replace('_', "").parse::<f64>() {
            Ok(v) => ValueExpr::Float { value: v },
            Err(_) => {
                ctx.diagnose(
                    format!("unparsed float literal `{}`", node_text(node, src)),
                    Some(span_of(node, ctx.file)),
                );
                ValueExpr::Unknown
            }
        },
        "true" | "True" => ValueExpr::Bool { value: true },
        "false" | "False" => ValueExpr::Bool { value: false },
        "none" | "None" => ValueExpr::Null,
        "attribute" => {
            let base = node
                .child_by_field_name("object")
                .map_or(ValueExpr::Unknown, |o| expression(o, ctx, out, src));
            let name = node
                .child_by_field_name("attribute")
                .map(|f| node_text(f, src))
                .unwrap_or_default();
            ValueExpr::Field {
                base: Box::new(base),
                name,
            }
        }
        "call" => {
            collect_callsite(node, ctx, out, src);
            let id = out
                .callsites
                .last()
                .map_or_else(|| ctx.alloc.next_callsite(), |cs| cs.id);
            ValueExpr::CallResult { callsite: id }
        }
        "binary_operator" | "boolean_operator" | "comparison_operator" => {
            let parts: Vec<Node<'_>> = {
                let mut cur = node.walk();
                node.children(&mut cur).collect()
            };
            let lhs = parts
                .first()
                .map_or(ValueExpr::Unknown, |l| expression(*l, ctx, out, src));
            let rhs = parts
                .get(2)
                .map_or(ValueExpr::Unknown, |r| expression(*r, ctx, out, src));
            let op = parts
                .get(1)
                .and_then(|o| o.utf8_text(src.as_bytes()).ok())
                .unwrap_or_default()
                .to_owned();
            match map_binop(&op) {
                Some(bin) => ValueExpr::Binary {
                    op: bin,
                    lhs: Box::new(lhs),
                    rhs: Box::new(rhs),
                },
                None => {
                    ctx.diagnose(
                        format!("unmapped binary operator `{op}`"),
                        Some(span_of(node, ctx.file)),
                    );
                    ValueExpr::Unknown
                }
            }
        }
        "unary_operator" | "not_operator" => {
            let mut cur = node.walk();
            let parts: Vec<Node<'_>> = node.children(&mut cur).collect();
            let op = parts
                .first()
                .and_then(|o| o.utf8_text(src.as_bytes()).ok())
                .unwrap_or_default()
                .to_owned();
            let operand = parts
                .last()
                .map_or(ValueExpr::Unknown, |o| expression(*o, ctx, out, src));
            match op.as_str() {
                "not" | "!" => ValueExpr::Unary {
                    op: UnaryOp::Not,
                    operand: Box::new(operand),
                },
                "-" => ValueExpr::Unary {
                    op: UnaryOp::Negate,
                    operand: Box::new(operand),
                },
                _ => {
                    ctx.diagnose(
                        format!("unmapped unary operator `{op}`"),
                        Some(span_of(node, ctx.file)),
                    );
                    ValueExpr::Unknown
                }
            }
        }
        "parenthesized_expression" | "generator" => {
            let parts: Vec<Node<'_>> = {
                let mut cur = node.walk();
                node.children(&mut cur).collect()
            };
            parts
                .into_iter()
                .find(|k| !(k.kind() == "(" || k.kind() == ")"))
                .map_or(ValueExpr::Unknown, |inner| expression(inner, ctx, out, src))
        }
        "conditional_expression" => {
            // v0: model as branch condition value (first child).
            let mut cur = node.walk();
            let first = if cur.goto_first_child() { Some(cur.node()) } else { None };
            first.map_or(ValueExpr::Unknown, |c| expression(c, ctx, out, src))
        }
        k => {
            ctx.diagnose(
                format!("unmapped expression `{k}`"),
                Some(span_of(node, ctx.file)),
            );
            ValueExpr::Unknown
        }
    }
}

pub(crate) fn map_binop(op: &str) -> Option<BinaryOp> {
    Some(match op {
        "==" => BinaryOp::Eq,
        "!=" => BinaryOp::Ne,
        "<" => BinaryOp::Lt,
        "<=" => BinaryOp::Le,
        ">" | "<<=" => BinaryOp::Gt,
        ">=" => BinaryOp::Ge,
        "and" => BinaryOp::And,
        "or" => BinaryOp::Or,
        "+" => BinaryOp::Add,
        "-" => BinaryOp::Sub,
        "*" => BinaryOp::Mul,
        "/" => BinaryOp::Div,
        "%" => BinaryOp::Rem,
        _ => return None,
    })
}

pub(crate) fn unquote(s: &str) -> String {
    let t = s.trim();
    if t.len() >= 2
        && (t.starts_with('"') || t.starts_with('\''))
        && t.ends_with(t.chars().next().unwrap_or('"'))
    {
        t[1..t.len() - 1].to_owned()
    } else {
        t.to_owned()
    }
}

impl LanguageFrontend for PythonFrontend {
    fn id(&self) -> &'static str {
        "frontend-python"
    }

    fn language(&self) -> Language {
        Language::Python
    }

    fn capabilities(&self) -> &'static [Capability] {
        CAPABILITIES
    }

    fn parse(&mut self, ctx: &mut ParseContext<'_>, source: &str) -> Result<ParsedFile> {
        let parsed = match self.parser.parse(source, None) {
            Some(t) => t,
            None => {
                ctx.diagnose("the parser produced no tree", None);
                return Ok(ParsedFile {
                    file: ctx.file,
                    language: Language::Python,
                    module: None,
                    imports: Vec::new(),
                    annotations: Vec::new(),
                    functions: Vec::new(),
                    callsites: Vec::new(),
                    guard_conditions: Vec::new(),
                    bodies: Vec::new(),
                });
            }
        };

        let mut out = Out::default();
        let mut stack = Vec::with_capacity(8);
        walk(parsed.root_node(), &mut stack, false, ctx, &mut out, source);

        let mut functions = out.functions;
        assign_returns(&mut functions, out.returns);
        // The ordered bodies are additive: they read the call sites the flat
        // walk registered (by span) and never add or reorder flat facts.
        let bodies = lowering::lower_bodies(
            parsed.root_node(),
            source,
            ctx.file,
            &functions,
            &out.callsites,
            ctx.alloc,
        );

        Ok(ParsedFile {
            file: ctx.file,
            language: Language::Python,
            module: None,
            imports: out.imports,
            annotations: out.decorators,
            functions,
            callsites: out.callsites,
            guard_conditions: out.guards,
            bodies,
        })
    }
}

/// Attach return expressions to their owning function by innermost span
/// containment (identical rule and provenance as the Java frontend).
fn assign_returns(functions: &mut [Function], returns: Vec<(ValueExpr, SourceSpan)>) {
    for (value, span) in returns {
        let mut best: Option<usize> = None;
        for (i, f) in functions.iter().enumerate() {
            if !covers(&f.span, &span) {
                continue;
            }
            let is_innermost = best.is_none_or(|b| {
                f.span.start_byte >= functions[b].span.start_byte
                    && f.span.end_byte <= functions[b].span.end_byte
            });
            if is_innermost {
                best = Some(i);
            }
        }
        if let Some(i) = best {
            functions[i].returns.push(value);
        }
    }
}

/// `outer.start <= inner.start && inner.end <= outer.end`.
fn covers(outer: &SourceSpan, inner: &SourceSpan) -> bool {
    outer.start_byte <= inner.start_byte
        && inner.end_byte <= outer.end_byte
        && outer.file == inner.file
}
