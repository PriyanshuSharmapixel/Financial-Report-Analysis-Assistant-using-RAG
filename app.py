"""Streamlit interface for page-cited financial report research."""

from decimal import Decimal, InvalidOperation
import os

import streamlit as st
from dotenv import load_dotenv

from financial_assistant.answer import generate_answer
from financial_assistant.documents import Report, extract_chunks
from financial_assistant.finance import Figure, revenue_growth, net_profit_margin, operating_margin
from financial_assistant.retrieval import RetrievalIndex


load_dotenv()
st.set_page_config(page_title="Financial Report Assistant", layout="wide")
st.title("Financial Report Analysis Assistant")
st.caption("Search uploaded annual reports, inspect PDF page evidence, and calculate ratios from verified figures.")

with st.sidebar:
    st.header("Reports")
    uploads = st.file_uploader("Text-based annual report PDFs", type="pdf", accept_multiple_files=True)
    report_specs = []
    for i, upload in enumerate(uploads or []):
        st.markdown(f"**{upload.name}**")
        company = st.text_input("Company", key=f"company_{i}_{upload.name}")
        year = st.text_input("Fiscal year (e.g. FY2025)", key=f"year_{i}_{upload.name}")
        report_specs.append((upload, company, year))
    if st.button("Index reports", type="primary"):
        if not report_specs:
            st.error("Upload at least one report.")
        elif len({u.name for u, _, _ in report_specs}) != len(report_specs):
            st.error("Each uploaded PDF needs a distinct filename.")
        elif any(not c.strip() or not y.strip() for _, c, y in report_specs):
            st.error("Enter a company and fiscal year for every report.")
        elif any(u.size > 25 * 1024 * 1024 for u, _, _ in report_specs):
            st.error("Each report must be 25 MB or smaller.")
        else:
            try:
                with st.spinner("Extracting pages and building retrieval indexes..."):
                    reports = [Report(u.name, c, y, u.getvalue()) for u, c, y in report_specs]
                    chunks = [chunk for report in reports for chunk in extract_chunks(report)]
                    index = RetrievalIndex(chunks)
                st.session_state.retrieval_index = index
                st.session_state.indexed_reports = [(r.filename, r.company, r.fiscal_year) for r in reports]
                st.success(f"Indexed {len(reports)} reports and {len(chunks)} page-aware passages.")
            except Exception as exc:
                st.error(f"Indexing failed: {exc}")
    if "retrieval_index" in st.session_state:
        st.caption(f"Indexed reports: {len(st.session_state.indexed_reports)}. Re-index after changing uploads or metadata.")

index = st.session_state.get("retrieval_index")
if index is None:
    st.info("Upload and index text-based annual reports to begin. Scanned pages require OCR and are not supported.")
    st.stop()

ask_tab, calc_tab = st.tabs(["Ask reports", "Verified calculations"])
with ask_tab:
    companies = sorted({c.company for c in index.chunks})
    years = sorted({c.fiscal_year for c in index.chunks})
    col1, col2, col3 = st.columns(3)
    with col1:
        company_filter = st.selectbox("Company filter", ["All", *companies])
    with col2:
        year_filter = st.selectbox("Fiscal year filter", ["All", *years])
    with col3:
        mode = st.selectbox("Retrieval", ["hybrid + rerank", "hybrid", "semantic"])
    with st.form("question_form"):
        question = st.text_input("Question", placeholder="What risks does the company discuss?")
        asked = st.form_submit_button("Find evidence and answer")
    if asked:
        if not question.strip():
            st.warning("Enter a question.")
        else:
            try:
                with st.spinner("Retrieving report passages..."):
                    evidence = index.search(
                        question, mode=mode, top_k=5,
                        company=None if company_filter == "All" else company_filter,
                        fiscal_year=None if year_filter == "All" else year_filter,
                    )
                st.session_state.last_evidence = evidence
                st.session_state.last_question = question
                api_key = os.getenv("GEMINI_API_KEY", "")
                if api_key and evidence:
                    with st.spinner("Generating cited answer..."):
                        st.session_state.last_answer = generate_answer(
                            question, evidence, api_key, os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
                        )
                elif not api_key:
                    st.session_state.last_answer = "Set GEMINI_API_KEY to generate an answer. Retrieved passages are available below."
                else:
                    st.session_state.last_answer = "No matching passages found. Try a different filter."
            except Exception as exc:
                st.error(f"Research failed: {exc}")
    if "last_answer" in st.session_state:
        st.subheader("Answer")
        st.markdown(st.session_state.last_answer)
        st.caption("Bracketed citations refer to the numbered passages below. Verify figures and claims in the original PDF.")
        for number, chunk in enumerate(st.session_state.get("last_evidence", []), start=1):
            with st.expander(f"[{number}] {chunk.document} · PDF p. {chunk.page} · {chunk.company} · {chunk.fiscal_year}"):
                st.write(chunk.text)

with calc_tab:
    st.write("Enter figures you have checked in the uploaded reports. The calculator does not extract or verify table values automatically.")
    metric = st.selectbox("Metric", ["Revenue growth", "Net profit margin", "Operating margin"])
    document_names = sorted({name for name, _, _ in st.session_state.indexed_reports})
    with st.form("calculation_form"):
        company = st.selectbox("Company", sorted({c for _, c, _ in st.session_state.indexed_reports}))
        year_a = st.text_input("Current fiscal year / margin fiscal year", placeholder="FY2025")
        year_b = st.text_input("Previous fiscal year", placeholder="FY2024") if metric == "Revenue growth" else year_a
        currency = st.text_input("Currency", value="INR")
        unit = st.text_input("Unit for both inputs", value="millions")
        basis = st.selectbox("Reporting basis", ["Consolidated", "Standalone"])
        first_label = "Current revenue" if metric == "Revenue growth" else ("Net profit" if metric == "Net profit margin" else "Operating profit")
        first_value = st.text_input(first_label)
        first_doc = st.selectbox(f"Source PDF for {first_label}", document_names, key="first_doc")
        first_page = st.number_input(f"PDF page for {first_label}", min_value=1, step=1)
        second_label = "Previous revenue" if metric == "Revenue growth" else "Revenue"
        second_value = st.text_input(second_label)
        second_doc = st.selectbox(f"Source PDF for {second_label}", document_names, key="second_doc")
        second_page = st.number_input(f"PDF page for {second_label}", min_value=1, step=1)
        calculated = st.form_submit_button("Calculate")
    if calculated:
        try:
            source_companies = {name: c for name, c, _ in st.session_state.indexed_reports}
            if source_companies[first_doc] != company or source_companies[second_doc] != company:
                raise ValueError("Both source PDFs must be tagged with the selected company")
            first = Figure(Decimal(first_value), company.strip(), year_a.strip(), currency.strip(),
                           unit.strip(), basis, first_doc, int(first_page))
            second = Figure(Decimal(second_value), company.strip(), year_b.strip(), currency.strip(),
                            unit.strip(), basis, second_doc, int(second_page))
            fn = {"Revenue growth": revenue_growth, "Net profit margin": net_profit_margin,
                  "Operating margin": operating_margin}[metric]
            result = fn(first, second)
            st.metric(result.label, f"{result.value:.2f}%")
            st.write(f"Formula with inputs: {result.formula}")
            st.write(f"Source 1: {result.sources[0]}; Source 2: {result.sources[1]}")
            st.warning("Check the entered values, period, units, reporting basis, and source pages against the PDFs.")
        except (InvalidOperation, ValueError) as exc:
            st.error(f"Cannot calculate: {exc}")
