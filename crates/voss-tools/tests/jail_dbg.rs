use voss_tools::sandbox::jail_path;

#[test]
fn dbg() {
    let tmp = tempfile::tempdir().unwrap();
    println!("tmp = {:?}", tmp.path());
    println!("canon = {:?}", tmp.path().canonicalize());
    let p = jail_path(tmp.path(), "a.txt").unwrap();
    println!("jail = {:?}", p);
    println!("parent = {:?}", p.parent());
    println!("parent exists = {}", p.parent().unwrap().exists());
    let r = std::fs::write(&p, b"hello");
    println!("write = {:?}", r);
}
