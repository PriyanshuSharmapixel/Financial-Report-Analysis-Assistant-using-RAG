"""Run a retrieval comparison against a manually reviewed JSONL question set."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from financial_assistant.documents import Report, extract_chunks
from financial_assistant.evaluation import evaluate_retrieval
from financial_assistant.retrieval import RetrievalIndex


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, help="JSON list of report path/company/year records")
    parser.add_argument("--questions", type=Path, required=True, help="Manually labeled JSONL question set")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    examples = [json.loads(line) for line in args.questions.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not examples:
        parser.error("Question set is empty")
    chunks = []
    for item in manifest:
        path = (args.manifest.parent / item["path"]).resolve()
        chunks.extend(extract_chunks(Report(path.name, item["company"], item["fiscal_year"], path.read_bytes())))
    index = RetrievalIndex(chunks)
    for mode in ("semantic", "hybrid", "hybrid + rerank"):
        result = evaluate_retrieval(index, examples, mode)
        print(f"{mode}: success@5={result.success_at_5!r} "
              f"({result.answerable} answerable / {result.questions} total), "
              f"median retrieval latency={result.median_latency_seconds:.3f}s")


if __name__ == "__main__":
    main()
