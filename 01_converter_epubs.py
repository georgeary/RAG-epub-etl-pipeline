import os
import re
import zipfile
import warnings
import unicodedata
from pathlib import Path
import pandas as pd
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
warnings.filterwarnings("ignore", category=UserWarning, module="ebooklib")

load_dotenv()

# ================= CONFIGURAÇÃO (lida do .env) =================
BASE_PROJETO = Path(os.getenv("BASE_PROJETO", r"E:\Projeto Deep Lore FR").strip().strip('"').rstrip("\\/"))
PASTA_ORIGEM_EPUBS = Path(os.getenv("PASTA_ORIGEM_EPUBS", "").strip().strip('"').rstrip("\\/"))
PLANILHA_OFICIAL = Path(
    os.getenv(
        "PLANILHA_OFICIAL",
        str(BASE_PROJETO / "00_indice_mestre" / "Colecao_Oficial_Forgotten_Realms_1987_2026.xlsx"),
    ).strip().strip('"')
)

PASTA_DESTINO_ROMANCES = BASE_PROJETO / "01_romances_md"
PASTA_DESTINO_ANTOLOGIAS = BASE_PROJETO / "02_antologias_md"
PASTA_INDICE = BASE_PROJETO / "00_indice_mestre"

TERMOS_IGNORAR = ["fans creation", "rise of the blade", "(full)", "(without", "russian"]
MIN_PALAVRAS_ALERTA = 1000
# ===============================================================


def texto_seguro(valor) -> str:
    return "" if pd.isna(valor) else str(valor).strip()


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    texto = texto.lower()
    for errado, certo in [
        ("wywern", "wyvern"),
        ("vantity", "vanity"),
        ("fistanadantilus", "fistandantilus"),
        ("sword play", "swordplay"),
        ("baldur gate", "baldur s gate"),
    ]:
        texto = texto.replace(errado, certo)
    texto = re.sub(r"\bcloak of shadow\b", "cloak of shadows", texto)
    texto = re.sub(r"^.*?\bbook\s*\d+\s*-\s*", "", texto)
    texto = re.sub(r"\s*-\s*forgotten realms$", "", texto)
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def slugify(texto: str, max_len: int = 50) -> str:
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-")
    return texto[:max_len]


def chave_ordem_natural(texto: str):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", texto)]


def extrair_texto_html(html_bytes: bytes) -> str:
    soup = BeautifulSoup(html_bytes, "lxml")
    for tag in soup(["script", "style", "nav", "head"]):
        tag.decompose()

    # Camada 1: extração estrutural limpa (h1..h4, p, blockquote)
    blocos = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "blockquote"]):
        txt = re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()
        if not txt:
            continue
        if el.name == "h1":
            blocos.append(f"# {txt}")
        elif el.name == "h2":
            blocos.append(f"## {txt}")
        elif el.name in ("h3", "h4"):
            blocos.append(f"### {txt}")
        elif el.name == "blockquote":
            blocos.append(f"> {txt}")
        else:
            blocos.append(txt)

    texto_estrutural = "\n\n".join(blocos)

    # Camada 2: fallback para EPUBs antigos que usam <div>, <br> ou texto direto no <body>
    alvo = soup.body if soup.body else soup
    texto_bruto = alvo.get_text("\n", strip=True)
    if len(texto_estrutural.split()) < len(texto_bruto.split()) * 0.5:
        linhas = [re.sub(r"[ \t]+", " ", ln).strip() for ln in texto_bruto.splitlines()]
        linhas = [ln for ln in linhas if ln]
        return "\n\n".join(linhas)

    return texto_estrutural


def extrair_via_zip_direto(caminho_epub: Path) -> str:
    # Camada 3: lê os arquivos HTML/XHTML direto de dentro do pacote .epub (ZIP)
    partes = []
    with zipfile.ZipFile(str(caminho_epub), "r") as zf:
        nomes = sorted(zf.namelist(), key=chave_ordem_natural)
        for nome in nomes:
            low = nome.lower()
            if not low.endswith((".xhtml", ".html", ".htm")):
                continue
            base = Path(low).name
            if base in ("nav.xhtml", "nav.html", "toc.xhtml", "toc.html"):
                continue
            try:
                conteudo = zf.read(nome)
                txt = extrair_texto_html(conteudo)
                if txt.strip():
                    partes.append(txt)
            except Exception:
                continue
    return "\n\n".join(partes)


