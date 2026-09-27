"""Retrieval-only evaluation against manually identified document pages."""

from dataclasses import dataclass
from statistics import median
from time import perf_counter

from .retrieval import RetrievalIndex


@dataclass(frozen=True)
class RetrievalResult:
    mode: str
    questions: int
    answerable: int
    success_at_5: float | None
    median_latency_seconds: float


def evaluate_retrieval(index: RetrievalIndex, examples: list[dict], mode: str) -> RetrievalResult:
    times: list[float] = []
    hits = 0
    answerable = 0
    for example in examples:
        start = perf_counter()
        results = index.search(
            example["question"], mode=mode, top_k=5,
            company=example.get("company"), fiscal_year=example.get("fiscal_year"),
        )
        times.append(perf_counter() - start)
        expected = {(source["document"], int(source["page"]))
                    for source in example.get("expected_sources", [])}
        if expected:
            answerable += 1
            found = {(chunk.document, chunk.page) for chunk in results}
            hits += expected.issubset(found)
    return RetrievalResult(mode, len(examples), answerable,
                           hits / answerable if answerable else None, median(times) if times else 0.0)
