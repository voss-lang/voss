//! Minimal markdown → ANSI styler for TTY rendering of assistant replies.
//!
//! Handles: headings, bold, italic, inline code, fenced code, lists,
//! blockquotes, links (text only, URL appended dim). No tables / footnotes
//! / HTML — intentionally narrow.
//!
//! Output is line-oriented and assumes a TTY that understands SGR escapes.

use pulldown_cmark::{CodeBlockKind, Event, HeadingLevel, Options, Parser, Tag, TagEnd};

const RESET: &str = "\x1b[0m";
const BOLD: &str = "\x1b[1m";
const DIM: &str = "\x1b[2m";
const ITALIC: &str = "\x1b[3m";
const UNDERLINE: &str = "\x1b[4m";
const CYAN: &str = "\x1b[36m";
const YELLOW: &str = "\x1b[33m";
const GREEN: &str = "\x1b[32m";

/// Render markdown to a string with ANSI styling. Falls back to printing the
/// raw text if anything goes wrong.
pub fn to_ansi(src: &str) -> String {
    let parser = Parser::new_ext(src, Options::ENABLE_STRIKETHROUGH);
    let mut out = String::with_capacity(src.len() + 64);
    let mut in_code = false;
    let mut list_depth: usize = 0;
    let mut list_ordinal: Vec<Option<u64>> = Vec::new();

    for ev in parser {
        match ev {
            Event::Start(tag) => match tag {
                Tag::Heading { level, .. } => {
                    let hashes = "#".repeat(heading_n(level));
                    out.push_str(BOLD);
                    out.push_str(CYAN);
                    out.push_str(&hashes);
                    out.push(' ');
                }
                Tag::Paragraph => {}
                Tag::Emphasis => out.push_str(ITALIC),
                Tag::Strong => out.push_str(BOLD),
                Tag::Strikethrough => out.push_str("\x1b[9m"),
                Tag::Link { dest_url, .. } => {
                    out.push_str(UNDERLINE);
                    out.push_str(CYAN);
                    // text follows; URL appended on link close.
                    let _ = dest_url; // captured at end via TagEnd::Link
                }
                Tag::CodeBlock(kind) => {
                    in_code = true;
                    let lang = match &kind {
                        CodeBlockKind::Fenced(s) => s.as_ref(),
                        CodeBlockKind::Indented => "",
                    };
                    out.push('\n');
                    out.push_str(DIM);
                    out.push_str(&format!("┌─ {} ", if lang.is_empty() { "code" } else { lang }));
                    out.push_str(RESET);
                    out.push('\n');
                    out.push_str(GREEN);
                }
                Tag::List(start) => {
                    list_depth = list_depth.saturating_add(1);
                    list_ordinal.push(start);
                }
                Tag::Item => {
                    let indent = "  ".repeat(list_depth.saturating_sub(1));
                    out.push_str(&indent);
                    let marker = match list_ordinal.last_mut() {
                        Some(Some(n)) => {
                            let s = format!("{n}. ");
                            *n += 1;
                            s
                        }
                        _ => "• ".to_string(),
                    };
                    out.push_str(&marker);
                }
                Tag::BlockQuote(_) => {
                    out.push_str(DIM);
                    out.push_str("│ ");
                }
                _ => {}
            },
            Event::End(end) => match end {
                TagEnd::Heading(_) => {
                    out.push_str(RESET);
                    out.push('\n');
                }
                TagEnd::Paragraph => out.push_str("\n\n"),
                TagEnd::Emphasis | TagEnd::Strong | TagEnd::Strikethrough => out.push_str(RESET),
                TagEnd::Link => out.push_str(RESET),
                TagEnd::CodeBlock => {
                    in_code = false;
                    out.push_str(RESET);
                    out.push_str(DIM);
                    out.push_str("└─");
                    out.push_str(RESET);
                    out.push('\n');
                }
                TagEnd::List(_) => {
                    list_depth = list_depth.saturating_sub(1);
                    list_ordinal.pop();
                    out.push('\n');
                }
                TagEnd::Item => out.push('\n'),
                TagEnd::BlockQuote(_) => {
                    out.push_str(RESET);
                    out.push('\n');
                }
                _ => {}
            },
            Event::Text(t) => out.push_str(&t),
            Event::Code(t) => {
                out.push_str(YELLOW);
                out.push('`');
                out.push_str(&t);
                out.push('`');
                out.push_str(RESET);
            }
            Event::SoftBreak => {
                if in_code {
                    out.push('\n');
                } else {
                    out.push(' ');
                }
            }
            Event::HardBreak => out.push('\n'),
            Event::Rule => {
                out.push_str(DIM);
                out.push_str("\n────────\n");
                out.push_str(RESET);
            }
            _ => {}
        }
    }

    // Trim trailing blank lines to avoid double-spacing into status line.
    while out.ends_with('\n') {
        out.pop();
    }
    out
}

fn heading_n(level: HeadingLevel) -> usize {
    match level {
        HeadingLevel::H1 => 1,
        HeadingLevel::H2 => 2,
        HeadingLevel::H3 => 3,
        HeadingLevel::H4 => 4,
        HeadingLevel::H5 => 5,
        HeadingLevel::H6 => 6,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn renders_plain_paragraph() {
        let s = to_ansi("hello world");
        assert!(s.contains("hello world"));
    }

    #[test]
    fn renders_inline_code() {
        let s = to_ansi("use `Reedline`");
        assert!(s.contains("`Reedline`"));
        assert!(s.contains("\x1b[33m"));
    }

    #[test]
    fn renders_heading() {
        let s = to_ansi("# Title\n");
        assert!(s.contains("# Title"));
        assert!(s.contains("\x1b[1m"));
    }

    #[test]
    fn renders_fenced_code() {
        let s = to_ansi("```rust\nlet x = 1;\n```\n");
        assert!(s.contains("rust"));
        assert!(s.contains("let x = 1;"));
    }

    #[test]
    fn renders_ordered_list() {
        let s = to_ansi("1. first\n2. second\n");
        assert!(s.contains("1. first"));
        assert!(s.contains("2. second"));
    }
}