def extrair_markdown_epub(caminho_epub: Path) -> str:
    partes = []
    try:
        livro = epub.read_epub(str(caminho_epub), options={"ignore_ncx": True})
        itens = []
        for item_id, _ in livro.spine:
            item = livro.get_item_with_id(item_id)
            if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
                itens.append(item)
        if not itens:
            itens = list(livro.get_items_of_type(ebooklib.ITEM_DOCUMENT))

        for item in itens:
            txt = extrair_texto_html(item.get_content())
            if txt.strip():
                partes.append(txt)
    except Exception:
        partes = []

    texto_final = "\n\n".join(partes)

    # Se o ebooklib retornou pouco ou nenhum texto (spine quebrada ou media-type fora do padrão), usa Camada 3
    if len(texto_final.split()) < MIN_PALAVRAS_ALERTA:
        texto_zip = extrair_via_zip_direto(caminho_epub)
        if len(texto_zip.split()) > len(texto_final.split()):
            return texto_zip

    return texto_final


def carregar_catalogo():
    df_rom = pd.read_excel(PLANILHA_OFICIAL, sheet_name="Romances Oficiais (285)")
    df_ant = pd.read_excel(PLANILHA_OFICIAL, sheet_name="Antologias Oficiais (19)")

    df_rom = df_rom[pd.to_numeric(df_rom["Ano"], errors="coerce").notna()].dropna(subset=["Título Original"])
    df_ant = df_ant[pd.to_numeric(df_ant["Ano"], errors="coerce").notna()].dropna(subset=["Título Original"])

    mapa = {}
    todos_titulos = []

    aliases = {
        "cormyr a novel": ["cormyr"],
        "crucible the trial of cyric the mad": ["crucible", "the trial of cyric the mad"],
        "baldur s gate ii shadows of amn": ["the shadows of amn", "shadows of amn"],
        "baldur s gate ii throne of bhaal": ["throne of bhaal"],
        "the halls of stormweather": ["halls of stormweather"],
        "brimstone angels lesser evils": ["lesser evils"],
        "shadowbane eye of justice": ["eye of justice"],
        "unbroken chain the darker road": ["the darker road"],
        "honor among thieves the druid s call": ["the druid s call", "druid s call"],
        "honor among thieves the road to neverwinter": ["the road to neverwinter", "road to neverwinter"],
        "the fallbacks bound for ruin": ["bound for ruin"],
        "the fallbacks dealing with dragons": ["dealing with dragons"],
        "baldur s gate 3 astarion": ["astarion"],
        "the best of the realms": ["the best of the realms i", "best of the realms i", "best of the realms 1"],
        "realms of the dragons": ["realms of the dragons i", "realms of the dragons 1"],
        "the best of the realms ii the stories of ed greenwood": ["the best of the realms ii", "best of the realms ii", "best of the realms 2"],
        "the best of the realms iii the stories of elaine cunningham": ["the best of the realms iii", "best of the realms iii", "best of the realms 3"],
        "the collected stories the legend of drizzt anthology": ["the legend of drizzt", "the collected stories"],
    }

    def registrar(k, meta):
        mapa[k] = meta
        for al in aliases.get(k, []):
            mapa[al] = meta

    for _, r in df_rom.iterrows():
        k = normalizar(r["Título Original"])
        meta = {
            "titulo": texto_seguro(r["Título Original"]),
            "autor": texto_seguro(r["Autor(es)"]),
            "ano": int(float(r["Ano"])),
            "edicao": texto_seguro(r["Edição de RPG"]),
            "saga": texto_seguro(r["Saga Principal"]),
            "volume": texto_seguro(r["Volume / Posição"]),
            "secundaria": texto_seguro(r["Série Secundária / Evento"]),
            "tipo": "romance",
        }
        registrar(k, meta)
        todos_titulos.append(("Romance", meta["ano"], meta["titulo"], meta["saga"]))

    for _, r in df_ant.iterrows():
        k = normalizar(r["Título Original"])
        meta = {
            "titulo": texto_seguro(r["Título Original"]),
            "autor": texto_seguro(r["Autor(es) / Organizador"]),
            "ano": int(float(r["Ano"])),
            "edicao": texto_seguro(r["Edição de RPG"]),
            "saga": texto_seguro(r["Linha / Coleção"]),
            "volume": texto_seguro(r["Volume"]),
            "secundaria": "",
            "tipo": "antologia",
        }
        registrar(k, meta)
        todos_titulos.append(("Antologia", meta["ano"], meta["titulo"], meta["saga"]))

    chaves_ordenadas = sorted(mapa.keys(), key=len, reverse=True)
    return mapa, chaves_ordenadas, todos_titulos


