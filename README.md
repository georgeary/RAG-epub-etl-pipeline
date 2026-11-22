# EPUB-to-Markdown ETL Pipeline for RAG & NotebookLM

Pipeline automatizado em Python para ingestão, padronização, auditoria e empacotamento de grandes coleções literárias (`.epub`) em bases de conhecimento estruturadas (`.md`) prontas para arquiteturas **RAG**, agentes via **MCP** e **NotebookLM**.

## Arquitetura do Pipeline

```text
EPUBs Brutos (subpastas heterogêneas)
  │
  ▼ [01_converter_epubs.py]
Normalização Unicode/Regex + Deduplicação + Enriquecimento via Catálogo (.xlsx)
  │  └── Extração resiliente em 3 camadas (Estrutural → Fallback DOM → ZIP direto)
  ▼
Arquivos Markdown Limpos (.md) com YAML Frontmatter + Relatórios de Auditoria
  │
  ▼ [02_gerar_compendios_notebooklm.py]
Compêndios Chunked (teto seguro de 380k palavras/arquivo, sem quebra de obra)
  │
  ▼ [pytest]
Validação Automatizada (Testes Unitários + Auditoria de Integridade do Acervo)