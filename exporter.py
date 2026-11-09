"""
Módulo Unificado de Persistência, Histórico Anti-Duplicação e Exportação em PDF (.pdf).

Concentra em um único módulo:
  1. Gerenciamento de histórico e desduplicação (`Planilhas/historico_leads.json`),
     garantindo que leads já prospectados nunca sejam repetidos.
  2. Geração do Relatório Executivo em PDF (`.pdf`) com design editorial suave
     (Soft Slate & Pastel), contendo Visão Geral em Tabela + Fichas Individuais de Abordagem.
"""

import sys
import os
import re
import json
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

PASTA_PLANILHAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Planilhas")
ARQUIVO_HISTORICO = os.path.join(PASTA_PLANILHAS, "historico_leads.json")


# ======================================================================================
# 1. GERENCIAMENTO DE HISTÓRICO E DESDUPLICAÇÃO DE LEADS
# ======================================================================================

def garantir_pasta_planilhas() -> str:
    """Cria o diretório Planilhas se ainda não existir."""
    os.makedirs(PASTA_PLANILHAS, exist_ok=True)
    return PASTA_PLANILHAS


def normalizar_texto(texto: str) -> str:
    """Remove caracteres especiais e converte para minúsculas."""
    if not texto:
        return ""
    texto = texto.lower().strip()
    texto = re.sub(r"[^\w\s]", "", texto)
    return re.sub(r"\s+", " ", texto)


def extrair_apenas_digitos(telefone: str) -> str:
    """Extrai somente os números do telefone."""
    if not telefone:
        return ""
    digitos = re.sub(r"\D", "", str(telefone))
    if digitos.startswith("0"):
        digitos = digitos[1:]
    return digitos


def carregar_historico() -> dict:
    """Carrega o banco de dados de leads já coletados."""
    garantir_pasta_planilhas()
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Aviso ao carregar histórico: {e}. Criando novo.")

    return {
        "telefones": {},
        "nomes_cidade": {},
        "urls_maps": {},
        "total_coletados": 0,
    }


def lead_ja_existe(lead_ou_card: dict, historico: dict) -> tuple[bool, str]:
    """Verifica se o lead já foi coletado anteriormente por URL, telefone ou nome+cidade."""
    url = lead_ou_card.get("url_maps") or lead_ou_card.get("href")
    if url:
        url_base = url.split("?")[0]
        if url_base in historico.get("urls_maps", {}):
            return True, "URL do Google Maps já cadastrada"

    tel = lead_ou_card.get("telefone")
    if tel:
        digitos = extrair_apenas_digitos(tel)
        if digitos and digitos in historico.get("telefones", {}):
            nome_anterior = historico["telefones"][digitos].get("nome", "")
            return True, f"Telefone ({tel}) já cadastrado para '{nome_anterior}'"

    nome = lead_ou_card.get("nome")
    cidade = lead_ou_card.get("cidade", "")
    if nome:
        chave = f"{normalizar_texto(nome)}_{normalizar_texto(cidade)}"
        if chave in historico.get("nomes_cidade", {}):
            return True, f"Nome da empresa ('{nome}') já cadastrado nesta cidade"

    return False, ""


def registrar_lead_em_memoria(lead: dict, historico: dict) -> None:
    """Registra o lead no dicionário de histórico em memória durante a sessão atual."""
    tel_dig = extrair_apenas_digitos(lead.get("telefone", ""))
    if tel_dig:
        historico.setdefault("telefones", {})[tel_dig] = {"nome": lead.get("nome", "")}
    if lead.get("nome"):
        chave_nc = f"{normalizar_texto(lead['nome'])}_{normalizar_texto(lead.get('cidade', ''))}"
        historico.setdefault("nomes_cidade", {})[chave_nc] = {"nome": lead["nome"]}
    if lead.get("url_maps"):
        historico.setdefault("urls_maps", {})[lead["url_maps"].split("?")[0]] = {"nome": lead.get("nome", "")}


