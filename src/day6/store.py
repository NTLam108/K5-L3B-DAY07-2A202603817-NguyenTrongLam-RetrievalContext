"""Lưu và tìm kiếm vector bằng PostgreSQL + pgvector.

Một bảng `chunks`, khóa chính (strategy, chunk_id): ba chiến lược A, B, C nằm
chung một store, mỗi chiến lược là một index logic riêng. Không tạo chỉ mục
vector nên tìm kiếm là EXACT, metric cosine (toán tử <=>); với vài trăm chunk
cách này đủ nhanh và không bị hụt kết quả khi có filter như tìm kiếm xấp xỉ.
"""
import math
import os
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .models import Chunk

# Tên cột không tham số hóa được, nên chỉ cho phép lọc theo các cột trong danh sách này.
ALLOWED_FILTERS = {"section", "document_id"}
MAX_TOP_K = 50


def _vector_literal(vector: list[float], dimensions: int) -> str:
    if len(vector) != dimensions:
        raise ValueError(f"Vector có {len(vector)} chiều, store yêu cầu {dimensions}")
    if not all(math.isfinite(x) for x in vector):
        raise ValueError("Vector chứa NaN hoặc vô cực")
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        if not database_url:
            raise ValueError("database_url rỗng")
        if not isinstance(dimensions, int) or not 0 < dimensions <= 2000:
            raise ValueError("dimensions phải là số nguyên trong (0, 2000]")
        self.database_url = database_url
        self.dimensions = dimensions

    @classmethod
    def from_env(cls, dimensions: int) -> "PgVectorStore":
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parents[2] / ".env")  # .env ở thư mục gốc repo Day 7
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("Thiếu DATABASE_URL: sao chép .env.example thành .env ở thư mục gốc")
        return cls(url, dimensions)

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url, connect_timeout=5)

    def create_schema(self) -> None:
        """Tạo bảng; nếu bảng đã có với số chiều khác thì báo lỗi, không tự sửa."""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS chunks (
                    strategy     text    NOT NULL,
                    chunk_id     text    NOT NULL,
                    document_id  text    NOT NULL,
                    source       text    NOT NULL,
                    page         integer NOT NULL,
                    printed_page integer,
                    section      text,
                    text         text    NOT NULL,
                    metadata     jsonb   NOT NULL DEFAULT '{{}}'::jsonb,
                    embedding    vector({int(self.dimensions)}) NOT NULL,
                    PRIMARY KEY (strategy, chunk_id)
                )""")
            cur.execute("CREATE INDEX IF NOT EXISTS chunks_strategy_section_idx ON chunks (strategy, section)")
            cur.execute("""SELECT atttypmod FROM pg_attribute
                           WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'""")
            existing = cur.fetchone()[0]
        if existing != self.dimensions:
            raise ValueError(f"Bảng chunks đang dùng vector({existing}) nhưng model có {self.dimensions} chiều. "
                             "Đổi model thì phải tạo lại bảng một cách có chủ đích.")

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> dict[str, int]:
        """Ghi chunk theo ID ổn định (không nhân đôi) và xóa chunk cũ không còn trong danh sách.

        Trả về {"upserted": n, "deleted": m}; m > 0 nghĩa là có chunk lỗi thời đã bị loại.
        """
        if not strategy:
            raise ValueError("strategy rỗng")
        if not chunks:
            raise ValueError("Danh sách chunk rỗng: từ chối ghi để không xóa nhầm cả chiến lược")
        if len(chunks) != len(vectors):
            raise ValueError(f"{len(chunks)} chunk nhưng {len(vectors)} vector")
        ids = [c.chunk_id for c in chunks]
        if len(set(ids)) != len(ids):
            raise ValueError("chunk_id bị trùng trong danh sách đầu vào")

        rows = [
            (strategy, c.chunk_id, c.document_id, c.source, c.page, c.metadata.get("printed_page"),
             c.metadata.get("section"), c.text, Jsonb(c.metadata), _vector_literal(v, self.dimensions))
            for c, v in zip(chunks, vectors)
        ]
        with self._connect() as conn, conn.cursor() as cur:  # một giao dịch: lỗi thì rollback toàn bộ
            cur.executemany("""
                INSERT INTO chunks (strategy, chunk_id, document_id, source, page, printed_page,
                                    section, text, metadata, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                ON CONFLICT (strategy, chunk_id) DO UPDATE SET
                    document_id = EXCLUDED.document_id, source = EXCLUDED.source, page = EXCLUDED.page,
                    printed_page = EXCLUDED.printed_page, section = EXCLUDED.section,
                    text = EXCLUDED.text, metadata = EXCLUDED.metadata, embedding = EXCLUDED.embedding
            """, rows)
            cur.execute("DELETE FROM chunks WHERE strategy = %s AND NOT (chunk_id = ANY(%s))", (strategy, ids))
            deleted = cur.rowcount
        return {"upserted": len(rows), "deleted": deleted}

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Top-k theo cosine trong một chiến lược; filter áp dụng trong SQL trước khi xếp hạng.

        filters: {"section": "khao_thi"} hoặc {"section": ["khao_thi", "ren_luyen"]}.
        Khóa lạ bị từ chối (không âm thầm bỏ qua). score = 1 - khoảng cách cosine.
        """
        if not isinstance(top_k, int) or not 1 <= top_k <= MAX_TOP_K:
            raise ValueError(f"top_k phải trong [1, {MAX_TOP_K}]")
        params: dict[str, Any] = {"s": strategy, "q": _vector_literal(query_vector, self.dimensions), "k": top_k}
        where = ["strategy = %(s)s"]
        for i, (key, value) in enumerate((filters or {}).items()):
            if key not in ALLOWED_FILTERS:
                raise ValueError(f"Không được lọc theo '{key}'; cho phép: {sorted(ALLOWED_FILTERS)}")
            if isinstance(value, (list, tuple, set)):
                where.append(f"{key} = ANY(%(f{i})s)")
                params[f"f{i}"] = list(value)
            else:
                where.append(f"{key} = %(f{i})s")
                params[f"f{i}"] = value
        sql = f"""
            SELECT chunk_id, document_id, source, page, printed_page, section, text, metadata,
                   1 - (embedding <=> %(q)s::vector) AS score
            FROM chunks
            WHERE {' AND '.join(where)}
            ORDER BY embedding <=> %(q)s::vector, chunk_id
            LIMIT %(k)s"""
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            hits = cur.fetchall()
        for rank, hit in enumerate(hits, start=1):
            hit["rank"] = rank
            hit["score"] = float(hit["score"])
        return hits

    def counts(self) -> dict[str, tuple[int, int]]:
        """{strategy: (số dòng, số chunk_id khác nhau)}; hai số phải bằng nhau (không trùng)."""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT strategy, count(*), count(DISTINCT chunk_id) FROM chunks GROUP BY strategy ORDER BY 1")
            return {s: (n, d) for s, n, d in cur.fetchall()}

    def versions(self) -> dict[str, str]:
        """Phiên bản PostgreSQL và pgvector để ghi vào báo cáo."""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT current_setting('server_version'), "
                        "(SELECT extversion FROM pg_extension WHERE extname = 'vector')")
            pg, vec = cur.fetchone()
        return {"postgresql": pg, "pgvector": vec, "psycopg": psycopg.__version__,
                "search": "exact (không có chỉ mục vector)", "metric": "cosine (<=>)"}
