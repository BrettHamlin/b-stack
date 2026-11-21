#![allow(unsafe_code)]

pub fn first(values: &[u32]) -> Option<u32> {
    values.first().copied()
}
