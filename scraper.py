"""
Motor de Scraping do Google Maps usando Playwright.
Opera em arquitetura de 2 Fases (Item 5):
  - FASE 1 (Coleta Bruta Regional): Varre e coleta todos os estabelecimentos possíveis da região
    escolhida no Google Maps, extraindo ficha cadastral, métricas de avaliações escritas e links.
  - FASE 2 (Funil Eliminatório Sequencial em Lote): Submete o lote completo da região ao motor
    `executar_funil_sequencial` (Pandas + NumPy), eliminando candidatos critério por critério
    (1. Integridade/Não-Franquia -> 2. Mínimo 10 avaliações escritas -> 3. Estrelas >= 4.0 ou >10 av.
     -> 4. 100% Sem Site/Sistema/LP no Maps, Instagram e Web -> 5. WhatsApp validado no Maps ou
     Instagram -> 6. Priorização de Autônomos e Micro-empreendedores em ascensão).
"""

import random
import re
import sys
import time

# Evita erros de UnicodeEncodeError no Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from config import NICHOS, NICHOS_ATUAIS, FILTROS, VERIFICACAO, gerar_config_nicho
from exporter import (
    calcular_score_potencial,
    carregar_historico,
    lead_ja_existe,
    registrar_lead_em_memoria,
)
from qualifier import executar_funil_sequencial
from verifier import VerificadorPresencaDigital, ResultadoPresencaDigital


def extrair_dono_ou_gerente(page: Page) -> str:
    """Tenta identificar o nome do proprietário através de respostas de avaliações ou informações adicionais."""
    try:
        respostas = page.locator('text=/Resposta do propriet[aá]rio/i').all()
        for resp in respostas[:3]:
            parent = resp.locator('..').inner_text()
            match = re.search(
                r"(?:atenciosamente|abraço|grato|obrigado),?\s+(?:dr\.?|dra\.?)?\s*([A-ZÁÉÍÓÚÂÊÔÃÕ][a-zà-ú]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕ][a-zà-ú]+)?)",
                parent,
                re.IGNORECASE,
            )
            if match:
                return match.group(1).strip()
    except Exception:
        pass
    return "A confirmar na abordagem (Secretária/Recepção)"


def extrair_metricas_avaliacoes(page: Page, meta_escritas: int = 10) -> tuple[float, int, int, bool]:
    """
    Extrai (nota, qtd_avaliacoes_totais, qtd_avaliacoes_escritas, avaliacoes_ocultas_pela_rede).
    Abre a aba de Avaliações quando disponível e conta quantas avaliações possuem texto escrito real.
    """
    nota = 0.0
    qtd_avaliacoes = 0
    qtd_escritas = 0
    ocultas_pela_rede = False

    painel = page.locator('div[role="main"]').filter(has=page.locator('h1.DUwDvf')).last
    if painel.count() == 0:
        painel = page

    try:
        container_nota = painel.locator('div.F7nice').first
        if container_nota.count() > 0:
            texto_nota = container_nota.locator('span[aria-hidden="true"]').first.inner_text()
            nota = float(texto_nota.replace(",", ".").strip())

            txt_qtd = container_nota.inner_text()
            match_qtd = re.search(r'\((\d+[\.\d]*)\)', txt_qtd)
            if match_qtd:
                qtd_avaliacoes = int(match_qtd.group(1).replace(".", ""))

        if qtd_avaliacoes == 0:
            txt_painel = painel.inner_text()
            m_av = re.search(r'(\d+[\.\d]*)\s+avalia[çc][õo]es', txt_painel, re.IGNORECASE)
            if m_av:
                qtd_avaliacoes = int(m_av.group(1).replace(".", ""))
    except Exception:
        pass

    # Inspeciona a aba de Avaliações para contar avaliações escritas reais
    try:
        aba_avaliacoes = painel.locator('button[role="tab"]').filter(has_text=re.compile(r"Avalia[çc][õo]es|Reviews", re.I)).first
        if aba_avaliacoes.count() > 0 and aba_avaliacoes.is_visible():
            if 0 < qtd_avaliacoes < meta_escritas:
                return nota, qtd_avaliacoes, qtd_avaliacoes, False

            aba_avaliacoes.click(timeout=3000)
            time.sleep(1.2)

            for _ in range(4):
                qtd_escritas = page.evaluate(
                    """() => {
                        const cards = document.querySelectorAll('div[data-review-id]');
                        let comTexto = 0;
                        cards.forEach(c => {
                            const txtEl = c.querySelector('span.wiI7pd, div.MyEned');
                            if (txtEl && (txtEl.innerText || '').trim().length >= 5) {
                                comTexto++;
                            }
                        });
                        return comTexto;
                    }"""
                )
                if qtd_escritas >= meta_escritas:
                    break
                page.evaluate(
                    """() => {
                        const rev = document.querySelector('div[data-review-id]');
                        let el = rev ? rev.parentElement : null;
                        while (el && el.scrollHeight <= el.clientHeight) {
                            el = el.parentElement;
                        }
                        if (el) el.scrollBy(0, 1200);
                    }"""
                )
                time.sleep(0.9)

            if qtd_avaliacoes == 0 and qtd_escritas > 0:
                qtd_avaliacoes = qtd_escritas

            aba_visao = painel.locator('button[role="tab"]').filter(has_text=re.compile(r"Vis[ãa]o geral|Overview", re.I)).first
            if aba_visao.count() > 0:
                aba_visao.click(timeout=2000)
                time.sleep(0.4)
        else:
            qtd_escritas = page.locator('div[data-review-id] span.wiI7pd').count()
            if qtd_avaliacoes == 0 and qtd_escritas == 0 and nota > 0:
                ocultas_pela_rede = True
    except Exception:
        pass

    return nota, qtd_avaliacoes, qtd_escritas, ocultas_pela_rede


