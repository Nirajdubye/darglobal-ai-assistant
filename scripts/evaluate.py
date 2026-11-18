"""End-to-end evaluation on realistic questions (real index + real OpenRouter model).

    python -m scripts.evaluate                       # in-process
    python -m scripts.evaluate --api https://...     # against a running deployment

Each question in tests/eval_questions.json declares what a correct answer needs:
    expect_url        substring that must appear in a retrieved source URL (retrieval relevance)
    expect_keywords   facts (any-of groups) that must appear in the answer (answer accuracy)
    forbid_keywords   values that would indicate hallucination
    answerable=false  the bot must decline / say the data is unavailable
Writes docs/eval_results.json and prints a summary table.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DECLINE_RE = re.compile(r"(don't|do not|doesn't|does not|not) (have|contain|include|available|provided|mention|specified|listed)|"
                        r"no information|not available|unavailable|cannot (find|answer)|isn't (available|included)|"
                        r"not in the (collected|provided)", re.I)


def ask_local():
    from app.config import get_settings
    from app.ingestion.indexing import VectorIndex
    from app.rag.generator import OpenRouterGenerator
    from app.rag.retriever import Retriever
    from app.services.chat_service import ChatService
    s = get_settings()
    idx = VectorIndex(s.chroma_dir, s.collection_name, embedding_model=s.embedding_model)
    svc = ChatService(Retriever(idx, s), OpenRouterGenerator(s), s)
    return lambda q, h: svc.answer(q, h)


def ask_api(base: str):
    def _ask(q, h):
        r = requests.post(f"{base.rstrip('/')}/chat", json={"question": q, "history": h}, timeout=180)
        if not r.ok:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
        return r.json()
    return _ask


def grade(item: dict, res: dict) -> dict:
    answer = res["answer"]
    low = answer.lower()
    urls = [s["url"] for s in res.get("sources", [])]
    g = {"id": item["id"], "question": item["question"], "answerable": item.get("answerable", True)}
    if g["answerable"]:
        g["retrieval_hit"] = any(item["expect_url"] in u for u in urls) if item.get("expect_url") else None
        groups = item.get("expect_keywords", [])
        g["keywords_ok"] = all(any(k.lower() in low for k in grp) for grp in groups) if groups else None
        g["has_citation"] = bool(re.search(r"\[\d+\]", answer))
        g["source_correct"] = g["retrieval_hit"] if g["retrieval_hit"] is not None else bool(urls)
    else:
        g["declined"] = (not res.get("grounded")) or bool(DECLINE_RE.search(answer))
    g["hallucination"] = any(k.lower() in low for k in item.get("forbid_keywords", []))
    g["model"] = res.get("model")
    g["answer"] = answer
    g["sources"] = urls[:4]
    return g


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api")
    ap.add_argument("--questions", default=str(ROOT / "tests" / "eval_questions.json"))
    ap.add_argument("--delay", type=float, default=4.0, help="seconds between questions (free-tier rate limits)")
    args = ap.parse_args()
    items = json.loads(Path(args.questions).read_text())
    ask = ask_api(args.api) if args.api else ask_local()

    results = []
    for item in items:
        history = []
        if item.get("follow_up_of"):
            prev = next(i for i in items if i["id"] == item["follow_up_of"])
            prev_res = next((r for r in results if r["id"] == prev["id"]), None)
            history = [{"role": "user", "content": prev["question"]},
                       {"role": "assistant", "content": prev_res["answer"] if prev_res else ""}]
        for attempt in range(3):
            try:
                res = ask(item["question"], history)
                break
            except Exception as e:  # rate limit / transient model error -> back off and retry
                print(f"  {item['id']}: {type(e).__name__}: {str(e)[:120]} (retry {attempt + 1})")
                time.sleep(20 * (attempt + 1))
        else:
            results.append({"id": item["id"], "question": item["question"], "error": True})
            continue
        g = grade(item, res)
        results.append(g)
        flag = "OK " if _passed(g) else "XX "
        print(f"{flag}{g['id']:<6} {item['question'][:70]}")
        time.sleep(args.delay)

    summary = _summary(results)
    out = ROOT / "docs" / "eval_results.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False))
    print(json.dumps(summary, indent=2))


def _passed(g: dict) -> bool:
    if g.get("error"):
        return False
    if not g["answerable"]:
        return g["declined"] and not g["hallucination"]
    return g["retrieval_hit"] is not False and g["keywords_ok"] is not False and not g["hallucination"]


def _summary(results: list[dict]) -> dict:
    ok = [r for r in results if not r.get("error")]
    ans = [r for r in ok if r["answerable"]]
    una = [r for r in ok if not r["answerable"]]
    rate = lambda xs: f"{sum(xs)}/{len(xs)}" if xs else "n/a"  # noqa: E731
    return {
        "questions": len(results),
        "errors": len(results) - len(ok),
        "passed": rate([_passed(r) for r in ok]),
        "retrieval_relevance": rate([r["retrieval_hit"] for r in ans if r["retrieval_hit"] is not None]),
        "answer_accuracy_keywords": rate([r["keywords_ok"] for r in ans if r["keywords_ok"] is not None]),
        "citations_present": rate([r["has_citation"] for r in ans]),
        "source_correctness": rate([r["source_correct"] for r in ans]),
        "unknown_questions_declined": rate([r["declined"] for r in una]),
        "hallucination_free": rate([not r["hallucination"] for r in ok]),
    }


if __name__ == "__main__":
    main()
