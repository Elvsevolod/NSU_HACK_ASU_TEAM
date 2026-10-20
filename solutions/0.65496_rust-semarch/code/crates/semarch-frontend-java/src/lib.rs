//! Tree-sitter based parser for Java source into semarch-core IR.
//!
//! The frontend has no knowledge of Spring or any framework. It exposes
//! syntax-level facts: package/imports, annotations, methods/constructors,
//! call sites, member access, literals, and if/do guard conditions. All
//! spans point into the original source so anchors stay byte-verified.

#![deny(clippy::correctness)]
#![warn(clippy::suspicious, clippy::complexity, clippy::perf)]

use semarch_core::ids::FileId;
use semarch_core::{
    AnnotationFact, BinaryOp, CallSite, Capability, FrontendError, Function,
    GuardCondition, ImportFact, Language, LanguageFrontend, ModuleDecl, ParsedFile,
    ParseContext, Result, SourceSpan, SymbolKind, UnaryOp, ValueExpr,
};
use tree_sitter::{Node, Parser};

pub mod lowering;

/// The v0 capability matrix: facts emitted whenever the construct exists.
/// Assignments, branches, returns and loops are all materialized by the
/// lowering pass, so they are claimed.
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

/// Java frontend over the pinned `tree-sitter-java` grammar.
pub struct JavaFrontend {
    parser: Parser,
}

impl JavaFrontend {
    /// Construct the frontend (grammar is loaded once and reused).
    ///
    /// # Errors
    /// Fails if the pinned grammar refuses the pinned runtime (ABI
    /// mismatch); this is exactly the spike failure mode recorded in
    /// `docs/adr/0002-grammar-pin.md`.
    pub fn new() -> Result<Self> {
        let mut parser = Parser::new();
        parser.set_language(&tree_sitter_java::LANGUAGE.into()).map_err(
            |e| FrontendError {
                language: Language::Java,
                message: format!("grammar/runtime ABI mismatch: {e}"),
                span: None,
            },
        )?;
        Ok(Self { parser })
    }
}

