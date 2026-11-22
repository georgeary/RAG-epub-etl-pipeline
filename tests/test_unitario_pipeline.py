import importlib.util
import zipfile
from pathlib import Path
import pandas as pd
import pytest

RAIZ_SCRIPTS = Path(__file__).resolve().parent.parent


def carregar_modulo(nome_arquivo: str, nome_modulo: str):
    """Importa scripts que começam com número (ex.: 01_converter_epubs.py)."""
    caminho = RAIZ_SCRIPTS / nome_arquivo
    spec = importlib.util.spec_from_file_location(nome_modulo, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


conv = carregar_modulo("01_converter_epubs.py", "converter_epubs")


# 1. Garante que variações de nomes sempre normalizam certo (sem duplicar letras)
@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("Book 02 - Cloak Of Shadow", "cloak of shadows"),
        ("Cloak of Shadows", "cloak of shadows"),
        ("Book 2 - The Wywern's Spur", "the wyvern s spur"),
        ("Book 3 - Vantity's Brood", "vanity s brood"),
        ("Book 1 - Sword Play", "swordplay"),
        ("Book 1 - Baldur Gate", "baldur s gate"),
    ],
)
def test_normalizar_corrige_variacoes_sem_duplicar_letras(entrada, esperado):
    assert conv.normalizar(entrada) == esperado


# 2. Garante que HTML padrão (<p>) e HTML antigo sem <p> (<div>/<br>) sejam extraídos
def test_extrair_texto_html_padrao_com_paragrafos():
    html = b"<html><body><h1>Chapter One</h1><p>Elminster walked into Shadowdale.</p></body></html>"
    resultado = conv.extrair_texto_html(html)
    assert "# Chapter One" in resultado
    assert "Elminster walked into Shadowdale." in resultado


def test_extrair_texto_html_legado_sem_tag_p():
    html = (
        b"<html><body>"
        b"<div>Drizzt drew Twinkle and Icingdeath.<br/>Guenhwyvar leaped from the mist.</div>"
        b"<div>They stood ready in the Underdark.</div>"
        b"</body></html>"
    )
    resultado = conv.extrair_texto_html(html)
    assert "Drizzt drew Twinkle" in resultado
    assert "Guenhwyvar leaped" in resultado
    assert len(resultado.split()) >= 15


# 3. Garante que o fallback direto via ZIP resgata texto quando a spine do EPUB falha
def test_extrair_markdown_epub_fallback_zip(tmp_path):
    epub_falso = tmp_path / "livro_legado.epub"
    texto_cap = " ".join(["Waterdeep"] * 1200)
    with zipfile.ZipFile(epub_falso, "w") as zf:
        zf.writestr("OEBPS/ch01.xhtml", f"<html><body><div>{texto_cap}</div></body></html>")

    resultado = conv.extrair_markdown_epub(epub_falso)
    assert len(resultado.split()) >= 1200


# 4. Garante que linhas em branco ou notas de rodapé (Ano=NaN) não quebram a leitura do Excel
def test_carregar_catalogo_ignora_linhas_vazias_e_rodape(tmp_path, monkeypatch):
    planilha_teste = tmp_path / "catalogo_teste.xlsx"

    df_rom = pd.DataFrame(
        [
            {
                "Título Original": "Homeland",
                "Autor(es)": "R. A. Salvatore",
                "Ano": 1990,
                "Edição de RPG": "AD&D 2ª Edição",
                "Saga Principal": "The Dark Elf Trilogy",
                "Volume / Posição": "Livro 1",
                "Série Secundária / Evento": "The Legend of Drizzt (#1)",
            },
            {
                "Título Original": None,
                "Autor(es)": None,
                "Ano": None,
                "Edição de RPG": None,
                "Saga Principal": None,
                "Volume / Posição": None,
                "Série Secundária / Evento": None,
            },
        ]
    )

    df_ant = pd.DataFrame(
        [
            {
                "Título Original": "Realms of Valor",
                "Autor(es) / Organizador": "Vários Autores",
                "Ano": 1993,
                "Edição de RPG": "AD&D 2ª Edição",
                "Linha / Coleção": "Série Realms of...",
                "Volume": "Vol. 1",
            },
            {
                "Título Original": "Nota de rodapé sem ano",
                "Autor(es) / Organizador": None,
                "Ano": None,
                "Edição de RPG": None,
                "Linha / Coleção": None,
                "Volume": None,
            },
        ]
    )

    with pd.ExcelWriter(planilha_teste, engine="openpyxl") as writer:
        df_rom.to_excel(writer, sheet_name="Romances Oficiais (285)", index=False)
        df_ant.to_excel(writer, sheet_name="Antologias Oficiais (19)", index=False)

    monkeypatch.setattr(conv, "PLANILHA_OFICIAL", planilha_teste)
    mapa, _, todos_titulos = conv.carregar_catalogo()

    assert "homeland" in mapa
    assert "realms of valor" in mapa
    assert len(todos_titulos) == 2