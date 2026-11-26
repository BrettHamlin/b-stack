#![no_std]
//! The greeting feature: what the app says to someone by name. No I/O here.

use core::fmt;

/// A greeting for one name, shown as `Hello, <name>!`.
pub struct Greeting<'a>(&'a str);

/// The greeting for `name`.
pub fn greet(name: &str) -> Greeting<'_> {
    Greeting(name)
}

impl fmt::Display for Greeting<'_> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Hello, {}!", self.0)
    }
}
