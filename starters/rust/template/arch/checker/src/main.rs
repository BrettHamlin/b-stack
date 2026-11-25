//! Parses every .rs file in the crates it's given and reports code the gates' other tools can't see:
//! suppressions, global state, std in no_std crates, skipped tests, `if/else` on enums in tests, and code hidden from parsing.
//!
//! Usage: arch-checker <crate-dir>=<std|no_std> ...
//! Prints `path:line:col: [rule-id] message` for each finding; exits 1 if there are any.

use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use proc_macro2::{Span, TokenStream, TokenTree};
use syn::parse::Parser;
use syn::spanned::Spanned;
use syn::visit::Visit;

const SUPPRESSION: &str = "a lint attribute that turns a check down. Fix the code instead; if the check is wrong here, stop and report. Only the owner changes lint levels (Cargo.toml, clippy.toml).";
const HIDDEN: &str = "it hides code from the checks, which see only the source as written. Write the code out; if that's impractical, stop and report.";
const GLOBAL: &str = "global state: any code can reach it, and tests and journeys can't start from a known state. Pass the value in as a parameter; it's created in the app crate (the composition root).";
const WRAPPER_ENUMS: [&str; 4] = ["Option", "Result", "Poll", "ControlFlow"];
const WRAPPER_VARIANTS: [&str; 6] = ["Some", "None", "Ok", "Err", "Ready", "Pending"];

struct Finding {
    path: PathBuf,
    span: Span,
    rule: &'static str,
    message: String,
}

struct Checker<'a> {
    path: &'a Path,
    no_std: bool,
    in_test: bool,
    enums: &'a HashMap<String, HashSet<String>>,
    bare_variants: HashSet<String>,
    findings: &'a mut Vec<Finding>,
}

impl Checker<'_> {
    fn report(&mut self, span: Span, rule: &'static str, message: String) {
        self.findings.push(Finding { path: self.path.to_path_buf(), span, rule, message });
    }
}

/// Any identifier named `name` anywhere in these tokens, including nested groups.
fn mentions(tokens: &TokenStream, names: &[&str]) -> Option<String> {
    tokens.clone().into_iter().find_map(|tree| match tree {
        TokenTree::Ident(ident) if names.iter().any(|n| ident == n) => Some(ident.to_string()),
        TokenTree::Group(group) => mentions(&group.stream(), names),
        TokenTree::Ident(_) | TokenTree::Punct(_) | TokenTree::Literal(_) => None,
    })
}

fn is_upper_camel(name: &str) -> bool {
    name.as_bytes().first().is_some_and(u8::is_ascii_uppercase) && name.bytes().any(|b| b.is_ascii_lowercase())
}

fn cfg_meta_is_test(meta: &syn::Meta) -> Option<bool> {
    match meta {
        syn::Meta::Path(p) if p.is_ident("test") => Some(true),
        syn::Meta::List(list) if list.path.is_ident("not") => {
            let inner = list.parse_args_with(syn::punctuated::Punctuated::<syn::Meta, syn::Token![,]>::parse_terminated).ok()?;
            (inner.len() == 1 && cfg_meta_is_test(&inner[0]) == Some(true)).then_some(false)
        }
        syn::Meta::List(list) if list.path.is_ident("all") => {
            let inner = list.parse_args_with(syn::punctuated::Punctuated::<syn::Meta, syn::Token![,]>::parse_terminated).ok()?;
            if inner.iter().any(|m| cfg_meta_is_test(m) == Some(false)) {
                Some(false)
            } else if inner.iter().any(|m| cfg_meta_is_test(m) == Some(true)) {
                Some(true)
            } else {
                None
            }
        }
        _ => None,
    }
}

fn test_attr_override(attrs: &[syn::Attribute]) -> Option<bool> {
    let mut found = None;
    for attr in attrs {
        if attr.path().is_ident("test") {
            found = Some(true);
        } else if attr.path().is_ident("cfg")
            && let syn::Meta::List(list) = &attr.meta
            && let Ok(inner) = list.parse_args_with(syn::punctuated::Punctuated::<syn::Meta, syn::Token![,]>::parse_terminated)
            && inner.len() == 1
            && let Some(is_test) = cfg_meta_is_test(&inner[0])
        {
            if !is_test {
                return Some(false);
            }
            found = Some(true);
        }
    }
    found
}

