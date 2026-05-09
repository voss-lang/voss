//! End-of-turn status line. (D-08, D-09, D-10)
//!
//! Format: `─ {model} · {tokens} tok · ${cost} · ctx {pct}% ` plus filler dashes.
//! Accent rules:
//!   - Yellow when `ctx_pct > 0.8`.
//!   - Red    when `cost_usd > 1.0`.
//!   - Audible bell (`\x07`) when `ctx_pct >= 0.9`.

#[derive(Clone, Copy)]
pub enum Accent {
    Dim,
    Yellow,
    Red,
}

pub fn format(
    model: &str,
    tokens: usize,
    cost_usd: f64,
    ctx_pct: f32,
    term_width: usize,
) -> String {
    let cost_paint = if cost_usd > 1.0 {
        Accent::Red
    } else {
        Accent::Dim
    };
    let ctx_paint = if ctx_pct > 0.8 {
        Accent::Yellow
    } else {
        Accent::Dim
    };
    let core = format!(
        "─ {} · {} tok · {} · ctx {} ",
        model,
        format_thousands(tokens),
        paint(&format!("${:.3}", cost_usd), cost_paint),
        paint(
            &format!("{:.0}%", (ctx_pct * 100.0).round()),
            ctx_paint,
        ),
    );
    let approx_visible = visible_len(&core);
    let dashes = "─".repeat(term_width.saturating_sub(approx_visible));
    let mut line = format!("{core}{dashes}");
    if ctx_pct >= 0.9 {
        line.push('\x07');
    }
    line
}

fn paint(s: &str, accent: Accent) -> String {
    match accent {
        Accent::Dim => format!("\x1b[2m{s}\x1b[0m"),
        Accent::Yellow => format!("\x1b[33m{s}\x1b[0m"),
        Accent::Red => format!("\x1b[31m{s}\x1b[0m"),
    }
}

fn format_thousands(n: usize) -> String {
    let s = n.to_string();
    let bytes: Vec<char> = s.chars().collect();
    let mut out = String::new();
    for (i, c) in bytes.iter().rev().enumerate() {
        if i > 0 && i % 3 == 0 {
            out.push(',');
        }
        out.push(*c);
    }
    out.chars().rev().collect()
}

/// Strip ANSI SGR sequences for length calc.
fn visible_len(s: &str) -> usize {
    let mut n: usize = 0;
    let mut iter = s.chars();
    while let Some(c) = iter.next() {
        if c == '\x1b' {
            for c2 in iter.by_ref() {
                if c2 == 'm' {
                    break;
                }
            }
        } else {
            n += 1;
        }
    }
    n
}
