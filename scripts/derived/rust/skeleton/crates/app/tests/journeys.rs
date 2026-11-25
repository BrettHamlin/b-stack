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
