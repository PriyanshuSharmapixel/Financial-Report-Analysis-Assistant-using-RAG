# Financial Report Analysis Assistant using RAG

A document question-answering application for exploring annual reports, comparing company financial information, and checking answers against their original sources.

> **Status: In progress.** This README describes the planned implementation and evaluation scope. Performance results have not been measured yet.

## Overview

Annual reports contain financial statements, business updates, and risk disclosures spread across many pages. This project aims to make that information easier to explore through questions in plain English.

The application uses Retrieval-Augmented Generation (RAG) to find relevant report sections and provide them to a language model. Answers include document names and page references so users can inspect the supporting evidence.

Python functions handle financial calculations using extracted and validated figures.

## Planned Features

- Upload and process text-based annual report PDFs.
- Search across reports using company and financial-year filters.
- Combine BM25 keyword search with FAISS semantic search.
- Rerank retrieved passages using a cross-encoder.
- Answer questions with document names, PDF page numbers, and supporting excerpts.
- Compare financial information across companies and years.
- Calculate revenue growth, net profit margin, and operating margin.
- Request clarification or report insufficient evidence when a question cannot be answered reliably.
- Provide a Streamlit interface for uploads, questions, and source inspection.

## Example Questions

- What major business risks does the company describe?
- How did revenue change between the two financial years?
- What were the reported reasons for changes in operating expenses?
- Compare the net profit margins of the selected companies.
- Which pages support this answer?

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Core application | Python | Data processing, retrieval, and calculations |
| PDF extraction | PyMuPDF | Extract text and retain PDF page references |
| Workflow | LangChain | Connect retrieval, prompts, and model calls |
| Embeddings | Sentence Transformers | Represent questions and passages as vectors |
| Semantic search | FAISS | Retrieve passages by semantic similarity |
| Keyword search | BM25 through rank-bm25 | Retrieve exact financial terms and names |
| Reranking | Sentence Transformers CrossEncoder | Rank candidate passages by relevance |
| Language model | Gemini API | Generate answers from supplied evidence |
| Financial analysis | Python and pandas | Validate figures and calculate metrics |
| Interface | Streamlit | Display uploads, answers, and evidence |

## How It Works

### 1. Document preparation

Extract text from each PDF, remove repeated headers and footers where practical, and split the content into sections. Retain company, financial year, document name, and page metadata with each chunk.

### 2. Indexing

Build a BM25 index and a FAISS embedding index over the same chunks. Record the embedding model and processing settings so the indexes can be reproduced.

### 3. Retrieval and reranking

Apply the selected company and year filters, retrieve candidates from both indexes, and combine their rankings using reciprocal rank fusion. A cross-encoder reranks the combined candidates before context is passed to the language model.

### 4. Answer generation

Provide the question and selected passages to Gemini. The answer should identify its sources and distinguish reported facts from calculated values. Missing or conflicting evidence should be surfaced to the user.

### 5. Financial calculations

Validate the figures, accounting period, currency, units, and reporting basis before calling a Python calculation function. Display the inputs and formula alongside the result.

## Supported Calculations — Planned

| Metric | Formula |
|---|---|
| Revenue growth | ((Current revenue - Previous revenue) / Previous revenue) × 100 |
| Net profit margin | (Net profit / Revenue) × 100 |
| Operating margin | (Operating profit / Revenue) × 100 |

Each result should cite the pages containing its inputs. Zero denominators must be handled explicitly. Growth from a negative base should be flagged as potentially misleading. Comparisons should use consistent periods, units, and consolidated or standalone figures.

## Dataset Scope

The initial target is **6 annual reports from 3 companies across 2 financial years**. Reports will be sourced from official investor-relations pages.

A source manifest will record the company, year, report title, source URL, and retrieval date. These counts are development targets, not a completed dataset claim.

## Evaluation Plan

Prepare **50 manually reviewed questions** with reference answers and expected source pages:

- 15 direct factual questions.
- 10 questions requiring multiple passages.
- 10 comparisons across reports.
- 10 financial calculation questions.
- 5 questions with missing or insufficient evidence.

Use 20 questions for development and keep 30 held out for final evaluation, with question types represented in both sets. Avoid placing near-duplicate questions across the two sets.

Compare three configurations on the same held-out questions:

| Configuration | Retrieval success@5 | Answer correctness | Citation support | Median latency |
|---|---|---|---|---|
| Semantic retrieval | Pending | Pending | Pending | Pending |
| BM25 + semantic retrieval | Pending | Pending | Pending | Pending |
| Hybrid retrieval + reranking | Pending | Pending | Pending | Pending |

- **Retrieval success@5:** Percentage of answerable questions for which the top five passages include all required source evidence.
- **Answer correctness:** Percentage of answers judged correct against manually reviewed references.
- **Citation support:** Percentage of cited factual claims supported by the cited passages.
- **Median latency:** Median time from question submission to the complete response.

Also report calculation accuracy and handling of unanswerable questions separately. Keep the generation model and prompt fixed when comparing retrieval configurations, and document the run settings.

## Setup Status

Installation and run instructions will be added once the application files, dependency versions, and entry point are implemented and tested. No runnable release is claimed at this stage.

The Gemini API key will be loaded from an environment variable and excluded from version control. Retrieved passages sent to the API should come only from documents the user is permitted to process with an external service.

## Limitations

- The initial scope covers text-based PDFs; scanned reports require an additional OCR step.
- Tables and complex layouts can produce extraction errors and may need manual review.
- Retrieval and citations reduce uncertainty but do not guarantee correct answers.
- Different accounting definitions or financial periods can make comparisons misleading.
- The application works with uploaded reports and does not provide live market data.
- This is a document research project, not an investment recommendation service.

## Roadmap

- [ ] Collect reports and create the source manifest.
- [ ] Implement PDF extraction and page metadata.
- [ ] Build a semantic retrieval baseline.
- [ ] Add BM25 retrieval, rank fusion, and reranking.
- [ ] Add cited answers and insufficient-evidence handling.
- [ ] Implement and test the three calculation functions.
- [ ] Build the Streamlit interface.
- [ ] Run the evaluation and publish measured results.
- [ ] Add tested setup instructions and demo screenshots.

## Author

**Priyanshu Kumar Sharma**  
Integrated M.Sc. in Mathematics, NIT Rourkela  
[GitHub](https://github.com/PriyanshuSharmapixel)
