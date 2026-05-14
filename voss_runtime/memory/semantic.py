from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .._config import get_config


@dataclass
class SemanticMemory:
    source: Optional[str] = None
    model: Optional[str] = None
    collection_name: str = "voss_semantic"
    persist_dir: str = "chroma"
    _client: object = field(default=None, init=False, repr=False)
    _collection: object = field(default=None, init=False, repr=False)

    def __post_init__(self):
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as e:
            raise ModuleNotFoundError(
                "chromadb is not installed. Semantic memory is an optional "
                "Voss feature. Install it with:\n"
                "    pip install 'voss[search]'\n"
                "(or, with the npm wrapper, `voss extras install search`)."
            ) from e

        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._embedding_function(),
        )
        if self.source:
            self._ingest_source(self.source)

    def _embedding_function(self):
        from chromadb.utils import embedding_functions

        cfg = get_config()
        requested = self.model or cfg.default_embedding_model
        if requested.startswith("text-embedding-") and not os.environ.get("OPENAI_API_KEY"):
            requested = cfg.local_embedding_model
        if requested.startswith("text-embedding-"):
            return embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.environ["OPENAI_API_KEY"], model_name=requested
            )
        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=requested.replace("sentence-transformers/", "")
        )

    def _ingest_source(self, source: str) -> None:
        path = Path(source)
        if not path.exists():
            return
        files = [path] if path.is_file() else list(path.rglob("*"))
        docs, ids, metas = [], [], []
        for f in files:
            if f.is_file() and f.suffix.lower() in {".md", ".txt", ".rst"}:
                docs.append(f.read_text())
                ids.append(str(f))
                metas.append({"path": str(f)})
        if docs:
            self._collection.add(documents=docs, ids=ids, metadatas=metas)

    def add(
        self,
        text: str,
        *,
        metadata: Optional[dict] = None,
        id: Optional[str] = None,
    ) -> None:
        kwargs = {
            "documents": [text],
            "ids": [id or str(uuid.uuid4())],
        }
        if metadata:
            kwargs["metadatas"] = [metadata]
        self._collection.add(**kwargs)

    def retrieve(self, query: str, *, top_k: int = 5) -> list[str]:
        result = self._collection.query(query_texts=[query], n_results=top_k)
        docs = result.get("documents") or [[]]
        return docs[0]
