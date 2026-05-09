use std::io::Cursor;
use tokio::io::BufReader;
use voss_bridge::{read_frame, write_frame};

#[tokio::test]
async fn happy_path() {
    let raw: &[u8] = b"Content-Length: 5\r\n\r\nhello";
    let mut r = BufReader::new(Cursor::new(raw));
    let body = read_frame(&mut r).await.unwrap();
    assert_eq!(body, b"hello");
}

#[tokio::test]
async fn missing_content_length() {
    let raw: &[u8] = b"X-Foo: bar\r\n\r\n";
    let mut r = BufReader::new(Cursor::new(raw));
    let err = read_frame(&mut r).await.unwrap_err();
    assert_eq!(err.kind(), std::io::ErrorKind::InvalidData);
}

#[tokio::test]
async fn negative_content_length() {
    let raw: &[u8] = b"Content-Length: -1\r\n\r\n";
    let mut r = BufReader::new(Cursor::new(raw));
    let err = read_frame(&mut r).await.unwrap_err();
    assert_eq!(err.kind(), std::io::ErrorKind::InvalidData);
}

#[tokio::test]
async fn unknown_header_tolerated() {
    let raw: &[u8] = b"X-Trace: 42\r\nContent-Length: 2\r\n\r\nok";
    let mut r = BufReader::new(Cursor::new(raw));
    let body = read_frame(&mut r).await.unwrap();
    assert_eq!(body, b"ok");
}

#[tokio::test]
async fn write_then_read_round_trip() {
    let mut buf: Vec<u8> = Vec::new();
    write_frame(&mut buf, b"hi").await.unwrap();
    let mut r = BufReader::new(Cursor::new(buf));
    let body = read_frame(&mut r).await.unwrap();
    assert_eq!(body, b"hi");
}
