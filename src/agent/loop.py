"""Vòng lặp agent Day 7, mở rộng từ `starter/agentic.py::run_agent`.

Giữ nguyên hành vi của starter (để so sánh được và vẫn qua các test của starter):
- context cộng dồn từ mọi lần search, ghép bằng `starter/baseline.pack_context` trong `budget` ký tự;
- controller chỉ nhận context cộng dồn MỚI NHẤT (không nhân budget theo số lượt);
- citation hợp lệ khi ID nằm trong context cuối VÀ xuất hiện dạng `[id]` trong câu trả lời;
- lỗi provider/retriever được ném ra, không có mock fallback. Không gold nào đi vào vòng lặp.

Mở rộng:
- action `abstain` (model chủ động từ chối) tách khỏi từ chối do citation sai hoặc hết lượt search;
- `stop_reason` cho mỗi lần chạy: answered | model_abstain | invalid_or_missing_citations | search_limit | max_steps;
- event `llm_call` cho mỗi lần controller gọi model (nếu controller có `pop_calls()`), event `search`
  có thêm `step`, `elapsed_ms`; kết quả có `num_searches`, `context_ids`, `elapsed_ms`.
Event `search` giữ đúng tên để `starter/agent_metrics.py` đếm tool use.
"""
import sys
import time
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "starter"))
from baseline import pack_context  # noqa: E402  — dùng chung với baseline retrieval

ABSTAIN_ANSWER = "Không đủ bằng chứng để trả lời."
STOP_REASONS = ("answered", "model_abstain", "invalid_or_missing_citations", "search_limit", "max_steps")


