#![cfg(test)]

#[test]
fn greeting_works() {
    assert_eq!(greeting::greet("Ada").to_string(), "Hello, Ada!");
}
