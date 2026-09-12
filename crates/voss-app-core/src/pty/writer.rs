pub const MAX_WRITE: usize = 1_048_576;

pub fn validate_write(data: &[u8]) -> Result<(), String> {
    if data.is_empty() {
        return Err("empty payload".into());
    }
    if data.len() > MAX_WRITE {
        return Err("payload exceeds 1MB limit".into());
    }
    Ok(())
}
