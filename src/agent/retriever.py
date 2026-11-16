"""Retriever cho agent Day 7.

DenseRetriever: embed query bằng đúng model đã ingest Day 6 (BAAI/bge-m3, 1024 chiều, chuẩn hóa L2,
không tiền tố) rồi tìm exact cosine trên bảng `chunks` của pgvector, trong một strategy (mặc định A).

- Kết quả theo định dạng chunk Day 7 (data/README.md): id, text, source_id, source, page, metadata,
  kèm score (1 - cosine distance), rank, retriever.
- Filter chỉ nhận key store cho phép (`section`, `document_id`); key lạ bị store từ chối, không bỏ qua.
  Filter phải đến từ người hỏi (trường `filter` của câu), không bao giờ từ gold.
- Lỗi embedding/database được ném ra; người gọi ghi `status: "error"`. Không có kết quả giả.
"""
import os
import time
from typing import Any

from src.day6.store import ALLOWED_FILTERS, MAX_TOP_K


def to_chunk(hit: dict[str, Any], retriever: str = "dense") -> dict[str, Any]:
    """Đổi một dòng kết quả pgvector (cột Day 6) sang chunk Day 7."""
    meta = {**(hit.get("metadata") or {}), "section": hit.get("section"), "printed_page": hit.get("printed_page")}
    return {"id": hit["chunk_id"], "text": hit["text"], "source_id": hit["document_id"], "source": hit["source"],
            "page": hit["page"], "metadata": meta, "score": hit["score"], "rank": hit["rank"],
            "retriever": retriever}


class DenseRetriever:
    """Dense retrieval trên vector store Day 6. Embedder/store có thể truyền vào để dùng chung hoặc test."""

    name = "dense"

    def __init__(self, embedder=None, store=None, strategy: str | None = None) -> None:
        if embedder is None:
            from src.day6.embeddings import MyEmbedder
            embedder = MyEmbedder()  # nạp model một lần (~50 giây trên CPU)
        if store is None:
            from src.day6.store import PgVectorStore
            store = PgVectorStore.from_env(embedder.dimensions)
        if getattr(store, "dimensions", embedder.dimensions) != embedder.dimensions:
            raise ValueError(f"Embedder {embedder.dimensions} chiều nhưng store {store.dimensions} chiều")
        self.embedder, self.store = embedder, store
        self.strategy = strategy or os.getenv("DAY6_STRATEGY", "A")
        self.last_timing: dict[str, float] = {}

    def describe(self) -> dict[str, Any]:
        """Cấu hình để ghi vào trace/summary."""
        return {"retriever": self.name, "store_strategy": self.strategy,
                "embedding_model": getattr(self.embedder, "model_name", None),
                "dimensions": self.embedder.dimensions, "metric": "cosine (exact)",
                "allowed_filters": sorted(ALLOWED_FILTERS)}

    def search(self, query: str, *, filters: dict[str, Any] | None, top_k: int) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query phải là chuỗi không rỗng")
        if not isinstance(top_k, int) or not 1 <= top_k <= MAX_TOP_K:
            raise ValueError(f"top_k phải trong [1, {MAX_TOP_K}]")
        t0 = time.perf_counter()
        vector = self.embedder.embed_query(query)
        t1 = time.perf_counter()
        hits = self.store.search(self.strategy, vector, top_k=top_k, filters=filters or None)
        t2 = time.perf_counter()
        self.last_timing = {"embed_ms": (t1 - t0) * 1000, "db_ms": (t2 - t1) * 1000}
        return [to_chunk(h, self.name) for h in hits]


# ----------------------------------------------------------------------------- lexical (BM25)

def tokenize(text: str, bigrams: bool = False) -> list[str]:
    """Tách theo âm tiết (giống starter/baseline.tokenize); tùy chọn thêm bigram âm tiết để xấp xỉ từ ghép
    tiếng Việt (vd. 'học_phần', 'cảnh_báo') mà không cần thư viện tách từ."""
    import re
    import unicodedata
    toks = re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold())
    return toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])] if bigrams else toks


