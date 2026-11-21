use core_types::Count;

pub fn one() -> Count {
    Count::ZERO.incremented().unwrap_or(Count::ZERO)
}
