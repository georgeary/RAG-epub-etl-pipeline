import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_PROJETO = Path(os.getenv("BASE_PROJETO", r"E:\Projeto Deep Lore FR").strip().strip('"').rstrip("\\/"))
PASTA_ROMANCES = BASE_PROJETO / "01_romances_md"
PASTA_ANTOLOGIAS = BASE_PROJETO / "02_antologias_md"
PASTA_SAIDA = BASE_PROJETO / "04_compendios_notebooklm"
LIMITE_PALAVRAS = 380_000


def empacotar(pasta_origem: Path, prefixo: str):
    arquivos = sorted(pasta_origem.glob("*.md"))
    if not arquivos:
        print(f"[AVISO] Nenhum arquivo .md encontrado em {pasta_origem}")
        return

    lote_atual = []
    palavras_lote = 0
    indice_lote = 1

    def salvar_lote():
        nonlocal indice_lote, lote_atual, palavras_lote
        if not lote_atual:
            return
        primeiro_ano = lote_atual[0][0][:4]
        ultimo_ano = lote_atual[-1][0][:4]
        nome = f"[{prefixo}]_Compendio_{indice_lote:02d}_{primeiro_ano}-{ultimo_ano}.md"
        conteudo = "\n\n============================================================\n\n".join(
            txt for _, txt in lote_atual
        )
        (PASTA_SAIDA / nome).write_text(conteudo, encoding="utf-8")
        print(f"[GERADO] {nome} -> {len(lote_atual)} obras | {palavras_lote:,} palavras")
        indice_lote += 1
        lote_atual = []
        palavras_lote = 0

    for arq in arquivos:
        texto = arq.read_text(encoding="utf-8")
        qtd = len(texto.split())
        if lote_atual and (palavras_lote + qtd) > LIMITE_PALAVRAS:
            salvar_lote()
        lote_atual.append((arq.name, texto))
        palavras_lote += qtd

    salvar_lote()


if __name__ == "__main__":
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    print("Empacotando Romances...")
    empacotar(PASTA_ROMANCES, "ROM")
    print("\nEmpacotando Antologias...")
    empacotar(PASTA_ANTOLOGIAS, "ANT")
    print(f"\nConcluído! Arquivos prontos em: {PASTA_SAIDA}")