//! Real storage: the tally kept in a text file, one `name count` line per item.

use std::fs;
use std::io::ErrorKind;
use std::path::PathBuf;

use core_types::Count;
use tally::{ItemName, StoreError, Tally, TallyStore};

pub struct FileTallyStore {
    path: PathBuf,
}

impl FileTallyStore {
    /// The tally in `tally.txt` inside `folder`. Nothing is read until the first load.
    pub fn in_folder(folder: PathBuf) -> FileTallyStore {
        FileTallyStore { path: folder.join("tally.txt") }
    }
}

impl TallyStore for FileTallyStore {
    fn load(&mut self) -> Result<Tally, StoreError> {
        let text = match fs::read_to_string(&self.path) {
            Ok(text) => text,
            Err(error) if error.kind() == ErrorKind::NotFound => return Ok(Tally::default()),
            Err(_) => return Err(StoreError::Unavailable),
        };
        text.lines().try_fold(Tally::default(), |tally, line| {
            let (raw_name, raw_count) = line.split_once(' ').ok_or(StoreError::Corrupt)?;
            let name = ItemName::parse(raw_name).map_err(|_| StoreError::Corrupt)?;
            let count = raw_count.parse::<u32>().map_err(|_| StoreError::Corrupt)?;
            Ok(tally.with(name, Count::new(count)))
        })
    }

    fn save(&mut self, tally: &Tally) -> Result<(), StoreError> {
        let text: String = tally.entries().map(|(name, count)| format!("{name} {count}\n")).collect();
        // Write a sibling file, then rename it over the old one, so a failed write never leaves half a tally.
        let staging = self.path.with_extension("txt.new");
        fs::write(&staging, text).map_err(|_| StoreError::Unavailable)?;
        fs::rename(&staging, &self.path).map_err(|_| StoreError::Unavailable)
    }
}
