"""
Motor de Scraping do Google Maps usando Playwright (Otimizado para Alta Velocidade e Eficiência).
Pré-filtra empresas diretamente na listagem (sem clicar em quem já tem site ou nota baixa),
extrai detalhes em chamada JS única (<15ms) e executa verificações externas em paralelo.
"""

import sys
import time
import re

# Evita erros de UnicodeEncodeError no Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
from config import NICHOS, REGIOES, FILTROS, gerar_config_nicho
from exporter import calcular_score_potencial
from historico import carregar_historico, lead_ja_existe, extrair_apenas_digitos, normalizar_texto
from verifier import (
    analisar_dados_painel_maps,
    investigar_lead_completo_paralelo,
    verificar_detalhes_google_maps,
    investigar_web_externa,
    investigar_instagram,
    investigar_whatsapp_bot_e_perfil
)


def extrair_dono_de_texto(texto_painel: str) -> str:
    """Identifica o nome do proprietário a partir do texto extraído do painel."""
    if not texto_painel:
        return "A confirmar na abordagem (Secretária/Recepção)"
    try:
        match = re.search(
            r"(?:atenciosamente|abraço|grato|obrigado),?\s+(?:dr\.?|dra\.?)?\s*([A-ZÁÉÍÓÚÂÊÔÃÕ][a-zà-ú]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕ][a-zà-ú]+)?)",
            texto_painel,
            re.IGNORECASE
        )
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return "A confirmar na abordagem (Secretária/Recepção)"


def raspar_detalhes_local(page: Page, nicho_nome: str, cidade: str, copy_template: str) -> dict:
    """
    Extrai TODOS os dados da empresa aberta no painel lateral do Google Maps
    em uma ÚNICA chamada JavaScript (ultra-rápida, sem múltiplos round-trips).
    """
    try:
        dados = page.evaluate("""() => {
            const mains = Array.from(document.querySelectorAll('div[role="main"]'));
            const painel = mains.find(m => m.querySelector('h1.DUwDvf')) || mains[mains.length - 1] || document.body;

            const nomeEl = painel.querySelector('h1.DUwDvf') || document.querySelector('h1.DUwDvf');
            const nome = nomeEl ? (nomeEl.innerText || '').trim() : '';
            if (!nome) return null;

            let nota = 0.0;
            let qtdAvaliacoes = 0;
            const containerNota = painel.querySelector('div.F7nice') || document.querySelector('div.F7nice');
            if (containerNota) {
                const spanNota = containerNota.querySelector('span[aria-hidden="true"]');
                if (spanNota && spanNota.innerText) {
                    const parsed = parseFloat(spanNota.innerText.replace(',', '.'));
                    if (!isNaN(parsed)) nota = parsed;
                }
                const txtQtd = containerNota.innerText || '';
                const matchQtd = txtQtd.match(/\\((\\d+[\\.\\d]*)\\)/);
                if (matchQtd) {
                    qtdAvaliacoes = parseInt(matchQtd[1].replace(/\\./g, ''), 10) || 0;
                }
            }

            let telefone = '';
            const telBtn = painel.querySelector('button[data-item-id*="phone:tel:"]') || document.querySelector('button[data-item-id*="phone:tel:"]');
            if (telBtn) {
                const attr = telBtn.getAttribute('data-item-id') || '';
                telefone = attr.replace('phone:tel:', '').trim();
            } else {
                const telAlt = painel.querySelector('button[aria-label*="Telefone:"]') || document.querySelector('button[aria-label*="Telefone:"]');
                if (telAlt) {
                    const aria = telAlt.getAttribute('aria-label') || '';
                    telefone = aria.replace('Telefone:', '').trim();
                }
            }

            let endereco = '';
            const endBtn = painel.querySelector('button[data-item-id="address"]') || document.querySelector('button[data-item-id="address"]');
            if (endBtn) {
                endereco = (endBtn.innerText || '').trim();
            }

            const fotoBtn = painel.querySelector('button[aria-label*="Foto"]') || document.querySelector('button[aria-label*="Foto"]');
            const temFotos = !!fotoBtn;

            const prioSelectors = [
                'a[data-item-id="authority"]',
                'a[data-tooltip*="website" i]',
                'a[data-tooltip*="site" i]',
                'a[aria-label*="website" i]',
                'a[aria-label*="acessar o site" i]',
                'a[aria-label*="abrir website" i]',
                'a[data-item-id="menu"]',
                'a[data-item-id*="order"]',
                'a[data-item-id*="action:"]',
                'a[aria-label*="cardápio" i]',
                'a[aria-label*="menu" i]',
                'a[aria-label*="pedido" i]',
                'a[aria-label*="agendamento" i]'
            ].join(', ');

            const linksPrioritarios = Array.from(painel.querySelectorAll(prioSelectors))
                .map(a => a.getAttribute('href') || '')
                .filter(Boolean);

            const botoesSite = Array.from(
                painel.querySelectorAll('button[aria-label*="website" i], button[aria-label*="site" i], button[data-tooltip*="website" i]')
            ).map(b => b.getAttribute('aria-label') || '').filter(Boolean);

            const todosLinks = Array.from(painel.querySelectorAll('a[href]'))
                .map(a => a.getAttribute('href') || '')
                .filter(Boolean);

            const textoPainel = painel.innerText || '';

            return {
                nome,
                nota,
                qtd_avaliacoes: qtdAvaliacoes,
                telefone,
                endereco,
                tem_fotos: temFotos,
                url_maps: window.location.href,
                links_prioritarios: linksPrioritarios,
                botoes_site: botoesSite,
                todos_links: todosLinks,
                texto_painel: textoPainel
            };
        }""")

        if not dados or not dados.get("nome"):
            return None

        nome = dados["nome"]
        tem_site, motivo_maps, instagram_url = analisar_dados_painel_maps(dados)
        url_site = motivo_maps if tem_site else ""
        dono = extrair_dono_de_texto(dados.get("texto_painel", ""))

        if not copy_template:
            copy_template = gerar_config_nicho(nicho_nome).get("copy_base", "")
        copy_pronta = copy_template.replace("{nome}", nome).replace("{nicho}", nicho_nome)

        lead = {
            "nome": nome,
            "nicho": nicho_nome,
            "cidade": cidade,
            "nota": dados.get("nota", 0.0),
            "qtd_avaliacoes": dados.get("qtd_avaliacoes", 0),
            "tem_site": tem_site,
            "url_site": url_site,
            "telefone": dados.get("telefone", ""),
            "endereco": dados.get("endereco", ""),
            "tem_fotos": dados.get("tem_fotos", False),
            "url_maps": dados.get("url_maps", page.url),
            "url_instagram": instagram_url,
            "dono_gerente": dono,
            "copy_abordagem": copy_pronta
        }

        lead["score_potencial"] = calcular_score_potencial(lead)
        return lead
    except Exception as e:
        return None