fn collect_enums(items: &[syn::Item], out: &mut HashMap<String, HashSet<String>>) {
    for item in items {
        match item {
            syn::Item::Enum(en) => {
                let entry = out.entry(en.ident.to_string()).or_default();
                entry.extend(en.variants.iter().map(|v| v.ident.to_string()));
            }
            syn::Item::Mod(m) => {
                if let Some((_, inner)) = &m.content {
                    collect_enums(inner, out);
                }
            }
            _ => {}
        }
    }
}

fn collect_use_tree(
    tree: &syn::UseTree,
    enum_prefix: Option<&str>,
    enums: &HashMap<String, HashSet<String>>,
    out: &mut HashSet<String>,
) {
    match tree {
        syn::UseTree::Path(p) => {
            let seg = p.ident.to_string();
            let is_enum = !WRAPPER_ENUMS.contains(&seg.as_str()) && (enums.contains_key(&seg) || is_upper_camel(&seg));
            collect_use_tree(&p.tree, is_enum.then_some(seg.as_str()), enums, out);
        }
        syn::UseTree::Name(n) => {
            let ident = n.ident.to_string();
            if let Some(en) = enum_prefix
                && ident != "self"
                && !WRAPPER_VARIANTS.contains(&ident.as_str())
                && (enums.get(en).is_some_and(|vs| vs.contains(&ident)) || is_upper_camel(&ident))
            {
                out.insert(ident);
            }
        }
        syn::UseTree::Rename(r) => {
            let orig = r.ident.to_string();
            let alias = r.rename.to_string();
            if let Some(en) = enum_prefix
                && !WRAPPER_VARIANTS.contains(&orig.as_str())
                && (enums.get(en).is_some_and(|vs| vs.contains(&orig)) || is_upper_camel(&orig))
            {
                out.insert(alias);
            }
        }
        syn::UseTree::Glob(_) => {
            if let Some(en) = enum_prefix
                && let Some(vs) = enums.get(en)
            {
                out.extend(vs.iter().cloned());
            }
        }
        syn::UseTree::Group(g) => {
            for item in &g.items {
                collect_use_tree(item, enum_prefix, enums, out);
            }
        }
    }
}

fn enum_path_2plus(path: &syn::Path, enums: &HashMap<String, HashSet<String>>) -> Option<String> {
    if path.segments.len() < 2 {
        return None;
    }
    let ty = path.segments[path.segments.len() - 2].ident.to_string();
    let var = path.segments[path.segments.len() - 1].ident.to_string();
    if WRAPPER_ENUMS.contains(&ty.as_str()) {
        return None;
    }
    if enums.get(&ty).is_some_and(|vs| vs.contains(&var)) || ((ty == "Self" || is_upper_camel(&ty)) && is_upper_camel(&var)) {
        Some(format!("{ty}::{var}"))
    } else {
        None
    }
}

fn enum_path(path: &syn::Path, enums: &HashMap<String, HashSet<String>>, bare: &HashSet<String>) -> Option<String> {
    if path.segments.len() == 1 {
        let ident = path.segments[0].ident.to_string();
        (!WRAPPER_VARIANTS.contains(&ident.as_str()) && bare.contains(&ident)).then_some(ident)
    } else {
        enum_path_2plus(path, enums)
    }
}

fn enum_variant_expr(expr: &syn::Expr, enums: &HashMap<String, HashSet<String>>, bare: &HashSet<String>) -> Option<String> {
    match expr {
        syn::Expr::Paren(p) => enum_variant_expr(&p.expr, enums, bare),
        syn::Expr::Group(g) => enum_variant_expr(&g.expr, enums, bare),
        syn::Expr::Reference(r) => enum_variant_expr(&r.expr, enums, bare),
        syn::Expr::Path(ep) if ep.qself.is_none() => enum_path(&ep.path, enums, bare),
        syn::Expr::Call(call) => match call.func.as_ref() {
            syn::Expr::Path(ep) if ep.qself.is_none() => enum_path(&ep.path, enums, bare),
            _ => None,
        },
        syn::Expr::Struct(st) if st.qself.is_none() => enum_path(&st.path, enums, bare),
        _ => None,
    }
}