def salvar_no_historico(novos_leads: list, id_lote: str):
    """Atualiza o arquivo JSON de histórico com os novos leads qualificados."""
    historico = carregar_historico()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    adicionados = 0
    for lead in novos_leads:
        nome = lead.get("nome", "")
        cidade = lead.get("cidade", "")
        tel = lead.get("telefone", "")
        url = lead.get("url_maps", "")

        info_registro = {
            "nome": nome,
            "cidade": cidade,
            "data_coleta": agora,
            "id_lote": id_lote,
        }

        if tel:
            digitos = extrair_apenas_digitos(tel)
            if digitos:
                historico["telefones"][digitos] = info_registro

        if nome:
            chave = f"{normalizar_texto(nome)}_{normalizar_texto(cidade)}"
            historico["nomes_cidade"][chave] = info_registro

        if url:
            url_base = url.split("?")[0]
            historico["urls_maps"][url_base] = info_registro

        adicionados += 1

    historico["total_coletados"] = max(len(historico["telefones"]), len(historico["nomes_cidade"]))
    historico["ultima_atualizacao"] = agora

    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)

    print(f"[*] Histórico atualizado: {adicionados} novos leads registrados (Total no banco: {historico['total_coletados']}).")


# ======================================================================================
# 2. FORMATAÇÃO E EXPORTAÇÃO DE RELATÓRIO EXECUTIVO EM PDF (.PDF)
# ======================================================================================

def limpar_numero_whatsapp(telefone: str) -> str:
    """Extrai apenas dígitos e valida se tem formato com DDD + DDI 55."""
    if not telefone:
        return ""
    digitos = re.sub(r"\D", "", str(telefone))
    if digitos.startswith("0"):
        digitos = digitos[1:]
    if not digitos.startswith("55") and len(digitos) in [10, 11]:
        digitos = "55" + digitos
    return digitos


def formatar_telefone_exibicao(telefone: str) -> str:
    """Formata o telefone no padrão brasileiro (DD) 9XXXX-XXXX para leitura suave."""
    if not telefone:
        return "Não informado"
    digitos = re.sub(r"\D", "", str(telefone))
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    if digitos.startswith("0") and len(digitos) in (11, 12):
        digitos = digitos[1:]
    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
    return str(telefone)


def calcular_score_potencial(lead: dict) -> int:
    """Calcula uma porcentagem base de potencial de venda (0 a 100%)."""
    score = 0
    if not lead.get("tem_site", False):
        score += 40

    nota = float(lead.get("nota", 0.0) or 0.0)
    if nota >= 4.5:
        score += 15
    elif nota >= 4.0:
        score += 10

    qtd = int(lead.get("qtd_avaliacoes", 0) or 0)
    if qtd >= 50:
        score += 15
    elif qtd >= 10:
        score += 10
    elif qtd > 0:
        score += 5

    if lead.get("telefone"):
        score += 15

    nicho = str(lead.get("nicho", "")).lower()
    if any(k in nicho for k in ["plastica", "odonto", "restaurante", "advocacia", "hair", "beleza", "nail"]):
        score += 15
    else:
        score += 10

    return min(100, max(10, score))


def _estilo_prioridade(score: int, em_ascensao: bool = False) -> dict:
    """Retorna cores pastel suaves de acordo com o score de conversão."""
    if score >= 85:
        return {
            "label": "Prioridade Máxima" if em_ascensao else "Alta Prioridade",
            "bg": "#ECFDF5",
            "border": "#A7F3D0",
            "text": "#047857",
            "bar": "#10B981",
        }
    if score >= 70:
        return {
            "label": "Boa Oportunidade",
            "bg": "#EFF6FF",
            "border": "#BFDBFE",
            "text": "#1D4ED8",
            "bar": "#3B82F6",
        }
    return {
        "label": "Potencial Moderado",
        "bg": "#FFFBEB",
        "border": "#FDE68A",
        "text": "#B45309",
        "bar": "#F59E0B",
    }