def _match_filters(chunk: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    """Áp cùng quy tắc filter với PgVectorStore (key section/document_id; giá trị hoặc danh sách)."""
    for key, value in (filters or {}).items():
        if key not in ALLOWED_FILTERS:
            raise ValueError(f"Không được lọc theo '{key}'; cho phép: {sorted(ALLOWED_FILTERS)}")
        actual = chunk["source_id"] if key == "document_id" else chunk["metadata"].get(key)
        allowed = list(value) if isinstance(value, (list, tuple, set)) else [value]
        if actual not in allowed:
            return False
    return True


class BM25Retriever:
    """BM25 Okapi trên chunks.json (cùng 363 chunk với index pgvector). Chạy trong bộ nhớ, không chi phí."""

    def __init__(self, chunks: list[dict[str, Any]], *, k1: float = 1.5, b: float = 0.75,
                 bigrams: bool = False) -> None:
        import collections
        import math
        self.chunks, self.k1, self.b, self.bigrams = chunks, k1, b, bigrams
        self.name = "bm25_bigram" if bigrams else "bm25"
        t0 = time.perf_counter()
        self.tf = [collections.Counter(tokenize(c["text"], bigrams)) for c in chunks]
        self.len = [sum(tf.values()) for tf in self.tf]
        self.avgdl = sum(self.len) / len(self.len)
        df = collections.Counter(t for tf in self.tf for t in tf)
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
        self.index_seconds = time.perf_counter() - t0
        self.last_timing: dict[str, float] = {}

    def describe(self) -> dict[str, Any]:
        return {"retriever": self.name, "k1": self.k1, "b": self.b, "tokenization": "âm tiết NFC casefold"
                + (" + bigram âm tiết" if self.bigrams else ""), "chunks": len(self.chunks)}

    def search(self, query: str, *, filters: dict[str, Any] | None, top_k: int) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query phải là chuỗi không rỗng")
        t0 = time.perf_counter()
        q = [t for t in dict.fromkeys(tokenize(query, self.bigrams)) if t in self.idf]
        scored = []
        for i, c in enumerate(self.chunks):
            if not _match_filters(c, filters):
                continue
            tf, norm = self.tf[i], self.k1 * (1 - self.b + self.b * self.len[i] / self.avgdl)
            s = sum(self.idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + norm) for t in q if t in tf)
            if s > 0:
                scored.append((s, c["id"], c))
        scored.sort(key=lambda x: (-x[0], x[1]))
        self.last_timing = {"search_ms": (time.perf_counter() - t0) * 1000}
        return [{**c, "score": s, "rank": r, "retriever": self.name}
                for r, (s, _, c) in enumerate(scored[:top_k], start=1)]


# ----------------------------------------------------------------------------- hybrid (RRF)

class HybridRRFRetriever:
    """Reciprocal Rank Fusion: score = Σ_i 1 / (k + rank_i) trên top-`depth` của mỗi retriever.

    Hợp nhất theo thứ hạng nên không cần chuẩn hóa score cosine và BM25. Score RRF chỉ so sánh được
    trong cùng một query (không dùng để xếp context qua nhiều lần search)."""

    def __init__(self, retrievers: list, *, k: int = 60, depth: int = 20) -> None:
        self.retrievers, self.k, self.depth = retrievers, k, depth
        self.name = "hybrid_rrf"
        self.last_timing: dict[str, float] = {}

    def describe(self) -> dict[str, Any]:
        return {"retriever": self.name, "rrf_k": self.k, "depth_per_retriever": self.depth,
                "components": [r.describe() for r in self.retrievers]}

    def search(self, query: str, *, filters: dict[str, Any] | None, top_k: int) -> list[dict[str, Any]]:
        t0 = time.perf_counter()
        fused: dict[str, dict[str, Any]] = {}
        for r in self.retrievers:
            for hit in r.search(query, filters=filters, top_k=self.depth):
                entry = fused.setdefault(hit["id"], {**hit, "score": 0.0, "component_ranks": {}})
                entry["score"] += 1.0 / (self.k + hit["rank"])
                entry["component_ranks"][r.name] = hit["rank"]
        ranked = sorted(fused.values(), key=lambda c: (-c["score"], c["id"]))[:top_k]
        self.last_timing = {"search_ms": (time.perf_counter() - t0) * 1000}
        return [{**c, "rank": i, "retriever": self.name} for i, c in enumerate(ranked, start=1)]


