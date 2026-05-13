//! EpisodicMemory — minimal Rust port of `voss_runtime.memory.episodic.EpisodicMemory`.

use std::collections::VecDeque;

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct EpisodicEntry {
    pub role: String,
    pub content: String,
}

#[derive(Clone, Debug)]
pub struct EpisodicMemory {
    capacity: usize,
    entries: VecDeque<EpisodicEntry>,
}

impl EpisodicMemory {
    pub fn new(capacity: usize) -> Self {
        Self {
            capacity,
            entries: VecDeque::with_capacity(capacity.max(1)),
        }
    }

    pub fn add(&mut self, content: impl Into<String>, role: impl Into<String>) {
        if self.entries.len() == self.capacity {
            self.entries.pop_front();
        }
        self.entries.push_back(EpisodicEntry {
            role: role.into(),
            content: content.into(),
        });
    }

    pub fn last(&self, n: usize) -> Vec<EpisodicEntry> {
        let take = n.min(self.entries.len());
        self.entries
            .iter()
            .skip(self.entries.len() - take)
            .cloned()
            .collect()
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}
