use std::cell::Cell;

pub struct Shared(pub Cell<u32>);

unsafe impl Sync for Shared {}
