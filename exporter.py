"""
Módulo para exportação de leads qualificados em Relatório Executivo (.pdf),
com ordenação por potencial de conversão e registro automático no histórico.
"""

import sys
import os
import re
import html
import uuid
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.sync_api import sync_playwright, Page
from historico import garantir_pasta_planilhas, salvar_no_historico


def limpar_numero_whatsapp(telefone: str) -> str:
    """Extrai apenas dígitos e valida se tem formato com DDD."""
    if not telefone:
        return ""
    digitos = re.sub(r"\D", "", telefone)
    if digitos.startswith("0"):
        digitos = digitos[1:]
    if not digitos.startswith("55") and len(digitos) in [10, 11]:
        digitos = "55" + digitos
    return digitos


def calcular_score_potencial(lead: dict) -> int:
    """
    Calcula uma porcentagem de potencial de venda (0 a 100%).
    Critérios:
    - Sem site: +40 pontos (alta dor / necessidade imediata)
    - Nota >= 4.5: +15 pontos (empresa que preza pela reputação)
    - Nota entre 4.0 e 4.4: +10 pontos
    - Avaliações > 50: +15 pontos (alto fluxo de clientes e faturamento)
    - Avaliações entre 10 e 49: +10 pontos
    - Telefone válido/WhatsApp: +15 pontos (fácil contato)
    - Nicho alto ticket: +15 pontos
    """
    score = 0
    if not lead.get("tem_site", False):
        score += 40

    nota = lead.get("nota", 0.0)
    if nota >= 4.5:
        score += 15
    elif nota >= 4.0:
        score += 10

    qtd = lead.get("qtd_avaliacoes", 0)
    if qtd >= 50:
        score += 15
    elif qtd >= 10:
        score += 10
    elif qtd > 0:
        score += 5

    tel = lead.get("telefone", "")
    if tel:
        score += 15

    nicho = lead.get("nicho", "").lower()
    if any(k in nicho for k in ["plastica", "odonto", "restaurante", "advocacia", "hair", "beleza", "nail"]):
        score += 15
    else:
        score += 10

    return min(100, max(10, score))


