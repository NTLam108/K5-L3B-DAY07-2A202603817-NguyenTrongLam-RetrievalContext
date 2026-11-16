"""Local embedding model (Sentence Transformers). Không có fallback sang vector giả.

Model lấy từ EMBEDDING_MODEL trong .env (thư mục gốc); bài này dùng BAAI/bge-m3
(1024 chiều, chuỗi dài nên chunk không bị cắt).
Giới hạn độ dài tùy chọn: EMBEDDING_MAX_SEQ_LENGTH. Một giá trị duy nhất phải
được dùng cho cả ba chiến lược và ghi vào báo cáo.

Xử lý query/document: bge-m3 (dense) không dùng tiền tố, nên query và document
được mã hóa giống nhau; vector được chuẩn hóa L2 để cosine = tích vô hướng.
"""
import os
from pathlib import Path
from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    def __init__(self, model_name: str | None = None, max_seq_length: int | None = None,
                 batch_size: int = 32) -> None:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parents[2] / ".env")  # .env ở thư mục gốc repo Day 7
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", "").strip()
        if not self.model_name:
            raise RuntimeError("Chưa chọn model: đặt EMBEDDING_MODEL trong .env ở thư mục gốc")
        self.batch_size = batch_size
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("Thiếu thư viện: python -m pip install sentence-transformers") from exc
        try:
            self._model = SentenceTransformer(self.model_name)
        except Exception as exc:  # lỗi mạng, tên model sai, hết dung lượng...
            raise RuntimeError(f"Không tải được model '{self.model_name}': {exc}") from exc

        requested = max_seq_length or int(os.getenv("EMBEDDING_MAX_SEQ_LENGTH") or 0) or None
        if requested:
            self._model.max_seq_length = requested
        self.max_seq_length = int(self._model.max_seq_length)
        self.dimensions = int(self._model.get_sentence_embedding_dimension())

    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        if vectors.shape != (len(texts), self.dimensions):
            raise RuntimeError(f"Kích thước vector bất thường: {vectors.shape}")
        if not bool((vectors == vectors).all()):
            raise RuntimeError("Vector chứa NaN")
        return vectors.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts) if texts else []

    def embed_query(self, question: str) -> list[float]:
        return self._encode([question])[0]

    def token_lengths(self, texts: list[str]) -> list[int]:
        """Số token của từng văn bản (gồm token đặc biệt), để biết chunk nào bị cắt."""
        ids = self._model.tokenizer(texts, add_special_tokens=True, truncation=False)["input_ids"]
        return [len(x) for x in ids]

    def info(self) -> dict:
        """Thông tin để ghi vào báo cáo và results/ingest_stats.json."""
        import sentence_transformers
        import torch
        import transformers

        return {
            "provider": "local (sentence-transformers)",
            "model": self.model_name,
            "dimensions": self.dimensions,
            "max_seq_length": self.max_seq_length,
            "normalize_embeddings": True,
            "query_document_handling": "không tiền tố; query và document mã hóa giống nhau",
            "device": str(self._model.device),
            "versions": {
                "sentence_transformers": sentence_transformers.__version__,
                "torch": torch.__version__,
                "transformers": transformers.__version__,
            },
            "cost_usd": 0,
        }
