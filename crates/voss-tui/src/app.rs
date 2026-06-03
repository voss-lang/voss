//! ratatui UI loop (H2.6, H2.7, H2.8).
//!
//! A single UI task owns terminal + state and runs `tokio::select!` over three
//! sources: crossterm input (`EventStream`), network events (mpsc from the SSE
//! task), and a render tick. `draw` is a pure function of `&App` — no I/O. The
//! network lives in spawned tasks so the render loop never blocks.

use anyhow::Result;
use crossterm::event::{Event as CtEvent, EventStream, KeyCode, KeyEventKind, KeyModifiers};
use futures_util::StreamExt;
use ratatui::layout::{Constraint, Layout};
use ratatui::style::{Modifier, Style};
use ratatui::widgets::{Block, Borders, Paragraph, Wrap};
use ratatui::{DefaultTerminal, Frame};
use tokio::sync::mpsc;
use tokio::time::{interval, Duration};

use crate::event::AppEvent;
use crate::net::HttpClient;

pub struct App {
    pub transcript: Vec<String>,
    pub streaming: String,
    pub input: String,
    pub status: String,
    pub pending_permission: Option<String>,
    pub busy: bool,
    pub mode: String, // plan | edit | auto (Tab cycles)
    pub quit: bool,
}

impl App {
    fn new() -> Self {
        App {
            transcript: vec![
                "connected — type a message + Enter; /help for commands; Esc to quit".into(),
            ],
            streaming: String::new(),
            input: String::new(),
            status: "ready".into(),
            pending_permission: None,
            busy: false,
            mode: "plan".into(),
            quit: false,
        }
    }

    /// Commit any partially-streamed text to the transcript so a terminal event
    /// (error / idle / final) never leaves an orphaned live line that re-renders
    /// forever and contaminates the next turn's buffer.
    fn flush_streaming(&mut self) {
        if !self.streaming.is_empty() {
            let s = std::mem::take(&mut self.streaming);
            self.transcript.push(s);
        }
    }

    fn apply(&mut self, ev: AppEvent) {
        match ev {
            AppEvent::Connected => self.status = "connected".into(),
            AppEvent::User(t) => self.transcript.push(format!("› {t}")),
            AppEvent::Thinking(label) => self.status = label,
            AppEvent::Plan { confidence, steps } => self
                .transcript
                .push(format!("plan (conf {confidence:.2}): {}", steps.join(", "))),
            AppEvent::Tool { name, state } => {
                self.transcript.push(format!("⚙ {name} [{state}]"))
            }
            AppEvent::StreamDelta(t) => self.streaming.push_str(&t),
            AppEvent::StreamFinalize => {
                if !self.streaming.is_empty() {
                    let s = std::mem::take(&mut self.streaming);
                    self.transcript.push(s);
                }
            }
            AppEvent::Final { text, confidence } => {
                self.flush_streaming();
                self.transcript.push(format!("= {text}  (conf {confidence:.2})"));
                self.status = "ready".into();
            }
            AppEvent::Clarify { question, confidence } => self
                .transcript
                .push(format!("? {question}  (conf {confidence:.2})")),
            AppEvent::Status { tokens, cost_usd } => {
                self.status = format!("tokens {tokens} · ${cost_usd:.4}")
            }
            AppEvent::Permission { id, tool_name } => {
                self.pending_permission = Some(id);
                self.status = format!("PERMISSION: allow {tool_name}?  [y]es / [n]o");
            }
            AppEvent::Warning(m) => self.transcript.push(format!("⚠ {m}")),
            AppEvent::SessionIdle => {
                self.flush_streaming();
                self.busy = false;
                if !self.status.starts_with("PERMISSION") {
                    self.status = "ready".into();
                }
            }
            AppEvent::Error(e) => {
                self.flush_streaming();
                self.busy = false;
                self.transcript.push(format!("✗ error: {e}"));
            }
            AppEvent::Other(_) => {}
        }
    }
}

