from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

DEFAULT_LOCAL_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass(frozen=True)
class Case:
    label: str
    description: str


class SemanticMatcher:
    def __init__(
        self,
        cases: Sequence[tuple[str, str]] | Sequence[Case],
        *,
        threshold: float = 0.75,
        model: str = DEFAULT_LOCAL_MODEL,
        embeddings: Optional[np.ndarray] = None,
    ):
        self.cases: list[Case] = [
            c if isinstance(c, Case) else Case(label=c[1], description=c[0])
            for c in cases
        ]
        self.threshold = threshold
        self.model_name = model
        self._encoder = None
        if embeddings is not None:
            self._embeddings = np.asarray(embeddings, dtype=np.float32)
        else:
            self._embeddings = self._encode([c.description for c in self.cases])

    def _ensure_encoder(self):
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer

            self._encoder = SentenceTransformer(self.model_name)
        return self._encoder

    def _encode(self, texts: list[str]) -> np.ndarray:
        enc = self._ensure_encoder()
        vecs = enc.encode(texts, normalize_embeddings=True)
        return np.asarray(vecs, dtype=np.float32)

    def match(self, input_text: str) -> Optional[str]:
        q = self._encode([input_text])[0]
        sims = self._embeddings @ q  # cosine sim (vectors are normalized)
        for case, score in zip(self.cases, sims):
            if score >= self.threshold:
                return case.label
        return None

    def to_index(self) -> dict:
        return {
            "model": self.model_name,
            "threshold": self.threshold,
            "cases": [
                {"label": c.label, "description": c.description, "embedding": e.tolist()}
                for c, e in zip(self.cases, self._embeddings)
            ],
        }

    def write_index(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_index()))

    @classmethod
    def from_index(cls, path: str | Path) -> "SemanticMatcher":
        data = json.loads(Path(path).read_text())
        cases = [
            Case(label=c["label"], description=c["description"]) for c in data["cases"]
        ]
        embeddings = np.asarray(
            [c["embedding"] for c in data["cases"]], dtype=np.float32
        )
        return cls(
            cases,
            threshold=data.get("threshold", 0.75),
            model=data["model"],
            embeddings=embeddings,
        )
