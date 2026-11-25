#![cfg(test)]

use probe::Side;

fn enemy_of(side: Side) -> Side {
    if side == Side::Blue {
        Side::Red
    } else {
        Side::Blue
    }
}

#[test]
fn picks_the_opposing_side() {
    assert_eq!(enemy_of(Side::Blue), Side::Red);
}