fn draw(f: &mut Frame, app: &App) {
    let [body, input, status] = Layout::vertical([
        Constraint::Min(3),
        Constraint::Length(3),
        Constraint::Length(1),
    ])
    .areas(f.area());

    let mut lines: Vec<String> = app.transcript.clone();
    if !app.streaming.is_empty() {
        lines.push(app.streaming.clone());
    }
    // Pin the newest output to the bottom by counting WRAPPED rows, not logical
    // lines: one entry can wrap to many rows (long/multi-line answers), so a
    // logical-line window clips the newest content. Width is char-approximated.
    let inner_w = body.width.saturating_sub(2).max(1) as usize;
    let avail = body.height.saturating_sub(2).max(1) as usize;
    let rows_of = |s: &str| -> usize {
        s.split('\n')
            .map(|seg| seg.chars().count().max(1).div_ceil(inner_w))
            .sum::<usize>()
            .max(1)
    };
    let mut used = 0usize;
    let mut start = lines.len();
    for i in (0..lines.len()).rev() {
        let r = rows_of(&lines[i]);
        if used + r > avail && used > 0 {
            break;
        }
        used += r;
        start = i;
    }
    let visible = lines[start..].join("\n");

    f.render_widget(
        Paragraph::new(visible)
            .block(Block::default().borders(Borders::ALL).title("voss"))
            .wrap(Wrap { trim: false }),
        body,
    );
    f.render_widget(
        Paragraph::new(format!("› {}", app.input)).block(
            Block::default()
                .borders(Borders::ALL)
                .title(format!("input · {} mode · Tab cycles", app.mode)),
        ),
        input,
    );
    f.render_widget(
        Paragraph::new(app.status.as_str()).style(Style::default().add_modifier(Modifier::DIM)),
        status,
    );
}

fn submit(http: &HttpClient, sid: &str, tx: &mpsc::Sender<AppEvent>, text: String, mode: String) {
    let http = http.clone();
    let sid = sid.to_string();
    let tx = tx.clone();
    tokio::spawn(async move {
        if let Err(e) = http.post_message(&sid, &text, &mode).await {
            let _ = tx.send(AppEvent::Error(e.to_string())).await;
            return;
        }
        let _ = http.stream_events(&sid, tx).await;
    });
}

/// Handle a slash command typed in the TUI (H4.4, minimal).
/// Edit/insight slashes (/diff /apply /budget /why) are deferred until the
/// server models pending-edits + budget envelopes.
fn slash(app: &mut App, cmd: &str, http: &HttpClient, sid: &str, tx: &mpsc::Sender<AppEvent>) {
    match cmd {
        "help" | "" => app
            .transcript
            .push("commands: /help /cost /clear /quit · Esc quit · Ctrl-C abort".into()),
        "clear" => {
            app.transcript.clear();
            app.streaming.clear();
        }
        "quit" => app.quit = true,
        "cost" => {
            let http = http.clone();
            let sid = sid.to_string();
            let tx = tx.clone();
            tokio::spawn(async move {
                let msg = match http.cost(&sid).await {
                    Ok((total, turns)) => AppEvent::Warning(format!(
                        "cost: ${total:.4} over {turns} turn(s)"
                    )),
                    Err(e) => AppEvent::Error(e.to_string()),
                };
                let _ = tx.send(msg).await;
            });
        }
        other => app
            .transcript
            .push(format!("unknown command: /{other} (try /help)")),
    }
}

/// Spawn a one-shot REST call off the UI task; report failure as an error event.
/// Keeps the select! loop responsive even if the server is slow/unreachable.
fn spawn_fire<F, Fut>(
    http: &HttpClient,
    sid: &str,
    tx: &mpsc::Sender<AppEvent>,
    label: &'static str,
    f: F,
) where
    F: FnOnce(HttpClient, String) -> Fut + Send + 'static,
    Fut: std::future::Future<Output = anyhow::Result<()>> + Send,
{
    let http = http.clone();
    let sid = sid.to_string();
    let tx = tx.clone();
    tokio::spawn(async move {
        if let Err(e) = f(http, sid).await {
            let _ = tx.send(AppEvent::Error(format!("{label}: {e}"))).await;
        }
    });
}

