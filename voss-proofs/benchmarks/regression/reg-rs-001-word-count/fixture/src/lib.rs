/// Count words separated by whitespace.
pub fn word_count(s: &str) -> usize {
    s.split(' ').count()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn two_words() {
        assert_eq!(word_count("hello world"), 2);
    }
}
