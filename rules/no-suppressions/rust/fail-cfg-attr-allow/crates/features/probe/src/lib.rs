#![no_std]
#[cfg_attr(all(), allow(clippy::unwrap_used))]
pub fn first(values: &[u32]) -> u32 {
    *values.first().unwrap()
}