async fn handle_key(
    app: &mut App,
    key: crossterm::event::KeyEvent,
    http: &HttpClient,
    sid: &str,
    tx: &mpsc::Sender<AppEvent>,
) {
    if key.kind != KeyEventKind::Press {
        return;
    }
    match key.code {
        KeyCode::Esc => app.quit = true,
        KeyCode::Tab => {
            app.mode = match app.mode.as_str() {
                "plan" => "edit",
                "edit" => "auto",
                _ => "plan",
            }
            .into();
            app.status = format!("mode: {}", app.mode);
        }
        KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            // Spawn — never await network on the UI task or a slow server
            // freezes the whole loop (incl. Esc-to-quit).
            spawn_fire(http, sid, tx, "abort", |h, s| async move { h.abort(&s).await });
            app.status = "aborting…".into();
        }
        KeyCode::Char(c) if app.pending_permission.is_some() && (c == 'y' || c == 'n') => {
            if let Some(id) = app.pending_permission.take() {
                let choice = if c == 'y' { "a" } else { "d" };
                spawn_fire(http, sid, tx, "permission", move |h, s| async move {
                    h.permission_reply(&s, &id, choice).await
                });
                app.status = "ready".into();
            }
        }
        KeyCode::Enter => {
            let text = app.input.trim().to_string();
            if text.is_empty() {
                // ignore
            } else if let Some(cmd) = text.strip_prefix('/') {
                app.input.clear();
                slash(app, cmd.trim(), http, sid, tx);
            } else if app.busy {
                app.status = "turn in progress — wait or Ctrl-C to abort".into();
            } else {
                app.input.clear();
                app.busy = true;
                submit(http, sid, tx, text, app.mode.clone());
            }
        }
        KeyCode::Backspace => {
            app.input.pop();
        }
        KeyCode::Char(c) => app.input.push(c),
        _ => {}
    }
}

/// Run the UI loop until the user quits.
pub async fn run(mut terminal: DefaultTerminal, http: HttpClient, sid: String) -> Result<()> {
    let mut app = App::new();
    let (tx, mut rx) = mpsc::channel::<AppEvent>(256);
    let mut input_events = EventStream::new();
    let mut ticker = interval(Duration::from_millis(50));

    terminal.draw(|f| draw(f, &app))?;
    loop {
        tokio::select! {
            maybe = input_events.next() => {
                match maybe {
                    Some(Ok(CtEvent::Key(k))) => handle_key(&mut app, k, &http, &sid, &tx).await,
                    Some(Err(e)) => app.status = format!("input error: {e}"),
                    None => break,
                    _ => {}
                }
            }
            Some(ev) = rx.recv() => app.apply(ev),
            _ = ticker.tick() => {}
        }
        if app.quit {
            break;
        }
        terminal.draw(|f| draw(f, &app))?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn error_flushes_partial_stream_and_clears_busy() {
        let mut a = App::new();
        a.busy = true;
        a.apply(AppEvent::StreamDelta("partial ".into()));
        a.apply(AppEvent::StreamDelta("answer".into()));
        a.apply(AppEvent::Error("boom".into()));
        assert!(a.streaming.is_empty(), "partial must be flushed");
        assert!(a.transcript.iter().any(|l| l == "partial answer"));
        assert!(a.transcript.iter().any(|l| l.contains("boom")));
        assert!(!a.busy);
    }

    #[test]
    fn idle_without_finalize_flushes_partial() {
        let mut a = App::new();
        a.busy = true;
        a.apply(AppEvent::StreamDelta("half".into()));
        a.apply(AppEvent::SessionIdle); // no stream.finalize arrived
        assert!(a.streaming.is_empty());
        assert!(a.transcript.iter().any(|l| l == "half"));
        assert!(!a.busy);
    }

    #[test]
    fn normal_path_leaves_no_orphan_and_no_contamination() {
        let mut a = App::new();
        a.apply(AppEvent::StreamDelta("hello".into()));
        a.apply(AppEvent::StreamFinalize); // drains "hello" -> transcript
        a.apply(AppEvent::Final {
            text: "hello".into(),
            confidence: 0.9,
        });
        a.apply(AppEvent::SessionIdle);
        assert!(a.streaming.is_empty());
        // next turn must not inherit prior text
        a.apply(AppEvent::StreamDelta("world".into()));
        assert_eq!(a.streaming, "world");
    }
}