def gerar_pdf_leads(leads: list, id_lote: str, caminho_pdf: str, page: Page = None) -> bool:
    """
    Renderiza o relatório PDF contendo todos os dados dos leads qualificados.
    Retorna True se o PDF foi gerado com sucesso.
    """
    linhas_tabela = ""
    for idx, lead in enumerate(leads, 1):
        score = lead.get("score_potencial", 0)
        badge_bg = "#dcfce7" if score >= 85 else "#fef9c3"
        badge_txt = "#15803d" if score >= 85 else "#854d0e"
        prioridade = "ALTA" if score >= 85 else "MÉDIA"
        lead_id = lead.get("id_lead", f"LEAD-{id_lote}-{idx:03d}")
        nome = html.escape(str(lead.get("nome", "N/A")))
        nicho = html.escape(str(lead.get("nicho", "N/A")))
        cidade = html.escape(str(lead.get("cidade", "N/A")))
        tel = html.escape(str(lead.get("telefone", "Não informado")))
        dono = html.escape(str(lead.get("dono_gerente", "Consultar na Recepção")))
        endereco = html.escape(str(lead.get("endereco", "N/A")))
        url_maps = lead.get("url_maps", "")
        copy = html.escape(str(lead.get("copy_abordagem", "")))

        num_zap = limpar_numero_whatsapp(lead.get("telefone", ""))
        link_zap = f"https://wa.me/{num_zap}" if num_zap else ""
        is_zap = "Sim (Provável)" if (len(num_zap) >= 12 and num_zap[4:5] in ["9", "8"]) else ("Sim" if tel else "Não")

        linhas_tabela += f"""
        <tr>
            <td style="text-align: center; font-weight: bold; white-space: nowrap;">{lead_id}</td>
            <td style="text-align: center; font-weight: bold; background: {badge_bg}; color: {badge_txt};">{score}%</td>
            <td style="text-align: center; font-weight: bold;">{prioridade}</td>
            <td style="font-weight: 600; color: #0f172a;">{nome}</td>
            <td style="color: #475569;">{nicho}</td>
            <td style="color: #475569;">{cidade}</td>
            <td style="text-align: center; font-weight: bold; color: #0f172a; white-space: nowrap;">{tel}</td>
            <td style="text-align: center;">{is_zap}</td>
            <td style="text-align: center;">
                {'<a href="' + link_zap + '" style="color: #0284c7; font-weight: bold; text-decoration: underline;">Abrir WhatsApp</a>' if link_zap else '-'}
            </td>
            <td style="color: #475569;">{dono}</td>
            <td style="text-align: center; white-space: nowrap;">{lead.get('nota', 0.0)} ⭐</td>
            <td style="text-align: center;">{lead.get('qtd_avaliacoes', 0)}</td>
            <td style="text-align: center; color: #dc2626; font-weight: bold; white-space: nowrap;">NÃO (Oportunidade)</td>
            <td style="font-size: 10px; color: #475569; line-height: 1.2;">{endereco}</td>
            <td style="text-align: center;">
                {'<a href="' + url_maps + '" style="color: #0284c7; text-decoration: underline;">Ver no Maps</a>' if url_maps else '-'}
            </td>
            <td style="font-size: 10px; color: #334155; line-height: 1.3;">{copy}</td>
        </tr>
        """

    total_leads = len(leads)
    alta_prioridade = sum(1 for l in leads if l.get("score_potencial", 0) >= 85)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Relatório de Leads Qualificados - ID {id_lote}</title>
        <style>
            @page {{
                size: 520mm 297mm;
                margin: 10mm 8mm;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                margin: 0;
                padding: 0;
                color: #0f172a;
                background: #ffffff;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 3px solid #1a365d;
                padding-bottom: 10px;
                margin-bottom: 14px;
            }}
            .title {{
                font-size: 22px;
                font-weight: 800;
                color: #1a365d;
            }}
            .subtitle {{
                font-size: 12px;
                color: #64748b;
                margin-top: 4px;
            }}
            .badge-id {{
                background: #1a365d;
                color: #ffffff;
                padding: 6px 14px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 700;
            }}
            .kpis {{
                display: flex;
                gap: 12px;
                margin-bottom: 14px;
            }}
            .kpi-card {{
                flex: 1;
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px;
                text-align: center;
            }}
            .kpi-num {{
                font-size: 18px;
                font-weight: 800;
                color: #1a365d;
            }}
            .kpi-label {{
                font-size: 10px;
                color: #64748b;
                text-transform: uppercase;
                margin-top: 2px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 11px;
                page-break-inside: auto;
            }}
            tr {{
                page-break-inside: avoid;
                page-break-after: auto;
            }}
            thead {{
                display: table-header-group;
            }}
            th {{
                background: #1a365d;
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                padding: 9px 6px;
                text-align: left;
                border: 1px solid #cbd5e1;
                white-space: nowrap;
            }}
            td {{
                padding: 7px 6px;
                border: 1px solid #cbd5e1;
                vertical-align: middle;
            }}
            tr:nth-child(even) {{
                background: #f8fafc;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <div class="title">RELATÓRIO EXECUTIVO DE LEADS QUALIFICADOS</div>
                <div class="subtitle">Investigação Profunda de Instagram, WhatsApp e Web | 100% Sem Site | Alta Prioridade</div>
            </div>
            <div class="badge-id">LOTE: {id_lote}</div>
        </div>

        <div class="kpis">
            <div class="kpi-card">
                <div class="kpi-num">{total_leads}</div>
                <div class="kpi-label">Total de Leads</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-num">100%</div>
                <div class="kpi-label">Sem Site / Cardápio Digital</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-num">{alta_prioridade}</div>
                <div class="kpi-label">Alta Prioridade (85%+)</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-num">DF & Valparaíso</div>
                <div class="kpi-label">Região Alvo</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 115px; text-align: center;">ID do Lead</th>
                    <th style="width: 60px; text-align: center;">Score</th>
                    <th style="width: 75px; text-align: center;">Prioridade</th>
                    <th style="width: 220px;">Nome da Empresa</th>
                    <th style="width: 140px;">Nicho</th>
                    <th style="width: 130px;">Cidade / Região</th>
                    <th style="width: 120px; text-align: center;">Telefone</th>
                    <th style="width: 80px; text-align: center;">WhatsApp?</th>
                    <th style="width: 115px; text-align: center;">Link WhatsApp</th>
                    <th style="width: 170px;">Dono / Gerente</th>
                    <th style="width: 65px; text-align: center;">Nota</th>
                    <th style="width: 75px; text-align: center;">Avaliações</th>
                    <th style="width: 120px; text-align: center;">Possui Site?</th>
                    <th style="width: 230px;">Endereço</th>
                    <th style="width: 95px; text-align: center;">Link Maps</th>
                    <th style="width: 330px;">Melhor Abordagem</th>
                </tr>
            </thead>
            <tbody>
                {linhas_tabela}
            </tbody>
        </table>
    </body>
    </html>
    """

    pdf_gerado = False
    if page:
        aba_pdf = None
        try:
            # Usa uma aba dedicada para não perder a página ativa do Google Maps nem falhar em modo non-headless
            aba_pdf = page.context.new_page()
            aba_pdf.set_content(html_content, wait_until="domcontentloaded")
            aba_pdf.pdf(
                path=caminho_pdf,
                width="520mm",
                height="297mm",
                print_background=True,
                margin={"top": "8mm", "bottom": "8mm", "left": "6mm", "right": "6mm"}
            )
            pdf_gerado = True
        except Exception:
            pdf_gerado = False
        finally:
            if aba_pdf:
                try:
                    aba_pdf.close()
                except Exception:
                    pass

    if not pdf_gerado:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                p_page = browser.new_page()
                p_page.set_content(html_content, wait_until="domcontentloaded")
                p_page.pdf(
                    path=caminho_pdf,
                    width="520mm",
                    height="297mm",
                    print_background=True,
                    margin={"top": "8mm", "bottom": "8mm", "left": "6mm", "right": "6mm"}
                )
                browser.close()
                pdf_gerado = True
        except Exception as e:
            print(f"[!] Erro ao renderizar PDF: {e}")
            return False

    print(f"\n[SUCESSO] Relatório PDF gerado com sucesso: {caminho_pdf}")
    return True


def salvar_relatorio_pdf(leads: list, id_lote: str = None, page: Page = None, pasta_destino: str = None) -> tuple[str, str]:
    """
    Ordena os leads por potencial, gera exclusivamente o relatório em PDF (.pdf)
    e registra o lote no histórico de desduplicação.
    Retorna (caminho_pdf, id_lote).
    """
    if not leads:
        return "", ""

    pasta_saida = pasta_destino or garantir_pasta_planilhas()
    os.makedirs(pasta_saida, exist_ok=True)

    if not id_lote:
        id_lote = uuid.uuid4().hex[:6].upper()

    agora = datetime.now()
    timestamp_str = agora.strftime("%Y-%m-%d_%H-%M-%S")

    leads_ordenados = sorted(leads, key=lambda x: x.get("score_potencial", 0), reverse=True)
    for idx, lead in enumerate(leads_ordenados, 1):
        lead["id_lead"] = f"LEAD-{id_lote}-{idx:03d}"

    nome_pdf = f"Leads_{timestamp_str}_ID-{id_lote}.pdf"
    caminho_pdf = os.path.join(pasta_saida, nome_pdf)

    sucesso = gerar_pdf_leads(leads_ordenados, id_lote, caminho_pdf, page=page)
    if not sucesso:
        return "", id_lote

    if pasta_destino is None:
        salvar_no_historico(leads_ordenados, id_lote)

    return caminho_pdf, id_lote
