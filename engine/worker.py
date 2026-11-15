"""Contrato local do Spring: um pedido JSON no stdin, eventos JSONL no stdout."""
import json
import sys
from contextlib import redirect_stdout

from playwright.sync_api import sync_playwright
from .config import VERIFICACAO, gerar_config_nicho
from .prospeccao import coletar_lotes
from .verifier import VerificadorPresencaDigital


def executar(pedido, emitir):
    nicho, regiao, meta = pedido["nicho"], pedido["regiao"], pedido["meta"]
    if not all(isinstance(s, str) and s.strip() for s in (nicho, regiao)):
        raise ValueError("Nicho e região obrigatórios")
    if type(meta) is not int or meta < 1:
        raise ValueError("Meta inválida")

    total = 0
    emitir({"tipo": "inicio", "meta": meta})
    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        contexto = navegador.new_context(locale="pt-BR")
        verificador = VerificadorPresencaDigital(contexto, config=VERIFICACAO)
        nichos = {nicho: gerar_config_nicho(nicho)}
        for lote in coletar_lotes(contexto.new_page(), nichos, [regiao], meta, {}, verificador):
            for lead in lote:
                total += 1
                emitir({"tipo": "lead", "total": total, "lead": lead})
        navegador.close()
    emitir({"tipo": "fim", "total": total})


def main():
    saida = sys.stdout

    def emitir(evento):
        print(json.dumps(evento, ensure_ascii=False, allow_nan=False), file=saida, flush=True)

    try:
        with redirect_stdout(sys.stderr):
            executar(json.load(sys.stdin), emitir)
    except Exception as erro:
        print(type(erro).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
