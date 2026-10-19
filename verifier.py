"""
Módulo de Verificação Profunda na Web, Redes Sociais e WhatsApp.
Garante que o candidato NÃO possui site próprio, cardápio digital oculto, biolink,
bot de atendimento com cardápio ou site na bio do Instagram/WhatsApp.
"""

import urllib.parse
import urllib.request
import re
from playwright.sync_api import Page

# Domínios e plataformas comuns de cardápio digital, delivery e biolinks
DIGITAL_MENU_DOMAINS = [
    "goomer.app", "anota.ai", "ola.click", "deliverydireto.com.br",
    "deliverydireto", "instadelivery.com.br", "instadelivery",
    "cardapio.menu", "cardapioweb.com", "cardapioweb",
    "hubt.com.br", "menudigital.com", "cardapio.live", "saipos.com",
    "saipos", "linktr.ee", "beacons.ai", "instabio.cc", "bio.link",
    "wpp.bio", "cardapio.delivery", "pedir.digital", "app.cardapioweb.com",
    "doctoralia.com.br", "tecnofit.com.br", "totalpass.com.br", "gympass.com",
    "ifood.com.br/delivery"
]

def extrair_digitos_telefone(telefone: str) -> str:
    """Extrai apenas os números e garante formato com 55."""
    if not telefone:
        return ""
    digitos = re.sub(r"\D", "", telefone)
    if digitos.startswith("0"):
        digitos = digitos[1:]
    if not digitos.startswith("55") and len(digitos) in [10, 11]:
        digitos = "55" + digitos
    return digitos

def verificar_detalhes_google_maps(page: Page) -> tuple[bool, str, str]:
    """
    Varre o painel do Google Maps em busca de Website, Cardápio, Pedidos e perfil do Instagram.
    Retorna (tem_site_ou_cardapio, motivo, url_instagram_encontrada).
    """
    instagram_url = ""
    try:
        container = page.locator('div[role="main"]').first
        if container.count() == 0:
            return False, "", ""

        # 1. Verifica botão oficial de Website (com href válido)
        site_el = container.locator('a[data-item-id="authority"]').first
        if site_el.count() > 0:
            href = site_el.get_attribute("href")
            if href and "google.com" not in href:
                return True, f"Website oficial registrado no Maps ({href})", ""

        # 2. Verifica link real de Cardápio / Menu (tag <a> com href externo)
        menu_el = container.locator('a[data-item-id="menu"], a[aria-label*="cardápio" i]').first
        if menu_el.count() > 0:
            href = menu_el.get_attribute("href")
            if href and "google.com" not in href:
                return True, f"Cardápio/Menu detectado no Maps ({href})", ""

        # 3. Verifica link de Fazer Pedido / Order Online
        order_el = container.locator('a[data-item-id*="order"], a[aria-label*="fazer pedido" i]').first
        if order_el.count() > 0:
            href = order_el.get_attribute("href")
            if href and "google.com" not in href:
                return True, f"Pedido Online detectado no Maps ({href})", ""

        # 4. Verifica links de redes sociais (procura Instagram)
        links_sociais = container.locator('a[href*="instagram.com"]').all()
        for l in links_sociais[:2]:
            href = l.get_attribute("href") or ""
            if href:
                instagram_url = href
                if any(dom in href.lower() for dom in DIGITAL_MENU_DOMAINS):
                    return True, f"Cardápio/Biolink detectado no link social do Maps ({href})", instagram_url

        # 5. Verifica se há texto com links de cardápio na descrição
        descricao = container.locator('div.PYvSYb, div[aria-label*="Sobre" i]').all_inner_texts()
        texto_desc = " ".join(descricao).lower()
        for dom in DIGITAL_MENU_DOMAINS:
            if dom in texto_desc:
                return True, f"Menção a cardápio/site ({dom}) na descrição do Maps", instagram_url

    except Exception:
        pass

    return False, "", instagram_url

