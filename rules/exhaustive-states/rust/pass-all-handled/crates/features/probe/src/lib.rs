#![no_std]
pub enum Load {
    Idle,
    Loading,
    Loaded(u32),
    Failed,
}

pub fn label(state: &Load) -> &'static str {
    match state {
        Load::Idle => "idle",
        Load::Loading | Load::Failed => "busy",
        Load::Loaded(_) => "loaded",
    }
}
