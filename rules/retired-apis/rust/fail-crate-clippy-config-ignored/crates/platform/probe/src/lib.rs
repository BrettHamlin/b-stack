use std::time::Duration;

pub fn wait_for_save() {
    std::thread::sleep(Duration::from_millis(50));
}
