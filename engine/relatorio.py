"""Renderiza o lote persistido recebido do Spring; stdout contém apenas o PDF."""
import json
import sys
from html import escape

from playwright.sync_api import sync_playwright


def documento(lote):
    def texto(valor):
        return escape(str(valor if valor is not None else ""))

    vagas = bool(lote.get("vagas"))
    campos = ("cargo", "empresa", "localidade", "modalidade", "urlOrigem") if vagas else (
        "nome", "cidade", "telefone", "score_potencial", "url_maps")
    colunas = ("Cargo", "Empresa", "Localidade", "Modalidade", "Origem") if vagas else (
        "Empresa", "Cidade", "Contato", "Pontuação", "Origem")
    linhas = []
    for i, lead in enumerate(lote["leads"], 1):
        valores = [i, *(lead.get(campo) for campo in campos)]
        linhas.append("<tr>" + "".join(f"<td>{texto(v)}</td>" for v in valores) + "</tr>")
    titulo = texto(lote["titulo"])
    return f"""<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>{titulo}</title>
    <style>@page {{size:A4 landscape;margin:14mm}} body {{font:12px sans-serif;color:#21132b}}
    table {{border-collapse:collapse;width:100%;table-layout:fixed}} tr {{break-inside:avoid}}
    td,th {{text-align:left;border-bottom:1px solid #ccc;padding:6px;overflow-wrap:anywhere}}
    th:first-child {{width:4%}}</style><h1>{titulo}</h1>
    <p>UrWork · Relatório {texto(lote["id"])} · Execução {texto(lote["execucao"])}</p>
    <p>{texto(lote["nicho"])} · {texto(lote["regiao"])}</p>
    <p>Início da coleta: {texto(lote["inicio"])} · Geração: {texto(lote["geracao"])} (Brasília)</p>
    <p>{"Vagas coletadas" if vagas else "Leads coletados"}: {len(linhas)} de {texto(lote["meta"])}</p>
    <table><thead><tr><th>#</th>{''.join('<th>' + c + '</th>' for c in colunas)}</tr></thead><tbody>{''.join(linhas)}</tbody></table></html>"""


if __name__ == "__main__":
    conteudo = documento(json.load(sys.stdin))
    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        pagina = navegador.new_page(java_script_enabled=False, offline=True)
        pagina.set_content(conteudo)
        sys.stdout.buffer.write(pagina.pdf(prefer_css_page_size=True))
        navegador.close()
