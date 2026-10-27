"""
Módulo para exportação de leads enriquecidos para Excel (.xlsx) e Relatório Executivo (.pdf)
com layout profissional, hyperlinks, KPIs e formatação executiva.
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

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
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
    Calcula uma porcentagem de potencial de venda (0 a 100%)
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

def gerar_pdf_leads(leads: list, id_planilha: str, caminho_pdf: str, page: Page = None):
    """
    Gera um PDF executivo no estilo Ultra-Wide Horizontal (semelhante ao Excel),
    contendo todas as 16 colunas completas da planilha.
    """
    linhas_tabela = ""
    for idx, lead in enumerate(leads, 1):
        score = lead.get("score_potencial", 0)
        badge_bg = "#dcfce7" if score >= 85 else "#fef9c3"
        badge_txt = "#15803d" if score >= 85 else "#854d0e"
        prioridade = "ALTA" if score >= 85 else "MÉDIA"
        lead_id = lead.get("id_lead", f"LEAD-{id_planilha}-{idx:03d}")
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
        <title>Relatório de Leads Qualificados - ID {id_planilha}</title>
        <style>
            @page {{
                size: 520mm 297mm; /* Canvas Ultra-Wide no estilo Planilha Excel */
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
                <div class="title">RELATÓRIO DE LEADS QUALIFICADOS (ESTILO PLANILHA EXCEL)</div>
                <div class="subtitle">Investigação Profunda de Instagram, WhatsApp e Web | 100% Sem Site | Alta Prioridade</div>
            </div>
            <div class="badge-id">LOTE: {id_planilha}</div>
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
        try:
            page.set_content(html_content)
            page.pdf(
                path=caminho_pdf,
                width="520mm",
                height="297mm",
                print_background=True,
                margin={"top": "8mm", "bottom": "8mm", "left": "6mm", "right": "6mm"}
            )
            pdf_gerado = True
        except Exception:
            pdf_gerado = False

    if not pdf_gerado:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                p_page = browser.new_page()
                p_page.set_content(html_content)
                p_page.pdf(
                    path=caminho_pdf,
                    width="520mm",
                    height="297mm",
                    print_background=True,
                    margin={"top": "8mm", "bottom": "8mm", "left": "6mm", "right": "6mm"}
                )
                browser.close()
        except Exception as e:
            print(f"[!] Erro ao renderizar PDF: {e}")
            return

    print(f"[SUCESSO] Relatório PDF Ultra-Wide gerado com sucesso: {caminho_pdf}")

def salvar_planilha_excel(leads: list, id_planilha: str = None, page: Page = None) -> tuple[str, str, str]:
    """
    Gera a planilha formatada (.xlsx) e o relatório executivo (.pdf).
    Salva no diretório 'Planilhas' com ID único e data/hora no nome.
    Retorna (caminho_excel, caminho_pdf, id_planilha).
    """
    pasta_destino = garantir_pasta_planilhas()

    if not id_planilha:
        id_planilha = uuid.uuid4().hex[:6].upper()

    agora = datetime.now()
    timestamp_str = agora.strftime("%Y-%m-%d_%H-%M-%S")
    nome_arquivo = f"Leads_{timestamp_str}_ID-{id_planilha}.xlsx"
    caminho_completo = os.path.join(pasta_destino, nome_arquivo)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Leads ID {id_planilha}"

    colunas = [
        ("ID do Lead", 16),
        ("Score Potencial", 15),
        ("Prioridade", 12),
        ("Nome da Empresa", 32),
        ("Nicho / Categoria", 22),
        ("Região / Cidade", 20),
        ("Telefone", 18),
        ("É WhatsApp?", 14),
        ("Link WhatsApp", 18),
        ("Nome do Dono / Gerente", 24),
        ("Nota", 8),
        ("Total Avaliações", 16),
        ("Possui Site?", 14),
        ("Endereço", 35),
        ("Link Maps", 15),
        ("Melhor Abordagem (Copy Personalizada)", 60)
    ]

    cor_cabecalho = "1A365D"
    fonte_cabecalho = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    preenchimento_cabecalho = PatternFill(start_color=cor_cabecalho, end_color=cor_cabecalho, fill_type="solid")

    fonte_normal = Font(name="Segoe UI", size=10)
    fonte_bold = Font(name="Segoe UI", size=10, bold=True)
    fonte_link = Font(name="Segoe UI", size=10, color="2B6CB0", underline="single")

    fill_verde = PatternFill(start_color="C6F6D5", end_color="C6F6D5", fill_type="solid")
    fill_amarelo = PatternFill(start_color="FEFCBF", end_color="FEFCBF", fill_type="solid")
    fill_zebra = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")

    borda_fina = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    for col_idx, (titulo, largura) in enumerate(colunas, 1):
        cell = ws.cell(row=1, column=col_idx, value=titulo)
        cell.font = fonte_cabecalho
        cell.fill = preenchimento_cabecalho
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = largura

    ws.row_dimensions[1].height = 30

    leads_ordenados = sorted(leads, key=lambda x: x.get("score_potencial", 0), reverse=True)

    for row_idx, lead in enumerate(leads_ordenados, 2):
        score = lead.get("score_potencial", 0)
        prioridade = "ALTA" if score >= 85 else "MÉDIA"
        lead_id = f"LEAD-{id_planilha}-{str(row_idx - 1).zfill(3)}"
        lead["id_lead"] = lead_id

        tel = lead.get("telefone", "")
        num_zap = limpar_numero_whatsapp(tel)
        is_zap = "Sim (Provável)" if (len(num_zap) >= 12 and num_zap[4:5] in ["9", "8"]) else ("Sim" if tel else "Não")

        link_zap = f"https://wa.me/{num_zap}" if num_zap else ""
        tem_site_str = "Sim" if lead.get("tem_site", False) else "NÃO (Oportunidade)"

        linha_dados = [
            lead_id,
            f"{score}%",
            prioridade,
            lead.get("nome", "N/A"),
            lead.get("nicho", "N/A"),
            lead.get("cidade", "N/A"),
            tel if tel else "Não informado",
            is_zap,
            link_zap,
            lead.get("dono_gerente", "Consultar na Recepção / Secretária"),
            lead.get("nota", 0.0),
            lead.get("qtd_avaliacoes", 0),
            tem_site_str,
            lead.get("endereco", "N/A"),
            lead.get("url_maps", ""),
            lead.get("copy_abordagem", "")
        ]

        ws.row_dimensions[row_idx].height = 45

        for col_idx, valor in enumerate(linha_dados, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = fonte_normal
            cell.border = borda_fina
            cell.alignment = Alignment(vertical="center")

            if col_idx == 1:
                cell.value = valor
                cell.font = fonte_bold
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 2:
                cell.value = valor
                cell.font = fonte_bold
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if score >= 85:
                    cell.fill = fill_verde
                else:
                    cell.fill = fill_amarelo
            elif col_idx == 3:
                cell.value = valor
                cell.font = fonte_bold
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx in [7, 8, 11, 12, 13]:
                cell.value = valor
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if col_idx == 13 and not lead.get("tem_site", False):
                    cell.font = Font(name="Segoe UI", size=10, bold=True, color="C53030")
            elif col_idx == 9:
                if link_zap:
                    cell.value = "Abrir WhatsApp"
                    cell.hyperlink = link_zap
                    cell.font = fonte_link
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.value = "-"
                    cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 15:
                url_maps = lead.get("url_maps", "")
                if url_maps:
                    cell.value = "Ver no Maps"
                    cell.hyperlink = url_maps
                    cell.font = fonte_link
                    cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 16:
                cell.value = valor
                cell.alignment = Alignment(vertical="center", wrap_text=True)
            else:
                cell.value = valor
                if row_idx % 2 == 0:
                    cell.fill = fill_zebra

    wb.save(caminho_completo)
    print(f"\n[SUCESSO] Planilha Excel salva com sucesso: {caminho_completo}")

    # Gera PDF executivo correspondente
    nome_pdf = f"Leads_{timestamp_str}_ID-{id_planilha}.pdf"
    caminho_pdf = os.path.join(pasta_destino, nome_pdf)
    try:
        gerar_pdf_leads(leads_ordenados, id_planilha, caminho_pdf, page=page)
    except Exception as e:
        print(f"[!] Aviso: Falha ao gerar PDF ({e})")
        caminho_pdf = ""

    salvar_no_historico(leads_ordenados, id_planilha)

    return caminho_completo, caminho_pdf, id_planilha