fn enum_variant_pat(pat: &syn::Pat, enums: &HashMap<String, HashSet<String>>, bare: &HashSet<String>) -> Option<String> {
    match pat {
        syn::Pat::Or(or_pat) => or_pat.cases.iter().find_map(|p| enum_variant_pat(p, enums, bare)),
        syn::Pat::Paren(p) => enum_variant_pat(&p.pat, enums, bare),
        syn::Pat::Reference(r) => enum_variant_pat(&r.pat, enums, bare),
        syn::Pat::Path(pp) if pp.qself.is_none() => enum_path(&pp.path, enums, bare),
        syn::Pat::TupleStruct(ts) if ts.qself.is_none() => enum_path(&ts.path, enums, bare),
        syn::Pat::Struct(st) if st.qself.is_none() => enum_path(&st.path, enums, bare),
        syn::Pat::Ident(pi) if pi.by_ref.is_none() && pi.mutability.is_none() && pi.subpat.is_none() => {
            let ident = pi.ident.to_string();
            (!WRAPPER_VARIANTS.contains(&ident.as_str()) && bare.contains(&ident)).then_some(ident)
        }
        _ => None,
    }
}

fn matches_macro_pat(tokens: &TokenStream) -> Option<syn::Pat> {
    let mut iter = tokens.clone().into_iter();
    for tt in iter.by_ref() {
        if matches!(&tt, TokenTree::Punct(p) if p.as_char() == ',') {
            break;
        }
    }
    let pat_tokens: TokenStream = iter
        .take_while(|tt| !matches!(tt, TokenTree::Ident(ident) if ident == "if"))
        .collect();
    if pat_tokens.is_empty() {
        return None;
    }
    syn::Pat::parse_multi_with_leading_vert.parse2(pat_tokens).ok()
}

fn enum_condition(expr: &syn::Expr, enums: &HashMap<String, HashSet<String>>, bare: &HashSet<String>) -> Option<String> {
    match expr {
        syn::Expr::Paren(p) => enum_condition(&p.expr, enums, bare),
        syn::Expr::Group(g) => enum_condition(&g.expr, enums, bare),
        syn::Expr::Unary(u) if matches!(u.op, syn::UnOp::Not(_)) => enum_condition(&u.expr, enums, bare),
        syn::Expr::Binary(b) if matches!(b.op, syn::BinOp::Eq(_) | syn::BinOp::Ne(_)) => {
            enum_variant_expr(&b.left, enums, bare).or_else(|| enum_variant_expr(&b.right, enums, bare))
        }
        syn::Expr::Let(l) => enum_variant_pat(&l.pat, enums, bare),
        syn::Expr::Macro(m) if m.mac.path.segments.last().is_some_and(|s| s.ident == "matches") => {
            matches_macro_pat(&m.mac.tokens).and_then(|pat| enum_variant_pat(&pat, enums, bare))
        }
        _ => None,
    }
}

fn has_final_else(expr_if: &syn::ExprIf) -> bool {
    match expr_if.else_branch.as_ref().map(|(_, e)| e.as_ref()) {
        Some(syn::Expr::If(next)) => has_final_else(next),
        Some(_) => true,
        None => false,
    }
}

const LINT_LEVELS: [&str; 3] = ["allow", "expect", "warn"];

