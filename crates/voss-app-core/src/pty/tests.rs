use std::io::Read;
use std::sync::mpsc;
use std::time::Duration;

use crate::pty::commands::{ContextData, FileContextEntry, PtyEvent};
use crate::pty::reader::{
    extract_voss_osc, scan_shell_marks, CommandTracker, ScanItem, ShellMark,
};
use crate::pty::writer::validate_write;
use crate::pty::{spawn_session, PtyRegistry};

/// Read from the blocking PTY reader on a helper thread until `needle` appears
/// or `timeout` elapses; returns the accumulated output.
fn read_until(mut reader: Box<dyn Read + Send>, needle: &str, timeout: Duration) -> String {
    let (tx, rx) = mpsc::channel::<String>();
    std::thread::spawn(move || {
        let mut acc = Vec::new();
        let mut buf = [0u8; 4096];
        loop {
            match reader.read(&mut buf) {
                Ok(0) => break,
                Ok(n) => {
                    acc.extend_from_slice(&buf[..n]);
                    if tx.send(String::from_utf8_lossy(&acc).into_owned()).is_err() {
                        break;
                    }
                }
                Err(_) => break,
            }
        }
    });

    let deadline = std::time::Instant::now() + timeout;
    let mut latest = String::new();
    while std::time::Instant::now() < deadline {
        match rx.recv_timeout(Duration::from_millis(100)) {
            Ok(s) => {
                latest = s;
                if latest.contains(needle) {
                    break;
                }
            }
            Err(mpsc::RecvTimeoutError::Timeout) => continue,
            Err(mpsc::RecvTimeoutError::Disconnected) => break,
        }
    }
    latest
}

#[test]
fn test_pty_spawn_env() {
    // PTY-01: spawned shell inherits TERM=xterm-256color + COLORTERM=truecolor.
    let (session, reader, _pause) = spawn_session(24, 80, None, false).expect("spawn");
    session
        .write(
            b"printf 'T=%s C=%s VE=%s VA=%s\\n' \"$TERM\" \"$COLORTERM\" \"${VOSS_EMBEDDED-unset}\" \"${VOSS_AGENT_ID-unset}\"\n",
        )
        .expect("write");
    let out = read_until(reader, "T=xterm-256color", Duration::from_secs(8));
    session.kill().ok();
    assert!(
        out.contains("T=xterm-256color"),
        "TERM not set; got: {out:?}"
    );
    assert!(
        out.contains("C=truecolor"),
        "COLORTERM not set; got: {out:?}"
    );
    assert!(
        out.contains("VE=unset VA=unset"),
        "plain shell received Voss environment; got: {out:?}"
    );
}

#[test]
fn test_pty_spawn_shell_integration_on() {
    // S3.8 opt-in: flag on → VOSS_EMBEDDED=1 reaches the shell; every other
    // VOSS_* var stays stripped. VOSS_TEST_STRIP is unique to this test so
    // parallel tests never observe it.
    std::env::set_var("VOSS_TEST_STRIP", "1");
    let (session, reader, _pause) = spawn_session(24, 80, None, true).expect("spawn");
    session
        .write(
            b"printf 'VE=%s TS=%s\\n' \"${VOSS_EMBEDDED-unset}\" \"${VOSS_TEST_STRIP-unset}\"\n",
        )
        .expect("write");
    let out = read_until(reader, "VE=1", Duration::from_secs(8));
    session.kill().ok();
    std::env::remove_var("VOSS_TEST_STRIP");
    assert!(out.contains("VE=1"), "VOSS_EMBEDDED not set; got: {out:?}");
    assert!(
        out.contains("TS=unset"),
        "other VOSS_* vars must stay stripped; got: {out:?}"
    );
}

#[test]
fn test_pty_round_trip() {
    // PTY-02: bytes written to the PTY are echoed back through the reader.
    let (session, reader, _pause) = spawn_session(24, 80, None, false).expect("spawn");
    session.write(b"echo hi_marker_42\n").expect("write");
    let out = read_until(reader, "hi_marker_42", Duration::from_secs(8));
    session.kill().ok();
    assert!(
        out.contains("hi_marker_42"),
        "round-trip failed; got: {out:?}"
    );

    // Session id is a UUID v4 (non-sequential — T-).
    assert_eq!(
        session.id.get_version_num(),
        4,
        "session id must be UUID v4"
    );
}