class Controller(Protocol):
    def decide(self, question: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        """Gọi model thật; trả một action đã chuẩn hóa:
        {'action': 'search', 'query': '...'}
        {'action': 'answer', 'answer': '... [chunk-id]', 'citations': ['chunk-id']}
        {'action': 'abstain', 'reason': '...'}
        """
        ...


class Retriever(Protocol):
    def search(self, query: str, *, filters: dict[str, Any] | None, top_k: int) -> list[dict[str, Any]]:
        """Trả tối đa top_k chunk (id, text, source_id, source, page, metadata, score) từ vector store thật."""
        ...


def _drain_llm_calls(controller: Any, step: int) -> list[dict[str, Any]]:
    pop = getattr(controller, "pop_calls", None)
    return [{"event": "llm_call", "step": step, **call} for call in (pop() if callable(pop) else [])]


def _finish(status: str, stop_reason: str, events: list, chunks: dict, started: float, *,
            answer: str = ABSTAIN_ANSWER, citations: list[str] | None = None, **extra) -> dict[str, Any]:
    return {"status": status, "stop_reason": stop_reason, "answer": answer, "citations": citations or [],
            "events": events, "num_searches": sum(e["event"] == "search" for e in events),
            "context_ids": list(chunks), "elapsed_ms": (time.perf_counter() - started) * 1000, **extra}


SELECTIONS = ("order", "score")
FIRST_QUERIES = ("model", "question")


def _norm_query(q: str) -> str:
    return " ".join(q.casefold().split())


def select_candidates(candidates: list[dict[str, Any]], selection: str) -> list[dict[str, Any]]:
    """Thứ tự đưa vào pack_context.
    - "order" (baseline/starter): theo thứ tự tìm được, chunk của lần search trước được giữ trước.
    - "score": mỗi chunk lấy score cao nhất qua các lần search, xếp giảm dần. Chỉ dùng với score so sánh
      được giữa các query (cosine dense, cross-encoder rerank); không dùng với RRF."""
    if selection == "order":
        return candidates
    best: dict[str, dict[str, Any]] = {}
    for c in candidates:
        if c["id"] not in best or c["score"] > best[c["id"]]["score"]:
            best[c["id"]] = c
    return sorted(best.values(), key=lambda c: (-c["score"], c["id"]))


def run_agent(question: str, controller: Controller, retriever: Retriever, *,
              filters: dict[str, Any] | None = None, max_searches: int = 4,
              top_k: int = 3, budget: int = 800, selection: str = "order",
              first_query: str = "model", dedupe_queries: bool = False) -> dict[str, Any]:
    """Chạy agent cho một câu hỏi; trả status, answer, citations, events và stop_reason.

    Mặc định (selection="order", first_query="model", dedupe_queries=False) = hành vi baseline/starter.
    - first_query="question": lần search đầu dùng nguyên văn câu hỏi, không qua model (event origin
      "question_verbatim"); model bắt đầu quyết định từ lượt sau.
    - dedupe_queries=True: query trùng (bỏ hoa/thường, khoảng trắng) với query đã dùng thì không search lại,
      vẫn tính một lượt, và báo model trong history để đổi cách diễn đạt.
    """
    if not question.strip() or max_searches < 1 or top_k < 1 or budget < 1:
        raise ValueError("question, max_searches, top_k hoặc budget không hợp lệ")
    if selection not in SELECTIONS or first_query not in FIRST_QUERIES:
        raise ValueError(f"selection phải thuộc {SELECTIONS}, first_query thuộc {FIRST_QUERIES}")
    started = time.perf_counter()
    history: list[dict[str, Any]] = []
    chunks: dict[str, dict[str, Any]] = {}
    candidates: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    used = lambda: sum(e["event"] in ("search", "duplicate_query") for e in events)  # noqa: E731

    def update_history(context, ids, note=None):
        history[:] = [{"tool": "search", "queries": [e["query"] for e in events if e["event"] == "search"],
                       "context": context, "context_ids": ids, "searches_left": max_searches - used(),
                       **({"note": note} if note else {})}]

    def do_search(step, query, origin):
        nonlocal chunks
        t0 = time.perf_counter()
        results = retriever.search(query, filters=filters, top_k=top_k)
        search_ms = (time.perf_counter() - t0) * 1000
        if len(results) > top_k or len({r["id"] for r in results}) != len(results):
            raise ValueError("retriever phải trả tối đa top_k chunk ID duy nhất")
        candidates.extend(results)
        context, ids = pack_context(select_candidates(candidates, selection), budget=budget)
        chunks = {c["id"]: c for c in candidates if c["id"] in ids}
        events.append({"event": "search", "step": step, "query": query, "origin": origin, "filter": filters,
                       "results": results, "context": context, "context_ids": ids, "elapsed_ms": search_ms,
                       "timing": dict(getattr(retriever, "last_timing", {}) or {})})
        # Chỉ gửi context cộng dồn mới nhất; tránh nhân budget theo số lượt.
        update_history(context, ids)

    if first_query == "question":
        do_search(-1, question, "question_verbatim")

    for step in range(max_searches + 1):
        try:
            action = controller.decide(question, history)
        finally:  # vẫn ghi lần gọi LLM khi provider lỗi
            events.extend(_drain_llm_calls(controller, step))
        kind = action.get("action")

        if kind == "search":
            if used() >= max_searches:
                return _finish("abstain", "search_limit", events + [{"event": "search_limit", "step": step}],
                               chunks, started)
            query = action.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ValueError("search query phải là chuỗi không rỗng")
            previous = {_norm_query(e["query"]) for e in events if e["event"] == "search"}
            if dedupe_queries and _norm_query(query) in previous:
                events.append({"event": "duplicate_query", "step": step, "query": query})
                last = history[0] if history else {"context": "", "context_ids": []}
                update_history(last["context"], last["context_ids"],
                               note=f"Query '{query}' đã dùng, không tìm lại. Hãy dùng từ khóa/cách diễn đạt khác "
                                    "hoặc trả lời/từ chối dựa trên CONTEXT.")
                continue
            do_search(step, query, "model")

        elif kind == "answer":
            answer, citations = action.get("answer"), action.get("citations")
            if not isinstance(answer, str) or not isinstance(citations, list) \
                    or any(not isinstance(i, str) for i in citations):
                raise ValueError("answer/citations không hợp lệ")
            valid = bool(answer.strip() and citations
                         and all(i in chunks and f"[{i}]" in answer for i in citations))
            if valid:
                return _finish("answered", "answered", events + [{"event": "answer", "step": step}], chunks,
                               started, answer=answer, citations=citations)
            # Giữ câu trả lời bị loại để phân tích lỗi; không tính là trả lời.
            return _finish("abstain", "invalid_or_missing_citations",
                           events + [{"event": "invalid_or_missing_citations", "step": step,
                                      "rejected_answer": answer, "rejected_citations": citations}],
                           chunks, started)

        elif kind == "abstain":
            reason = action.get("reason")
            if not isinstance(reason, str):
                raise ValueError("abstain cần reason là chuỗi")
            searched = any(e["event"] == "search" for e in events)
            return _finish("abstain", "model_abstain",
                           events + [{"event": "abstain", "step": step, "reason": reason,
                                      "searched_before_abstain": searched}],
                           chunks, started, abstain_reason=reason)
        else:
            raise ValueError("action phải là search, answer hoặc abstain")

    return _finish("abstain", "max_steps", events + [{"event": "max_steps"}], chunks, started)
