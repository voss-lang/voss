//! Rust client SDK for the Voss local harness REST and SSE protocol.

pub mod auth;
pub mod client;
pub mod error;
pub mod types;

pub use auth::Handshake;
pub use client::VossClient;
