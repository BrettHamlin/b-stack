//! 200 seeded random sequences of records, failed loads and failed saves, each checked step by step against a
//! model of the spec (a plain map). Stops at the first divergence and prints the seed and the steps so far.
#![cfg(test)]
mod support;

use std::collections::BTreeMap;

use core_types::Count;
use support::MemoryStore;
use tally::{ItemName, StoreError, TallyError, current, record};

/// A small seeded generator (xorshift64*), so a failing sequence reruns exactly from its seed.
struct Rng(u64);

impl Rng {
    fn below(&mut self, n: u64) -> u64 {
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        self.0.wrapping_mul(0x2545_F491_4F6C_DD1D) % n
    }
}

#[derive(Debug, Clone, Copy)]
enum Step {
    Record(usize),
    FailNextLoad,
    FailNextSave,
}

const NAMES: [&str; 3] = ["apple", "pear", "fig"];

#[test]
fn record_matches_the_model() {
    for seed in 1..=200_u64 {
        let mut rng = Rng(seed.wrapping_mul(0x9E37_79B9_7F4A_7C15));
        let mut store = MemoryStore::default();
        let mut model: BTreeMap<&str, u32> = BTreeMap::new();
        let mut steps = Vec::new();
        for _ in 0..40 {
            let step = match rng.below(10) {
                0 => Step::FailNextLoad,
                1 => Step::FailNextSave,
                _ => Step::Record(usize::try_from(rng.below(3)).unwrap()),
            };
            steps.push(step);
            match step {
                Step::FailNextLoad => store.fail_loads = 1,
                Step::FailNextSave => store.fail_saves = 1,
                Step::Record(i) => {
                    let raw = NAMES[i];
                    let expected = if store.fail_loads > 0 || store.fail_saves > 0 {
                        Err(TallyError::Store(StoreError::Unavailable))
                    } else {
                        let next = model.get(raw).copied().unwrap_or(0) + 1;
                        model.insert(raw, next);
                        Ok(Count::new(next))
                    };
                    let actual = record(&mut store, &ItemName::parse(raw).unwrap());
                    assert_eq!(actual, expected, "seed {seed}, steps {steps:?}");
                }
            }
            if store.fail_loads == 0 {
                let saved = current(&mut store).unwrap();
                let saved: BTreeMap<String, u32> = saved.entries().map(|(n, c)| (n.to_string(), c.value())).collect();
                let model: BTreeMap<String, u32> = model.iter().map(|(n, c)| (n.to_string(), *c)).collect();
                assert_eq!(saved, model, "seed {seed}, steps {steps:?}");
            }
        }
    }
}
