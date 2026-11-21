use std::cell::Cell;

thread_local! {
    pub static CURRENT: Cell<u32> = const { Cell::new(0) };
}