impl<'ast> Visit<'ast> for Checker<'_> {
    fn visit_attribute(&mut self, attr: &'ast syn::Attribute) {
        let path = attr.path();
        let name = path.segments.last().map(|s| s.ident.to_string()).unwrap_or_default();
        if path.segments.len() == 1 && LINT_LEVELS.contains(&name.as_str()) {
            self.report(attr.span(), "no-suppressions", format!("`#[{name}(...)]` is {SUPPRESSION}"));
        } else if path.is_ident("cfg_attr") {
            if let syn::Meta::List(list) = &attr.meta {
                if let Some(level) = mentions(&list.tokens, &LINT_LEVELS) {
                    self.report(attr.span(), "no-suppressions", format!("`#[cfg_attr(..., {level}(...))]` is {SUPPRESSION}"));
                }
                if mentions(&list.tokens, &["ignore"]).is_some() {
                    self.report(attr.span(), "tests-always-run", "`#[cfg_attr(..., ignore)]` skips a test. Every test runs in the tests gate; fix the test or the code, or stop and report.".into());
                }
            }
        } else if path.is_ident("ignore") {
            self.report(attr.span(), "tests-always-run", "`#[ignore]` skips a test. Every test runs in the tests gate; fix the test or the code, or stop and report.".into());
        } else if path.is_ident("path") {
            self.report(attr.span(), "no-suppressions", format!("`#[path = ...]` loads a module from outside its usual place; {HIDDEN}"));
        }
        syn::visit::visit_attribute(self, attr);
    }

    fn visit_item_mod(&mut self, item: &'ast syn::ItemMod) {
        let prev_test = self.in_test;
        let prev_bare = self.bare_variants.clone();
        if let Some(is_test) = test_attr_override(&item.attrs) {
            self.in_test = is_test;
        }
        if let Some((_, items)) = &item.content {
            for inner in items {
                if let syn::Item::Use(u) = inner {
                    collect_use_tree(&u.tree, None, self.enums, &mut self.bare_variants);
                }
            }
        }
        syn::visit::visit_item_mod(self, item);
        self.in_test = prev_test;
        self.bare_variants = prev_bare;
    }

    fn visit_item_fn(&mut self, item: &'ast syn::ItemFn) {
        let prev_test = self.in_test;
        let prev_bare = self.bare_variants.clone();
        if let Some(is_test) = test_attr_override(&item.attrs) {
            self.in_test = is_test;
        }
        for stmt in &item.block.stmts {
            if let syn::Stmt::Item(syn::Item::Use(u)) = stmt {
                collect_use_tree(&u.tree, None, self.enums, &mut self.bare_variants);
            }
        }
        syn::visit::visit_item_fn(self, item);
        self.in_test = prev_test;
        self.bare_variants = prev_bare;
    }

    fn visit_expr_if(&mut self, expr_if: &'ast syn::ExprIf) {
        if self.in_test && has_final_else(expr_if) {
            let mut reported = false;
            let mut current = expr_if;
            loop {
                for attr in &current.attrs {
                    self.visit_attribute(attr);
                }
                if !reported && let Some(variant) = enum_condition(&current.cond, self.enums, &self.bare_variants) {
                    self.report(
                        current.if_token.span,
                        "exhaustive-states",
                        format!(
                            "`if ... else` puts every variant other than `{variant}` in the `else` branch, as a `_` arm in `match` does, so a variant added later is handled there unseen. Use `match` naming every variant."
                        ),
                    );
                    reported = true;
                }
                self.visit_expr(&current.cond);
                self.visit_block(&current.then_branch);
                match current.else_branch.as_ref().map(|(_, e)| e.as_ref()) {
                    Some(syn::Expr::If(next)) => current = next,
                    Some(other) => {
                        self.visit_expr(other);
                        break;
                    }
                    None => break,
                }
            }
            return;
        }
        syn::visit::visit_expr_if(self, expr_if);
    }

    fn visit_item_static(&mut self, item: &'ast syn::ItemStatic) {
        self.report(item.static_token.span, "explicit-dependencies", format!("`static {}` is {GLOBAL} For a constant, use `const`.", item.ident));
        syn::visit::visit_item_static(self, item);
    }

    fn visit_item_extern_crate(&mut self, item: &'ast syn::ItemExternCrate) {
        if self.no_std && item.ident == "std" {
            self.report(item.span(), "no-io-in-logic", "`extern crate std` brings std (files, network, clocks, threads) into a no_std crate. Define a trait here for what you need and implement it in a platform crate.".into());
        }
        syn::visit::visit_item_extern_crate(self, item);
    }

    fn visit_item_macro(&mut self, item: &'ast syn::ItemMacro) {
        if item.mac.path.is_ident("macro_rules") {
            self.report(item.span(), "no-suppressions", format!("`macro_rules!` defines a macro; {HIDDEN}"));
        }
        syn::visit::visit_item_macro(self, item);
    }

    fn visit_macro(&mut self, mac: &'ast syn::Macro) {
        let name = mac.path.segments.last().map(|s| s.ident.to_string()).unwrap_or_default();
        match name.as_str() {
            "thread_local" | "lazy_static" => self.report(mac.span(), "explicit-dependencies", format!("`{name}!` is {GLOBAL}")),
            "include" => self.report(mac.span(), "no-suppressions", format!("`include!` pastes in code from another file; {HIDDEN}")),
            _ => {}
        }
        syn::visit::visit_macro(self, mac);
    }
}

