use std::path::Path;

pub fn exists(path: &Path) -> bool {
    std::fs::metadata(path).is_ok()
}
