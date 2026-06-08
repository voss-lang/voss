//! Rust client SDK for the Voss local harness REST and SSE protocol.

pub mod auth;
pub mod client;
pub mod error;
pub mod projection;
pub mod stream;
pub mod types;

pub use auth::Handshake;
pub use client::VossClient;
pub use projection::UiProjection;
pub use stream::event_stream;
