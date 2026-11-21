#![no_std]
extern crate std;

pub fn load() -> bool {
    std::fs::read_to_string("data.txt").is_ok()
}