fn rust_files(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = fs::read_dir(dir) else { return };
    let mut entries: Vec<PathBuf> = entries.filter_map(|e| e.ok().map(|e| e.path())).collect();
    entries.sort();
    for path in entries {
        let name = path.file_name().and_then(|n| n.to_str()).unwrap_or_default();
        if name.starts_with('.') || name == "target" {
            continue;
        }
        if path.is_dir() {
            rust_files(&path, out);
        } else if name.ends_with(".rs") {
            out.push(path);
        }
    }
}

fn check_crate(dir: &Path, no_std: bool, findings: &mut Vec<Finding>) {
    let mut paths = Vec::new();
    rust_files(dir, &mut paths);
    let mut parsed_files = Vec::new();
    let mut enums = HashMap::new();
    for path in paths {
        let parsed = fs::read_to_string(&path).map_err(|e| e.to_string()).and_then(|text| syn::parse_file(&text).map_err(|e| e.to_string()));
        match parsed {
            Ok(file) => {
                collect_enums(&file.items, &mut enums);
                parsed_files.push((path, file));
            }
            Err(error) => {
                findings.push(Finding { path, span: Span::call_site(), rule: "arch", message: format!("can't parse this file: {error}") });
            }
        }
    }
    for (path, file) in &parsed_files {
        if no_std && path == &dir.join("src/lib.rs") && !file.attrs.iter().any(|a| a.path().is_ident("no_std") && matches!(a.style, syn::AttrStyle::Inner(_))) {
            findings.push(Finding { path: path.clone(), span: Span::call_site(), rule: "no-io-in-logic", message: "this crate's role is no_std (arch/shape.toml), so src/lib.rs must start with `#![no_std]`. Logic does no I/O: define a trait for what you need and implement it in a platform crate.".into() });
        }
        let mut in_test = path.strip_prefix(dir).ok().and_then(|rel| rel.components().next()).is_some_and(|c| c.as_os_str() == "tests");
        if let Some(is_test) = test_attr_override(&file.attrs) {
            in_test = is_test;
        }
        let mut bare_variants = HashSet::new();
        for item in &file.items {
            if let syn::Item::Use(u) = item {
                collect_use_tree(&u.tree, None, &enums, &mut bare_variants);
            }
        }
        Checker { path, no_std, in_test, enums: &enums, bare_variants, findings }.visit_file(file);
    }
}

fn main() -> ExitCode {
    let mut findings = Vec::new();
    for arg in std::env::args().skip(1) {
        match arg.rsplit_once('=') {
            Some((dir, "std")) => check_crate(Path::new(dir), false, &mut findings),
            Some((dir, "no_std")) => check_crate(Path::new(dir), true, &mut findings),
            _ => {
                eprintln!("usage: arch-checker <crate-dir>=<std|no_std> ...");
                return ExitCode::from(2);
            }
        }
    }
    for f in &findings {
        let start = f.span.start();
        println!("{}:{}:{}: [{}] {}", f.path.display(), start.line.max(1), start.column + 1, f.rule, f.message);
    }
    if findings.is_empty() { ExitCode::SUCCESS } else { ExitCode::FAILURE }
}
