//! Journeys: each runs the built app the way a user would and checks what they'd see. feature-map/ names which
//! journeys prove which feature; the verify gate runs them and fails on any journey the map doesn't name.
#![cfg(test)]

use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::process::Command;

struct Run {
    ok: bool,
    stdout: String,
    stderr: String,
}

fn app(data: &Path, args: &[&str]) -> Run {
    let output = Command::new(env!("CARGO_BIN_EXE_app")).arg("--data").arg(data).args(args).output().unwrap();
    let run = Run { ok: output.status.success(), stdout: String::from_utf8(output.stdout).unwrap(), stderr: String::from_utf8(output.stderr).unwrap() };
    // Evidence: the verify gate keeps each journey's output.
    println!("$ app --data <folder> {}\n{}{}", args.join(" "), run.stdout, run.stderr);
    run
}

/// A new, empty folder for one journey's data.
fn data_folder(journey: &str) -> PathBuf {
    let folder = PathBuf::from(env!("CARGO_TARGET_TMPDIR")).join(journey);
    let _ = fs::remove_dir_all(&folder);
    fs::create_dir_all(&folder).unwrap();
    folder
}

#[test]
fn tally_is_saved_across_runs() {
    let data = data_folder("tally_is_saved_across_runs");
    assert_eq!(app(&data, &["show"]).stdout, "(empty)\n");
    assert_eq!(app(&data, &["add", "apple"]).stdout, "apple 1\n");
    assert_eq!(app(&data, &["add", "apple"]).stdout, "apple 2\n");
    assert_eq!(app(&data, &["add", "pear"]).stdout, "pear 1\n");
    assert_eq!(app(&data, &["show"]).stdout, "apple 2\npear 1\n");
}

#[test]
fn failed_save_keeps_the_old_tally() {
    let data = data_folder("failed_save_keeps_the_old_tally");
    assert!(app(&data, &["add", "apple"]).ok);
    fs::set_permissions(&data, fs::Permissions::from_mode(0o555)).unwrap();
    let failed = app(&data, &["add", "apple"]);
    fs::set_permissions(&data, fs::Permissions::from_mode(0o755)).unwrap();
    assert!(!failed.ok);
    assert_eq!(failed.stderr, "error: the tally couldn't be read or saved\n");
    assert_eq!(app(&data, &["show"]).stdout, "apple 1\n");
}

#[test]
fn bad_name_is_refused() {
    let data = data_folder("bad_name_is_refused");
    let refused = app(&data, &["add", "two words"]);
    assert!(!refused.ok);
    assert_eq!(refused.stderr, "error: names are 1 to 32 letters, digits, '-' or '_'\n");
    assert_eq!(app(&data, &["show"]).stdout, "(empty)\n");
}

#[test]
fn unmapped_check() {
    assert!(app(&data_folder("unmapped_check"), &["show"]).ok);
}
