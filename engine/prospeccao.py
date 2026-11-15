"""Varredura de nichos e regiões a partir de uma sessão de coleta já aberta."""

from .scraper import buscar_leads_google_maps


def coletar_lotes(page, nichos: dict, regioes: list, meta: int, historico: dict, verificador):
    """Entrega cada lote qualificado até atingir a meta ou esgotar a varredura."""
    total = 0
    while total < meta:
        total_anterior = total
        for nome, configuracao in nichos.items():
            for regiao in regioes:
                for termo in configuracao.get("termos", [nome]):
                    leads = buscar_leads_google_maps(
                        page=page,
                        nicho_nome=nome,
                        termo_busca=termo,
                        cidade=regiao,
                        limite_leads=min(35, meta - total),
                        historico=historico,
                        verificador=verificador,
                    )
                    if leads:
                        total += len(leads)
                        yield leads
                        if total >= meta:
                            return
        if total == total_anterior:
            return
