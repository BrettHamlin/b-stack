use std::sync::{Arc, Mutex};
use std::thread;

pub fn count_in_threads() -> Option<u32> {
    let total = Arc::new(Mutex::new(0_u32));
    let workers: Vec<_> = (0..4)
        .map(|_| {
            let total = Arc::clone(&total);
            thread::spawn(move || total.lock().map(|mut n| *n += 1).is_ok())
        })
        .collect();
    let ok = workers.into_iter().all(|w| w.join().unwrap_or(false));
    let value = total.lock().ok().map(|n| *n);
    value.filter(|_| ok)
}
