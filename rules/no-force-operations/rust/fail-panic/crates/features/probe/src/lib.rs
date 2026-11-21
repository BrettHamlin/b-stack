#![no_std]
pub fn first(values: &[u32]) -> u32 {
    match values.first() {
        Some(v) => *v,
        None => panic!("empty"),
    }
}
