import os
import re
from pathlib import Path
import pytest
from dotenv import load_dotenv

load_dotenv()

BASE_PROJETO = Path(os.getenv("BASE_PROJETO", r"E:\Projeto Deep Lore FR").strip().strip('"').rstrip("\\/"))
PASTA_ROMANCES = BASE_PROJETO / "01_romances_md"
PASTA_ANTOLOGIAS = BASE_PROJETO / "02_antologias_md"
PASTA_COMPENDIOS = BASE_PROJETO / "04_compendios_notebooklm"

MIN_PALAVRAS_OBRA = 3_000
MAX_PALAVRAS_NOTEBOOKLM = 450_000

# Se alguém rodar o pytest no GitHub (onde não existem os seus livros), estes testes são pulados automaticamente
pytestmark = pytest.mark.skipif(
    not PASTA_ROMANCES.exists(),
    reason="Pasta local do acervo não encontrada (validação apenas local).",
)


def listar_mds_acervo():
    return sorted(PASTA_ROMANCES.glob("*.md")) + sorted(PASTA_ANTOLOGIAS.glob("*.md"))


def test_nenhum_livro_vazio_ou_truncado():
    problemas = []
    for arq in listar_mds_acervo():
        palavras = len(arq.read_text(encoding="utf-8").split())
        if palavras < MIN_PALAVRAS_OBRA:
            problemas.append(f"{arq.name}: apenas {palavras} palavras")
    assert not problemas, "Arquivos com texto suspeito:\n" + "\n".join(problemas)


def test_todos_arquivos_possuem_cabecalho_yaml_valido():
    sem_yaml = []
    for arq in listar_mds_acervo():
        inicio = arq.read_text(encoding="utf-8")[:600]
        if not (inicio.startswith("---\n") and 'titulo: "' in inicio and 'edicao: "' in inicio):
            sem_yaml.append(arq.name)
    assert not sem_yaml, "Arquivos sem cabeçalho YAML válido:\n" + "\n".join(sem_yaml)


def test_sem_titulos_duplicados_no_acervo():
    vistos = {}
    duplicados = []
    for arq in listar_mds_acervo():
        inicio = arq.read_text(encoding="utf-8")[:600]
        m = re.search(r'^titulo:\s*"(.+)"$', inicio, re.MULTILINE)
        if m:
            titulo = m.group(1)
            if titulo in vistos:
                duplicados.append(f"{titulo} ({vistos[titulo]} e {arq.name})")
            vistos[titulo] = arq.name
    assert not duplicados, "Títulos duplicados encontrados:\n" + "\n".join(duplicados)


def test_compendios_respeitam_teto_do_notebooklm():
    if not PASTA_COMPENDIOS.exists() or not list(PASTA_COMPENDIOS.glob("*.md")):
        pytest.skip("Compêndios ainda não foram gerados pelo script 02.")
    acima_do_limite = []
    for arq in sorted(PASTA_COMPENDIOS.glob("*.md")):
        palavras = len(arq.read_text(encoding="utf-8").split())
        if palavras > MAX_PALAVRAS_NOTEBOOKLM:
            acima_do_limite.append(f"{arq.name}: {palavras:,} palavras")
    assert not acima_do_limite, "Compêndios acima da margem segura:\n" + "\n".join(acima_do_limite)