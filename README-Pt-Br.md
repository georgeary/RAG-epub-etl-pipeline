# EPUB-to-Markdown ETL Pipeline for RAG & NotebookLM

> 🇺🇸 [Read this documentation in English](README.md)

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
```

## Destaques Técnicos

* **Extração resiliente em 3 camadas:** trata EPUBs modernos (`<p>`, `<h1>..<h4>`, `<blockquote>`), EPUBs legados sem tags semânticas (`<div>`/`<br>`) e arquivos com `spine` corrompida via leitura direta do pacote ZIP.
* **Enriquecimento com metadados estruturados:** cruza cada obra com um catálogo mestre em Excel, injetando cabeçalho YAML (`titulo`, `autor`, `tipo`, `edicao`, `ano_publicacao`, `saga`, `volume`) no topo de cada Markdown.
* **Configuração desacoplada:** caminhos locais isolados via `.env` (`python-dotenv`), mantendo o repositório limpo e portável.
* **Qualidade garantida com `pytest` e CI (GitHub Actions):** testes unitários cobrindo normalização, parsing de HTML legado, fallback via ZIP e leitura defensiva de planilhas, além de auditoria automatizada contra arquivos vazios, duplicatas e estouro de limite de palavras.

## Como Executar

```bash
# 1. Criar e ativar ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar caminhos locais
copy .env.example .env
# Edite o .env apontando para seus diretórios locais

# 4. Executar o pipeline
python 01_converter_epubs.py
python 02_gerar_compendios_notebooklm.py

# 5. Rodar os testes automatizados
pytest -v
```