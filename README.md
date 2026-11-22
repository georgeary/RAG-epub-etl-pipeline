# EPUB-to-Markdown ETL Pipeline for RAG & NotebookLM

> 🇧🇷 [Leia esta documentação em Português](README-Pt-Br.md)

Automated Python ETL pipeline for ingesting, normalizing, auditing, and chunking large `.epub` literary collections into structured `.md` knowledge bases ready for **RAG** architectures, **MCP** agents, and **NotebookLM**.

## Pipeline Architecture

```text
Raw EPUBs (heterogeneous subfolders)
  │
  ▼ [01_converter_epubs.py]
Unicode/Regex Normalization + Deduplication + Catalog Enrichment (.xlsx)
  │  └── 3-Tier Resilient Extraction (Structured → Fallback DOM → Direct ZIP)
  ▼
Clean Markdown Files (.md) with YAML Frontmatter + Audit Reports
  │
  ▼ [02_gerar_compendios_notebooklm.py]
Chunked Compendiums (380k-word safe ceiling per file, without splitting books)
  │
  ▼ [pytest]
Automated Validation (Unit Tests + Corpus Integrity Audit)
```

## Technical Highlights

* **3-Tier Resilient Text Extraction:** handles modern EPUBs (`<p>`, `<h1>..<h4>`, `<blockquote>`), legacy EPUBs lacking semantic tags (`<div>`/`<br>`), and files with broken spines via direct ZIP archive parsing.
* **Structured Metadata Enrichment:** cross-references each title against a master Excel catalog, injecting YAML frontmatter (`titulo`, `autor`, `tipo`, `edicao`, `ano_publicacao`, `saga`, `volume`) at the top of every Markdown file.
* **Decoupled Configuration:** isolates local file paths via `.env` (`python-dotenv`), keeping the repository clean and portable.
* **Quality Assurance with `pytest` & CI (GitHub Actions):** unit tests covering normalization, legacy HTML parsing, ZIP fallback, and defensive spreadsheet loading, plus automated integrity checks against empty files, duplicates, and word-count ceilings.

## How to Run

```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure local paths
copy .env.example .env
# Edit .env to point to your local directories

# 4. Run the ETL pipeline
python 01_converter_epubs.py
python 02_gerar_compendios_notebooklm.py

# 5. Run the automated test suite
pytest -v
```