def montar_html_relatorio(leads: list, id_lote: str, data_geracao: str = None) -> str:
    """Gera o HTML/CSS completo do relatório executivo com design suave e legível."""
    if not data_geracao:
        data_geracao = datetime.now().strftime("%d/%m/%Y às %H:%M")

    total_leads = len(leads)
    alta_prioridade = sum(1 for l in leads if l.get("score_potencial", 0) >= 85)
    notas_validas = [float(l.get("nota", 0.0)) for l in leads if l.get("nota", 0.0) > 0]
    media_nota = round(sum(notas_validas) / len(notas_validas), 1) if notas_validas else 0.0
    total_avaliacoes = sum(int(l.get("qtd_avaliacoes", 0)) for l in leads)
    regioes_unicas = sorted({str(l.get("cidade", "")).strip() for l in leads if l.get("cidade")})
    resumo_regioes = ", ".join(regioes_unicas[:3]) + (f" (+{len(regioes_unicas) - 3})" if len(regioes_unicas) > 3 else "")
    if not resumo_regioes:
        resumo_regioes = "DF & Entorno"

    linhas_resumo = ""
    cards_detalhados = ""

    for idx, lead in enumerate(leads, 1):
        score = int(lead.get("score_potencial", 0))
        em_ascensao = bool(lead.get("em_ascensao", False))
        prio = _estilo_prioridade(score, em_ascensao=em_ascensao)
        lead_id = html.escape(str(lead.get("id_lead", f"LEAD-{id_lote}-{idx:03d}")))
        nome = html.escape(str(lead.get("nome", "N/A")))
        nicho = html.escape(str(lead.get("nicho", "N/A")))
        cidade = html.escape(str(lead.get("cidade", "N/A")))
        tel_raw = str(lead.get("telefone", "") or "")
        tel_fmt = html.escape(formatar_telefone_exibicao(tel_raw))
        dono = html.escape(str(lead.get("dono_gerente", "Confirmar na abordagem")))
        endereco = html.escape(str(lead.get("endereco", "Endereço não informado")))
        url_maps = html.escape(str(lead.get("url_maps", "") or ""))
        url_insta = html.escape(str(lead.get("url_instagram", "") or ""))
        copy = html.escape(str(lead.get("copy_abordagem", "") or ""))
        nota = float(lead.get("nota", 0.0) or 0.0)
        qtd_av = int(lead.get("qtd_avaliacoes", 0) or 0)
        qtd_esc = int(lead.get("qtd_avaliacoes_escritas", 0) or 0)
        porte = html.escape(str(lead.get("porte_classificacao") or lead.get("perfil_lead") or "Oportunidade Digital"))

        num_zap = limpar_numero_whatsapp(lead.get("telefone_e164") or tel_raw)
        link_zap = lead.get("link_whatsapp") or (f"https://wa.me/{num_zap}" if num_zap else "")
        status_zap = lead.get("whatsapp_confirmado")
        if status_zap is True:
            zap_badge = '<span class="tag tag-zap">WhatsApp Verificado</span>'
        elif len(num_zap) >= 12 and num_zap[4:5] in ["9", "8"]:
            zap_badge = '<span class="tag tag-zap">WhatsApp Móvel</span>'
        elif tel_raw:
            zap_badge = '<span class="tag tag-neutral">Telefone Fixo</span>'
        else:
            zap_badge = '<span class="tag tag-muted">Sem Telefone</span>'

        insta_user = ""
        if isinstance(lead.get("instagram"), dict) and lead["instagram"].get("username"):
            insta_user = "@" + html.escape(str(lead["instagram"]["username"]))
        elif url_insta and "instagram.com/" in url_insta:
            partes = [p for p in url_insta.split("instagram.com/")[-1].split("/") if p]
            if partes:
                insta_user = "@" + html.escape(partes[0].split("?")[0])

        acoes_html = []
        if link_zap:
            acoes_html.append(f'<a class="btn-link btn-zap" href="{link_zap}">WhatsApp</a>')
        if url_insta:
            acoes_html.append(f'<a class="btn-link btn-insta" href="{url_insta}">{insta_user or "Instagram"}</a>')
        if url_maps:
            acoes_html.append(f'<a class="btn-link btn-maps" href="{url_maps}">Maps</a>')
        acoes_str = " ".join(acoes_html) if acoes_html else '<span class="muted">-</span>'

        obs_lista = lead.get("observacoes") or []
        obs_html = ""
        if obs_lista:
            itens_obs = " • ".join(html.escape(str(o)) for o in obs_lista[:3])
            obs_html = f'<div class="card-obs">💡 <strong>Insights da Triagem:</strong> {itens_obs}</div>'

        sub_av = f"{qtd_av} avaliações ({qtd_esc} escritas)" if qtd_esc else f"{qtd_av} avaliações"

        linhas_resumo += f"""
        <tr>
            <td class="col-idx">
                <span class="idx-num">{idx:02d}</span>
                <span class="idx-id">{lead_id}</span>
            </td>
            <td class="col-empresa">
                <div class="emp-nome">{nome}</div>
                <div class="emp-sub">{nicho} • {cidade}</div>
            </td>
            <td class="col-reputacao">
                <div class="rep-nota">★ {nota:.1f}</div>
                <div class="rep-qtd">{sub_av}</div>
            </td>
            <td class="col-contato">
                <div class="cnt-tel">{tel_fmt}</div>
                <div>{zap_badge}</div>
            </td>
            <td class="col-dono">
                <div class="dono-nome">{dono}</div>
                <div class="dono-sub">{porte}</div>
            </td>
            <td class="col-score">
                <div class="score-row">
                    <span class="score-val" style="color: {prio['text']};">{score}%</span>
                    <span class="badge-prio" style="background: {prio['bg']}; color: {prio['text']}; border-color: {prio['border']};">
                        {prio['label']}
                    </span>
                </div>
                <div class="score-track">
                    <div class="score-fill" style="width: {min(100, max(8, score))}%; background: {prio['bar']};"></div>
                </div>
            </td>
            <td class="col-acoes">
                <div class="acoes-wrap">{acoes_str}</div>
            </td>
        </tr>
        """

        cards_detalhados += f"""
        <div class="lead-card">
            <div class="card-top">
                <div class="card-title-group">
                    <div class="card-eyebrow">#{idx:02d} • {lead_id} • {nicho}</div>
                    <div class="card-title">{nome}</div>
                </div>
                <div class="card-badges">
                    <span class="badge-score" style="background: {prio['bg']}; color: {prio['text']}; border-color: {prio['border']};">
                        {score}% • {prio['label']}
                    </span>
                </div>
            </div>

            <div class="card-grid">
                <div class="info-item">
                    <span class="info-label">Telefone / WhatsApp</span>
                    <span class="info-val">{tel_fmt} {zap_badge}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Reputação no Google</span>
                    <span class="info-val">★ {nota:.1f} <span class="muted">({sub_av})</span></span>
                </div>
                <div class="info-item">
                    <span class="info-label">Decisor / Responsável</span>
                    <span class="info-val">{dono}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Presença Digital</span>
                    <span class="info-val status-sem-site">100% Sem Site • {porte}</span>
                </div>
                <div class="info-item info-full">
                    <span class="info-label">Localização ({cidade})</span>
                    <span class="info-val">{endereco}</span>
                </div>
            </div>

            {obs_html}

            <div class="copy-box">
                <div class="copy-label">Mensagem de Abordagem Sugerida</div>
                <div class="copy-text">{copy if copy else 'Abordagem personalizada disponível no contato.'}</div>
            </div>

            <div class="card-footer">
                <span class="footer-hint">Acesso rápido:</span>
                <div class="acoes-wrap">{acoes_str}</div>
            </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório de Leads Qualificados — Lote {id_lote}</title>
    <style>
        @page {{
            size: A4 landscape;
            margin: 12mm 14mm 14mm 14mm;
        }}
        * {{
            box-sizing: border-box;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
        body {{
            font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 0;
            color: #334155;
            background-color: #F8FAFC;
            font-size: 11px;
            line-height: 1.45;
        }}
        .report-header {{
            background: linear-gradient(135deg, #FFFFFF 0%, #F1F5F9 100%);
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 16px 22px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 14px;
        }}
        .brand-eyebrow {{
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #64748B;
            margin-bottom: 3px;
        }}
        .report-title {{
            font-size: 19px;
            font-weight: 700;
            color: #1E293B;
            margin: 0;
            letter-spacing: -0.01em;
        }}
        .report-subtitle {{
            font-size: 11.5px;
            color: #64748B;
            margin-top: 3px;
        }}
        .header-meta {{
            text-align: right;
        }}
        .lote-pill {{
            display: inline-block;
            background: #EEF2FF;
            color: #4338CA;
            border: 1px solid #C7D2FE;
            padding: 5px 12px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 600;
        }}
        .meta-date {{
            font-size: 10px;
            color: #94A3B8;
            margin-top: 5px;
        }}
        .kpi-row {{
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
        }}
        .kpi-card {{
            flex: 1;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 11px 14px;
        }}
        .kpi-label {{
            font-size: 10px;
            font-weight: 600;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .kpi-value {{
            font-size: 18px;
            font-weight: 700;
            color: #1E293B;
            margin-top: 3px;
        }}
        .kpi-sub {{
            font-size: 10px;
            color: #94A3B8;
            margin-top: 1px;
        }}
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin: 8px 2px 10px 2px;
        }}
        .section-title {{
            font-size: 13px;
            font-weight: 700;
            color: #1E293B;
        }}
        .section-hint {{
            font-size: 10.5px;
            color: #64748B;
        }}
        .table-card {{
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 18px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        thead {{
            display: table-header-group;
        }}
        th {{
            background: #F1F5F9;
            color: #475569;
            font-weight: 600;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #E2E8F0;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #F1F5F9;
            vertical-align: middle;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        tr:nth-child(even) {{
            background-color: #FAFBFD;
        }}
        tr {{
            page-break-inside: avoid;
        }}
        .col-idx {{ width: 108px; white-space: nowrap; }}
        .idx-num {{
            display: inline-block;
            background: #F1F5F9;
            color: #475569;
            font-weight: 700;
            font-size: 10px;
            padding: 2px 7px;
            border-radius: 6px;
            margin-right: 4px;
        }}
        .idx-id {{
            display: block;
            font-size: 9px;
            color: #94A3B8;
            margin-top: 3px;
            font-family: Consolas, monospace;
            white-space: nowrap;
        }}
        .col-empresa {{ width: 230px; }}
        .emp-nome {{
            font-weight: 600;
            font-size: 11.5px;
            color: #1E293B;
        }}
        .emp-sub {{
            font-size: 10px;
            color: #64748B;
            margin-top: 2px;
        }}
        .col-reputacao {{ width: 115px; }}
        .rep-nota {{
            font-weight: 700;
            color: #B45309;
            font-size: 11px;
        }}
        .rep-qtd {{
            font-size: 9.5px;
            color: #64748B;
        }}
        .col-contato {{ width: 135px; }}
        .cnt-tel {{
            font-weight: 600;
            color: #1E293B;
            font-size: 11px;
            margin-bottom: 3px;
            white-space: nowrap;
        }}
        .col-dono {{ width: 170px; }}
        .dono-nome {{
            font-weight: 500;
            color: #334155;
            font-size: 10.5px;
        }}
        .dono-sub {{
            font-size: 9.5px;
            color: #0D9488;
            margin-top: 2px;
        }}
        .col-score {{ width: 175px; }}
        .score-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 6px;
            margin-bottom: 5px;
        }}
        .score-val {{
            font-weight: 700;
            font-size: 12px;
        }}
        .badge-prio {{
            font-size: 9.5px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 999px;
            border: 1px solid transparent;
            white-space: nowrap;
        }}
        .score-track {{
            width: 100%;
            height: 5px;
            background: #F1F5F9;
            border-radius: 999px;
            overflow: hidden;
        }}
        .score-fill {{
            height: 100%;
            border-radius: 999px;
        }}
        .tag {{
            display: inline-block;
            font-size: 9px;
            font-weight: 600;
            padding: 1.5px 7px;
            border-radius: 999px;
        }}
        .tag-zap {{
            background: #ECFDF5;
            color: #047857;
            border: 1px solid #A7F3D0;
        }}
        .tag-neutral {{
            background: #F1F5F9;
            color: #475569;
            border: 1px solid #E2E8F0;
        }}
        .tag-muted {{
            background: #FEF2F2;
            color: #B91C1C;
        }}
        .acoes-wrap {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        }}
        .btn-link {{
            display: inline-block;
            text-decoration: none;
            font-size: 9.5px;
            font-weight: 600;
            padding: 3.5px 9px;
            border-radius: 6px;
            border: 1px solid transparent;
            white-space: nowrap;
        }}
        .btn-zap {{
            background: #ECFDF5;
            color: #047857;
            border-color: #A7F3D0;
        }}
        .btn-insta {{
            background: #FDF2F8;
            color: #BE185D;
            border-color: #FBCFE8;
        }}
        .btn-maps {{
            background: #EFF6FF;
            color: #1D4ED8;
            border-color: #BFDBFE;
        }}
        .muted {{ color: #94A3B8; }}
        .page-break {{
            page-break-before: always;
        }}
        .cards-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}
        .lead-card {{
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 10px 13px;
            page-break-inside: avoid;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .card-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 8px;
            border-bottom: 1px solid #F1F5F9;
            padding-bottom: 5px;
            margin-bottom: 6px;
        }}
        .card-eyebrow {{
            font-size: 9px;
            color: #64748B;
            font-weight: 600;
        }}
        .card-title {{
            font-size: 12px;
            font-weight: 700;
            color: #1E293B;
            margin-top: 1px;
        }}
        .badge-score {{
            font-size: 9.5px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 999px;
            border: 1px solid transparent;
            white-space: nowrap;
        }}
        .card-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4px 10px;
            margin-bottom: 6px;
        }}
        .info-item {{
            display: flex;
            flex-direction: column;
        }}
        .info-full {{
            grid-column: 1 / -1;
        }}
        .info-label {{
            font-size: 8.5px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #94A3B8;
        }}
        .info-val {{
            font-size: 10px;
            color: #334155;
            font-weight: 500;
            margin-top: 1px;
        }}
        .status-sem-site {{
            color: #0D9488;
            font-weight: 600;
        }}
        .card-obs {{
            background: #F8FAFC;
            border-left: 3px solid #818CF8;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 9px;
            color: #475569;
            margin-bottom: 6px;
        }}
        .copy-box {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 7px;
            padding: 6px 9px;
            margin-bottom: 6px;
        }}
        .copy-label {{
            font-size: 8.5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #64748B;
            margin-bottom: 2px;
        }}
        .copy-text {{
            font-size: 9.5px;
            color: #334155;
            line-height: 1.35;
        }}
        .card-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 5px;
            border-top: 1px dashed #E2E8F0;
        }}
        .footer-hint {{
            font-size: 9.5px;
            color: #94A3B8;
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <div>
            <div class="brand-eyebrow">Inteligência Comercial • Prospecção Qualificada</div>
            <h1 class="report-title">Relatório Executivo de Leads Qualificados</h1>
            <div class="report-subtitle">Estabelecimentos verificados sem site próprio, sistema de agendamento ou landing page</div>
        </div>
        <div class="header-meta">
            <div class="lote-pill">Lote #{html.escape(str(id_lote))}</div>
            <div class="meta-date">Gerado em {html.escape(data_geracao)}</div>
        </div>
    </div>

    <div class="kpi-row">
        <div class="kpi-card">
            <div class="kpi-label">Leads Qualificados</div>
            <div class="kpi-value">{total_leads}</div>
            <div class="kpi-sub">100% livres de duplicidade</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Alta Prioridade (85%+)</div>
            <div class="kpi-value" style="color: #047857;">{alta_prioridade}</div>
            <div class="kpi-sub">Maior propensão de fechamento</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Reputação Média</div>
            <div class="kpi-value" style="color: #B45309;">★ {media_nota}</div>
            <div class="kpi-sub">{total_avaliacoes} avaliações somadas</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Presença Digital</div>
            <div class="kpi-value" style="color: #0D9488;">100% Sem Site</div>
            <div class="kpi-sub">Verificado no Maps, Instagram e Web</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Abrangência</div>
            <div class="kpi-value" style="font-size: 14px; margin-top: 6px;">{html.escape(resumo_regioes)}</div>
            <div class="kpi-sub">Regiões prospectadas no lote</div>
        </div>
    </div>

    <div class="section-header">
        <div class="section-title">1. Visão Geral para Prospecção Rápida</div>
        <div class="section-hint">Ordenado por maior potencial de conversão • Clique nos botões para abrir o WhatsApp, Instagram ou Google Maps</div>
    </div>

    <div class="table-card">
        <table>
            <thead>
                <tr>
                    <th># / ID</th>
                    <th>Estabelecimento & Nicho</th>
                    <th>Reputação</th>
                    <th>Contato</th>
                    <th>Responsável & Perfil</th>
                    <th>Potencial de Conversão</th>
                    <th>Ações Rápidas</th>
                </tr>
            </thead>
            <tbody>
                {linhas_resumo}
            </tbody>
        </table>
    </div>

    <div class="page-break"></div>

    <div class="section-header">
        <div class="section-title">2. Fichas Detalhadas & Mensagens de Abordagem</div>
        <div class="section-hint">Dados completos de cada lead com sugestão de copy pronta para envio</div>
    </div>

    <div class="cards-container">
        {cards_detalhados}
    </div>
</body>
</html>"""


