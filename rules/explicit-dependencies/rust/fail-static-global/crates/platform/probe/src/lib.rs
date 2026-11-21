use std::sync::Mutex;

pub static SHARED_COUNT: Mutex<u32> = Mutex::new(0);