#[test]
fn test_pty_write_validation() {
    // PTY-02 guard: empty / >1MiB rejected; unknown session id rejected.
    assert!(validate_write(b"").is_err(), "empty must reject");
    assert!(
        validate_write(&vec![0u8; 1_048_577]).is_err(),
        ">1MiB must reject"
    );
    assert!(validate_write(b"ok").is_ok(), "normal payload must pass");

    let reg = PtyRegistry::default();
    assert!(
        reg.get("no-such-session").is_none(),
        "unknown session = None"
    );
}

#[test]
fn test_foreground_pgid() {
    // PTY-06: foreground process name resolves via tcgetpgrp + pgid→pid.
    let (session, mut reader, _pause) = spawn_session(24, 80, None, false).expect("spawn");
    // Drain PTY output so the shell never blocks on a full master buffer.
    std::thread::spawn(move || {
        let mut buf = [0u8; 4096];
        while let Ok(n) = reader.read(&mut buf) {
            if n == 0 {
                break;
            }
        }
    });

    // `exec` replaces the shell process image with sleep (same pid), so the
    // foreground process is deterministically `sleep` (no job-control race)
    // and SIGKILL reaps it cleanly (no interactive shell that never exits).
    // Interactive shell startup (rc files) is variable, so poll until the
    // foreground name resolves to the exec'd `sleep` rather than guessing a
    // fixed settle delay.
    std::thread::sleep(Duration::from_millis(400));
    session.write(b"exec sleep 30\n").expect("write");

    let mut name: Option<String> = None;
    let deadline = std::time::Instant::now() + Duration::from_secs(10);
    while std::time::Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(300));
        let n = session
            .master_raw_fd()
            .and_then(crate::pty::foreground::get_foreground_name);
        if n.as_deref().is_some_and(|s| s.contains("sleep")) {
            name = n;
            break;
        }
        name = n;
    }
    session.kill().ok();

    #[cfg(any(target_os = "macos", target_os = "linux"))]
    {
        let n = name.expect("foreground name should resolve on macOS/Linux");
        assert!(n.contains("sleep"), "expected 'sleep', got: {n:?}");
    }
    #[cfg(not(any(target_os = "macos", target_os = "linux")))]
    {
        assert!(name.is_none(), "non-unix returns None (Windows stub)");
    }
}

// ── F3: extract_voss_osc unit tests ─────────────────────────────────────

#[test]
fn test_extract_voss_osc_parses_well_formed() {
    let payload = br#"{"tokens_used":100,"token_limit":1000,"cost_usd":0.005,"iteration":1,"model":"claude-3"}"#;
    let mut data = b"\x1b]1337;voss-budget=".to_vec();
    data.extend_from_slice(payload);
    data.push(0x07);
    let (json, display) =
        extract_voss_osc(&data, b"\x1b]1337;voss-budget=").expect("should find the sequence");
    assert_eq!(json, payload.to_vec());
    assert!(display.is_empty());
}

#[test]
fn test_extract_voss_osc_strips_surrounding_display_bytes() {
    let before = b"hello ";
    let after = b" world";
    let osc = b"\x1b]1337;voss-budget={\"tokens_used\":1,\"token_limit\":null,\"cost_usd\":0.0,\"iteration\":1,\"model\":\"m\"}\x07";
    let mut data = before.to_vec();
    data.extend_from_slice(osc);
    data.extend_from_slice(after);
    let (_, display) = extract_voss_osc(&data, b"\x1b]1337;voss-budget=").expect("found");
    assert_eq!(display, b"hello  world");
}

#[test]
fn test_extract_voss_osc_returns_none_for_partial_sequence() {
    let data = b"\x1b]1337;voss-budget={\"tokens_used\":1";
    assert!(extract_voss_osc(data, b"\x1b]1337;voss-budget=").is_none());
}

#[test]
fn test_extract_voss_osc_returns_none_for_unrelated_bytes() {
    let data = b"normal terminal output \x1b[32mgreen text\x1b[0m";
    assert!(extract_voss_osc(data, b"\x1b]1337;voss-budget=").is_none());
}

// ── F4: context OSC unit tests ────────────────────────────────────────

#[test]
fn test_extract_context_osc_parses_well_formed() {
    let payload = br#"{"system_tokens":500,"conversation_tokens":1200,"total_tokens":3000,"token_limit":200000,"files":[{"path":"src/main.rs","tokens":800,"state":"full","pinned":false}]}"#;
    let mut data = b"\x1b]1337;voss-context=".to_vec();
    data.extend_from_slice(payload);
    data.push(0x07);
    let (json, display) =
        extract_voss_osc(&data, b"\x1b]1337;voss-context=").expect("should find context OSC");
    assert_eq!(json, payload.to_vec());
    assert!(display.is_empty());
}

