# Financial Report Analysis Assistant

A Streamlit application for asking questions across uploaded annual report PDFs and inspecting the evidence behind an answer. It combines BM25 keyword retrieval, FAISS semantic retrieval, reciprocal-rank fusion, and optional cross-encoder reranking. Gemini drafts answers from retrieved passages; each passage retains its document name and PDF page number.

The app also provides a calculator for revenue growth, net profit margin, and operating margin. You enter figures **after checking the PDF**, and it displays the formula and source pages. It does not infer figures from financial tables.

## What works today

| Capability | Implementation |
| --- | --- |
| Upload | Text-based PDFs uploaded in Streamlit, tagged by company and fiscal year |
| Extraction | PyMuPDF page text split into overlapping, page-bound passages |
| Retrieval | BM25, normalized sentence embeddings in FAISS, rank fusion, and optional cross-encoder reranking |
| Filters | Company and fiscal year applied before retrieval ranking |
| Answers | Gemini receives the top five passages and is instructed to cite numbered references or state insufficient evidence |
| Evidence | Expandable excerpts show the PDF name, one-based PDF page, company, and year |
| Calculations | Decimal arithmetic with source pages and compatibility checks |
| Evaluation | Retrieval success@5 and median retrieval latency on a user-supplied reviewed question set |

### Request flow

1. Upload annual reports and tag each file with its company and fiscal year.
2. Extract text while retaining PDF page numbers, then build BM25 and embedding indexes.
3. Filter eligible passages, retrieve candidates by semantic and keyword matching, combine ranked lists, and optionally rerank them.
4. Send the five selected excerpts to Gemini. The UI displays the answer alongside the passages used in the prompt.
5. Inspect the original report pages before relying on a claim or entering values in the calculator.

Bracketed citations refer to displayed passage numbers, **not** independently verified fact-level citations. The app checks that citation numbers are valid, but does not prove that each claim is supported.

## Installation and local run

Use a recent Python 3 environment. The first run downloads embedding and reranker model weights. An internet connection is needed for these downloads and Gemini answers.

```bash
git clone https://github.com/PriyanshuSharmapixel/Financial-Report-Analysis-Assistant-using-RAG.git
cd Financial-Report-Analysis-Assistant-using-RAG
python -m venv .venv
```

Activate the environment and install dependencies:

```bash
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a local `.env` using [`.env.example`](.env.example) as a guide, and set `GEMINI_API_KEY`. Optionally set `GEMINI_MODEL` (default: `gemini-3.8-flash`). **Do not commit API keys.** Retrieval and calculation work without a Gemini key; answer generation requires one. Only selected text passages, not the entire uploaded PDF, are sent to Gemini.

```bash
streamlit run app.py
```

Upload text-based reports (maximum 25 MB each), provide labels, then click **Index reports**. Uploaded data and indexes stay in the current Streamlit session; they are not persisted. Re-index after changing files or labels.

## Financial calculations

| Metric | Formula | Inputs |
| --- | --- | --- |
| Revenue growth | `(current revenue - previous revenue) / previous revenue × 100` | Two distinct years, positive previous revenue |
| Net profit margin | `net profit / revenue × 100` | Same year, positive revenue |
| Operating margin | `operating profit / revenue × 100` | Same year, positive revenue |

Inputs must have the same company, currency, unit, and reporting basis (consolidated or standalone). Margin inputs must also share a fiscal year. Source pages are supplied by the user; **their values are not automatically checked against the PDF**. A report can include comparative figures, so its filename/year tag alone cannot verify a figure's accounting period.

## Evaluate retrieval

No reports or reviewed question set are included. The original target of **six reports from three companies and 50 questions** remains dataset work; there are no measured answer or citation-support results to report.

Create a local manifest JSON with PDF paths relative to the manifest file:

```json
[{"path":"data/company_a_fy2025.pdf","company":"Company A","fiscal_year":"FY2025"}]
```

Create a JSONL question file, one object per line. Include every PDF page needed to support an answer; use an empty list for unanswerable questions.

```json
{"question":"What was reported revenue?","company":"Company A","fiscal_year":"FY2025","expected_sources":[{"document":"company_a_fy2025.pdf","page":42}]}
```

```bash
python scripts/evaluate.py --manifest reports.json --questions questions.jsonl
```

The script compares **semantic**, **hybrid**, and **hybrid + rerank** retrieval. Success@5 is the fraction of answerable questions whose top five passages contain **all** expected `(document, PDF page)` pairs. Median latency measures retrieval only, not Gemini generation. Answer correctness, citation support, and unanswerable-question behavior require separate manual review.

## Project structure

| Path | Purpose |
| --- | --- |
| [`app.py`](app.py) | Upload, Q&A, evidence display, and calculator UI |
| [`financial_assistant/documents.py`](financial_assistant/documents.py) | Page-aware PDF extraction |
| [`financial_assistant/retrieval.py`](financial_assistant/retrieval.py) | BM25, FAISS, fusion, reranking |
| [`financial_assistant/answer.py`](financial_assistant/answer.py) | Gemini prompt and citation-number checks |
| [`financial_assistant/finance.py`](financial_assistant/finance.py) | Arithmetic on user-verified figures |
| [`financial_assistant/evaluation.py`](financial_assistant/evaluation.py) | Retrieval metric definitions |
| [`scripts/evaluate.py`](scripts/evaluate.py) | Evaluation command-line entry point |
| [`tests/test_core.py`](tests/test_core.py) | Offline checks of core behavior |

Run checks with `python -m unittest discover -s tests -v` after installing dependencies.

## Limits

- Scanned/image-only PDFs require OCR. Tables, footnotes, and multiple columns can be extracted imperfectly.
- Embedding and reranker downloads can be substantial. Several long reports may take time and memory to index on a CPU.
- A relevant excerpt does not guarantee a correct answer. Check important claims and figures in the original pages.
- Company/year tags are supplied by the uploader; report provenance and accounting definitions are not independently verified.
- Build a reviewed dataset before claiming benchmark performance. This tool does not supply live market data or investment recommendations.