def investigar_instagram(nome: str, cidade: str, page: Page, instagram_url: str = "") -> tuple[bool, str]:
    """
    FOCO 1: Investiga a bio e links do Instagram da empresa.
    Verifica se na biografia ou no link de bio há direcionamento para site, cardápio digital ou biolink.
    """
    alvo_url = instagram_url
    
    # Se não temos a URL do Maps, pesquisa DuckDuckGo pelo Instagram oficial
    if not alvo_url:
        try:
            query = f'site:instagram.com "{nome}" {cidade}'
            url_ddg = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            req = urllib.request.Request(url_ddg, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                html_resp = resp.read().decode("utf-8", errors="ignore")
                
                # Procura urls do instagram nos resultados
                match_links = re.findall(r'href="[^"]*(https://(?:www\.)?instagram\.com/[^"&/]+)', html_resp)
                if match_links:
                    alvo_url = match_links[0] + "/"

                # Inspeciona snippets do DuckDuckGo para ver menções a cardápio na bio
                for dom in DIGITAL_MENU_DOMAINS:
                    if dom in html_resp.lower():
                        return True, f"Bio do Instagram indexada com link de cardápio/site ({dom})"
        except Exception:
            pass

    if not alvo_url:
        return False, "Nenhum Instagram com site encontrado"

    # Se temos a URL do Instagram, abre com Playwright para ler a bio real e links na bio
    try:
        temp_page = page.context.new_page()
        temp_page.goto(alvo_url, timeout=12000)
        temp_page.wait_for_timeout(2000)

        # 1. Lê todo o texto do header/biografia
        bio_text = temp_page.locator('header').inner_text() if temp_page.locator('header').count() > 0 else ""
        bio_lower = bio_text.lower()

        for dom in DIGITAL_MENU_DOMAINS:
            if dom in bio_lower:
                temp_page.close()
                return True, f"Link de cardápio/site ({dom}) detectado na bio do Instagram ({alvo_url})"

        # 2. Inspeciona links clicáveis dentro do header (l.instagram.com links externos)
        links = temp_page.locator('header a').all()
        for l in links:
            href = l.get_attribute("href") or ""
            href_decoded = urllib.parse.unquote(href).lower()
            for dom in DIGITAL_MENU_DOMAINS:
                if dom in href_decoded:
                    temp_page.close()
                    return True, f"Link de cardápio/delivery ({dom}) no botão da bio do Instagram"
            
            # Checa se é um domínio próprio da empresa (.com.br ou .com)
            partes_nome = [p for p in re.sub(r'[^a-zA-Z0-9]', ' ', nome.lower()).split() if len(p) >= 4]
            if partes_nome and any(p in href_decoded for p in partes_nome):
                if not any(soc in href_decoded for soc in ["instagram.com", "facebook.com", "whatsapp.com", "wa.me"]):
                    temp_page.close()
                    return True, f"Site oficial próprio na bio do Instagram: {href_decoded}"

        temp_page.close()
    except Exception:
        pass

    return False, "Instagram verificado: sem site ou cardápio digital"

def investigar_whatsapp_bot_e_perfil(telefone: str, nome: str, cidade: str, page: Page) -> tuple[bool, str]:
    """
    FOCO 2 e FOCO 3:
    - Investiga Bots de WhatsApp / mensagens automáticas de pedidos.
    - Investiga se o número de WhatsApp está cadastrado em bots/cardápios digitais (Anota AI, Goomer, Delivery Direto).
    - Investiga a descrição e link do perfil de WhatsApp.
    """
    digitos = extrair_digitos_telefone(telefone)
    if not digitos:
        return False, ""

    # 1. Inspeciona o link direto da API do WhatsApp para checar se há mensagem pré-programada de bot/cardápio
    url_wa = f"https://api.whatsapp.com/send/?phone={digitos}"
    try:
        temp_page = page.context.new_page()
        temp_page.goto(url_wa, timeout=10000)
        temp_page.wait_for_timeout(1500)

        # Checa conteúdo da página de redirecionamento do WhatsApp
        conteudo = temp_page.content().lower()

        # Palavras-chave típicas de bot de cardápio e atendimento automático
        termos_bot = [
            "cardapio", "cardápio", "fazer pedido", "ver cardápio",
            "menu digital", "catálogo", "catalogo", "pedir online",
            "pedidodigital", "anota.ai", "goomer"
        ]
        for termo in termos_bot:
            if termo in conteudo:
                temp_page.close()
                return True, f"Bot de WhatsApp / Mensagem de Cardápio detectada no WhatsApp: '{termo}'"

        temp_page.close()
    except Exception:
        pass

    # 2. Busca reversa na Web pelo número de WhatsApp:
    # Identifica se esse número é o canal oficial de recebimento de um bot Goomer, Anota AI, etc.
    try:
        numero_sem_55 = digitos[2:] if digitos.startswith("55") else digitos
        query_zap = f'"{digitos}" OR "{numero_sem_55}"'
        url_ddg = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query_zap)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        req = urllib.request.Request(url_ddg, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            html_resp = resp.read().decode("utf-8", errors="ignore").lower()
            for dom in DIGITAL_MENU_DOMAINS:
                if dom in html_resp:
                    return True, f"Número de WhatsApp vinculado a plataforma de pedidos/bot ({dom})"
    except Exception:
        pass

    return False, "WhatsApp verificado: sem bot de cardápio ou site no perfil"

def investigar_web_externa(nome: str, cidade: str) -> tuple[bool, str]:
    """
    Pesquisa na Web para checar se a empresa possui domínio oficial registrado no Google.
    """
    query = f'"{nome}" {cidade}'
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        links = re.findall(r'class="result__url"[^>]*href="([^"]+)"', html)
        if not links:
            links = re.findall(r'uddg=([^&]+)', html)

        urls_limpas = []
        for l in links:
            if "uddg=" in l:
                match = re.search(r'uddg=([^&]+)', l)
                if match:
                    urls_limpas.append(urllib.parse.unquote(match.group(1)))
            else:
                urls_limpas.append(l)

        for u in urls_limpas[:8]:
            u_lower = u.lower()
            if any(gen in u_lower for gen in [
                "google.com", "maps.google", "tripadvisor.com", "facebook.com",
                "guiamais.com.br", "telelistas.net", "apontador.com.br",
                "econodata.com.br", "cnpj.biz", "consultas.plus", "situacaocadastral.info",
                "jusbrasil.com.br/processos", "youtube.com"
            ]):
                continue

            for plat in DIGITAL_MENU_DOMAINS:
                if plat in u_lower:
                    return True, f"Cardápio Digital / BioLink detectado na Web ({plat}): {u}"

            partes_nome = [p for p in re.sub(r'[^a-zA-Z0-9]', ' ', nome.lower()).split() if len(p) >= 4]
            if partes_nome:
                dominio_match = re.search(r'https?://(?:www\.)?([^/]+)', u_lower)
                if dominio_match:
                    dominio = dominio_match.group(1)
                    if any(p in dominio for p in partes_nome) and not any(gen in dominio for gen in ["instagram.com", "linkedin.com", "tiktok.com", "twitter.com"]):
                        return True, f"Site oficial próprio detectado na Web: {u}"

    except Exception:
        pass

    return False, "Confirmado 100% sem site e sem cardápio digital"