#[test]
fn test_extract_context_osc_strips_surrounding_bytes() {
    let before = b"output ";
    let after = b" more";
    let mut data = before.to_vec();
    data.extend_from_slice(b"\x1b]1337;voss-context=");
    data.extend_from_slice(br#"{"system_tokens":0,"conversation_tokens":0,"total_tokens":0,"token_limit":null,"files":[]}"#);
    data.push(0x07);
    data.extend_from_slice(after);
    let (_, display) = extract_voss_osc(&data, b"\x1b]1337;voss-context=").expect("found");
    assert_eq!(display, b"output  more");
}

#[test]
fn test_extract_context_osc_returns_none_for_partial() {
    let data = b"\x1b]1337;voss-context={\"system_tokens\":500";
    assert!(extract_voss_osc(data, b"\x1b]1337;voss-context=").is_none());
}

#[test]
fn test_extract_context_osc_returns_none_for_budget_prefix() {
    let mut data = b"\x1b]1337;voss-budget=".to_vec();
    data.extend_from_slice(
        br#"{"tokens_used":1,"token_limit":null,"cost_usd":0.0,"iteration":1,"model":"m"}"#,
    );
    data.push(0x07);
    assert!(extract_voss_osc(&data, b"\x1b]1337;voss-context=").is_none());
}

#[test]
fn test_context_data_serde_roundtrip() {
    let original = ContextData {
        system_tokens: 500,
        conversation_tokens: 1200,
        total_tokens: 3000,
        token_limit: Some(200_000),
        files: vec![
            FileContextEntry {
                path: "src/main.rs".to_string(),
                tokens: 800,
                state: "full".to_string(),
                pinned: false,
            },
            FileContextEntry {
                path: "src/lib.rs".to_string(),
                tokens: 400,
                state: "compressed".to_string(),
                pinned: true,
            },
        ],
    };
    let serialized = serde_json::to_vec(&original).expect("serialize");
    let deserialized: ContextData = serde_json::from_slice(&serialized).expect("deserialize");
    assert_eq!(deserialized.system_tokens, 500);
    assert_eq!(deserialized.total_tokens, 3000);
    assert_eq!(deserialized.token_limit, Some(200_000));
    assert_eq!(deserialized.files.len(), 2);
    assert_eq!(deserialized.files[0].path, "src/main.rs");
    assert_eq!(deserialized.files[0].state, "full");
    assert!(!deserialized.files[0].pinned);
    assert_eq!(deserialized.files[1].path, "src/lib.rs");
    assert_eq!(deserialized.files[1].state, "compressed");
    assert!(deserialized.files[1].pinned);
}

#[test]
fn test_extract_budget_osc_ignores_context_prefix() {
    let mut data = b"\x1b]1337;voss-context=".to_vec();
    data.extend_from_slice(br#"{"system_tokens":0,"conversation_tokens":0,"total_tokens":0,"token_limit":null,"files":[]}"#);
    data.push(0x07);
    assert!(extract_voss_osc(&data, b"\x1b]1337;voss-budget=").is_none());
}

// ── S3.2: shell-mark scanner (OSC 133 / OSC 7 / voss-cmd) ───────────────

fn marks_of(data: &[u8]) -> Vec<ShellMark> {
    scan_shell_marks(data)
        .into_iter()
        .filter_map(|i| match i {
            ScanItem::Mark(m) => Some(m),
            ScanItem::Display(_) => None,
        })
        .collect()
}

fn display_of(data: &[u8]) -> Vec<u8> {
    let mut out = Vec::new();
    for item in scan_shell_marks(data) {
        if let ScanItem::Display(bytes) = item {
            out.extend_from_slice(&bytes);
        }
    }
    out
}

#[test]
fn test_scan_osc133_all_marks() {
    let data = b"\x1b]133;A\x07\x1b]133;B\x07\x1b]133;C\x07\x1b]133;D;0\x07";
    assert_eq!(
        marks_of(data),
        vec![
            ShellMark::PromptStart,
            ShellMark::PromptEnd,
            ShellMark::CommandStart,
            ShellMark::CommandEnd(0),
        ]
    );
    assert!(display_of(data).is_empty());
}

#[test]
fn test_scan_osc133_d_exit_code_and_st_terminator() {
    let data = b"\x1b]133;D;127\x1b\\";
    assert_eq!(marks_of(data), vec![ShellMark::CommandEnd(127)]);
}

#[test]
fn test_scan_osc133_d_without_exit_defaults_zero() {
    assert_eq!(marks_of(b"\x1b]133;D\x07"), vec![ShellMark::CommandEnd(0)]);
}

#[test]
fn test_scan_osc133_trailing_params_accepted() {
    // wezterm-style `133;C;` / `133;A;cl=m;aid=1` carry extra fields.
    assert_eq!(marks_of(b"\x1b]133;C;\x07"), vec![ShellMark::CommandStart]);
    assert_eq!(
        marks_of(b"\x1b]133;A;cl=m;aid=1\x07"),
        vec![ShellMark::PromptStart]
    );
}

#[test]
fn test_scan_osc7_extracts_cwd_path() {
    let data = b"\x1b]7;file://myhost/Users/ben/project\x07";
    assert_eq!(
        marks_of(data),
        vec![ShellMark::Cwd("/Users/ben/project".to_string())]
    );
}

#[test]
fn test_scan_voss_cmd_parses_json() {
    let data = b"\x1b]1337;voss-cmd={\"cmd_id\":\"abc-123\",\"argv_text\":\"pnpm test\",\"cwd\":\"/repo\"}\x07";
    let marks = marks_of(data);
    assert_eq!(marks.len(), 1);
    match &marks[0] {
        ShellMark::CommandMeta(m) => {
            assert_eq!(m.cmd_id, "abc-123");
            assert_eq!(m.argv_text, "pnpm test");
            assert_eq!(m.cwd, "/repo");
        }
        other => panic!("expected CommandMeta, got {other:?}"),
    }
}

#[test]
fn test_scan_interleaved_display_and_marks_keep_order() {
    let data = b"out\n\x1b]133;D;1\x07\x1b]133;A\x07prompt$ ";
    let items = scan_shell_marks(data);
    assert_eq!(
        items,
        vec![
            ScanItem::Display(b"out\n".to_vec()),
            ScanItem::Mark(ShellMark::CommandEnd(1)),
            ScanItem::Mark(ShellMark::PromptStart),
            ScanItem::Display(b"prompt$ ".to_vec()),
        ]
    );
}

#[test]
fn test_scan_unknown_osc_passes_through_as_display() {
    let data = b"a\x1b]0;window title\x07b";
    assert!(marks_of(data).is_empty());
    assert_eq!(display_of(data), b"a\x1b]0;window title\x07b".to_vec());
}

#[test]
fn test_scan_unterminated_osc_passes_through() {
    let data = b"text\x1b]133;C";
    assert!(marks_of(data).is_empty());
    assert_eq!(display_of(data), data.to_vec());
}

#[test]
fn test_scan_malformed_voss_cmd_json_passes_through() {
    let data = b"\x1b]1337;voss-cmd={not json}\x07";
    assert!(marks_of(data).is_empty());
    assert_eq!(display_of(data), data.to_vec());
}

// ── S3.2: CommandTracker lifecycle ──────────────────────────────────────

fn apply_all(tracker: &mut CommandTracker, data: &[u8]) -> Vec<PtyEvent> {
    let mut events = Vec::new();
    for item in scan_shell_marks(data) {
        match item {
            ScanItem::Display(bytes) => tracker.capture_bytes(&bytes),
            ScanItem::Mark(mark) => events.extend(tracker.apply(&mark)),
        }
    }
    events
}

#[test]
fn test_tracker_full_command_lifecycle() {
    let mut t = CommandTracker::default();
    assert!(apply_all(&mut t, b"\x1b]7;file://h/repo\x07").is_empty());
    assert!(apply_all(&mut t, b"\x1b]133;A\x07prompt$ ").is_empty());
    assert!(apply_all(&mut t, b"\x1b]133;B\x07").is_empty());
    assert!(apply_all(&mut t, b"\x1b]133;C\x07").is_empty());
    let started = apply_all(
        &mut t,
        b"\x1b]1337;voss-cmd={\"cmd_id\":\"id-1\",\"argv_text\":\"pnpm test\",\"cwd\":\"/repo\"}\x07",
    );
    assert_eq!(started.len(), 1);
    match &started[0] {
        PtyEvent::CommandStarted {
            cmd_id,
            argv_text,
            cwd,
            at,
        } => {
            assert_eq!(cmd_id, "id-1");
            assert_eq!(argv_text, "pnpm test");
            assert_eq!(cwd, "/repo");
            assert!(at.ends_with('Z') && at.contains('T'), "ISO 8601: {at}");
        }
        other => panic!("expected CommandStarted, got {other:?}"),
    }
    std::thread::sleep(Duration::from_millis(5));
    assert!(apply_all(&mut t, b"FAIL src/foo.test.ts\n").is_empty());
    let finished = apply_all(&mut t, b"\x1b]133;D;1\x07");
    assert_eq!(finished.len(), 1);
    match &finished[0] {
        PtyEvent::CommandFinished {
            cmd_id,
            exit,
            duration_ms,
            output,
            truncated,
        } => {
            assert_eq!(cmd_id, "id-1");
            assert_eq!(*exit, 1);
            assert!(*duration_ms >= 5 && *duration_ms < 60_000);
            assert_eq!(output, &b"FAIL src/foo.test.ts\n".to_vec());
            assert!(!truncated);
        }
        other => panic!("expected CommandFinished, got {other:?}"),
    }
}

#[test]
fn test_tracker_command_end_without_start_is_ignored() {
    let mut t = CommandTracker::default();
    assert!(apply_all(&mut t, b"\x1b]133;D;0\x07").is_empty());
}

#[test]
fn test_tracker_voss_cmd_without_c_yields_zero_duration() {
    let mut t = CommandTracker::default();
    let started = apply_all(
        &mut t,
        b"\x1b]1337;voss-cmd={\"cmd_id\":\"id-2\",\"argv_text\":\"ls\",\"cwd\":\"/r\"}\x07",
    );
    assert!(matches!(started[0], PtyEvent::CommandStarted { .. }));
    let finished = apply_all(&mut t, b"\x1b]133;D;0\x07");
    match &finished[0] {
        PtyEvent::CommandFinished {
            cmd_id,
            duration_ms,
            ..
        } => {
            assert_eq!(cmd_id, "id-2");
            assert_eq!(*duration_ms, 0);
        }
        other => panic!("expected CommandFinished, got {other:?}"),
    }
}

#[test]
fn test_tracker_output_cap_head_plus_tail() {
    let mut t = CommandTracker::default();
    apply_all(&mut t, b"\x1b]133;C\x07");
    let mut big = Vec::with_capacity(1024 * 1024);
    for i in 0..(1024 * 1024) {
        big.push((i / 1024) as u8);
    }
    t.capture_bytes(&big);
    let finished = apply_all(&mut t, b"\x1b]133;D;0\x07");
    match &finished[0] {
        PtyEvent::CommandFinished {
            output, truncated, ..
        } => {
            assert!(truncated);
            assert_eq!(output.len(), 256 * 1024);
            assert_eq!(&output[..192 * 1024], &big[..192 * 1024]);
            assert_eq!(&output[192 * 1024..], &big[big.len() - 64 * 1024..]);
        }
        other => panic!("expected CommandFinished, got {other:?}"),
    }
}

#[test]
fn test_tracker_output_between_head_cap_and_total_cap_not_truncated() {
    let mut t = CommandTracker::default();
    apply_all(&mut t, b"\x1b]133;C\x07");
    let payload = vec![b'x'; 200 * 1024];
    t.capture_bytes(&payload);
    let finished = apply_all(&mut t, b"\x1b]133;D;0\x07");
    match &finished[0] {
        PtyEvent::CommandFinished {
            output, truncated, ..
        } => {
            assert!(!truncated);
            assert_eq!(*output, payload);
        }
        other => panic!("expected CommandFinished, got {other:?}"),
    }
}

#[test]
fn test_tracker_sequential_commands_get_separate_events() {
    let mut t = CommandTracker::default();
    for n in 0..2 {
        let id = format!("id-{n}");
        apply_all(&mut t, b"\x1b]133;C\x07");
        let meta = format!(
            "\x1b]1337;voss-cmd={{\"cmd_id\":\"{id}\",\"argv_text\":\"cmd{n}\",\"cwd\":\"/r\"}}\x07"
        );
        apply_all(&mut t, meta.as_bytes());
        apply_all(&mut t, format!("output-{n}\n").as_bytes());
        let finished = apply_all(&mut t, b"\x1b]133;D;0\x07");
        match &finished[0] {
            PtyEvent::CommandFinished {
                cmd_id, output, ..
            } => {
                assert_eq!(*cmd_id, id);
                assert_eq!(*output, format!("output-{n}\n").into_bytes());
            }
            other => panic!("expected CommandFinished, got {other:?}"),
        }
    }
}

#[test]
fn test_command_events_serde_tagged_wire_format() {
    let started = serde_json::to_value(PtyEvent::CommandStarted {
        cmd_id: "id".to_string(),
        argv_text: "ls".to_string(),
        cwd: "/r".to_string(),
        at: "2026-09-06T00:00:00Z".to_string(),
    })
    .expect("serialize");
    assert_eq!(started["type"], "command_started");
    assert_eq!(started["cmd_id"], "id");
    let finished = serde_json::to_value(PtyEvent::CommandFinished {
        cmd_id: "id".to_string(),
        exit: 1,
        duration_ms: 42,
        output: b"out".to_vec(),
        truncated: false,
    })
    .expect("serialize");
    assert_eq!(finished["type"], "command_finished");
    assert_eq!(finished["exit"], 1);
    assert_eq!(finished["duration_ms"], 42);
}

#[test]
fn command_capture_survives_every_read_boundary() {
    use super::reader::OscBuffer;
    let wire = b"\x1b]133;C\x07\x1b]1337;voss-cmd={\"cmd_id\":\"boundary\",\"argv_text\":\"pnpm test\",\"cwd\":\"/repo\"}\x07FAIL sample.spec.ts\x1b]133;D;1\x1b\\";
    for split in 0..=wire.len() {
        let mut buffer = OscBuffer::default();
        let mut tracker = CommandTracker::default();
        let mut events = Vec::new();
        for chunk in [&wire[..split], &wire[split..]] {
            for item in scan_shell_marks(&buffer.push(chunk)) {
                match item {
                    ScanItem::Mark(mark) => events.extend(tracker.apply(&mark)),
                    ScanItem::Display(bytes) => tracker.capture_bytes(&bytes),
                }
            }
        }
        assert_eq!(events.len(), 2, "split {split}");
        match &events[1] {
            PtyEvent::CommandFinished { cmd_id, exit, output, truncated, .. } => {
                assert_eq!(cmd_id, "boundary");
                assert_eq!(*exit, 1);
                assert_eq!(output, b"FAIL sample.spec.ts");
                assert!(!truncated);
            }
            other => panic!("unexpected event {other:?}"),
        }
    }
}

#[test]
fn malformed_osc_buffer_is_bounded() {
    use super::reader::OscBuffer;
    let mut buffer = OscBuffer::default();
    assert!(buffer.push(b"\x1b]1337;").is_empty());
    assert_eq!(buffer.push(&vec![b'x'; 65536]).len(), 65543);
    assert_eq!(buffer.push(b"visible"), b"visible");
}

#[test]
fn shell_integration_sources_hooks_only_when_enabled() {
    use std::os::unix::fs::PermissionsExt;
    if std::env::var_os("VOSS_CAPTURE_TEST_CHILD").is_some() {
        for enabled in [false, true] {
            let (session, reader, _) = spawn_session(24, 80, None, enabled).unwrap();
            session.write(b"printf 'shell %s\\n' ready\n").unwrap();
            let output = read_until(reader, "shell ready", Duration::from_secs(8));
            session.kill().ok();
            assert!(output.contains("shell ready"));
            assert_eq!(output.contains("VOSS_CAPTURE_INSTALLED"), enabled);
        }
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let shell = dir.path().join("bash");
    std::fs::write(&shell, "#!/bin/sh\nexec /bin/bash --noprofile --norc -i\n").unwrap();
    let voss = dir.path().join("voss");
    std::fs::write(&voss, "#!/bin/sh\nprintf '%s\\n' 'printf \"VOSS_CAPTURE_INSTALLED\\n\"'\n").unwrap();
    for path in [&shell, &voss] {
        std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o700)).unwrap();
    }
    let status = std::process::Command::new(std::env::current_exe().unwrap())
        .args(["--exact", "pty::tests::shell_integration_sources_hooks_only_when_enabled", "--nocapture"])
        .env_clear()
        .env("VOSS_CAPTURE_TEST_CHILD", "1")
        .env("HOME", dir.path())
        .env("SHELL", shell)
        .env("PATH", format!("{}:/usr/bin:/bin", dir.path().display()))
        .status().unwrap();
    assert!(status.success());
}
