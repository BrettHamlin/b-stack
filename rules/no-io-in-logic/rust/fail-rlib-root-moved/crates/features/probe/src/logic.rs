pub fn read_data() -> Option<String> {
    std::fs::read_to_string("data.txt").ok()
}
