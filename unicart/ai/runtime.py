"""In-process AI runtime: Gemini client + in-memory product vector index kept in sync with MySQL.

Vectors live in table product_embedding (survive restarts); the index is rebuilt from it at start and refreshed
whenever a product text changes. Only products whose text hash changed are re-embedded, so the free quota
is spent once per change, not once per start."""
from __future__ import annotations

import hashlib
import logging
import threading
from array import array
from collections import OrderedDict
from dataclasses import dataclass, field
from operator import mul

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from .. import config
from ..domain.models import Product
from ..persistence.database import Database
from ..persistence.repositories import EmbeddingRepository
import time

from .gemini import AiQuotaExceeded, AiUnavailable, GeminiClient

log = logging.getLogger("unicart.ai")


def product_document(p: Product) -> str:
    """Searchable text of a product: what a shopper might type to find it."""
    attrs = ", ".join(f"{k}: {v}" for k, v in (p.attributes or {}).items())
    parts = [p.name, f"Thương hiệu: {p.brand}" if p.brand else "", f"Danh mục: {p.category.name}" if p.category else "",
             p.description or "", attrs]
    return ". ".join(x for x in parts if x)


def dot(a: array, b: array) -> float:
    return sum(map(mul, a, b))


def to_array(blob: bytes) -> array:
    a = array("f")
    a.frombytes(blob)
    return a


@dataclass
class IndexStatus:
    enabled: bool
    ready: bool
    indexed: int
    model: str
    syncing: bool
    last_error: str | None = None


@dataclass
class AiRuntime:
    db: Database
    gemini: GeminiClient | None = None
    _vectors: dict[int, array] = field(default_factory=dict)
    _query_cache: "OrderedDict[str, list[float]]" = field(default_factory=OrderedDict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _syncing: bool = False
    _again: bool = False
    _last_error: str | None = None
    sleep: object = time.sleep                  # replaced in tests

    @classmethod
    def from_config(cls, db: Database) -> "AiRuntime":
        if not config.GEMINI_API_KEY:
            log.warning("GEMINI_API_KEY is not set: AI search is disabled, keyword search is used")
            return cls(db, None)
        client = GeminiClient(config.GEMINI_API_KEY, config.GEMINI_TEXT_MODEL, config.GEMINI_FALLBACK_MODEL,
                              config.GEMINI_EMBED_MODEL, config.GEMINI_EMBED_DIM,
                              config.AI_QUERY_TIMEOUT, config.AI_GENERATE_TIMEOUT)
        return cls(db, client)

    # ------------------------------------------------------------------ state
    @property
    def enabled(self) -> bool:
        return self.gemini is not None

    @property
    def ready(self) -> bool:
        return self.enabled and bool(self._vectors)

    def vectors(self) -> dict[int, array]:
        return self._vectors                                   # replaced atomically, never mutated in place

    def status(self) -> IndexStatus:
        return IndexStatus(self.enabled, self.ready, len(self._vectors),
                           self.gemini.embed_model if self.gemini else "", self._syncing, self._last_error)

    # ------------------------------------------------------------------ query embedding (cached: saves latency and quota)
    def embed_query(self, text: str) -> array:
        assert self.gemini is not None
        key = " ".join(text.lower().split())
        with self._lock:
            if key in self._query_cache:
                self._query_cache.move_to_end(key)
                return array("f", self._query_cache[key])
        vec = self.gemini.embed([text], "RETRIEVAL_QUERY", timeout=self.gemini.query_timeout)[0]
        with self._lock:
            self._query_cache[key] = vec
            while len(self._query_cache) > 512:
                self._query_cache.popitem(last=False)
        return array("f", vec)

    # ------------------------------------------------------------------ index maintenance
    def load(self) -> int:
        with self.db.new_session() as s:
            rows = EmbeddingRepository(s).all()
        self._vectors = {pid: to_array(e.vector) for pid, e in rows.items()}
        return len(self._vectors)

    def sync(self) -> dict:
        """Embed new or changed products, drop deleted ones, then reload the in-memory index."""
        if self.gemini is None:
            return {"embedded": 0, "removed": 0, "indexed": 0}
        model, dim = self.gemini.embed_model, self.gemini.dim
        with self.db.new_session() as s:
            products = list(s.scalars(select(Product).options(joinedload(Product.category))).unique())
            repo = EmbeddingRepository(s)
            existing = repo.all()
            todo = []
            for p in products:
                text = product_document(p)
                digest = hashlib.md5(f"{model}|{dim}|{text}".encode()).hexdigest()
                row = existing.get(p.id)
                if row is None or row.content_hash != digest:
                    todo.append((p.id, text, digest))
            try:
                for i in range(0, len(todo), 40):
                    chunk = todo[i:i + 40]
                    vectors = self._embed_with_backoff([t for _, t, _ in chunk])
                    for (pid, _, digest), vec in zip(chunk, vectors):
                        repo.upsert(pid, model, dim, digest, array("f", vec).tobytes())
                    s.commit()                                  # keep progress if the quota runs out half-way
            except AiUnavailable:
                self.load()                                     # whatever was saved is searchable right away
                raise
            removed = repo.delete_except({p.id for p in products})
            s.commit()
        indexed = self.load()
        log.info("AI index: %s embedded, %s removed, %s indexed", len(todo), removed, indexed)
        return {"embedded": len(todo), "removed": removed, "indexed": indexed}

    def _embed_with_backoff(self, texts: list[str]) -> list[list[float]]:
        """Free tier allows ~100 embeddings a minute: on HTTP 429 wait for the window to reset and retry."""
        for wait in (25, 45, 65, None):
            try:
                return self.gemini.embed(texts, "RETRIEVAL_DOCUMENT")
            except AiQuotaExceeded:
                if wait is None:
                    raise
                log.info("AI index: quota reached, waiting %ss", wait)
                self.sleep(wait)
        raise AiUnavailable("unreachable")

    def schedule_sync(self) -> None:
        """Run sync() in the background; calls made while it runs are coalesced into one more pass."""
        if not self.enabled:
            return
        with self._lock:
            if self._syncing:
                self._again = True
                return
            self._syncing = True
        threading.Thread(target=self._sync_loop, name="ai-index-sync", daemon=True).start()

    def _sync_loop(self) -> None:
        while True:
            try:
                self.sync()
                self._last_error = None
            except AiUnavailable as e:
                self._last_error = str(e)
                log.warning("AI index sync failed: %s", e)
            except Exception:
                self._last_error = "unexpected error"
                log.exception("AI index sync crashed")
            with self._lock:
                if not self._again:
                    self._syncing = False
                    return
                self._again = False
