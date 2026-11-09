"""
Motor de Scraping do Google Maps usando Playwright.
Navega, extrai informações detalhadas, aplica filtros (sem site, boa reputação, fotos) e gera a abordagem personalizada.
"""

import sys
import time
import random
import re

# Evita erros de UnicodeEncodeError no Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from config import NICHOS, FILTROS, VERIFICACAO
from exporter import calcular_score_potencial
from historico import carregar_historico, lead_ja_existe, extrair_apenas_digitos, normalizar_texto
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


def aplicar_resultado_presenca(lead: dict, resultado: ResultadoPresencaDigital) -> None:
    """Grava no lead o resultado da verificação de presença digital."""
    perfil = resultado.perfil_instagram
    lead["tem_site"] = resultado.tem_site
    lead["url_site"] = resultado.motivo
    lead["evidencias_site"] = [str(e) for e in resultado.evidencias]
    lead["observacoes"] = list(resultado.observacoes)
    lead["pendencias_verificacao"] = list(resultado.inconclusivos)
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
    """Extrai os dados da empresa aberta no painel lateral do Google Maps."""
    try:
        nome = ""
        try:
            nome_el = page.locator('h1.DUwDvf').first
            nome = nome_el.inner_text().strip()
        except Exception:
            return None, None

        if not nome:
            return None, None

        # Nota e Avaliações
        nota = 0.0
        qtd_avaliacoes = 0
        try:
            container_nota = page.locator('div.F7nice').first
            if container_nota.count() > 0:
                texto_nota = container_nota.locator('span[aria-hidden="true"]').first.inner_text()
                nota = float(texto_nota.replace(",", "."))

                txt_qtd = container_nota.inner_text()
                match_qtd = re.search(r'\((\d+[\.\d]*)\)', txt_qtd)
                if match_qtd:
                    qtd_avaliacoes = int(match_qtd.group(1).replace(".", ""))
            if qtd_avaliacoes == 0:
                # Fallback: busca no aria-label de estrelas/avaliações do painel principal
                painel = page.locator('div[role="main"]').filter(has=page.locator('h1.DUwDvf')).last
                txt_painel = painel.inner_text() if painel.count() else ""
                m_av = re.search(r'(\d+[\.\d]*)\s+avalia[çc][õo]es', txt_painel, re.IGNORECASE)
                if m_av:
                    qtd_avaliacoes = int(m_av.group(1).replace(".", ""))
        except Exception:
            pass

        # Telefone
        telefone = ""
        try:
            tel_el = page.locator('button[data-item-id*="phone:tel:"]').first
            if tel_el.count() > 0:
                tel_text = tel_el.get_attribute("data-item-id")
                telefone = tel_text.replace("phone:tel:", "").strip()
            else:
                tel_alt = page.locator('button[aria-label*="Telefone:"]').first
                if tel_alt.count() > 0:
                    aria = tel_alt.get_attribute("aria-label")
                    telefone = aria.replace("Telefone:", "").strip()
        except Exception:
            pass

        # Endereço
        endereco = ""
        try:
            end_el = page.locator('button[data-item-id="address"]').first
            if end_el.count() > 0:
                endereco = end_el.inner_text().strip()
        except Exception:
            pass

        # Fotos bem estruturadas (presença de galeria de fotos)
        tem_fotos = False
        try:
            foto_el = page.locator('button[aria-label*="Foto"]').first
            if foto_el.count() > 0:
                tem_fotos = True
        except Exception:
            pass

        url_maps = page.url
        dono = extrair_dono_ou_gerente(page)
        copy_pronta = copy_template.replace("{nome}", nome)

        lead = {
            "nome": nome,
            "nicho": nicho_nome,
            "cidade": cidade,
            "nota": nota,
            "qtd_avaliacoes": qtd_avaliacoes,
            "telefone": telefone,
            "endereco": endereco,
            "tem_fotos": tem_fotos,
            "url_maps": url_maps,
            "dono_gerente": dono,
            "copy_abordagem": copy_pronta,
        }

        # Etapa 1 da verificação: links no painel do Google Maps (ignorando avaliações de terceiros)
        resultado_maps = verificador.analisar_maps(page, lead)
        aplicar_resultado_presenca(lead, resultado_maps)
        lead["score_potencial"] = calcular_score_potencial(lead)

        return lead, resultado_maps
    except Exception as e:
        print(f"Erro ao extrair detalhes: {e}")
        return None, None


