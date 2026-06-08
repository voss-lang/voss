//! Rust client SDK for the Voss local harness REST and SSE protocol.

pub mod auth;
pub mod client;
pub mod error;
pub mod projection;
pub mod stream;
pub mod supervisor;
pub mod types;

pub use auth::Handshake;
pub use client::VossClient;
pub use projection::UiProjection;
pub use stream::event_stream;
pub use supervisor::{spawn, spawn_with, Supervisor};