def extrair_metadados_cards_feed(page: Page) -> list:
    """
    Lê instantaneamente todos os cards carregados no feed do Google Maps via JS,
    identificando ANTES DE CLICAR:
    - Nome e URL do estabelecimento
    - Se já possui botão de Site/Website visível no próprio card da lista
    - Nota e quantidade de avaliações visíveis no card da lista
    """
    try:
        return page.evaluate("""() => {
            const anchors = Array.from(document.querySelectorAll('div[role="feed"] a[href*="/maps/place/"]'));
            return anchors.map((a, idx) => {
                const href = a.getAttribute('href') || '';
                const nome = (a.getAttribute('aria-label') || '').trim();
                const card = a.closest('div.Nv2PK') || a.parentElement?.parentElement || a.parentElement;

                let temSiteNoCard = false;
                let notaCard = -1;
                let qtdAvalCard = -1;

                if (card) {
                    // Verifica se já existe botão de Website/Site direto na listagem
                    const siteBtn = card.querySelector(
                        'a[data-value="Website"], a[data-value="Site"], a[aria-label*="website" i], a[aria-label*="site" i], a[href^="http"]:not([href*="google.com"]):not([href*="instagram.com"]):not([href*="facebook.com"])'
                    );
                    if (siteBtn) {
                        temSiteNoCard = true;
                    }

                    const notaEl = card.querySelector('span.MW4etd');
                    if (notaEl && notaEl.innerText) {
                        const parsedN = parseFloat(notaEl.innerText.replace(',', '.'));
                        if (!isNaN(parsedN)) notaCard = parsedN;
                    }

                    const avalEl = card.querySelector('span.UY7F9');
                    if (avalEl && avalEl.innerText) {
                        const m = avalEl.innerText.match(/(\\d+[\\.\\d]*)/);
                        if (m) qtdAvalCard = parseInt(m[1].replace(/\\./g, ''), 10);
                    }
                }

                return {
                    idx,
                    href,
                    nome,
                    tem_site_card: temSiteNoCard,
                    nota_card: notaCard,
                    qtd_aval_card: qtdAvalCard
                };
            });
        }""")
    except Exception:
        return []


