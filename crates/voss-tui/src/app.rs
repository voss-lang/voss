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
    pub quit: bool,
}

impl App {
    fn new() -> Self {
        App {
            transcript: vec!["connected — type a message, Enter to send, Esc to quit".into()],
            streaming: String::new(),
            input: String::new(),
            status: "ready".into(),
            pending_permission: None,
            busy: false,
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
    // Keep the tail visible without a full scrollback model (MVP).
    let height = body.height.saturating_sub(2) as usize;
    let start = lines.len().saturating_sub(height.max(1));
    let visible = lines[start..].join("\n");

    f.render_widget(
        Paragraph::new(visible)
            .block(Block::default().borders(Borders::ALL).title("voss"))
            .wrap(Wrap { trim: false }),
        body,
    );
    f.render_widget(
        Paragraph::new(format!("› {}", app.input))
            .block(Block::default().borders(Borders::ALL).title("input")),
        input,
    );
    f.render_widget(
        Paragraph::new(app.status.as_str()).style(Style::default().add_modifier(Modifier::DIM)),
        status,
    );
}

fn submit(http: &HttpClient, sid: &str, tx: &mpsc::Sender<AppEvent>, text: String) {
    let http = http.clone();
    let sid = sid.to_string();
    let tx = tx.clone();
    tokio::spawn(async move {
        if let Err(e) = http.post_message(&sid, &text, "plan").await {
            let _ = tx.send(AppEvent::Error(e.to_string())).await;
            return;
        }
        let _ = http.stream_events(&sid, tx).await;
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
        KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            let _ = http.abort(sid).await;
            app.status = "aborting…".into();
        }
        KeyCode::Char(c) if app.pending_permission.is_some() && (c == 'y' || c == 'n') => {
            if let Some(id) = app.pending_permission.take() {
                let choice = if c == 'y' { "a" } else { "d" };
                let _ = http.permission_reply(sid, &id, choice).await;
                app.status = "ready".into();
            }
        }
        KeyCode::Enter => {
            let text = app.input.trim().to_string();
            if !text.is_empty() {
                app.input.clear();
                submit(http, sid, tx, text);
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
