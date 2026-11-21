//! Parses every .rs file in the crates it's given and reports code the gates' other tools can't see:
//! suppressions, global state, std in no_std crates, skipped tests, and code hidden from parsing.
//!
//! Usage: arch-checker <crate-dir>=<std|no_std> ...
//! Prints `path:line:col: [rule-id] message` for each finding; exits 1 if there are any.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use proc_macro2::{Span, TokenStream, TokenTree};
use syn::spanned::Spanned;
use syn::visit::Visit;

const SUPPRESSION: &str = "a lint attribute that turns a check down. Fix the code instead; if the check is wrong here, stop and report. Only the owner changes lint levels (Cargo.toml, clippy.toml).";
const HIDDEN: &str = "it hides code from the checks, which see only the source as written. Write the code out; if that's impractical, stop and report.";
const GLOBAL: &str = "global state: any code can reach it, and tests and journeys can't start from a known state. Pass the value in as a parameter; it's created in the app crate (the composition root).";

struct Finding {
    path: PathBuf,
    span: Span,
    rule: &'static str,
    message: String,
}

struct Checker<'a> {
    path: &'a Path,
    no_std: bool,
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
    let mut files = Vec::new();
    rust_files(dir, &mut files);
    for path in files {
        let parsed = fs::read_to_string(&path).map_err(|e| e.to_string()).and_then(|text| syn::parse_file(&text).map_err(|e| e.to_string()));
        let file = match parsed {
            Ok(file) => file,
            Err(error) => {
                findings.push(Finding { path, span: Span::call_site(), rule: "arch", message: format!("can't parse this file: {error}") });
                continue;
            }
        };
        if no_std && path == dir.join("src/lib.rs") && !file.attrs.iter().any(|a| a.path().is_ident("no_std") && matches!(a.style, syn::AttrStyle::Inner(_))) {
            findings.push(Finding { path: path.clone(), span: Span::call_site(), rule: "no-io-in-logic", message: "this crate's role is no_std (arch/shape.toml), so src/lib.rs must start with `#![no_std]`. Logic does no I/O: define a trait for what you need and implement it in a platform crate.".into() });
        }
        Checker { path: &path, no_std, findings }.visit_file(&file);
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
