#![cfg(test)]

use probe::Side;

fn enemy_of(side: Side) -> Side {
    match side {
        Side::Blue => Side::Red,
        Side::Red => Side::Blue,
    }
}

#[test]
fn matches_every_variant_while_allowing_option_and_guards() {
    let mut blue_seen = false;
    if Side::Blue == Side::Blue {
        blue_seen = true;
    }
    let fallback = if let Some(found) = Some(Side::Blue) { found } else { Side::Red };
    let bounded = if 1u32 == u32::MAX { 0 } else { 1 };
    assert_eq!((enemy_of(fallback), blue_seen, bounded), (Side::Red, true, 1));
}
