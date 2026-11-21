#![no_std]
pub fn run_scoped(work: impl FnOnce()) {
    work();
}

#[deprecated(note = "Use run_scoped, which ends the work with its scope")]
pub fn legacy_timer(work: impl FnOnce()) {
    work();
}

pub fn refresh() {
    legacy_timer(|| {});
}