def aguardar_atualizacao_painel(page: Page, nome_anterior: str, nome_esperado: str, timeout_ms: int = 2400):
    """
    Aguarda de forma reativa a troca do painel lateral após o clique no card,
    evitando esperas fixas longas (time.sleep(2.5)).
    """
    inicio = time.time()
    nome_esp_norm = normalizar_texto(nome_esperado)
    while (time.time() - inicio) * 1000 < timeout_ms:
        try:
            nome_atual = page.evaluate("""() => {
                const mains = Array.from(document.querySelectorAll('div[role="main"]'));
                const p = mains.find(m => m.querySelector('h1.DUwDvf')) || document;
                const h1 = p.querySelector('h1.DUwDvf');
                return h1 ? (h1.innerText || '').trim() : '';
            }""")
            if nome_atual:
                if nome_esp_norm and nome_esp_norm in normalizar_texto(nome_atual):
                    time.sleep(0.12)
                    return
                if nome_anterior and nome_atual != nome_anterior:
                    time.sleep(0.15)
                    return
        except Exception:
            pass
        time.sleep(0.08)


def buscar_leads_google_maps(
    page: Page,
    nicho_nome: str,
    termo_busca: str,
    cidade: str,
    limite_leads: int = 25,
    historico: dict = None,
    copy_base: str = ""
) -> list:
    """
    Pesquisa no Google Maps com rolagem acelerada, pré-filtragem inteligente no feed
    (pula em 0ms quem já tem site ou nota baixa na lista) e verificação paralela.
    """
    if historico is None:
        historico = carregar_historico()

    copy_template = copy_base or gerar_config_nicho(nicho_nome).get("copy_base", "")
    exigir_sem_site = FILTROS.get("exigir_sem_site", True)
    nota_minima = FILTROS.get("nota_minima", 4.0)
    min_avaliacoes = FILTROS.get("min_avaliacoes", 5)
    exigir_telefone = FILTROS.get("exigir_telefone", True)

    query = f"{termo_busca} em {cidade}"
    url_busca = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    print(f"\n==================================================")
    print(f"⚡ Buscando Rápido: '{query}' (Nicho: {nicho_nome} | Meta lote: {limite_leads})")
    print(f"==================================================")

    try:
        page.goto(url_busca, timeout=30000, wait_until="domcontentloaded")
    except Exception as e:
        print(f"Erro ao carregar busca: {e}")
        return []

    # Espera inteligente pelo feed ou painel único (sem sleep fixo de 3s)
    try:
        page.locator('div[role="feed"], h1.DUwDvf, button:has-text("Aceitar tudo")').first.wait_for(timeout=8000)
    except Exception:
        pass

    # Lidar com possíveis diálogos de consentimento
    try:
        botao_aceitar = page.locator('button:has-text("Aceitar tudo"), button:has-text("Concordo")').first
        if botao_aceitar.count() > 0 and botao_aceitar.is_visible():
            botao_aceitar.click()
            time.sleep(0.8)
    except Exception:
        pass

    feed = page.locator('div[role="feed"]').first
    if feed.count() == 0:
        if page.locator('h1.DUwDvf').count() > 0:
            lead = raspar_detalhes_local(page, nicho_nome, cidade, copy_template)
            if lead:
                duplicado, _ = lead_ja_existe(lead, historico)
                if not duplicado and (not exigir_sem_site or not lead["tem_site"]):
                    tem_ext, _ = investigar_lead_completo_paralelo(lead, page)
                    if not tem_ext:
                        return [lead]
        print("Nenhum resultado na listagem para esta busca.")
        return []

    # Rolagem Turbo com contagem em tempo real de candidatos pré-qualificados (sem site na listagem)
    print("⏳ Carregando e pré-filtrando empresas no feed em alta velocidade...")
    max_scrolls = 18
    ultimo_total = 0
    scrolls_sem_novos = 0
    alvo_candidatos_limpos = max(limite_leads * 2, 16)

    for _ in range(max_scrolls):
        feed.evaluate("el => el.scrollBy(0, 2800)")
        time.sleep(0.55)

        info_scroll = page.evaluate("""(params) => {
            const cards = Array.from(document.querySelectorAll('div.Nv2PK'));
            let candidatosSemSite = 0;
            for (const c of cards) {
                const siteBtn = c.querySelector('a[data-value="Website"], a[data-value="Site"], a[aria-label*="website" i], a[aria-label*="site" i]');
                if (!siteBtn) candidatosSemSite++;
            }
            const fim = document.body.innerText.includes('Você chegou ao final da lista');
            return { total: cards.length, semSite: candidatosSemSite, fim };
        }""", {})

        total_atual = info_scroll.get("total", 0)
        sem_site_atual = info_scroll.get("semSite", 0)

        if info_scroll.get("fim") or sem_site_atual >= alvo_candidatos_limpos:
            break

        if total_atual == ultimo_total:
            scrolls_sem_novos += 1
            if scrolls_sem_novos >= 2:
                break
        else:
            scrolls_sem_novos = 0
            ultimo_total = total_atual

    # Extrai metadados de todos os cards do feed de uma só vez para pré-filtrar antes do clique!
    metadados_cards = extrair_metadados_cards_feed(page)
    cards_locators = page.locator('div[role="feed"] a[href*="/maps/place/"]').all()
    print(f"📌 {len(metadados_cards)} empresas listadas. Aplicando pré-filtro instantâneo no feed...")

    leads_coletados = []
    links_visitados = set()
    pulados_pre_filtro = 0
    nome_painel_atual = ""

    for meta in metadados_cards:
        if len(leads_coletados) >= limite_leads:
            print(f"🎯 Meta de {limite_leads} leads atingida para esta busca.")
            break

        idx = meta.get("idx", 0)
        href = meta.get("href", "")
        nome_card = meta.get("nome", "")

        if not href or href in links_visitados:
            continue
        links_visitados.add(href)

        # PRÉ-FILTRO 1 (0ms, sem clicar): Já tem botão de site visível no card do feed!
        if exigir_sem_site and meta.get("tem_site_card"):
            pulados_pre_filtro += 1
            continue

        # PRÉ-FILTRO 2 (0ms, sem clicar): Nota visível no card abaixo da mínima
        nota_c = meta.get("nota_card", -1)
        if nota_c > 0 and nota_c < nota_minima:
            pulados_pre_filtro += 1
            continue

        # PRÉ-FILTRO 3 (0ms, sem clicar): Avaliações visíveis no card abaixo do mínimo
        aval_c = meta.get("qtd_aval_card", -1)
        if aval_c >= 0 and aval_c < min_avaliacoes:
            pulados_pre_filtro += 1
            continue

        # PRÉ-FILTRO 4 (0ms, sem clicar): Já existe no histórico por URL ou Nome+Cidade
        duplicado_pre, _ = lead_ja_existe({"url_maps": href, "nome": nome_card, "cidade": cidade}, historico)
        if duplicado_pre:
            pulados_pre_filtro += 1
            continue

        if idx >= len(cards_locators):
            continue

        card_el = cards_locators[idx]

        try:
            # Clica no candidato pré-aprovado e aguarda reativamente o painel atualizar (~0.3s a 0.6s)
            try:
                card_el.scroll_into_view_if_needed(timeout=1500)
            except Exception:
                pass
            card_el.click(timeout=3500)
            aguardar_atualizacao_painel(page, nome_painel_atual, nome_card, timeout_ms=2200)

            # Extração em chamada JS única (< 15ms)
            lead = raspar_detalhes_local(page, nicho_nome, cidade, copy_template)
            if not lead:
                continue

            nome_painel_atual = lead["nome"]

            # 1. Desduplicação completa com telefone extraído
            duplicado, motivo = lead_ja_existe(lead, historico)
            if duplicado:
                continue

            # 2. Sem site no painel detalhado do Maps
            if exigir_sem_site and lead["tem_site"]:
                print(f"  ⏭️ Ignorado no painel: '{lead['nome']}' (Link/Site no Maps)")
                continue

            # 3. Nota mínima
            if lead["nota"] < nota_minima and lead["nota"] > 0:
                continue

            # 4. Mínimo de avaliações
            if lead["qtd_avaliacoes"] < min_avaliacoes:
                continue

            # 5. Deve ter telefone
            if exigir_telefone and not lead["telefone"]:
                continue

            # 6. INVESTIGAÇÃO PARALELA ULTRA-RÁPIDA (Web + WhatsApp + Instagram simultâneos)
            print(f"  ⚡ Verificando em paralelo (Web + WhatsApp + Instagram): '{lead['nome']}'...")
            tem_presenca_digital, motivo_verif = investigar_lead_completo_paralelo(lead, page)
            if tem_presenca_digital:
                print(f"  ⏭️ Desqualificado ({motivo_verif})")
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

            print(f"  ✅ [LEAD #{len(leads_coletados)} APROVADO] {lead['nome']} | Tel: {lead['telefone']} | {lead['nota']}⭐ ({lead['qtd_avaliacoes']} aval.) | Score: {lead['score_potencial']}%")

        except Exception:
            continue

    if pulados_pre_filtro > 0:
        print(f"  🚀 [TURBO] {pulados_pre_filtro} empresas com site/nota baixa/repetidas foram filtradas direto na lista sem perder tempo clicando!")

    return leads_coletados
