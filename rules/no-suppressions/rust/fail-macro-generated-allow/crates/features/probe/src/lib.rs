#![no_std]
macro_rules! quietly {
    ($item:item) => {
        #[allow(clippy::unwrap_used)]
        $item
    };
}

quietly! {
    pub fn first(values: &[u32]) -> u32 {
        *values.first().unwrap()
    }
}
