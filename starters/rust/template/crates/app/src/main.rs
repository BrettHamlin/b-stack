//! The composition root: reads the command line, wires the real store in, runs the feature.
//!
//! Usage: app --data <folder> add <name> | app --data <folder> show

use std::env;
use std::path::PathBuf;
use std::process::ExitCode;

use files::FileTallyStore;
use tally::{ItemName, TallyError, current, record};

enum Command {
    Add(String),
    Show,
}

fn parse(args: &[String]) -> Option<(PathBuf, Command)> {
    match args {
        [flag, folder, verb, name] if flag == "--data" && verb == "add" => Some((PathBuf::from(folder), Command::Add(name.clone()))),
        [flag, folder, verb] if flag == "--data" && verb == "show" => Some((PathBuf::from(folder), Command::Show)),
        _ => None,
    }
}

fn run(folder: PathBuf, command: Command) -> Result<String, TallyError> {
    let mut store = FileTallyStore::in_folder(folder);
    match command {
        Command::Add(raw) => {
            let name = ItemName::parse(&raw)?;
            let count = record(&mut store, &name)?;
            Ok(format!("{name} {count}"))
        }
        Command::Show => {
            let lines: Vec<String> = current(&mut store)?.entries().map(|(name, count)| format!("{name} {count}")).collect();
            Ok(if lines.is_empty() { String::from("(empty)") } else { lines.join("\n") })
        }
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let Some((folder, command)) = parse(&args) else {
        eprintln!("usage: app --data <folder> add <name> | app --data <folder> show");
        return ExitCode::from(2);
    };
    match run(folder, command) {
        Ok(output) => {
            println!("{output}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::FAILURE
        }
    }
}
