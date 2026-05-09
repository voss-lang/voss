use voss_render::status_line;

#[test]
fn yellow_when_ctx_pct_above_80() {
    let line = status_line::format("m", 100, 0.5, 0.85, 80);
    assert!(
        line.contains("\x1b[33m"),
        "expected yellow accent, got: {line}"
    );
}

#[test]
fn no_yellow_when_ctx_pct_below_80() {
    let line = status_line::format("m", 100, 0.5, 0.5, 80);
    assert!(!line.contains("\x1b[33m"), "unexpected yellow at 50% ctx");
}

#[test]
fn red_when_cost_above_one_dollar() {
    let line = status_line::format("m", 100, 1.5, 0.5, 80);
    assert!(line.contains("\x1b[31m"), "expected red accent for $1.50");
}

#[test]
fn bell_at_90_percent() {
    let line = status_line::format("m", 100, 0.5, 0.95, 80);
    assert!(line.contains('\x07'), "expected audible bell at 95% ctx");
}

#[test]
fn no_bell_below_90_percent() {
    let line = status_line::format("m", 100, 0.5, 0.85, 80);
    assert!(!line.contains('\x07'), "no bell at 85% ctx");
}
