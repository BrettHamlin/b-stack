#![no_std]
//! Domain types shared by every feature. No I/O: the crate can't name std.

use core::fmt;

/// How many times something happened. Only counts up, and refuses to wrap.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Default)]
pub struct Count(u32);

impl Count {
    pub const ZERO: Count = Count(0);

    pub fn new(value: u32) -> Count {
        Count(value)
    }

    pub fn value(self) -> u32 {
        self.0
    }

    /// One more, or None if the count is already at its maximum.
    pub fn incremented(self) -> Option<Count> {
        self.0.checked_add(1).map(Count)
    }
}

impl fmt::Display for Count {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}
