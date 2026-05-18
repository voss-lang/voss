// Minimal Rust fixture

pub fn shared_entry(x: i32) -> i32 {
    helper_value(x) + 1
}

fn helper_value(n: i32) -> i32 {
    n * 2
}

pub struct HelperStruct {
    pub value: i32,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn it_works() {
        assert_eq!(shared_entry(41), 83);
    }
}
