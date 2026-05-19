//! PTY core tests (A2-02). Drive `spawn_session` directly (Tauri-free) so no
//! `AppHandle`/`Channel` is required.

use std::io::Read;
use std::sync::mpsc;
use std::time::Duration;

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
    let (session, reader, _pause) = spawn_session(24, 80, None).expect("spawn");
    session
        .write(b"printf 'T=%s C=%s\\n' \"$TERM\" \"$COLORTERM\"\n")
        .expect("write");
    let out = read_until(reader, "T=xterm-256color", Duration::from_secs(8));
    session.kill().ok();
    assert!(
        out.contains("T=xterm-256color"),
        "TERM not set; got: {out:?}"
    );
    assert!(out.contains("C=truecolor"), "COLORTERM not set; got: {out:?}");
}

#[test]
fn test_pty_round_trip() {
    // PTY-02: bytes written to the PTY are echoed back through the reader.
    let (session, reader, _pause) = spawn_session(24, 80, None).expect("spawn");
    session.write(b"echo hi_marker_42\n").expect("write");
    let out = read_until(reader, "hi_marker_42", Duration::from_secs(8));
    session.kill().ok();
    assert!(out.contains("hi_marker_42"), "round-trip failed; got: {out:?}");

    // Session id is a UUID v4 (non-sequential — T-A2-03).
    assert_eq!(session.id.get_version_num(), 4, "session id must be UUID v4");
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
    assert!(reg.get("no-such-session").is_none(), "unknown session = None");
}

#[test]
fn test_foreground_pgid() {
    // PTY-06: foreground process name resolves via tcgetpgrp + pgid→pid.
    let (session, reader, _pause) = spawn_session(24, 80, None).expect("spawn");
    // Settle the shell prompt before launching the foreground child.
    let _ = read_until(reader, "$", Duration::from_secs(3));
    session.write(b"sleep 5\n").expect("write");
    std::thread::sleep(Duration::from_millis(800));

    let fd = session.master_raw_fd();
    let name = fd.and_then(crate::pty::foreground::get_foreground_name);
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
