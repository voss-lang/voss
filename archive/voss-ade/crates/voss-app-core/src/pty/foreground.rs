#[cfg(target_os = "macos")]
pub fn get_foreground_name(master_fd: std::os::unix::io::RawFd) -> Option<String> {
    use std::os::fd::BorrowedFd;

    use libproc::processes::{pids_by_type, ProcFilter};

    // Safety: the master fd outlives this borrowed view (held by PtySession).
    let borrowed = unsafe { BorrowedFd::borrow_raw(master_fd) };
    let pgid = nix::unistd::tcgetpgrp(borrowed).ok()?;
    let pgid_raw = pgid.as_raw() as u32;

    let pids = pids_by_type(ProcFilter::ByProgramGroup { pgrpid: pgid_raw }).ok()?;
    // group leader — under job control the leader is often the shell, not the
    // foreground child we want to name.
    let pid = pids.first().copied()?;

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

#[cfg(not(any(target_os = "macos", target_os = "linux")))]
pub fn get_foreground_name(_master_fd: std::os::unix::io::RawFd) -> Option<String> {
    None
}
