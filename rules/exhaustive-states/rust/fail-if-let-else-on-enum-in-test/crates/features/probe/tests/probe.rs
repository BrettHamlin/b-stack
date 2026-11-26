#![cfg(test)]

use probe::Side;

fn enemy_of(side: Side) -> Side {
    if let Side::Blue = side {
        Side::Red
    } else {
        Side::Blue
    }
}

#[test]
fn picks_the_opposing_side() {
    assert_eq!(enemy_of(Side::Blue), Side::Red);
}