#[derive(Default)]
struct Out {
    module: Option<ModuleDecl>,
    imports: Vec<ImportFact>,
    annotations: Vec<AnnotationFact>,
    functions: Vec<Function>,
    callsites: Vec<CallSite>,
    guards: Vec<GuardCondition>,
    /// Return expressions collected during the walk; the owning function is
    /// resolved afterwards by innermost-span containment (language-neutral,
    /// same rule as call-site ownership).
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
        "program" | "block" | "class_body" | "interface_body" | "enum_body" => {
            for_each_child(node, stack, in_body, ctx, out, src);
        }
        "package_declaration" => {
            let dotted = dotted(node, src);
            out.module = Some(ModuleDecl {
                id: semarch_core::ids::ModuleId::from_raw(ctx.file.raw()),
                path: dotted,
            });
        }
        "import_declaration" => {
            out.imports.push(import_fact(node, ctx, src));
        }
        "annotation" | "marker_annotation" => {
            let name_node = node
                .child_by_field_name("name")
                .unwrap_or(node);
            let name = dotted(name_node, src);
            let args = node.child_by_field_name("arguments").map(|a| node_text(a, src));
            out.annotations.push(AnnotationFact {
                name,
                args,
                span: span_of(node, ctx.file),
            });
        }
        "class_declaration" | "interface_declaration" | "enum_declaration"
        | "record_declaration" => {
            let Some(name) = field_name(node, src) else {
                ctx.diagnose("declaration without a name", Some(span_of(node, ctx.file)));
                return;
            };
            stack.push(name);
            for_each_child(node, stack, in_body, ctx, out, src);
            stack.pop();
        }
        "method_declaration" | "constructor_declaration" => {
            let Some(name) = field_name(node, src) else {
                ctx.diagnose("method without a name", Some(span_of(node, ctx.file)));
                return;
            };

            // NOTE: tree-sitter-java gives `method_declaration` the fields
            // dimensions/name/parameters/type/type_parameters/body — there is
            // no `modifiers` field, so annotations are reached by walking all
            // children (the `annotation` arm captures them).
            for_each_child(node, stack, true, ctx, out, src);

            let (params, param_names) = match node.child_by_field_name("parameters") {
                Some(p) => {
                    let mut n = 0u16;
                    let mut names = Vec::new();
                    let mut cur = p.walk();
                    for ch in p.children(&mut cur) {
                        if ch.kind() == "formal_parameter" && n < u16::MAX {
                            n += 1;
                            // tree-sitter-java: `formal_parameter` has a
                            // `name` field → identifier.
                            let name = ch
                                .child_by_field_name("name")
                                .map(|id| node_text(id, src))
                                .unwrap_or_default();
                            names.push(name);
                        }
                    }
                    (n, names)
                }
                None => (0, Vec::new()),
            };

            let body = node.child_by_field_name("body");
            out.functions.push(Function {
                id: ctx.alloc.next_function(),
                qualified: qualified(stack, &name),
                name,
                kind: if node.kind() == "method_declaration" {
                    SymbolKind::Method
                } else {
                    SymbolKind::Function
                },
                span: span_of(node, ctx.file),
                params: (0..params)
                    .map(|i| ValueExpr::Parameter { index: i })
                    .collect(),
                param_names,
                // Filled by the span-containment post-pass after the walk.
                returns: Vec::new(),
                is_decl_only: body.is_none(),
            });
        }
        "method_invocation" if in_body => {
            collect_callsite(node, ctx, out, src);
        }
        "if_statement" => {
            // tree-sitter-java fields: `condition`, `consequence`,
            // `alternative`. The guarded body is the consequence *only*: the
            // predicate is evaluated before the branch, and the `else` branch
            // runs when the predicate does not hold, so neither belongs to the
            // region this condition protects.
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
            walk_children_except(node, cond, stack, ctx, out, src);
        }
        "do_statement" => {
            // `do { body } while (cond);` — the body runs at least once, so
            // this condition guards *nothing*: a call site inside the body must
            // never be pruned by it. The condition is still recorded so the
            // audit trail can show that it was seen and why it does not guard.
            let cond = node.child_by_field_name("condition");
            if let Some(cond) = cond {
                let condition = expression(cond, ctx, out, src);
                out.guards.push(GuardCondition {
                    condition,
                    span: span_of(cond, ctx.file),
                    then_span: None,
                    else_span: None,
                    body_span: Some(span_of(node, ctx.file)),
                    body_always_runs: true,
                });
            }
            walk_children_except(node, cond, stack, ctx, out, src);
        }
        "return_statement" => {
            // Children: `return` keyword, optional expression, `;`.
            let mut cursor = node.walk();
            let expr_node = node
                .children(&mut cursor)
                .find(|c| c.kind() != "return" && c.kind() != ";");
            if let Some(e) = expr_node {
                let value = expression(e, ctx, out, src);
                out.returns.push((value, span_of(e, ctx.file)));
            }
        }
        "comment" | "line_comment" | "block_comment" => {}
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

/// Walk every child of `node` except `skip` (typically the condition, already
/// consumed by the expression walk). Prevents a call site inside the predicate
/// from being registered twice.
fn walk_children_except<'c>(
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
        if skip.is_some_and(|s| s == child) {
            continue;
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

/// Re-assemble an identifier chain (`a.b.C`) from its identifier children.
fn dotted(node: Node<'_>, src: &str) -> String {
    let mut out = String::new();
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        match child.kind() {
            "identifier" | "type_identifier" | "scoped_identifier" | "dotted_name"
            | "package_identifier" => {
                let piece = dotted(child, src);
                if !piece.is_empty() && !matches!(piece.as_str(), "import" | "static") {
                    if !out.is_empty() {
                        out.push('.');
                    }
                    out.push_str(&piece);
                }
            }
            "comment" => {}
            k if k != node.kind() => {}
            _ => {}
        }
    }
    if out.is_empty() {
        let raw = node_text(node, src);
        out = raw.replace("import ", "").replace("static ", "");
    }
    out
}

fn import_fact(node: Node<'_>, ctx: &mut ParseContext<'_>, src: &str) -> ImportFact {
    // `import com.foo.Bar;` | `import static com.foo.Bar.baz;`
    let raw = node_text(node, src);
    let is_static = raw.contains("static");
    let span = span_of(node, ctx.file);
    let path = raw
        .trim()
        .trim_start_matches("import")
        .trim()
        .trim_start_matches("static")
        .trim()
        .trim_end_matches(';')
        .to_owned();
    ImportFact {
        path,
        alias: is_static.then(|| "static".to_owned()),
        span,
    }
}

fn qualified(stack: &[String], name: &str) -> Option<String> {
    if stack.is_empty() {
        return Some(name.to_owned()); // top-level function
    }
    Some(stack.join("."))
}

fn collect_callsite(node: Node<'_>, ctx: &mut ParseContext<'_>, out: &mut Out, src: &str) {
    // Fields: `object` (optional), `name`, `arguments`.
    let name_node = node.child_by_field_name("name");
    let callee = name_node
        .map(|n| node_text(n, src))
        .unwrap_or_default();
    let name_span = name_node.map(|n| span_of(n, ctx.file));
    let receiver = node.child_by_field_name("object").map(|obj| expression(obj, ctx, out, src));
    let mut args = Vec::new();
    if let Some(arglist) = node.child_by_field_name("arguments") {
        let mut cur = arglist.walk();
        for a in arglist.children(&mut cur) {
            if matches!(a.kind(), "(" | ")" | "," | "comment") {
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

/// Map an expression node to `ValueExpr`; method invocations encountered
/// here are registered as call sites (inner-first), so a receiver `f().g`
/// refers to the inner call result.
fn expression(
    node: Node<'_>,
    ctx: &mut ParseContext<'_>,
    out: &mut Out,
    src: &str,
) -> ValueExpr {
    match node.kind() {
        "identifier" => ValueExpr::Symbolic { name: node_text(node, src) },
        "string_literal" => ValueExpr::Str { value: unquote(&node_text(node, src)) },
        "decimal_integer_literal" | "hex_integer_literal" | "octal_integer_literal"
        | "binary_integer_literal" => {
            match node_text(node, src).trim_end_matches(['l', 'L']).parse::<i64>() {
                Ok(v) => ValueExpr::Int { value: v },
                Err(_) => {
                    ctx.diagnose(
                        format!("unparsed integer literal `{}`", node_text(node, src)),
                        Some(span_of(node, ctx.file)),
                    );
                    ValueExpr::Unknown
                }
            }
        }
        "decimal_floating_point_literal" => {
            match node_text(node, src).trim_end_matches(['f', 'F', 'd', 'D']).parse::<f64>() {
                Ok(v) => ValueExpr::Float { value: v },
                Err(_) => {
                    ctx.diagnose(
                        format!("unparsed float literal `{}`", node_text(node, src)),
                        Some(span_of(node, ctx.file)),
                    );
                    ValueExpr::Unknown
                }
            }
        }
        "true" => ValueExpr::Bool { value: true },
        "false" => ValueExpr::Bool { value: false },
        "null_literal" => ValueExpr::Null,
        "parenthesized_expression" => {
            let parts: Vec<Node<'_>> = {
                let mut cur = node.walk();
                node.children(&mut cur).collect()
            };
            parts
                .into_iter()
                .find(|k| !(k.kind() == "(" || k.kind() == ")"))
                .map_or(ValueExpr::Unknown, |inner| expression(inner, ctx, out, src))
        }
        "field_access" => {
            let base = node
                .child_by_field_name("object")
                .map_or(ValueExpr::Unknown, |o| expression(o, ctx, out, src));
            let name = node
                .child_by_field_name("field")
                .map(|f| node_text(f, src))
                .unwrap_or_default();
            ValueExpr::Field {
                base: Box::new(base),
                name,
            }
        }
        "method_invocation" => {
            collect_callsite(node, ctx, out, src);
            let id = out
                .callsites
                .last()
                .map_or_else(|| ctx.alloc.next_callsite(), |cs| cs.id);
            ValueExpr::CallResult { callsite: id }
        }
        "binary_expression" => {
            let mut cur = node.walk();
            let parts: Vec<Node<'_>> = node.children(&mut cur).collect();
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
        "unary_expression" => {
            let mut cur = node.walk();
            let parts: Vec<Node<'_>> = node.children(&mut cur).collect();
            let op = parts
                .first()
                .and_then(|o| o.utf8_text(src.as_bytes()).ok())
                .unwrap_or_default()
                .to_owned();
            let operand = parts
                .get(1)
                .map_or(ValueExpr::Unknown, |o| expression(*o, ctx, out, src));
            match op.as_str() {
                "!" => ValueExpr::Unary {
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
        "ternary_expression" => {
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
        ">" => BinaryOp::Gt,
        ">=" => BinaryOp::Ge,
        "&&" => BinaryOp::And,
        "||" => BinaryOp::Or,
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
    if t.len() >= 2 && (t.starts_with('"') || t.starts_with('\'')) {
        t[1..t.len() - 1].to_owned()
    } else {
        t.to_owned()
    }
}

impl LanguageFrontend for JavaFrontend {
    fn id(&self) -> &'static str {
        "frontend-java"
    }

    fn language(&self) -> Language {
        Language::Java
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
                    language: Language::Java,
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
            language: Language::Java,
            module: out.module,
            imports: out.imports,
            annotations: out.annotations,
            functions,
            callsites: out.callsites,
            guard_conditions: out.guards,
            bodies,
        })
    }
}

/// Attach return expressions to their owning function by innermost span
/// containment (the function's declaration span covers its body).
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
