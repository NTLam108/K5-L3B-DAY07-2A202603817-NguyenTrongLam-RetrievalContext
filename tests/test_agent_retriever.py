"""Kiểm tra DenseRetriever bằng embedder/store giả — chỉ kiểm tra code, không đo chất lượng retrieval."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.agent.loop import run_agent  # noqa: E402
from src.agent.retriever import DenseRetriever, to_chunk  # noqa: E402

ROW = {"chunk_id": "A-p63-001", "document_id": "stsv-hcmus-2025", "source": "https://example/stsv.pdf",
       "page": 63, "printed_page": 61, "section": "dao_tao", "text": "kéo dài thêm không vượt quá ba (03) năm học",
       "metadata": {"strategy": "A", "chunk_index": 1}, "score": 0.73, "rank": 1}


class FakeEmbedder:
    model_name, dimensions = "fake", 4
    def __init__(self): self.queries = []
    def embed_query(self, q): self.queries.append(q); return [1.0, 0.0, 0.0, 0.0]


class FakeStore:
    dimensions = 4
    def __init__(self, rows): self.rows, self.calls = rows, []
    def search(self, strategy, vector, top_k=3, filters=None):
        self.calls.append((strategy, top_k, filters))
        if filters and set(filters) - {"section", "document_id"}:
            raise ValueError("Không được lọc theo key lạ")
        return self.rows[:top_k]


class Controller:
    def __init__(self, actions): self.actions = iter(actions)
    def decide(self, question, history): return next(self.actions)


class DenseRetrieverTests(unittest.TestCase):
    def make(self, rows=(ROW,)):
        self.emb, self.store = FakeEmbedder(), FakeStore(list(rows))
        return DenseRetriever(self.emb, self.store, strategy="A")

    def test_to_chunk_matches_day7_contract(self):
        c = to_chunk(ROW)
        self.assertEqual({k: c[k] for k in ("id", "source_id", "page", "score", "rank", "retriever")},
                         {"id": "A-p63-001", "source_id": "stsv-hcmus-2025", "page": 63, "score": 0.73,
                          "rank": 1, "retriever": "dense"})
        self.assertEqual(c["metadata"]["section"], "dao_tao")
        self.assertEqual(c["metadata"]["printed_page"], 61)
        self.assertEqual(c["metadata"]["chunk_index"], 1)

    def test_search_passes_query_filter_and_top_k(self):
        r = self.make()
        out = r.search("kéo dài thời gian học", filters={"section": "dao_tao"}, top_k=5)
        self.assertEqual(self.emb.queries, ["kéo dài thời gian học"])
        self.assertEqual(self.store.calls, [("A", 5, {"section": "dao_tao"})])
        self.assertEqual(out[0]["id"], "A-p63-001")
        self.assertEqual(set(r.last_timing), {"embed_ms", "db_ms"})

    def test_empty_filter_becomes_none(self):
        r = self.make()
        r.search("q", filters={}, top_k=3)
        self.assertIsNone(self.store.calls[0][2])

    def test_invalid_inputs_and_unknown_filter_raise(self):
        r = self.make()
        for bad in ("", "   "):
            with self.assertRaises(ValueError):
                r.search(bad, filters=None, top_k=3)
        for k in (0, 51):
            with self.assertRaises(ValueError):
                r.search("q", filters=None, top_k=k)
        with self.assertRaises(ValueError):
            r.search("q", filters={"year": 2025}, top_k=3)

    def test_dimension_mismatch_rejected(self):
        store = FakeStore([ROW]); store.dimensions = 1024
        with self.assertRaises(ValueError):
            DenseRetriever(FakeEmbedder(), store)

    def test_works_inside_agent_loop(self):
        r = self.make()
        c = Controller([{"action": "search", "query": "kéo dài"},
                        {"action": "answer", "answer": "Tối đa 3 năm [A-p63-001]", "citations": ["A-p63-001"]}])
        result = run_agent("Kéo dài tối đa bao lâu?", c, r)
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["events"][0]["results"][0]["retriever"], "dense")


if __name__ == "__main__":
    unittest.main()
