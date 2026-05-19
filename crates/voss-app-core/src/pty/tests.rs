//! RED Rust test scaffolds for the PTY core. Each panics so
//! `cargo test -p voss-app-core` produces discoverable FAILED output for the
//! Nyquist contract. A2-02 replaces the panics with real assertions.

#[test]
fn test_pty_spawn_env() {
    // RED: PTY-01 not implemented — A2-02
    // (spawned PTY must inherit a sane env: TERM=xterm-256color, cwd, $SHELL)
    panic!("RED: PTY-01 spawn-env not implemented — A2-02");
}

#[test]
fn test_pty_round_trip() {
    // RED: PTY-02 not implemented — A2-02
    // (write bytes to PTY stdin, read the echoed bytes back from the master)
    panic!("RED: PTY-02 round-trip not implemented — A2-02");
}

#[test]
fn test_foreground_pgid() {
    // RED: PTY-06 not implemented — A2-02
    // (tcgetpgrp/libproc resolves the foreground pgid for SIGINT routing)
    panic!("RED: PTY-06 foreground-pgid not implemented — A2-02");
}
