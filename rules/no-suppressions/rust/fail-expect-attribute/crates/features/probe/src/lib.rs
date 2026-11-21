#![no_std]
#![expect(clippy::unwrap_used, reason = "always has one")]
pub fn first(values: &[u32]) -> u32 {
    *values.first().unwrap()
}
