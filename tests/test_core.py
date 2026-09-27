import unittest
from decimal import Decimal
from unittest.mock import patch
import sys
import types

import numpy as np

from financial_assistant.answer import build_prompt
from financial_assistant.documents import Chunk, Report, extract_chunks, split_text
from financial_assistant.evaluation import evaluate_retrieval
from financial_assistant.finance import Figure, net_profit_margin, operating_margin, revenue_growth
from financial_assistant.retrieval import RetrievalIndex, reciprocal_rank_fusion


def figure(value, year="FY2025", *, page=1, basis="Consolidated"):
    return Figure(Decimal(value), "Example Co", year, "INR", "millions", basis, "annual.pdf", page)


class CoreTests(unittest.TestCase):
    def test_calculations_and_sources(self):
        growth = revenue_growth(figure("120"), figure("100", "FY2024", page=2))
        self.assertEqual(growth.value, Decimal("20"))
        self.assertEqual(growth.sources, ("annual.pdf, PDF p. 1", "annual.pdf, PDF p. 2"))
        self.assertEqual(net_profit_margin(figure("12"), figure("120")).value, Decimal("10.0"))
        self.assertEqual(operating_margin(figure("18"), figure("120")).value, Decimal("15.00"))

    def test_reject_incompatible_and_zero_denominator(self):
        with self.assertRaises(ValueError):
            revenue_growth(figure("120"), figure("0", "FY2024"))
        with self.assertRaises(ValueError):
            net_profit_margin(figure("12", basis="Standalone"), figure("120"))
        with self.assertRaises(ValueError):
            revenue_growth(figure("120"), figure("100"))

    def test_page_chunks_and_prompt_metadata(self):
        import fitz
        pdf = fitz.open()
        for sentence in ("Revenue was 120 million.", "Operating profit was 18 million."):
            page = pdf.new_page()
            page.insert_text((72, 72), sentence)
        chunks = extract_chunks(Report("annual.pdf", "Example Co", "FY2025", pdf.tobytes()))
        pdf.close()
        self.assertEqual([c.page for c in chunks], [1, 2])
        self.assertIn("PDF page: 1", build_prompt("What was revenue?", chunks))
        self.assertGreater(len(split_text("word " * 400, max_chars=120)), 1)

    def test_rank_fusion(self):
        self.assertEqual(reciprocal_rank_fusion([[1, 2], [2, 3]])[0], 2)

    def test_semantic_filter_applies_before_ranking(self):
        chunks = [Chunk("a", "a.pdf", "A", "FY2025", 1, "first"),
                  Chunk("b", "b.pdf", "B", "FY2025", 1, "second")]
        class Encoder:
            def encode(self, *args, **kwargs):
                return [[1.0, 0.0]]
        class FakeFaissIndex:
            def __init__(self, dimension):
                self.vectors = None
            def add(self, vectors):
                self.vectors = vectors
            def search(self, query, k):
                scores = self.vectors @ query[0]
                positions = np.argsort(-scores)[:k]
                return scores[positions][None, :], positions[None, :]
        index = RetrievalIndex.__new__(RetrievalIndex)
        index.chunks = chunks
        index.vectors = np.array([[1, 0], [0, 1]], dtype="float32")
        index.encoder = Encoder()
        index._reranker = None
        fake_faiss = types.SimpleNamespace(IndexFlatIP=FakeFaissIndex)
        with patch.dict(sys.modules, {"faiss": fake_faiss}):
            result = index.search("question", mode="semantic", company="B")
        self.assertEqual([item.id for item in result], ["b"])

    def test_retrieval_evaluation_needs_all_expected_pages(self):
        chunks = [Chunk("a", "one.pdf", "Example Co", "FY2025", 1, "A"),
                  Chunk("b", "one.pdf", "Example Co", "FY2025", 2, "B")]
        class FakeIndex:
            def search(self, *args, **kwargs):
                return chunks[:1]
        examples = [{"question": "Compare", "expected_sources": [
            {"document": "one.pdf", "page": 1}, {"document": "one.pdf", "page": 2}]}]
        result = evaluate_retrieval(FakeIndex(), examples, "hybrid")
        self.assertEqual(result.success_at_5, 0.0)


if __name__ == "__main__":
    unittest.main()