def aplicar_resultado_presenca(lead: dict, resultado: ResultadoPresencaDigital) -> None:
    """Grava no lead o resultado da verificação de presença digital."""
    perfil = resultado.perfil_instagram
    lead["_presenca_digital"] = resultado
    lead["tem_site"] = resultado.tem_site
    lead["url_site"] = resultado.motivo
    lead["evidencias_site"] = [str(e) for e in resultado.evidencias]
    lead["observacoes"] = list(resultado.observacoes)
    lead["pendencias_verificacao"] = list(resultado.inconclusivos)
    lead["links_brutos_maps"] = list(resultado.links_maps_brutos)
    lead["links_agregador_instagram"] = list(resultado.links_expandidos)
    lead["url_instagram"] = resultado.url_instagram
    lead["status_instagram"] = resultado.status_instagram
    lead["detalhe_instagram"] = resultado.detalhe_instagram
    lead["instagram"] = perfil.to_dict() if perfil and perfil.acessivel else {}


def motivo_reprovacao_presenca(resultado: ResultadoPresencaDigital) -> str:
    """Retorna o motivo de reprovação no critério 'sem site', ou '' se aprovado."""
    if resultado.tem_site:
        return f"Possui site/sistema/landing page: {resultado.motivo}"
    if resultado.status_instagram == "inacessivel" and VERIFICACAO.get("exigir_instagram_verificado", False):
        return f"Instagram não pôde ser verificado ({resultado.detalhe_instagram})"
    if resultado.inconclusivos and VERIFICACAO.get("rejeitar_inconclusivos", True):
        return f"Verificação inconclusiva: {resultado.inconclusivos[0]}"
    return ""


def raspar_detalhes_local(
    page: Page,
    nicho_nome: str,
    cidade: str,
    copy_template: str,
    verificador: VerificadorPresencaDigital,
) -> tuple[dict | None, ResultadoPresencaDigital | None]:
    """Extrai os dados brutos completos da empresa aberta no painel lateral do Google Maps."""
    try:
        nome = ""
        try:
            nome_el = page.locator('h1.DUwDvf').first
            nome = nome_el.inner_text().strip()
        except Exception:
            return None, None

        if not nome:
            return None, None

        painel = page.locator('div[role="main"]').filter(has=page.locator('h1.DUwDvf')).last
        if painel.count() == 0:
            painel = page

        # Categoria e status operacional (Aberto / Fechado permanentemente)
        categoria_maps = ""
        fechado_perm = False
        fechado_temp = False
        try:
            cat_el = painel.locator('button.DkEaL').first
            if cat_el.count() > 0:
                categoria_maps = cat_el.inner_text().strip()
            txt_status = painel.inner_text()[:1200].lower()
            fechado_perm = "fechado permanentemente" in txt_status or "permanently closed" in txt_status
            fechado_temp = "fechado temporariamente" in txt_status or "temporarily closed" in txt_status
        except Exception:
            pass

        # Telefone
        telefone = ""
        try:
            tel_el = painel.locator('button[data-item-id*="phone:tel:"]').first
            if tel_el.count() > 0:
                tel_text = tel_el.get_attribute("data-item-id")
                telefone = tel_text.replace("phone:tel:", "").strip()
            else:
                tel_alt = painel.locator('button[aria-label*="Telefone:"]').first
                if tel_alt.count() > 0:
                    aria = tel_alt.get_attribute("aria-label")
                    telefone = aria.replace("Telefone:", "").strip()
        except Exception:
            pass

        # Endereço
        endereco = ""
        try:
            end_el = painel.locator('button[data-item-id="address"]').first
            if end_el.count() > 0:
                endereco = end_el.inner_text().strip()
        except Exception:
            pass

        # Fotos bem estruturadas (presença de galeria de fotos)
        tem_fotos = False
        try:
            foto_el = painel.locator('button[aria-label*="Foto"]').first
            if foto_el.count() > 0:
                tem_fotos = True
        except Exception:
            pass

        url_maps = page.url

        # Coleta bruta dos links presentes na ficha do Google Maps
        lead_parcial = {"nome": nome, "telefone": telefone, "cidade": cidade}
        resultado_maps = verificador.analisar_maps(page, lead_parcial)

        # Extração de Nota, Total de Avaliações e Avaliações Escritas
        meta_escritas = int(FILTROS.get("min_avaliacoes_escritas", 10))
        nota, qtd_avaliacoes, qtd_escritas, ocultas_rede = extrair_metricas_avaliacoes(page, meta_escritas=meta_escritas)

        dono = extrair_dono_ou_gerente(page)
        copy_pronta = copy_template.replace("{nome}", nome)

        lead = {
            "nome": nome,
            "nicho": nicho_nome,
            "categoria_maps": categoria_maps,
            "cidade": cidade,
            "nota": nota,
            "qtd_avaliacoes": qtd_avaliacoes,
            "qtd_avaliacoes_escritas": qtd_escritas,
            "avaliacoes_ocultas_pela_rede": ocultas_rede,
            "fechado_permanentemente": fechado_perm,
            "fechado_temporariamente": fechado_temp,
            "telefone": telefone,
            "endereco": endereco,
            "tem_fotos": tem_fotos,
            "url_maps": url_maps,
            "dono_gerente": dono,
            "copy_abordagem": copy_pronta,
        }

        aplicar_resultado_presenca(lead, resultado_maps)
        lead["score_potencial"] = calcular_score_potencial(lead)

        return lead, resultado_maps
    except Exception as e:
        print(f"Erro ao extrair detalhes: {e}")
        return None, None


