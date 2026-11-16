"""Kiểm tra BM25, Hybrid RRF, Rerank bằng dữ liệu nhỏ và model giả — chỉ kiểm tra code."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.agent.retriever import BM25Retriever, HybridRRFRetriever, RerankRetriever, build_retriever, tokenize  # noqa

CHUNKS = [
    {"id": "c1", "text": "Học phần tiên quyết phải học và thi đạt.", "source_id": "doc", "source": "s", "page": 1,
     "metadata": {"section": "dao_tao"}},
    {"id": "c2", "text": "Sinh viên bị cảnh báo học tập khi điểm trung bình thấp.", "source_id": "doc", "source": "s",
     "page": 2, "metadata": {"section": "dao_tao"}},
    {"id": "c3", "text": "Khiển trách sinh viên bị trừ 25% điểm học phần.", "source_id": "doc", "source": "s",
     "page": 3, "metadata": {"section": "khao_thi"}},
]


class Fixed:
    """Retriever giả trả danh sách ID cố định."""
    def __init__(self, name, ids): self.name, self.ids, self.last_timing = name, ids, {}
    def describe(self): return {"retriever": self.name}
    def search(self, query, *, filters, top_k):
        by = {c["id"]: c for c in CHUNKS}
        return [{**by[i], "score": 1.0 / r, "rank": r, "retriever": self.name}
                for r, i in enumerate(self.ids[:top_k], start=1)]


class FakeCrossEncoder:
    def __init__(self, prefer): self.prefer, self.calls = prefer, 0
    def predict(self, pairs, **kw):
        self.calls += 1
        return [0.9 if self.prefer in text else 0.1 for _, text in pairs]


class RetrieverTests(unittest.TestCase):
    def test_tokenize_bigrams(self):
        self.assertEqual(tokenize("Học Phần"), ["học", "phần"])
        self.assertEqual(tokenize("học phần tiên", bigrams=True), ["học", "phần", "tiên", "học_phần", "phần_tiên"])

    def test_bm25_ranks_and_filters(self):
        r = BM25Retriever(CHUNKS)
        out = r.search("khiển trách trừ điểm", filters=None, top_k=3)
        self.assertEqual(out[0]["id"], "c3")
        self.assertEqual([o["rank"] for o in out], list(range(1, len(out) + 1)))
        filtered = r.search("sinh viên", filters={"section": "dao_tao"}, top_k=3)
        self.assertEqual({o["id"] for o in filtered}, {"c2"})
        with self.assertRaises(ValueError):
            r.search("x", filters={"year": 1}, top_k=3)
        self.assertEqual(r.search("zzz", filters=None, top_k=3), [])

    def test_rrf_fuses_by_rank(self):
        h = HybridRRFRetriever([Fixed("a", ["c1", "c2", "c3"]), Fixed("b", ["c2", "c3", "c1"])], k=60, depth=3)
        out = h.search("q", filters=None, top_k=3)
        self.assertEqual(out[0]["id"], "c2")  # hạng 2 + hạng 1 > hạng 1 + hạng 3
        self.assertAlmostEqual(out[0]["score"], 1 / 62 + 1 / 61)
        self.assertEqual(out[0]["component_ranks"], {"a": 2, "b": 1})
        self.assertEqual(out[0]["retriever"], "hybrid_rrf")

    def test_rerank_reorders_and_keeps_first_stage_rank(self):
        enc = FakeCrossEncoder(prefer="25%")
        r = RerankRetriever(Fixed("dense", ["c1", "c2", "c3"]), model=enc, candidates=3)
        out = r.search("khiển trách", filters=None, top_k=2)
        self.assertEqual([o["id"] for o in out], ["c3", "c1"])
        self.assertEqual(out[0]["first_stage_rank"], 3)
        self.assertEqual(out[0]["rank"], 1)
        self.assertEqual(set(r.last_timing), {"first_stage_ms", "rerank_ms"})

    def test_rerank_empty_candidates(self):
        enc = FakeCrossEncoder(prefer="x")
        self.assertEqual(RerankRetriever(Fixed("d", []), model=enc).search("q", filters=None, top_k=3), [])
        self.assertEqual(enc.calls, 0)

    def test_build_rerank_hybrid_uses_hybrid_first_stage(self):
        dense = Fixed("dense", ["c1", "c2"])
        r = build_retriever("rerank_hybrid", chunks=CHUNKS, dense=dense, reranker=FakeCrossEncoder("x"))
        self.assertIsInstance(r.base, HybridRRFRetriever)
        self.assertIs(build_retriever("rerank_dense", chunks=CHUNKS, dense=dense,
                                      reranker=FakeCrossEncoder("x")).base, dense)
        with self.assertRaises(ValueError):
            build_retriever("unknown", chunks=CHUNKS, dense=dense)


if __name__ == "__main__":
    unittest.main()
