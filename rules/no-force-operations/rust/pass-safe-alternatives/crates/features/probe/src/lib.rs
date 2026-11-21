#![no_std]
pub fn first(values: &[u32]) -> Option<u32> {
    values.first().copied()
}

pub fn low_byte(value: u32) -> Option<u8> {
    u8::try_from(value).ok()
}

pub fn widen(value: u8) -> u32 {
    u32::from(value)
}