def coletar_leads_brutos_regiao(
    page: Page,
    nicho_nome: str,
    termo_busca: str,
    cidade: str,
    limite_coleta_bruta: int,
    historico: dict,
    verificador: VerificadorPresencaDigital,
) -> list[dict]:
    """
    FASE 1 (Coleta Bruta Regional):
    Varre o Google Maps na região/termo escolhido e coleta os dados brutos de todos os
    estabelecimentos inéditos disponíveis (até `limite_coleta_bruta`), sem eliminar
    individualmente durante a coleta para que passem pelo Funil Eliminatório em Lote (Fase 2).
    """
    query = f"{termo_busca} em {cidade}"
    url_busca = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    print(f"\n================================================================================")
    print(f"🔎 [FASE 1 • COLETA REGIONAL] Buscando todos os candidatos: '{query}'")
    print(f"================================================================================")

    try:
        page.goto(url_busca, timeout=30000, wait_until="domcontentloaded")
    except Exception as e:
        print(f"Erro ao carregar busca: {e}")
        return []

    time.sleep(3)

    try:
        botao_aceitar = page.locator('button:has-text("Aceitar tudo"), button:has-text("Concordo")').first
        if botao_aceitar.count() > 0 and botao_aceitar.is_visible():
            botao_aceitar.click()
            time.sleep(0.8)
    except Exception:
        pass

    copy_template = (
        NICHOS_ATUAIS.get(nicho_nome, {}).get("copy_base")
        or NICHOS.get(nicho_nome, {}).get("copy_base")
        or gerar_config_nicho(nicho_nome).get("copy_base", "")
    )
    feed = page.locator('div[role="feed"]').first

    try:
        feed.wait_for(timeout=10000)
    except PlaywrightTimeoutError:
        if page.locator('h1.DUwDvf').count() > 0:
            lead, _ = raspar_detalhes_local(page, nicho_nome, cidade, copy_template, verificador)
            if lead:
                duplicado, _ = lead_ja_existe(lead, historico)
                if not duplicado:
                    return [lead]
        print("Nenhum resultado encontrado para a busca.")
        return []

    print("⏳ Rolando feed do Google Maps para capturar todos os estabelecimentos da região...")
    max_scrolls = int(FILTROS.get("max_scrolls_regiao", 20))
    contagem_anterior = 0
    tentativas_sem_novos = 0

    for _ in range(max_scrolls):
        cards = page.locator('div[role="feed"] a[href*="/maps/place/"]').all()
        if len(cards) >= limite_coleta_bruta:
            break
        if page.locator('text=/Você chegou ao final da lista/i').count() > 0:
            break

        if len(cards) == contagem_anterior:
            tentativas_sem_novos += 1
            if tentativas_sem_novos >= 3:
                break
        else:
            tentativas_sem_novos = 0
            contagem_anterior = len(cards)

        feed.evaluate("el => el.scrollBy(0, 1200)")
        time.sleep(random.uniform(1.3, 2.2))

    cards = page.locator('div[role="feed"] a[href*="/maps/place/"]').all()
    total_cards = min(len(cards), limite_coleta_bruta)
    print(f"📌 {len(cards)} estabelecimentos mapeados na região (coletando até {total_cards} inéditos)...")

    leads_brutos: list[dict] = []
    links_visitados: set[str] = set()

    for idx_card, card in enumerate(cards, 1):
        if len(leads_brutos) >= limite_coleta_bruta:
            break

        try:
            href = card.get_attribute("href")
            if not href or href in links_visitados:
                continue
            links_visitados.add(href)

            duplicado_url, _ = lead_ja_existe({"url_maps": href}, historico)
            if duplicado_url:
                continue

            try:
                card.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass
            card.click(timeout=6000)
            time.sleep(random.uniform(1.6, 2.4))

            page.locator('h1.DUwDvf').first.wait_for(timeout=5000)

            lead, _ = raspar_detalhes_local(page, nicho_nome, cidade, copy_template, verificador)
            if not lead:
                continue

            duplicado, _ = lead_ja_existe(lead, historico)
            if duplicado:
                continue

            leads_brutos.append(lead)
            print(
                f"  📥 [{len(leads_brutos):02d}/{total_cards:02d}] Coletado: '{lead['nome']}' "
                f"({lead['nota']}⭐ | {lead['qtd_avaliacoes']} av. | {lead['qtd_avaliacoes_escritas']} escritas)"
            )
        except Exception:
            continue

    return leads_brutos


