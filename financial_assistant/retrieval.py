"""BM25, FAISS semantic search, reciprocal-rank fusion, and reranking."""

from collections import defaultdict
import re
from typing import Sequence

import numpy as np

from .documents import Chunk


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def reciprocal_rank_fusion(rankings: Sequence[Sequence[int]], constant: int = 60) -> list[int]:
    scores: dict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, index in enumerate(ranking, start=1):
            scores[index] += 1.0 / (constant + rank)
    return sorted(scores, key=lambda index: (-scores[index], index))


class RetrievalIndex:
    def __init__(self, chunks: list[Chunk], embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        if not chunks:
            raise ValueError("Upload at least one text-based PDF")
        from rank_bm25 import BM25Okapi
        from sentence_transformers import SentenceTransformer

        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(chunk.text) or [""] for chunk in chunks])
        self.encoder = SentenceTransformer(embedding_model)
        self.vectors = np.asarray(
            self.encoder.encode([chunk.text for chunk in chunks], normalize_embeddings=True, show_progress_bar=False),
            dtype="float32",
        )
        self._reranker = None

    def search(
        self, question: str, mode: str = "hybrid + rerank", top_k: int = 5,
        company: str | None = None, fiscal_year: str | None = None,
    ) -> list[Chunk]:
        if mode not in {"semantic", "hybrid", "hybrid + rerank"}:
            raise ValueError("Unknown retrieval mode")
        if not question.strip() or top_k < 1:
            return []

        eligible = [i for i, c in enumerate(self.chunks)
                    if (not company or c.company == company)
                    and (not fiscal_year or c.fiscal_year == fiscal_year)]
        if not eligible:
            return []

        # Build a FAISS index for eligible chunks so filters apply before ranking.
        import faiss
        subset = np.ascontiguousarray(self.vectors[eligible])
        faiss_index = faiss.IndexFlatIP(subset.shape[1])
        faiss_index.add(subset)
        query = np.asarray(self.encoder.encode([question], normalize_embeddings=True), dtype="float32")
        candidate_count = min(max(top_k * 5, 20), len(eligible))
        _, positions = faiss_index.search(query, candidate_count)
        semantic = [eligible[int(pos)] for pos in positions[0] if pos >= 0]

        if mode == "semantic":
            candidates = semantic
        else:
            bm25_scores = self.bm25.get_scores(tokenize(question))
            keyword = sorted(eligible, key=lambda i: (-bm25_scores[i], i))[:candidate_count]
            candidates = reciprocal_rank_fusion([semantic, keyword])[:candidate_count]

        if mode == "hybrid + rerank" and candidates:
            if self._reranker is None:
                from sentence_transformers import CrossEncoder
                self._reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            scores = self._reranker.predict([(question, self.chunks[i].text) for i in candidates])
            candidates = sorted(zip(candidates, scores), key=lambda pair: -float(pair[1]))
            candidates = [index for index, _ in candidates]
        return [self.chunks[i] for i in candidates[:top_k]]
