//! Default toolset registry.

use std::path::Path;
use std::sync::Arc;

use crate::tool_trait::Tool;
use crate::{
    fs_edit, fs_glob, fs_grep, fs_read, fs_write, git_diff, git_status, shell_run, voss_check,
};

pub fn default_toolset(cwd: &Path) -> Vec<Arc<dyn Tool>> {
    let cwd = cwd.to_path_buf();
    vec![
        Arc::new(fs_read::FsRead { cwd: cwd.clone() }),
        Arc::new(fs_glob::FsGlob { cwd: cwd.clone() }),
        Arc::new(fs_grep::FsGrep { cwd: cwd.clone() }),
        Arc::new(fs_write::FsWrite { cwd: cwd.clone() }),
        Arc::new(fs_edit::FsEdit { cwd: cwd.clone() }),
        Arc::new(shell_run::ShellRun::new(cwd.clone())),
        Arc::new(git_status::GitStatus { cwd: cwd.clone() }),
        Arc::new(git_diff::GitDiff { cwd: cwd.clone() }),
        Arc::new(voss_check::VossCheck::new(cwd.clone())),
    ]
}
