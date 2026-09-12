//! voss-tui thin terminal client for the Voss harness REST+SSE server
//! Library surface so integration tests can drive the network + event layers


pub mod app;
pub mod doctor;
pub mod event;
pub mod net;
pub mod server;
pub mod sessions;
pub mod store;
