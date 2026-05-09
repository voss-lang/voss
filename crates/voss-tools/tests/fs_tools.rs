use serde_json::json;

use voss_tools::{
    fs_edit::FsEdit, fs_glob::FsGlob, fs_read::FsRead, fs_write::FsWrite, Tool,
};

#[tokio::test]
async fn fs_write_then_read() {
    let tmp = tempfile::tempdir().unwrap();
    let cwd = tmp.path().to_path_buf();
    let writer = FsWrite { cwd: cwd.clone() };
    let reader = FsRead { cwd: cwd.clone() };

    let w = writer
        .invoke(json!({"path": "a.txt", "content": "hello"}))
        .await
        .unwrap();
    assert!(w.contains("wrote 5 bytes"), "got: {w}");

    let r = reader.invoke(json!({"path": "a.txt"})).await.unwrap();
    assert_eq!(r, "hello");
}

#[tokio::test]
async fn fs_edit_unique_match() {
    let tmp = tempfile::tempdir().unwrap();
    let cwd = tmp.path().to_path_buf();
    let writer = FsWrite { cwd: cwd.clone() };
    let editor = FsEdit { cwd: cwd.clone() };
    let reader = FsRead { cwd: cwd.clone() };

    writer
        .invoke(json!({"path": "f.txt", "content": "foo"}))
        .await
        .unwrap();
    let res = editor
        .invoke(json!({"path": "f.txt", "old": "foo", "new": "bar"}))
        .await
        .unwrap();
    assert!(res.contains("edited f.txt"), "got: {res}");
    assert_eq!(reader.invoke(json!({"path": "f.txt"})).await.unwrap(), "bar");
}

#[tokio::test]
async fn fs_edit_multiple_matches_errors() {
    let tmp = tempfile::tempdir().unwrap();
    let cwd = tmp.path().to_path_buf();
    let writer = FsWrite { cwd: cwd.clone() };
    let editor = FsEdit { cwd: cwd.clone() };
    writer
        .invoke(json!({"path": "f.txt", "content": "foofoo"}))
        .await
        .unwrap();
    let res = editor
        .invoke(json!({"path": "f.txt", "old": "foo", "new": "bar"}))
        .await
        .unwrap();
    assert!(res.contains("matches 2 times"), "got: {res}");
}

#[tokio::test]
async fn fs_edit_no_match_errors() {
    let tmp = tempfile::tempdir().unwrap();
    let cwd = tmp.path().to_path_buf();
    let writer = FsWrite { cwd: cwd.clone() };
    let editor = FsEdit { cwd: cwd.clone() };
    writer
        .invoke(json!({"path": "f.txt", "content": "foo"}))
        .await
        .unwrap();
    let res = editor
        .invoke(json!({"path": "f.txt", "old": "missing", "new": "x"}))
        .await
        .unwrap();
    assert!(res.contains("not found"), "got: {res}");
}

#[tokio::test]
async fn fs_glob_lists_files() {
    let tmp = tempfile::tempdir().unwrap();
    let cwd = tmp.path().to_path_buf();
    let writer = FsWrite { cwd: cwd.clone() };
    let glob = FsGlob { cwd: cwd.clone() };
    writer
        .invoke(json!({"path": "a.txt", "content": "1"}))
        .await
        .unwrap();
    writer
        .invoke(json!({"path": "b.txt", "content": "2"}))
        .await
        .unwrap();
    let res = glob.invoke(json!({"pattern": "*.txt"})).await.unwrap();
    let lines: Vec<&str> = res.lines().collect();
    assert_eq!(lines, vec!["a.txt", "b.txt"], "got: {res}");
}
