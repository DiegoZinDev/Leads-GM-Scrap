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

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
from config import NICHOS, REGIOES, FILTROS
from exporter import calcular_score_potencial
from historico import carregar_historico, lead_ja_existe, extrair_apenas_digitos, normalizar_texto
from verifier import (
    verificar_detalhes_google_maps,
    investigar_web_externa,
    investigar_instagram,
    investigar_whatsapp_bot_e_perfil
)

def extrair_dono_ou_gerente(page: Page) -> str:
    """Tenta identificar o nome do proprietário através de respostas de avaliações ou informações adicionais."""
    try:
        # Procura por respostas do proprietário nas avaliações recentes
        respostas = page.locator('text=/Resposta do propriet[aá]rio/i').all()
        for resp in respostas[:3]:
            parent = resp.locator('..').inner_text()
            # Padrões comuns: "Atenciosamente, Dr. Fulano", "Abraço, Fulano (Gerente)", etc.
            match = re.search(r"(?:atenciosamente|abraço|grato|obrigado),?\s+(?:dr\.?|dra\.?)?\s*([A-ZÁÉÍÓÚÂÊÔÃÕ][a-zà-ú]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕ][a-zà-ú]+)?)", parent, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    except Exception:
        pass
    return "A confirmar na abordagem (Secretária/Recepção)"

def raspar_detalhes_local(page: Page, nicho_nome: str, cidade: str, copy_template: str) -> dict:
    """Extrai os dados da empresa aberta no painel lateral do Google Maps."""
    try:
        # Nome da empresa
        nome = ""
        try:
            nome_el = page.locator('h1.DUwDvf').first
            nome = nome_el.inner_text().strip()
        except Exception:
            return None

        if not nome:
            return None

        # Nota e Avaliações
        nota = 0.0
        qtd_avaliacoes = 0
        try:
            container_nota = page.locator('div.F7nice').first
            if container_nota.count() > 0:
                texto_nota = container_nota.locator('span[aria-hidden="true"]').first.inner_text()
                nota = float(texto_nota.replace(",", "."))
                
                # Total de avaliações: geralmente vem como "(142)"
                txt_qtd = container_nota.inner_text()
                match_qtd = re.search(r'\((\d+[\.\d]*)\)', txt_qtd)
                if match_qtd:
                    qtd_avaliacoes = int(match_qtd.group(1).replace(".", ""))
        except Exception:
            pass

        # Verificar se tem Site oficial, Cardápio Digital ou Pedido Online no Maps
        tem_site, motivo_maps, instagram_url = verificar_detalhes_google_maps(page)
        url_site = motivo_maps if tem_site else ""

        # Telefone
        telefone = ""
        try:
            tel_el = page.locator('button[data-item-id*="phone:tel:"]').first
            if tel_el.count() > 0:
                tel_text = tel_el.get_attribute("data-item-id")
                telefone = tel_text.replace("phone:tel:", "").strip()
            else:
                # Tenta pelo aria-label
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

        # URL atual do Maps
        url_maps = page.url

        # Tentar extrair dono ou gerente
        dono = extrair_dono_ou_gerente(page)

        # Montar cópia personalizada com o nome da loja
        copy_pronta = copy_template.replace("{nome}", nome)

        lead = {
            "nome": nome,
            "nicho": nicho_nome,
            "cidade": cidade,
            "nota": nota,
            "qtd_avaliacoes": qtd_avaliacoes,
            "tem_site": tem_site,
            "url_site": url_site,
            "telefone": telefone,
            "endereco": endereco,
            "tem_fotos": tem_fotos,
            "url_maps": url_maps,
            "url_instagram": instagram_url,
            "dono_gerente": dono,
            "copy_abordagem": copy_pronta
        }

        # Calcular Score de Potencial
        lead["score_potencial"] = calcular_score_potencial(lead)

        return lead
    except Exception as e:
        print(f"Erro ao extrair detalhes: {e}")
        return None

def buscar_leads_google_maps(
    page: Page,
    nicho_nome: str,
    termo_busca: str,
    cidade: str,
    limite_leads: int = 15,
    historico: dict = None
) -> list:
    """Pesquisa no Google Maps, rola os resultados e extrai os leads qualificados (sem repetir leads anteriores)."""
    if historico is None:
        historico = carregar_historico()

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

    # Localizar o container de resultados (role="feed")
    feed = page.locator('div[role="feed"]').first
    try:
        feed.wait_for(timeout=10000)
    except PlaywrightTimeoutError:
        # Pode ter aberto direto a página do único estabelecimento encontrado
        if page.locator('h1.DUwDvf').count() > 0:
            copy = NICHOS.get(nicho_nome, {}).get("copy_base", "")
            lead = raspar_detalhes_local(page, nicho_nome, cidade, copy)
            if lead:
                duplicado, motivo = lead_ja_existe(lead, historico)
                if not duplicado:
                    return [lead]
        print("Nenhum resultado encontrado para a busca.")
        return []

    leads_coletados = []
    links_visitados = set()

    # Rolar o painel para carregar empresas
    print("⏳ Carregando listagem de empresas no Google Maps...")
    max_scrolls = 15

    for scroll_idx in range(max_scrolls):
        # Seleciona todos os links de estabelecimentos na lista
        cards = page.locator('div[role="feed"] a[href*="/maps/place/"]').all()
        
        # Rola o feed para baixo
        feed.evaluate("el => el.scrollBy(0, 1000)")
        time.sleep(random.uniform(1.5, 2.5))

        # Verificar se chegou ao fim da lista ("Você chegou ao fim da lista")
        if page.locator('text=/Você chegou ao final da lista/i').count() > 0:
            break

        if len(cards) >= limite_leads * 2:
            break

    # Re-seleciona os cards carregados
    cards = page.locator('div[role="feed"] a[href*="/maps/place/"]').all()
    print(f"📌 {len(cards)} estabelecimentos encontrados na lista. Analisando critérios e histórico...")

    copy_template = NICHOS.get(nicho_nome, {}).get("copy_base", "")

    for idx, card in enumerate(cards):
        if len(leads_coletados) >= limite_leads:
            print(f"🎯 Meta de {limite_leads} leads atingida para esta busca.")
            break

        try:
            href = card.get_attribute("href")
            if not href or href in links_visitados:
                continue
            links_visitados.add(href)

            # 0. Checagem rápida antes de clicar: se a URL já foi coletada no passado, pula!
            duplicado_url, motivo_url = lead_ja_existe({"url_maps": href}, historico)
            if duplicado_url:
                print(f"  ⏭️ Ignorado: Estabelecimento já coletado anteriormente em outra planilha.")
                continue

            # Clica no card para abrir os detalhes
            card.click()
            time.sleep(random.uniform(1.8, 2.8))

            # Aguarda o nome carregar
            page.locator('h1.DUwDvf').first.wait_for(timeout=5000)

            # Extrai os dados
            lead = raspar_detalhes_local(page, nicho_nome, cidade, copy_template)
            if not lead:
                continue

            # 1. Checagem de Desduplicação (Telefone ou Nome+Cidade já no histórico)
            duplicado, motivo = lead_ja_existe(lead, historico)
            if duplicado:
                print(f"  ⏭️ Ignorado: '{lead['nome']}' ({motivo})")
                continue

            # FILTROS SOLICITADOS:
            # 2. Sem site
            if FILTROS.get("exigir_sem_site") and lead["tem_site"]:
                print(f"  ⏭️ Ignorado: '{lead['nome']}' (Já possui site: {lead['url_site']})")
                continue

            # 3. Nota mínima
            if lead["nota"] < FILTROS.get("nota_minima", 4.0) and lead["nota"] > 0:
                print(f"  ⏭️ Ignorado: '{lead['nome']}' (Nota baixa: {lead['nota']})")
                continue

            # 4. Mínimo de avaliações (loja estruturada com movimento)
            if lead["qtd_avaliacoes"] < FILTROS.get("min_avaliacoes", 5):
                print(f"  ⏭️ Ignorado: '{lead['nome']}' (Poucas avaliações: {lead['qtd_avaliacoes']})")
                continue

            # 5. Deve ter telefone para podermos abordar
            if FILTROS.get("exigir_telefone") and not lead["telefone"]:
                print(f"  ⏭️ Ignorado: '{lead['nome']}' (Sem telefone cadastrado)")
                continue

            # 6. INVESTIGAÇÃO 1: Instagram (Bio do Perfil e Links na Bio)
            print(f"  📸 Inspecionando Bio e links do Instagram de '{lead['nome']}'...")
            tem_insta, motivo_insta = investigar_instagram(lead["nome"], cidade, page, instagram_url=lead.get("url_instagram", ""))
            if tem_insta:
                print(f"  ⏭️ Desqualificado na bio do Instagram: {motivo_insta}")
                continue

            # 7. INVESTIGAÇÃO 2 e 3: WhatsApp Bot e Perfil Comercial / Catálogo
            print(f"  💬 Inspecionando WhatsApp (Bots de atendimento, mensagens e perfil) de '{lead['nome']}'...")
            tem_zap, motivo_zap = investigar_whatsapp_bot_e_perfil(lead["telefone"], lead["nome"], cidade, page)
            if tem_zap:
                print(f"  ⏭️ Desqualificado no WhatsApp: {motivo_zap}")
                continue

            # 8. INVESTIGAÇÃO COMPLEMENTAR: Domínio próprio registrado na Web
            print(f"  🔎 Investigando a fundo na Web por site próprio de '{lead['nome']}'...")
            tem_web, motivo_web = investigar_web_externa(lead["nome"], cidade)
            if tem_web:
                print(f"  ⏭️ Desqualificado na investigação da Web: {motivo_web}")
                continue

            leads_coletados.append(lead)

            # Registra na memória do histórico desta execução para evitar repetição interna
            tel_dig = extrair_apenas_digitos(lead["telefone"])
            if tel_dig:
                historico.setdefault("telefones", {})[tel_dig] = {"nome": lead["nome"]}
            chave_nc = f"{normalizar_texto(lead['nome'])}_{normalizar_texto(lead['cidade'])}"
            historico.setdefault("nomes_cidade", {})[chave_nc] = {"nome": lead["nome"]}
            if lead["url_maps"]:
                historico.setdefault("urls_maps", {})[lead["url_maps"].split("?")[0]] = {"nome": lead["nome"]}

            print(f"  🎯 [LEAD 100% VERIFICADO #{len(leads_coletados)}]")
            print(f"     Nome: {lead['nome']}")
            print(f"     Telefone: {lead['telefone']}")
            print(f"     Nota: {lead['nota']}⭐ ({lead['qtd_avaliacoes']} avaliações)")
            print(f"     Status: Confirmado 100% sem site e sem cardápio digital!")
            print(f"     Potencial de Venda: {lead['score_potencial']}%\n")

        except Exception as err:
            continue

    return leads_coletados
