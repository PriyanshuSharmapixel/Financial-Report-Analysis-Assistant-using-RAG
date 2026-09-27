"""Extract page-aware chunks from text-based annual report PDFs."""

from dataclasses import dataclass
import hashlib
import re


@dataclass(frozen=True)
class Report:
    filename: str
    company: str
    fiscal_year: str
    pdf_bytes: bytes


@dataclass(frozen=True)
class Chunk:
    id: str
    document: str
    company: str
    fiscal_year: str
    page: int  # One-based PDF page, not a printed page number.
    text: str


def split_text(text: str, max_chars: int = 1200, overlap_words: int = 35) -> list[str]:
    """Split one page without allowing a chunk to cross a PDF page boundary."""
    if max_chars < 100 or overlap_words < 0:
        raise ValueError("Invalid chunk settings")
    words = re.sub(r"\s+", " ", text).strip().split()
    pieces: list[str] = []
    start = 0
    while start < len(words):
        end = start
        length = 0
        while end < len(words) and (length + len(words[end]) + 1 <= max_chars or end == start):
            length += len(words[end]) + 1
            end += 1
        pieces.append(" ".join(words[start:end]))
        if end == len(words):
            break
        overlap = min(overlap_words, (end - start) // 2)
        start = end - overlap
    return pieces


def extract_chunks(report: Report, max_chars: int = 1200) -> list[Chunk]:
    import fitz  # PyMuPDF

    if not report.pdf_bytes:
        raise ValueError(f"{report.filename}: empty PDF")
    if not report.company.strip() or not report.fiscal_year.strip():
        raise ValueError("Company and fiscal year are required")
    try:
        pdf = fitz.open(stream=report.pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"{report.filename}: could not open PDF") from exc

    chunks: list[Chunk] = []
    identity = hashlib.sha256(report.pdf_bytes).hexdigest()[:12]
    try:
        for page_number, page in enumerate(pdf, start=1):
            for part, content in enumerate(split_text(page.get_text("text"), max_chars), start=1):
                chunks.append(Chunk(
                    id=f"{identity}:p{page_number}:c{part}",
                    document=report.filename,
                    company=report.company.strip(),
                    fiscal_year=report.fiscal_year.strip(),
                    page=page_number,
                    text=content,
                ))
    finally:
        pdf.close()
    if not chunks:
        raise ValueError(f"{report.filename}: no extractable text; scanned PDFs require OCR")
    return chunks
