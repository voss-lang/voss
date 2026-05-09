//! LSP-style Content-Length framing for JSON-RPC over stdio.
//!
//! Per phase D-01..D-03: header lines terminated by `\r\n`, header block
//! terminated by an empty `\r\n` line, then exactly Content-Length bytes of
//! body. Unknown headers are tolerated (forward-compat); missing or negative
//! Content-Length is rejected.

use std::io;
use tokio::io::{AsyncBufReadExt, AsyncReadExt, AsyncWrite, AsyncWriteExt, AsyncBufRead};

/// Read one LSP-framed message from `r` and return its body bytes.
///
/// Returns `InvalidData` on missing/negative/unparseable Content-Length.
/// Returns `UnexpectedEof` if the stream closes before a body is fully read.
pub async fn read_frame<R: AsyncBufRead + Unpin>(r: &mut R) -> io::Result<Vec<u8>> {
    let mut content_length: Option<i64> = None;

    loop {
        let mut line = String::new();
        let n = r.read_line(&mut line).await?;
        if n == 0 {
            return Err(io::Error::new(
                io::ErrorKind::UnexpectedEof,
                "eof while reading headers",
            ));
        }
        // Strip CRLF (or lone LF for tolerance).
        let trimmed = line.trim_end_matches(|c| c == '\r' || c == '\n');
        if trimmed.is_empty() {
            break;
        }
        if let Some((name, value)) = trimmed.split_once(':') {
            if name.trim().eq_ignore_ascii_case("content-length") {
                let v = value.trim();
                let parsed: i64 = v.parse().map_err(|_| {
                    io::Error::new(
                        io::ErrorKind::InvalidData,
                        format!("unparseable Content-Length: {v}"),
                    )
                })?;
                if parsed < 0 {
                    return Err(io::Error::new(
                        io::ErrorKind::InvalidData,
                        format!("negative Content-Length: {parsed}"),
                    ));
                }
                content_length = Some(parsed);
            }
            // Other headers tolerated (D-02 forward-compat).
        }
        // Lines without ':' are ignored (defensive).
    }

    let n = content_length.ok_or_else(|| {
        io::Error::new(io::ErrorKind::InvalidData, "missing Content-Length")
    })?;
    let mut body = vec![0u8; n as usize];
    r.read_exact(&mut body).await?;
    Ok(body)
}

/// Write one LSP-framed message to `w`.
pub async fn write_frame<W: AsyncWrite + Unpin>(w: &mut W, body: &[u8]) -> io::Result<()> {
    let header = format!("Content-Length: {}\r\n\r\n", body.len());
    w.write_all(header.as_bytes()).await?;
    w.write_all(body).await?;
    w.flush().await?;
    Ok(())
}
