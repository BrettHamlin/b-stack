#![cfg(test)]
mod support;

use core_types::Count;
use support::MemoryStore;
use tally::{ItemName, StoreError, Tally, TallyError, current, record};

fn name(raw: &str) -> ItemName {
    ItemName::parse(raw).unwrap()
}

#[test]
fn recording_counts_up_and_saves() {
    let mut store = MemoryStore::default();
    assert_eq!(record(&mut store, &name("apple")), Ok(Count::new(1)));
    assert_eq!(record(&mut store, &name("apple")), Ok(Count::new(2)));
    assert_eq!(record(&mut store, &name("pear")), Ok(Count::new(1)));
    assert_eq!(store.saves, 3);
    assert_eq!(current(&mut store).unwrap(), Tally::default().with(name("apple"), Count::new(2)).with(name("pear"), Count::new(1)));
}

#[test]
fn a_failed_save_changes_nothing() {
    let mut store = MemoryStore::default();
    record(&mut store, &name("apple")).unwrap();
    store.fail_saves = 1;
    assert_eq!(record(&mut store, &name("apple")), Err(TallyError::Store(StoreError::Unavailable)));
    assert_eq!(current(&mut store).unwrap().count(&name("apple")), Count::new(1));
}

#[test]
fn a_failed_load_saves_nothing() {
    let mut store = MemoryStore { fail_loads: 1, ..MemoryStore::default() };
    assert_eq!(record(&mut store, &name("apple")), Err(TallyError::Store(StoreError::Unavailable)));
    assert_eq!(store.saves, 0);
}

#[test]
fn a_full_count_is_refused() {
    let mut store = MemoryStore { saved: Tally::default().with(name("apple"), Count::new(u32::MAX)), ..MemoryStore::default() };
    assert_eq!(record(&mut store, &name("apple")), Err(TallyError::CountFull));
    assert_eq!(store.saves, 0);
}

#[test]
fn names_are_validated() {
    for bad in ["", " apple", "a/b", "é", &"x".repeat(ItemName::MAX_LEN + 1)] {
        assert_eq!(ItemName::parse(bad), Err(TallyError::InvalidName), "{bad:?}");
    }
    for good in ["a", "apple-2", "big_pear", &"x".repeat(ItemName::MAX_LEN)] {
        assert!(ItemName::parse(good).is_ok(), "{good:?}");
    }
}
