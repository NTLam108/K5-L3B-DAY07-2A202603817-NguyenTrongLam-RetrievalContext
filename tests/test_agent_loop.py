"""Kiểm tra src/agent/loop.py bằng adapter giả — chỉ kiểm tra code, không đo chất lượng model."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_agentic as starter_tests  # noqa: E402  — chạy lại kịch bản của starter trên loop mới
from src.agent import loop  # noqa: E402
from src.agent.loop import run_agent  # noqa: E402

CHUNK = starter_tests.CHUNK
Controller, Retriever = starter_tests.Controller, starter_tests.Retriever


class StarterBehaviourOnNewLoop(starter_tests.AgentTests):
    """Mọi test của starter phải pass khi thay run_agent bằng bản mở rộng."""

    def setUp(self):
        self._orig = starter_tests.run_agent
        starter_tests.run_agent = run_agent

    def tearDown(self):
        starter_tests.run_agent = self._orig


class LoggingController(Controller):
    def __init__(self, actions):
        super().__init__(actions)
        self.pending = []

    def decide(self, question, history):
        self.pending.append({"model": "fake", "prompt_tokens": 10, "completion_tokens": 2})
        return super().decide(question, history)

    def pop_calls(self):
        calls, self.pending = self.pending, []
        return calls


class ExtendedLoopTests(unittest.TestCase):
    def test_model_abstain_is_separate_from_invalid_citation(self):
        c = Controller([{"action": "search", "query": "q"}, {"action": "abstain", "reason": "không có mức tiền"}])
        result = run_agent("q", c, Retriever([CHUNK]))
        self.assertEqual((result["status"], result["stop_reason"]), ("abstain", "model_abstain"))
        self.assertEqual(result["abstain_reason"], "không có mức tiền")
        self.assertTrue(result["events"][-1]["searched_before_abstain"])

        c = Controller([{"action": "search", "query": "q"},
                        {"action": "answer", "answer": "7 ngày [x]", "citations": ["x"]}])
        result = run_agent("q", c, Retriever([CHUNK]))
        self.assertEqual(result["stop_reason"], "invalid_or_missing_citations")
        self.assertEqual(result["events"][-1]["rejected_citations"], ["x"])
        self.assertEqual(result["citations"], [])

    def test_abstain_without_search_is_flagged(self):
        result = run_agent("q", Controller([{"action": "abstain", "reason": "r"}]), Retriever([CHUNK]))
        self.assertFalse(result["events"][-1]["searched_before_abstain"])
        self.assertEqual(result["num_searches"], 0)

    def test_answer_result_fields_and_llm_events(self):
        c = LoggingController([{"action": "search", "query": "hoàn tiền"},
                               {"action": "answer", "answer": "7 ngày [c1]", "citations": ["c1"]}])
        result = run_agent("Hoàn tiền?", c, Retriever([CHUNK]))
        self.assertEqual(result["stop_reason"], "answered")
        self.assertEqual(result["num_searches"], 1)
        self.assertEqual(result["context_ids"], ["c1"])
        kinds = [e["event"] for e in result["events"]]
        self.assertEqual(kinds, ["llm_call", "search", "llm_call", "answer"])
        self.assertIn("elapsed_ms", result["events"][1])

    def test_history_reports_searches_left(self):
        seen = []

        class Inspect:
            def __init__(self): self.i = 0
            def decide(self, question, history):
                self.i += 1
                seen.append(history[0]["searches_left"] if history else None)
                return {"action": "search", "query": str(self.i)} if self.i <= 2 else \
                    {"action": "abstain", "reason": "r"}

        run_agent("q", Inspect(), Retriever([CHUNK]), max_searches=3)
        self.assertEqual(seen, [None, 2, 1])

    def test_search_limit_reason(self):
        c = Controller([{"action": "search", "query": str(i)} for i in range(3)])
        result = run_agent("q", c, Retriever([CHUNK]), max_searches=2)
        self.assertEqual(result["stop_reason"], "search_limit")

    def test_llm_call_logged_even_when_provider_fails(self):
        class Failing(LoggingController):
            def decide(self, question, history):
                self.pending.append({"model": "fake", "error": "timeout"})
                raise TimeoutError("provider timeout")

        with self.assertRaises(TimeoutError):
            run_agent("q", Failing([]), Retriever([CHUNK]))

    def test_unknown_action_rejected(self):
        with self.assertRaises(ValueError):
            run_agent("q", Controller([{"action": "guess"}]), Retriever([CHUNK]))

    def test_first_query_verbatim_skips_model(self):
        r = Retriever([CHUNK])
        c = Controller([{"action": "answer", "answer": "7 ngày [c1]", "citations": ["c1"]}])
        result = run_agent("Hoàn tiền mất bao lâu?", c, r, first_query="question", max_searches=2)
        self.assertEqual(r.calls[0][0], "Hoàn tiền mất bao lâu?")
        self.assertEqual(result["events"][0]["origin"], "question_verbatim")
        self.assertEqual(result["status"], "answered")

    def test_dedupe_queries_counts_and_notes(self):
        seen = []

        class Repeat:
            def __init__(self): self.i = 0
            def decide(self, question, history):
                self.i += 1
                seen.append(history[0].get("note") if history else None)
                if self.i <= 2:
                    return {"action": "search", "query": "Hoàn  TIỀN"}
                return {"action": "abstain", "reason": "r"}

        r = Retriever([CHUNK])
        result = run_agent("q", Repeat(), r, dedupe_queries=True, max_searches=3)
        self.assertEqual(len(r.calls), 1)
        self.assertEqual([e["event"] for e in result["events"]].count("duplicate_query"), 1)
        self.assertIn("đã dùng", seen[2])

    def test_score_selection_prefers_higher_score_from_later_search(self):
        low = {**CHUNK, "id": "low", "text": "x" * 60, "score": 0.2}
        high = {**CHUNK, "id": "high", "text": "y" * 60, "score": 0.9}

        class Seq:
            def __init__(self): self.i = 0
            def search(self, query, *, filters, top_k):
                self.i += 1
                return [low] if self.i == 1 else [high]

        actions = [{"action": "search", "query": "a"}, {"action": "search", "query": "b"},
                   {"action": "abstain", "reason": "r"}]
        by_order = run_agent("q", Controller(actions), Seq(), budget=100)
        by_score = run_agent("q", Controller(actions), Seq(), budget=100, selection="score")
        self.assertEqual(by_order["context_ids"], ["low"])
        self.assertEqual(by_score["context_ids"], ["high"])

    def test_invalid_options_rejected(self):
        with self.assertRaises(ValueError):
            run_agent("q", Controller([]), Retriever([CHUNK]), selection="random")

    def test_stop_reasons_documented(self):
        self.assertIn("model_abstain", loop.STOP_REASONS)


if __name__ == "__main__":
    unittest.main()
