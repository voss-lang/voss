use textstats::word_count;

#[test]
fn ac1_empty_and_blank() {
    assert_eq!(word_count(""), 0);
    assert_eq!(word_count("   \t\n"), 0);
}

#[test]
fn ac2_mixed_whitespace() {
    assert_eq!(word_count("a  b"), 2);
    assert_eq!(word_count(" lead and trail "), 3);
    assert_eq!(word_count("tab\tsep\nnew line"), 4);
}
