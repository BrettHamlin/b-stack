//! The composition root: reads the command line and runs the app's features.

use std::process::ExitCode;

fn main() -> ExitCode {
    eprintln!("usage: app --data <folder> <command>");
    ExitCode::from(2)
}
