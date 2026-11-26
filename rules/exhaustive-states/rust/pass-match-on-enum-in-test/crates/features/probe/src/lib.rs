#![no_std]

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Side {
    Blue,
    Red,
}

#[cfg(not(test))]
pub fn is_blue_turn(side: Side) -> &'static str {
    if side == Side::Blue { "blue" } else { "not-blue" }
}
