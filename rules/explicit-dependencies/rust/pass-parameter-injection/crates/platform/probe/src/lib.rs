pub trait Clock {
    fn now(&self) -> u64;
}

pub fn elapsed(clock: &impl Clock, since: u64) -> u64 {
    clock.now().saturating_sub(since)
}

pub const START: u64 = 0;
