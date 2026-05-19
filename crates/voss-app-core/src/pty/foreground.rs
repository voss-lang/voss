//! Foreground-process name resolution for the Variant B pane header and
//! PTY-06 shell-vs-child SIGINT routing.
//!
//! Resolution chain: `tcgetpgrp(master_fd)` → foreground process-group id →
//! the pids in that group → the leader's process name.
//!
//! NOTE (A2-RESEARCH OQ-3 footgun): do NOT pass the pgid to
//! `libproc::proc_pid::name()` directly — a pgid is not a pid. The plan
//! referenced `libproc::proc_pid::listpids(ProcType::ProcPGRPOnly(pgid))`, but
//! libproc-rs 0.14 cannot pass the pgid through `listpids` (it takes no
//! type-info arg). The correct 0.14 API is
//! `libproc::processes::pids_by_type(ProcFilter::ByProgramGroup { pgid })`,
//! used below; documented here as a plan-API-version defect.

#[cfg(target_os = "macos")]
pub fn get_foreground_name(master_fd: std::os::unix::io::RawFd) -> Option<String> {
    use std::os::fd::BorrowedFd;

    use libproc::processes::{pids_by_type, ProcFilter};

    // Safety: the master fd outlives this borrowed view (held by PtySession).
    let borrowed = unsafe { BorrowedFd::borrow_raw(master_fd) };
    let pgid = nix::unistd::tcgetpgrp(borrowed).ok()?;
    let pgid_raw = pgid.as_raw() as u32;

    let pids = pids_by_type(ProcFilter::ByProgramGroup { pgrpid: pgid_raw }).ok()?;
    // Prefer the group leader (pid == pgid) when present, else the first pid.
    let pid = pids
        .iter()
        .copied()
        .find(|&p| p == pgid_raw)
        .or_else(|| pids.first().copied())?;

    libproc::proc_pid::name(pid as i32).ok()
}

#[cfg(target_os = "linux")]
pub fn get_foreground_name(master_fd: std::os::unix::io::RawFd) -> Option<String> {
    use std::os::fd::BorrowedFd;

    let borrowed = unsafe { BorrowedFd::borrow_raw(master_fd) };
    let pgid = nix::unistd::tcgetpgrp(borrowed).ok()?;
    std::fs::read_to_string(format!("/proc/{}/comm", pgid.as_raw()))
        .ok()
        .map(|s| s.trim().to_owned())
}

// GAP: Windows foreground detection — owning future Windows phase.
// Windows has no tcgetpgrp/pgid model; ConPTY foreground resolution is a
// separate effort (A2-RESEARCH OQ-2). Explicit documented stub.
#[cfg(not(any(target_os = "macos", target_os = "linux")))]
pub fn get_foreground_name(_master_fd: std::os::unix::io::RawFd) -> Option<String> {
    None
}