def buscar_leads_google_maps(
    page: Page,
    nicho_nome: str,
    termo_busca: str,
    cidade: str,
    limite_leads: int = 15,
    historico: dict = None,
    verificador: VerificadorPresencaDigital = None,
) -> list:
    """Pesquisa no Google Maps, rola os resultados e extrai os leads qualificados (sem repetir leads anteriores)."""
    if historico is None:
        historico = carregar_historico()
    if verificador is None:
        verificador = VerificadorPresencaDigital(page.context, config=VERIFICACAO)

    query = f"{termo_busca} em {cidade}"
    url_busca = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    print(f"\n==================================================")
    print(f"🔍 Buscando: '{query}'")
    print(f"==================================================")

    try:
        page.goto(url_busca, timeout=45000)
    except Exception as e:
        print(f"Erro ao carregar busca: {e}")
        return []

    time.sleep(3)

    # Lidar com possíveis diálogos de consentimento
    try:
        botao_aceitar = page.locator('button:has-text("Aceitar tudo"), button:has-text("Concordo")').first
        if botao_aceitar.count() > 0 and botao_aceitar.is_visible():
            botao_aceitar.click()
            time.sleep(2)
    except Exception:
        pass

    feed = page.locator('div[role="feed"]').first
    try:
        feed.wait_for(timeout=10000)
    except PlaywrightTimeoutError:
        if page.locator('h1.DUwDvf').count() > 0:
            copy = NICHOS.get(nicho_nome, {}).get("copy_base", "")
            lead, res_maps = raspar_detalhes_local(page, nicho_nome, cidade, copy, verificador)
            if lead:
                duplicado, _ = lead_ja_existe(lead, historico)
                if not duplicado:
                    res_final = verificador.verificar(page, lead, resultado_maps=res_maps)
                    aplicar_resultado_presenca(lead, res_final)
                    if not (FILTROS.get("exigir_sem_site") and motivo_reprovacao_presenca(res_final)):
                        return [lead]
        print("Nenhum resultado encontrado para a busca.")
        return []

    leads_coletados = []
    links_visitados = set()

    print("⏳ Carregando listagem de empresas no Google Maps...")
    max_scrolls = 15

    for _ in range(max_scrolls):
        cards = page.locator('div[role="feed"] a[href*="/maps/place/"]').all()
        feed.evaluate("el => el.scrollBy(0, 1000)")
        time.sleep(random.uniform(1.5, 2.5))

        if page.locator('text=/Você chegou ao final da lista/i').count() > 0:
            break
        if len(cards) >= limite_leads * 2:
            break

    cards = page.locator('div[role="feed"] a[href*="/maps/place/"]').all()
    print(f"📌 {len(cards)} estabelecimentos encontrados na lista. Analisando critérios e histórico...")

    copy_template = NICHOS.get(nicho_nome, {}).get("copy_base", "")

    for card in cards:
        if len(leads_coletados) >= limite_leads:
            print(f"🎯 Meta de {limite_leads} leads atingida para esta busca.")
            break

        try:
            href = card.get_attribute("href")
            if not href or href in links_visitados:
                continue
            links_visitados.add(href)

            # 0. Checagem rápida antes de clicar: se a URL já foi coletada no passado, pula!
            duplicado_url, _ = lead_ja_existe({"url_maps": href}, historico)
            if duplicado_url:
                print("  ⏭️ Ignorado: Estabelecimento já coletado anteriormente em outra planilha.")
                continue

            try:
                card.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass
            card.click(timeout=6000)
            time.sleep(random.uniform(1.8, 2.8))

            page.locator('h1.DUwDvf').first.wait_for(timeout=5000)

            lead, resultado_maps = raspar_detalhes_local(page, nicho_nome, cidade, copy_template, verificador)
            if not lead:
                continue

            # 1. Checagem de Desduplicação (Telefone ou Nome+Cidade já no histórico)
            duplicado, motivo = lead_ja_existe(lead, historico)
            if duplicado:
                print(f"  ⏭️ Ignorado: '{lead['nome']}' ({motivo})")
                continue

            # 2. Sem site no Google Maps (wa.me e instagram.com são permitidos; sites/sistemas reprovam)
            if FILTROS.get("exigir_sem_site") and lead["tem_site"]:
                print(f"  ⏭️ Ignorado no Maps: '{lead['nome']}' ({lead['url_site']})")
                continue

            # 3. Nota mínima
            if lead["nota"] < FILTROS.get("nota_minima", 4.0) and lead["nota"] > 0:
                print(f"  ⏭️ Ignorado: '{lead['nome']}' (Nota baixa: {lead['nota']})")
                continue

            # 4. Mínimo de avaliações
            if lead["qtd_avaliacoes"] < FILTROS.get("min_avaliacoes", 5) and lead["qtd_avaliacoes"] > 0:
                print(f"  ⏭️ Ignorado: '{lead['nome']}' (Poucas avaliações: {lead['qtd_avaliacoes']})")
                continue

            # 5. Deve ter telefone para podermos abordar
            if FILTROS.get("exigir_telefone") and not lead["telefone"]:
                print(f"  ⏭️ Ignorado: '{lead['nome']}' (Sem telefone cadastrado)")
                continue

            # 6. Verificação completa de presença digital (Instagram bio + destaques + domínios + web)
            print(f"  🔎 Verificando presença digital (Instagram bio/destaques + Web) de '{lead['nome']}'...")
            resultado_final = verificador.verificar(page, lead, resultado_maps=resultado_maps)
            aplicar_resultado_presenca(lead, resultado_final)
            lead["score_potencial"] = calcular_score_potencial(lead)

            if FILTROS.get("exigir_sem_site"):
                motivo_reprov = motivo_reprovacao_presenca(resultado_final)
                if motivo_reprov:
                    print(f"  ⏭️ Desqualificado: '{lead['nome']}' — {motivo_reprov}")
                    continue

            leads_coletados.append(lead)

            tel_dig = extrair_apenas_digitos(lead["telefone"])
            if tel_dig:
                historico.setdefault("telefones", {})[tel_dig] = {"nome": lead["nome"]}
            chave_nc = f"{normalizar_texto(lead['nome'])}_{normalizar_texto(lead['cidade'])}"
            historico.setdefault("nomes_cidade", {})[chave_nc] = {"nome": lead["nome"]}
            if lead["url_maps"]:
                historico.setdefault("urls_maps", {})[lead["url_maps"].split("?")[0]] = {"nome": lead["nome"]}

            insta_info = f"@{lead['instagram']['username']}" if lead.get("instagram") else lead.get("status_instagram", "n/a")
            print(f"  🎯 [LEAD 100% VERIFICADO #{len(leads_coletados)}]")
            print(f"     Nome: {lead['nome']}")
            print(f"     Telefone: {lead['telefone']}")
            print(f"     Instagram: {insta_info} ({lead.get('detalhe_instagram', '')})")
            print(f"     Nota: {lead['nota']}⭐ ({lead['qtd_avaliacoes']} avaliações)")
            if lead.get("observacoes"):
                print(f"     Observações: {' | '.join(lead['observacoes'])}")
            print(f"     Status: Confirmado sem site, sistema próprio ou landing page!")
            print(f"     Potencial de Venda: {lead['score_potencial']}%\n")

        except Exception:
            continue

    return leads_coletados