def gerar_pdf_leads(leads: list, id_lote: str, caminho_pdf: str, page: Page = None) -> bool:
    """Renderiza o relatório PDF em formato A4 Paisagem com cabeçalho/rodapé suaves."""
    html_content = montar_html_relatorio(leads, id_lote)
    footer_template = """
    <div style="width: 100%; font-family: 'Segoe UI', sans-serif; font-size: 8.5px; color: #94A3B8;
                padding: 0 14mm; display: flex; justify-content: space-between; align-items: center;">
        <span>Relatório de Prospecção Qualificada • Lote """ + html.escape(str(id_lote)) + """</span>
        <span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span>
    </div>
    """

    opcoes_pdf = {
        "path": caminho_pdf,
        "format": "A4",
        "landscape": True,
        "print_background": True,
        "display_header_footer": True,
        "header_template": "<div></div>",
        "footer_template": footer_template,
        "margin": {"top": "10mm", "bottom": "13mm", "left": "12mm", "right": "12mm"},
    }

    pdf_gerado = False
    if page:
        aba_pdf = None
        try:
            aba_pdf = page.context.new_page()
            aba_pdf.set_content(html_content, wait_until="domcontentloaded")
            aba_pdf.pdf(**opcoes_pdf)
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
                p_page.pdf(**opcoes_pdf)
                browser.close()
                pdf_gerado = True
        except Exception as e:
            print(f"[!] Erro ao renderizar PDF: {e}")
            return False

    print(f"\n[SUCESSO] Relatório PDF gerado com sucesso: {caminho_pdf}")
    return True


def salvar_relatorio_pdf(leads: list, id_lote: str = None, page: Page = None, pasta_destino: str = None) -> tuple[str, str]:
    """
    Ordena os leads por prioridade/potencial, gera exclusivamente o relatório em PDF (.pdf)
    e registra o lote no histórico de desduplicação.
    """
    if not leads:
        return "", ""

    pasta_saida = pasta_destino or garantir_pasta_planilhas()
    os.makedirs(pasta_saida, exist_ok=True)

    if not id_lote:
        id_lote = uuid.uuid4().hex[:6].upper()

    agora = datetime.now()
    timestamp_str = agora.strftime("%Y-%m-%d_%H-%M-%S")

    leads_ordenados = sorted(
        leads,
        key=lambda x: (
            1 if x.get("prioridade_maxima") else 0,
            int(x.get("score_potencial", 0)),
            float(x.get("nota", 0.0)),
        ),
        reverse=True,
    )
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
