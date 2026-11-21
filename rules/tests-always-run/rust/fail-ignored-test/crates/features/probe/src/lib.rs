#![no_std]
pub fn double(value: u32) -> u32 {
    value.saturating_mul(2)
}
