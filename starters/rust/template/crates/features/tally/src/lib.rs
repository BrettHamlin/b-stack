#![no_std]
//! The tally feature: count named items, saved through an injected store. No I/O here; the store does it.

extern crate alloc;

use alloc::collections::BTreeMap;
use alloc::string::String;
use core::fmt;
use core_types::Count;

/// An item's name: 1 to 32 characters, letters, digits, '-' or '_'. Only `parse` makes one.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct ItemName(String);

impl ItemName {
    pub const MAX_LEN: usize = 32;

    pub fn parse(raw: &str) -> Result<ItemName, TallyError> {
        let valid_char = |c: char| c.is_ascii_alphanumeric() || c == '-' || c == '_';
        if raw.is_empty() || raw.len() > Self::MAX_LEN || !raw.chars().all(valid_char) {
            return Err(TallyError::InvalidName);
        }
        Ok(ItemName(String::from(raw)))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for ItemName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

/// Every item's count. Items never recorded aren't in it.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Tally {
    counts: BTreeMap<ItemName, Count>,
}

impl Tally {
    pub fn count(&self, name: &ItemName) -> Count {
        self.counts.get(name).copied().unwrap_or(Count::ZERO)
    }

    pub fn entries(&self) -> impl Iterator<Item = (&ItemName, Count)> {
        self.counts.iter().map(|(name, count)| (name, *count))
    }

    /// Set an item's count directly, for stores rebuilding a saved tally.
    pub fn with(mut self, name: ItemName, count: Count) -> Tally {
        self.counts.insert(name, count);
        self
    }

    fn incremented(&self, name: &ItemName) -> Result<Tally, TallyError> {
        let next = self.count(name).incremented().ok_or(TallyError::CountFull)?;
        Ok(self.clone().with(name.clone(), next))
    }
}

/// Where the tally is kept. The app passes a real one in; tests pass their own.
pub trait TallyStore {
    fn load(&mut self) -> Result<Tally, StoreError>;
    fn save(&mut self, tally: &Tally) -> Result<(), StoreError>;
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StoreError {
    Unavailable,
    Corrupt,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TallyError {
    InvalidName,
    CountFull,
    Store(StoreError),
}

impl From<StoreError> for TallyError {
    fn from(error: StoreError) -> TallyError {
        TallyError::Store(error)
    }
}

impl fmt::Display for TallyError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TallyError::InvalidName => write!(f, "names are 1 to {} letters, digits, '-' or '_'", ItemName::MAX_LEN),
            TallyError::CountFull => f.write_str("that count is at its maximum"),
            TallyError::Store(StoreError::Unavailable) => f.write_str("the tally couldn't be read or saved"),
            TallyError::Store(StoreError::Corrupt) => f.write_str("the saved tally is damaged"),
        }
    }
}

/// Add one to `name` and save. If anything fails, the saved tally is unchanged and the error says why.
pub fn record(store: &mut impl TallyStore, name: &ItemName) -> Result<Count, TallyError> {
    let next = store.load()?.incremented(name)?;
    store.save(&next)?;
    Ok(next.count(name))
}

/// The saved tally.
pub fn current(store: &mut impl TallyStore) -> Result<Tally, TallyError> {
    Ok(store.load()?)
}
