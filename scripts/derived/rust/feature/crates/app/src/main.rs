//! The composition root: reads the command line and runs the app's features.
//!
//! Usage: app --data <folder> greet <name>

use std::env;
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    match args.as_slice() {
        [flag, _folder, verb, name] if flag == "--data" && verb == "greet" => {
            println!("{}", greeting::greet(name));
            ExitCode::SUCCESS
        }
        _ => {
            eprintln!("usage: app --data <folder> greet <name>");
            ExitCode::from(2)
        }
    }
}
