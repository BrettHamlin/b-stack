pub fn first(values: &[u32]) -> u32 {
    unsafe { *values.as_ptr() }
}
