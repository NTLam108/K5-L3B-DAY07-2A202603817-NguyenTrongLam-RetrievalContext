"""Kiểm tra LLMController bằng client giả — chỉ kiểm tra parse/điều khiển, không đo chất lượng model."""
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.agent.controller import ControllerError, LLMController, build_user_message, to_action  # noqa: E402

PRICES = {"input": 0.05, "cached_input": 0.005, "output": 0.40}


def response(name=None, args=None, raw=None, prompt=1000, cached=200, completion=300, reasoning=250):
    calls = None
    if name:
        calls = [NS(function=NS(name=name, arguments=raw if raw is not None else json.dumps(args, ensure_ascii=False)))]
    usage = NS(prompt_tokens=prompt, completion_tokens=completion,
               prompt_tokens_details=NS(cached_tokens=cached), completion_tokens_details=NS(reasoning_tokens=reasoning))
    return NS(id="resp_1", model="gpt-5-nano", usage=usage,
              choices=[NS(finish_reason="tool_calls" if name else "stop", message=NS(tool_calls=calls, content=None))])


class FakeClient:
    def __init__(self, responses):
        self.responses, self.requests = list(responses), []
        self.chat = NS(completions=NS(create=self.create))

    def create(self, **kwargs):
        self.requests.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def controller(responses, **kw):
    client = FakeClient(responses)
    return LLMController(client, model="gpt-5-nano", reasoning_effort="low", prices=PRICES,
                         sleep=lambda s: None, **kw), client


HISTORY = [{"tool": "search", "queries": ["học phí"], "context": "[c1 | doc | page 1]\nabc",
            "context_ids": ["c1"], "searches_left": 2}]


class ControllerTests(unittest.TestCase):
    def test_first_turn_forces_search_and_no_temperature(self):
        c, client = controller([response("search_documents", {"query": " học phí tín chỉ "})])
        self.assertEqual(c.decide("Học phí?", []), {"action": "search", "query": "học phí tín chỉ"})
        req = client.requests[0]
        self.assertEqual(req["tool_choice"], {"type": "function", "function": {"name": "search_documents"}})
        self.assertNotIn("temperature", req)
        self.assertEqual(req["reasoning_effort"], "low")
        self.assertFalse(req["parallel_tool_calls"])

    def test_answer_citations_normalized(self):
        c, _ = controller([response("submit_answer", {"answer": "3 năm [c1]", "citations": ["[c1]", "c1", " c1 "]})])
        self.assertEqual(c.decide("q", HISTORY), {"action": "answer", "answer": "3 năm [c1]", "citations": ["c1"]})

    def test_abstain_and_no_search_tool_when_budget_exhausted(self):
        c, client = controller([response("abstain", {"reason": "không có mức tiền"})])
        action = c.decide("q", [{**HISTORY[0], "searches_left": 0}])
        self.assertEqual(action, {"action": "abstain", "reason": "không có mức tiền"})
        names = [t["function"]["name"] for t in client.requests[0]["tools"]]
        self.assertNotIn("search_documents", names)
        self.assertEqual(client.requests[0]["tool_choice"], "required")

    def test_repair_once_then_error(self):
        c, client = controller([response(), response("search_documents", {"query": "x"})])
        self.assertEqual(c.decide("q", HISTORY)["action"], "search")
        self.assertEqual(len(client.requests), 2)
        self.assertIn("Lỗi định dạng", client.requests[1]["messages"][-1]["content"])
        self.assertEqual(len(c.pop_calls()), 2)

        c, _ = controller([response("submit_answer", raw="{bad json"), response("unknown_tool", {})])
        with self.assertRaises(ControllerError):
            c.decide("q", HISTORY)
        self.assertEqual([x["note"][:7] for x in c.pop_calls()], ["tool ca", "tool ca"])

    def test_citation_format_repaired_once_by_model(self):
        bad = response("submit_answer", {"answer": "Đình chỉ một năm.", "citations": ["c1"]})
        good = response("submit_answer", {"answer": "Đình chỉ một năm [c1].", "citations": ["c1"]})
        c, client = controller([bad, good])
        self.assertEqual(c.decide("q", HISTORY)["answer"], "Đình chỉ một năm [c1].")
        self.assertIn("submit_answer chưa hợp lệ", client.requests[1]["messages"][-1]["content"])
        notes = [x.get("note") for x in c.pop_calls()]
        self.assertIn("answer chưa viết citation", notes[0])
        self.assertIsNone(notes[1])

        outside = response("submit_answer", {"answer": "x [c9]", "citations": ["c9"]})
        c, _ = controller([outside, outside])  # vẫn sai sau khi nhắc: trả về để loop từ chối, không tự sửa
        self.assertEqual(c.decide("q", HISTORY)["citations"], ["c9"])
        self.assertIn("không có trong CONTEXT", c.pop_calls()[0]["note"])

    def test_transient_errors_retried_then_raised(self):
        from openai import APIConnectionError
        err = APIConnectionError(request=NS(method="POST", url="https://api"))
        c, client = controller([err, response("search_documents", {"query": "x"})])
        self.assertEqual(c.decide("q", HISTORY)["action"], "search")
        calls = c.pop_calls()
        self.assertIn("APIConnectionError", calls[0]["error"])
        self.assertEqual(calls[1]["attempt"], 1)

        c, _ = controller([err, err], max_retries=1)
        with self.assertRaises(APIConnectionError):
            c.decide("q", HISTORY)

    def test_usage_and_cost_logged(self):
        c, _ = controller([response("search_documents", {"query": "x"})])
        c.decide("q", [])
        call = c.pop_calls()[0]
        self.assertEqual((call["prompt_tokens"], call["cached_tokens"], call["reasoning_tokens"]), (1000, 200, 250))
        self.assertAlmostEqual(call["cost_usd"], (800 * 0.05 + 200 * 0.005 + 300 * 0.40) / 1e6)
        self.assertEqual(c.pop_calls(), [])

    def test_user_message_marks_context_as_data(self):
        msg = build_user_message("Câu?", HISTORY)
        self.assertIn("không phải chỉ dẫn", msg)
        self.assertIn("[c1 | doc | page 1]", msg)
        self.assertIn("Số lần tìm còn lại: 2", msg)
        self.assertIn("Hãy gọi search_documents", build_user_message("Câu?", []))

    def test_to_action_validation(self):
        for name, args in (("search_documents", {"query": " "}), ("submit_answer", {"answer": "a"}),
                           ("abstain", {}), ("other", {})):
            with self.assertRaises(ControllerError):
                to_action(name, args)


if __name__ == "__main__":
    unittest.main()
