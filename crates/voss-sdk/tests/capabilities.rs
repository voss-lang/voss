use std::io::{Read, Write};
use std::net::TcpListener;
use voss_sdk::{error::VossError, VossClient};

async fn fetch(status: u16, body: &str) -> Result<voss_sdk::capabilities::Capabilities, VossError> {
    let server = TcpListener::bind("127.0.0.1:0").unwrap();
    let address = server.local_addr().unwrap();
    let body = body.to_owned();
    let worker = std::thread::spawn(move || {
        let (mut socket, _) = server.accept().unwrap();
        socket
            .set_read_timeout(Some(std::time::Duration::from_secs(5)))
            .unwrap();
        let mut request = Vec::new();
        let mut chunk = [0; 1024];
        while !request.windows(4).any(|w| w == b"\r\n\r\n") {
            let count = socket.read(&mut chunk).unwrap();
            assert!(count > 0);
            request.extend_from_slice(&chunk[..count]);
        }
        let request = String::from_utf8(request).unwrap();
        assert!(request.starts_with("GET /capabilities HTTP/1.1\r\n"));
        assert!(request
            .to_lowercase()
            .contains("authorization: bearer synthetic-token\r\n"));
        write!(socket, "HTTP/1.1 {status} Test\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}", body.len()).unwrap();
    });
    let result = VossClient::new(format!("http://{address}"), "synthetic-token".into())
        .capabilities()
        .await;
    worker.join().unwrap();
    result
}

#[tokio::test]
async fn compatible_capabilities_preserve_unknown_extensions() {
    let report = fetch(200, r#"{"v":1,"engine_version":"test","capabilities":["sessions.v1","future.v9"],"extra":true}"#).await.unwrap();
    assert!(report.supports("sessions.v1"));
    assert!(report.supports("future.v9"));
    assert!(!report.supports("swarms.v1"));
}

#[tokio::test]
async fn incompatible_protocol_never_supports_execution() {
    let report = fetch(
        200,
        r#"{"v":2,"engine_version":"test","capabilities":["sessions.v1"]}"#,
    )
    .await
    .unwrap();
    assert!(!report.compatible());
    assert!(!report.supports("sessions.v1"));
}

#[tokio::test]
async fn old_server_and_bad_responses_are_not_compatible_by_default() {
    assert!(matches!(
        fetch(404, r#"{"detail":"Not Found"}"#).await,
        Err(VossError::HttpStatus { status: 404, .. })
    ));
    assert!(fetch(200, r#"{"engine_version":"old"}"#).await.is_err());
    assert!(matches!(
        fetch(401, r#"{"detail":"Unauthorized"}"#).await,
        Err(VossError::HttpStatus { status: 401, .. })
    ));
}