def buscar_leads_google_maps(
    page: Page,
    nicho_nome: str,
    termo_busca: str,
    cidade: str,
    limite_leads: int = 15,
    historico: dict = None,
    verificador: VerificadorPresencaDigital = None,
) -> list:
    """
    Executa a captação de leads na região em 2 fases:
      - Fase 1: Coleta todos os leads brutos da região no Google Maps;
      - Fase 2: Executa o Funil Eliminatório Sequencial em Lote (Critérios 1 a 6) via Pandas/NumPy.
    """
    if historico is None:
        historico = carregar_historico()
    if verificador is None:
        verificador = VerificadorPresencaDigital(page.context, config=VERIFICACAO)

    fator_lote = int(FILTROS.get("fator_coleta_bruta_regiao", 3))
    limite_coleta_bruta = max(limite_leads * fator_lote, 12)

    # FASE 1: Coleta de todos os leads candidatos da região
    leads_brutos = coletar_leads_brutos_regiao(
        page=page,
        nicho_nome=nicho_nome,
        termo_busca=termo_busca,
        cidade=cidade,
        limite_coleta_bruta=limite_coleta_bruta,
        historico=historico,
        verificador=verificador,
    )

    if not leads_brutos:
        return []

    # FASE 2: Funil Eliminatório Sequencial critério por critério sobre o lote da região
    relatorio_funil = executar_funil_sequencial(
        leads_brutos=leads_brutos,
        regiao=cidade,
        nicho=nicho_nome,
        verificador=verificador,
        page=page,
        config_filtros=FILTROS,
        config_verificacao=VERIFICACAO,
        silencioso=False,
    )

    leads_qualificados: list[dict] = []
    for lead in relatorio_funil.leads_aprovados:
        if len(leads_qualificados) >= limite_leads:
            break

        # Verifica desduplicação pós-Instagram (caso o telefone de WhatsApp tenha vindo da bio)
        duplicado_pos, motivo_pos = lead_ja_existe(lead, historico)
        if duplicado_pos:
            print(f"  ⏭️ Ignorado após recuperar WhatsApp: '{lead['nome']}' ({motivo_pos})")
            continue

        registrar_lead_em_memoria(lead, historico)
        leads_qualificados.append(lead)

        insta_info = f"@{lead['instagram']['username']}" if lead.get("instagram") else lead.get("status_instagram", "n/a")
        prioridade_tag = "PRIORIDADE MÁXIMA" if lead.get("prioridade_maxima") else "QUALIFICADO"
        print(f"  🎯 [LEAD APROVADO #{len(leads_qualificados)} • {prioridade_tag}]")
        print(f"     Nome: {lead['nome']} ({lead.get('porte_classificacao', '')})")
        print(f"     WhatsApp: {lead['telefone']} (Origem: {lead.get('origem_whatsapp', 'Maps')})")
        print(f"     Instagram: {insta_info} ({lead.get('detalhe_instagram', '')})")
        print(f"     Reputação: {lead['nota']}⭐ ({lead['qtd_avaliacoes']} avaliações | {lead['qtd_avaliacoes_escritas']} escritas)")
        print(f"     Potencial de Conversão: {lead['score_potencial']}%\n")

    return leads_qualificados
