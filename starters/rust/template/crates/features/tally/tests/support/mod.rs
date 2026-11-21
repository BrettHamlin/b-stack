use tally::{StoreError, Tally, TallyStore};

/// A store in memory that fails the next saves or loads when told to.
#[derive(Default)]
pub struct MemoryStore {
    pub saved: Tally,
    pub fail_loads: usize,
    pub fail_saves: usize,
    pub saves: usize,
}

impl TallyStore for MemoryStore {
    fn load(&mut self) -> Result<Tally, StoreError> {
        if self.fail_loads > 0 {
            self.fail_loads -= 1;
            return Err(StoreError::Unavailable);
        }
        Ok(self.saved.clone())
    }

    fn save(&mut self, tally: &Tally) -> Result<(), StoreError> {
        if self.fail_saves > 0 {
            self.fail_saves -= 1;
            return Err(StoreError::Unavailable);
        }
        self.saves += 1;
        self.saved = tally.clone();
        Ok(())
    }
}
