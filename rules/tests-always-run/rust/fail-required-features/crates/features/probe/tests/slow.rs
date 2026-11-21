#![cfg(test)]

#[test]
fn doubles_large_values() {
    assert_eq!(probe::double(u32::MAX), 0);
}