def buscar_metadado(stem_norm: str, mapa: dict, chaves_ordenadas: list):
    if stem_norm in mapa:
        return mapa[stem_norm]
    for chave in chaves_ordenadas:
        if len(chave) < 4:
            continue
        if re.search(rf"\b{re.escape(chave)}\b", stem_norm):
            return mapa[chave]
    return None


def gerar_cabecalho(meta: dict, palavras: int) -> str:
    return (
        "---\n"
        f'titulo: "{meta["titulo"]}"\n'
        f'autor: "{meta["autor"]}"\n'
        f'tipo: "{meta["tipo"]}"\n'
        f'edicao: "{meta["edicao"]}"\n'
        f'ano_publicacao: {meta["ano"]}\n'
        f'saga: "{meta["saga"]}"\n'
        f'volume: "{meta["volume"]}"\n'
        f'serie_secundaria: "{meta["secundaria"]}"\n'
        f'palavras_aprox: {palavras}\n'
        "---\n\n"
        f"# {meta['titulo']} ({meta['ano']})\n\n"
    )


def main():
    if not str(PASTA_ORIGEM_EPUBS) or not PASTA_ORIGEM_EPUBS.exists():
        print(f"[ERRO] Pasta de origem não encontrada: {PASTA_ORIGEM_EPUBS}")
        print("Confira o caminho em PASTA_ORIGEM_EPUBS dentro do arquivo .env")
        return

    if not PLANILHA_OFICIAL.exists():
        print(f"[ERRO] Planilha oficial não encontrada em: {PLANILHA_OFICIAL}")
        print("Copie Colecao_Oficial_Forgotten_Realms_1987_2026.xlsx para 00_indice_mestre")
        return

    PASTA_DESTINO_ROMANCES.mkdir(parents=True, exist_ok=True)
    PASTA_DESTINO_ANTOLOGIAS.mkdir(parents=True, exist_ok=True)
    PASTA_INDICE.mkdir(parents=True, exist_ok=True)

    mapa, chaves_ordenadas, todos_titulos = carregar_catalogo()
    convertidos = set()
    registros_csv = []
    nao_mapeados = []
    erros = []
    suspeitos = []
    partes_cold_steel = []

    epubs = sorted(PASTA_ORIGEM_EPUBS.rglob("*.epub"))
    print(f"Total de arquivos .epub encontrados: {len(epubs)}")

    for epub_path in epubs:
        caminho_lower = str(epub_path).lower()
        if any(t in caminho_lower for t in TERMOS_IGNORAR):
            continue

        if "cold steel and secrets" in caminho_lower:
            partes_cold_steel.append(epub_path)
            continue

        chave_arq = normalizar(epub_path.stem)
        meta = buscar_metadado(chave_arq, mapa, chaves_ordenadas)

        if not meta:
            nao_mapeados.append(str(epub_path))
            continue

        titulo_id = meta["titulo"]
        if titulo_id in convertidos:
            continue

        try:
            corpo_md = extrair_markdown_epub(epub_path)
            palavras = len(corpo_md.split())
            nome_saida = f"{meta['ano']}_{slugify(meta['edicao'], 15)}_{slugify(meta['saga'], 25)}_{slugify(meta['titulo'], 40)}.md"
            pasta_out = PASTA_DESTINO_ROMANCES if meta["tipo"] == "romance" else PASTA_DESTINO_ANTOLOGIAS
            arq_out = pasta_out / nome_saida

            arq_out.write_text(gerar_cabecalho(meta, palavras) + corpo_md, encoding="utf-8")
            registros_csv.append({**meta, "arquivo_md": str(arq_out), "palavras": palavras})
            convertidos.add(titulo_id)

            if palavras < MIN_PALAVRAS_ALERTA:
                suspeitos.append(f"{meta['titulo']} ({palavras} palavras) -> {epub_path}")
                print(f"[ALERTA - POUCO TEXTO] {meta['titulo']} ({palavras:,} palavras)")
            else:
                print(f"[OK] {meta['titulo']} ({palavras:,} palavras)")
        except Exception as e:
            erros.append(f"{epub_path} -> {e}")

    if partes_cold_steel and "cold steel and secrets" in mapa:
        meta = mapa["cold steel and secrets"]
        try:
            secoes = []
            for parte in sorted(partes_cold_steel):
                secoes.append(f"## {parte.stem}\n\n" + extrair_markdown_epub(parte))
            corpo_md = "\n\n---\n\n".join(secoes)
            palavras = len(corpo_md.split())
            nome_saida = f"{meta['ano']}_{slugify(meta['edicao'], 15)}_{slugify(meta['saga'], 25)}_{slugify(meta['titulo'], 40)}.md"
            arq_out = PASTA_DESTINO_ROMANCES / nome_saida
            arq_out.write_text(gerar_cabecalho(meta, palavras) + corpo_md, encoding="utf-8")
            registros_csv.append({**meta, "arquivo_md": str(arq_out), "palavras": palavras})
            convertidos.add(meta["titulo"])
            if palavras < MIN_PALAVRAS_ALERTA:
                suspeitos.append(f"{meta['titulo']} ({palavras} palavras) -> Cold Steel and Secrets")
                print(f"[ALERTA - POUCO TEXTO] {meta['titulo']} ({palavras:,} palavras)")
            else:
                print(f"[OK] {meta['titulo']} ({len(partes_cold_steel)} partes | {palavras:,} palavras)")
        except Exception as e:
            erros.append(f"Cold Steel and Secrets -> {e}")

    faltantes = [
        f"[{tipo}] {ano} | {titulo} ({saga})"
        for tipo, ano, titulo, saga in todos_titulos
        if titulo not in convertidos
    ]

    pd.DataFrame(registros_csv).to_csv(PASTA_INDICE / "catalogo_romances_convertidos.csv", index=False, encoding="utf-8-sig")
    (PASTA_INDICE / "epubs_nao_mapeados.txt").write_text("\n".join(nao_mapeados), encoding="utf-8")
    (PASTA_INDICE / "epubs_com_erro.txt").write_text("\n".join(erros), encoding="utf-8")
    (PASTA_INDICE / "epubs_texto_suspeito.txt").write_text("\n".join(suspeitos), encoding="utf-8")
    (PASTA_INDICE / "relatorio_faltantes_conversao.txt").write_text("\n".join(faltantes), encoding="utf-8")

    print("\n================ RESUMO ================")
    print(f"Obras únicas convertidas para .md: {len(convertidos)} / {len(todos_titulos)}")
    print(f"Faltando converter (ver relatorio_faltantes_conversao.txt): {len(faltantes)}")
    print(f"EPUBs não reconhecidos (ver epubs_nao_mapeados.txt): {len(nao_mapeados)}")
    print(f"Livros com menos de {MIN_PALAVRAS_ALERTA} palavras (ver epubs_texto_suspeito.txt): {len(suspeitos)}")
    print(f"Erros de leitura (ver epubs_com_erro.txt): {len(erros)}")


if __name__ == "__main__":
    main()