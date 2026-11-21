#![no_std]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PlayerId(u32);

impl PlayerId {
    pub fn parse(raw: u32) -> Option<PlayerId> {
        (raw > 0).then_some(PlayerId(raw))
    }
}

pub fn score(_player: PlayerId) -> u32 {
    0
}

pub fn lookup() -> u32 {
    score(7)
}