# ----------------------------------------------------------------------------- rerank (cross-encoder)

class RerankRetriever:
    """Lấy `candidates` chunk từ retriever gốc rồi xếp lại bằng cross-encoder (mặc định BAAI/bge-reranker-v2-m3).

    Score = điểm cross-encoder (sigmoid, 0..1) cho cặp (query, chunk): so sánh được giữa các query nên dùng được
    để xếp context qua nhiều lần search. Giữ `first_stage_rank` để so sánh trước/sau rerank."""

    def __init__(self, base, *, model_name: str | None = None, candidates: int = 20, model=None,
                 max_length: int = 512, batch_size: int = 16) -> None:
        self.base, self.candidates, self.batch_size = base, candidates, batch_size
        self.model_name = model_name or os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
        if model is None:
            from sentence_transformers import CrossEncoder
            cache = os.getenv("RERANKER_CACHE_DIR") or None
            model = CrossEncoder(self.model_name, max_length=max_length, cache_folder=cache, device="cpu")
        self.model = model
        self.name = f"rerank({base.name})"
        self.last_timing: dict[str, float] = {}

    def describe(self) -> dict[str, Any]:
        return {"retriever": self.name, "reranker_model": self.model_name, "candidates": self.candidates,
                "first_stage": self.base.describe()}

    def search(self, query: str, *, filters: dict[str, Any] | None, top_k: int) -> list[dict[str, Any]]:
        t0 = time.perf_counter()
        cands = self.base.search(query, filters=filters, top_k=self.candidates)
        t1 = time.perf_counter()
        if not cands:
            self.last_timing = {"first_stage_ms": (t1 - t0) * 1000, "rerank_ms": 0.0}
            return []
        scores = self.model.predict([(query, c["text"]) for c in cands], batch_size=self.batch_size,
                                    show_progress_bar=False)
        ranked = sorted(zip((float(s) for s in scores), cands), key=lambda x: (-x[0], x[1]["id"]))[:top_k]
        self.last_timing = {"first_stage_ms": (t1 - t0) * 1000, "rerank_ms": (time.perf_counter() - t1) * 1000}
        return [{**c, "score": s, "first_stage_rank": c["rank"], "first_stage_score": c["score"], "rank": i,
                 "retriever": self.name} for i, (s, c) in enumerate(ranked, start=1)]


def build_retriever(method: str, *, chunks: list[dict[str, Any]] | None = None, dense: "DenseRetriever | None" = None,
                    rrf_k: int = 60, depth: int = 20, candidates: int = 20, reranker=None):
    """Tạo retriever theo tên phương pháp; dùng chung DenseRetriever/reranker đã nạp nếu truyền vào."""
    def need_chunks():
        if chunks is None:
            raise ValueError(f"{method} cần chunks.json")
        return chunks
    if method == "dense":
        return dense or DenseRetriever()
    if method in ("bm25", "bm25_bigram"):
        return BM25Retriever(need_chunks(), bigrams=method == "bm25_bigram")
    if method in ("hybrid_rrf", "hybrid_rrf_bigram"):
        lexical = BM25Retriever(need_chunks(), bigrams=method.endswith("bigram"))
        return HybridRRFRetriever([dense or DenseRetriever(), lexical], k=rrf_k, depth=depth)
    if method in ("rerank_dense", "rerank_hybrid", "rerank_hybrid_bigram"):
        dense = dense or DenseRetriever()
        if method == "rerank_dense":
            base = dense
        else:
            lexical = BM25Retriever(need_chunks(), bigrams=method.endswith("bigram"))
            base = HybridRRFRetriever([dense, lexical], k=rrf_k, depth=depth)
        return RerankRetriever(base, candidates=candidates, model=reranker)
    raise ValueError(f"Phương pháp retrieval không hỗ trợ: {method}")
