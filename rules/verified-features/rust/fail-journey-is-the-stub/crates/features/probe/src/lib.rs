#![no_std]
//! The probe feature. No I/O here: what it needs from outside (a store, a clock) is a trait it defines, implemented
//! in a platform crate and passed in by the app (see crates/features/tally).

/// What the app shows for the probe feature.
pub fn summary() -> &'static str {
    "probe"
}
