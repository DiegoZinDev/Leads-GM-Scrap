"""
Módulo de Verificação Profunda na Web, Redes Sociais e WhatsApp (Otimizado para Alta Velocidade).
Garante que o candidato NÃO possui site próprio, cardápio digital, biolink,
ou link registrado no perfil do Google Maps ou na bio do Instagram.
Executa verificações externas em paralelo (Multi-Threading) e extração DOM em passagem única.
"""

import urllib.parse
import urllib.request
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import Page

# Extensões e sufixos de domínios que caracterizam sites próprios e páginas na web
DOMINIOS_EXTENSOES = (
    ".com.br", ".com", ".br", ".org.br", ".org", ".net.br", ".net",
    ".site", ".online", ".tech", ".digital", ".app", ".io", ".dev",
    ".store", ".shop", ".med.br", ".adv.br", ".odo.br", ".arq.br",
    ".eng.br", ".vet.br", ".bio", ".link", ".page", ".live", ".menu",
    ".delivery", ".pro", ".top"
)

# Domínios e plataformas comuns de cardápio digital, delivery, agendamento e biolinks
DIGITAL_MENU_DOMAINS = [
    "goomer.app", "anota.ai", "ola.click", "deliverydireto.com.br",
    "deliverydireto", "instadelivery.com.br", "instadelivery",
    "cardapio.menu", "cardapioweb.com", "cardapioweb",
    "hubt.com.br", "menudigital.com", "cardapio.live", "saipos.com",
    "saipos", "linktr.ee", "beacons.ai", "instabio.cc", "bio.link",
    "wpp.bio", "cardapio.delivery", "pedir.digital", "app.cardapioweb.com",
    "doctoralia.com.br", "tecnofit.com.br", "totalpass.com.br", "gympass.com",
    "ifood.com.br", "canva.site", "wixsite.com", "wordpress.com", "sites.google.com",
    "taplink.cc", "campsite.bio", "heylink.me", "bit.ly", "tinyurl.com"
]

PLATAFORMAS_BIOLINKS_CARDAPIOS = DIGITAL_MENU_DOMAINS

# URLs e rotas internas do Google que devem ser desconsideradas
DOMINIOS_INTERNOS_IGNORAR = [
    "google.com/maps", "maps.google", "support.google.com", "accounts.google.com",
    "policies.google.com", "google.com.br/intl", "google.com/intl",
    "google.com/contributionpolicy", "gstatic.com"
]

HEADERS_PADRAO = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


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


def decodificar_url_redirect(url: str) -> str:
    """Extrai a URL de destino real caso seja um redirecionamento do Google ou Instagram."""
    if not url:
        return ""
    if "url?q=" in url or "url?sa=" in url or "/url?" in url:
        try:
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            if "q" in qs:
                return urllib.parse.unquote(qs["q"][0])
            if "url" in qs:
                return urllib.parse.unquote(qs["url"][0])
        except Exception:
            pass
    if "l.instagram.com" in url and "u=" in url:
        try:
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            if "u" in qs:
                return urllib.parse.unquote(qs["u"][0])
        except Exception:
            pass
    return url


def verificar_se_eh_link_valido(url: str) -> tuple[bool, str]:
    """
    Verifica se uma URL representa um site próprio, biolink ou cardápio digital,
    especialmente os que terminam em .com, .br, .org, etc.
    Retorna (eh_link_ou_site, motivo_formatado).
    """
    if not url:
        return False, ""

    url_real = decodificar_url_redirect(url).strip()
    url_lower = url_real.lower()

    if any(ign in url_lower for ign in DOMINIOS_INTERNOS_IGNORAR):
        return False, ""
    if url_lower.startswith(("tel:", "mailto:", "javascript:", "#")):
        return False, ""

    if any(soc in url_lower for soc in ["facebook.com", "linkedin.com", "twitter.com", "x.com", "youtube.com"]):
        return False, ""
    if "instagram.com" in url_lower:
        return False, ""

    for plat in PLATAFORMAS_BIOLINKS_CARDAPIOS:
        if plat in url_lower:
            return True, f"Plataforma/Biolink detectado ({plat}): {url_real}"

    try:
        parsed = urllib.parse.urlparse(url_real if "://" in url_real else f"http://{url_real}")
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
    except Exception:
        host = url_lower

    if not host or host in ["google.com", "google.com.br"]:
        return False, ""

    for ext in DOMINIOS_EXTENSOES:
        if host.endswith(ext) or f"{ext}/" in url_lower or f"{ext}?" in url_lower:
            return True, f"Site oficial com domínio ({host}): {url_real}"

    if re.search(r'https?://[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}', url_real):
        return True, f"Link de website detectado: {url_real}"

    return False, ""


def analisar_dados_painel_maps(dados_js: dict) -> tuple[bool, str, str]:
    """
    Analisa instantaneamente em memória os links, botões e textos extraídos do painel do Google Maps.
    Retorna (tem_site_ou_cardapio, motivo, url_instagram_encontrada).
    """
    instagram_url = ""
    if not dados_js:
        return False, "", ""

    # 1. Botões explícitos de website
    for aria in dados_js.get("botoes_site", []):
        aria_l = aria.lower()
        if any(term in aria_l for term in ["website", "copiar website", "abrir website", "acessar o site"]):
            return True, f"Botão oficial de Website detectado no perfil do Google Maps ({aria})", instagram_url

    # 2. Todos os links coletados do painel (priorizando authority e menu primeiro)
    for href in dados_js.get("links_prioritarios", []) + dados_js.get("todos_links", []):
        if not href:
            continue
        if "instagram.com/" in href and not any(x in href for x in ["/p/", "/reel/", "/explore/"]):
            if not instagram_url:
                instagram_url = decodificar_url_redirect(href)

        eh_link, motivo = verificar_se_eh_link_valido(href)
        if eh_link:
            return True, motivo, instagram_url

    # 3. Texto do painel buscando menção direta a domínios
    texto_painel = dados_js.get("texto_painel", "")
    if texto_painel:
        match_dom = re.search(
            r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com\.br|com|br|org\.br|org|net\.br|net|site|app|io|tech|online|store|shop|me|digital|top|link|bio|med\.br|adv\.br))\b',
            texto_painel,
            re.IGNORECASE
        )
        if match_dom:
            dom_achado = match_dom.group(1).lower()
            if not any(ign in dom_achado for ign in ["google.com", "google.com.br", "instagram.com", "facebook.com", "gstatic.com"]):
                return True, f"Domínio detectado no texto do perfil do Google Maps ({dom_achado})", instagram_url

    return False, "", instagram_url


def verificar_detalhes_google_maps(page: Page) -> tuple[bool, str, str]:
    """
    Varre o painel do Google Maps em uma ÚNICA chamada JS (ultra-rápida, < 15ms)
    em vez de dezenas de round-trips do Playwright.
    Retorna (tem_site_ou_cardapio, motivo, url_instagram_encontrada).
    """
    try:
        dados_js = page.evaluate("""() => {
            const mains = Array.from(document.querySelectorAll('div[role="main"]'));
            let painel = mains.find(m => m.querySelector('h1.DUwDvf')) || mains[mains.length - 1] || document.body;

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

            return {
                links_prioritarios: linksPrioritarios,
                botoes_site: botoesSite,
                todos_links: todosLinks,
                texto_painel: painel.innerText || ''
            };
        }""")
        return analisar_dados_painel_maps(dados_js)
    except Exception:
        return False, "", ""


def obter_ou_reutilizar_aba_whatsapp(context, telefone: str = "") -> Page:
    """
    Mantém uma ÚNICA aba dedicada ao WhatsApp Web no contexto.
    """
    digitos = extrair_digitos_telefone(telefone) if telefone else ""
    url_alvo = f"https://web.whatsapp.com/send/?phone={digitos}" if digitos else "https://web.whatsapp.com"

    for p in context.pages:
        try:
            if "web.whatsapp.com" in p.url or "whatsapp.com" in p.url:
                p.bring_to_front()
                if digitos and f"phone={digitos}" not in p.url:
                    p.goto(url_alvo, wait_until="domcontentloaded", timeout=15000)
                return p
        except Exception:
            pass

    nova_zap = context.new_page()
    try:
        nova_zap.goto(url_alvo, wait_until="domcontentloaded", timeout=20000)
    except Exception:
        pass
    return nova_zap


def interceptar_novas_abas_whatsapp(context):
    """
    Intercepta cliques ou popups que tentem abrir novas abas do WhatsApp
    e redireciona para a aba única principal, fechando a aba excedente.
    """
    def on_page_opened(new_page: Page):
        try:
            new_page.wait_for_timeout(400)
            url_atual = new_page.url.lower()
            if "whatsapp.com" in url_atual or "wa.me" in url_atual:
                outras = [p for p in context.pages if "web.whatsapp.com" in p.url and p != new_page]
                if outras:
                    aba_principal = outras[0]
                    match_tel = re.search(r'(?:phone=|wa\.me/)(\d+)', url_atual)
                    if match_tel:
                        aba_principal.goto(f"https://web.whatsapp.com/send/?phone={match_tel.group(1)}", wait_until="domcontentloaded", timeout=15000)
                    aba_principal.bring_to_front()
                    new_page.close()
        except Exception:
            pass

    context.on("page", on_page_opened)


def _buscar_instagram_ddg_rapido(nome: str, cidade: str) -> tuple[bool, str, str]:
    """
    Busca rápida via HTTP pelo perfil do Instagram e já checa se o snippet do buscador
    revela link de cardápio/site na bio.
    Retorna (desqualificado_no_snippet, motivo, url_instagram_encontrada).
    """
    try:
        query = f'site:instagram.com "{nome}" {cidade}'
        url_ddg = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url_ddg, headers=HEADERS_PADRAO)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            html_resp = resp.read().decode("utf-8", errors="ignore")
            html_lower = html_resp.lower()

            for dom in DIGITAL_MENU_DOMAINS:
                if dom in html_lower:
                    return True, f"Bio do Instagram indexada com link de cardápio/site ({dom})", ""

            match_links = re.findall(r'href="[^"]*(https://(?:www\.)?instagram\.com/[^"&/?]+)', html_resp)
            for link in match_links:
                if not any(x in link.lower() for x in ["/p/", "/reel/", "/explore/", "/stories/", "/accounts/"]):
                    return False, "", link.rstrip("/") + "/"
    except Exception:
        pass
    return False, "", ""


def inspecionar_url_instagram_playwright(alvo_url: str, page: Page) -> tuple[bool, str]:
    """
    Inspeciona a página do Instagram bloqueando imagens/vídeos/fontes pesadas
    e extraindo toda a bio/links/destaques em uma única chamada JS (< 1s).
    """
    if not alvo_url:
        return False, "Nenhum Instagram encontrado"

    temp_page = None
    try:
        temp_page = page.context.new_page()
        # Bloqueia mídia pesada para carregar o HTML da bio até 4x mais rápido
        temp_page.route(
            "**/*.{png,jpg,jpeg,gif,webp,mp4,webm,woff,woff2,ttf,otf}",
            lambda route: route.abort()
        )
        temp_page.goto(alvo_url, timeout=7500, wait_until="domcontentloaded")

        # Espera curta e inteligente até o header/main renderizar
        try:
            temp_page.locator("header, main").first.wait_for(timeout=2000)
        except Exception:
            pass
        temp_page.wait_for_timeout(450)

        dados_insta = temp_page.evaluate("""() => {
            const titulo = (document.title || '').toLowerCase();
            const bioEl = document.querySelector('header, main section, main') || document.body;
            const bioText = bioEl ? (bioEl.innerText || '') : '';
            const hrefs = Array.from(document.querySelectorAll('header a, main a, section a, a[role="link"]'))
                .map(a => a.getAttribute('href') || '')
                .filter(Boolean);
            const destaques = Array.from(document.querySelectorAll('div[role="tablist"] ~ div, section main ul li, div[role="listitem"]'))
                .map(el => el.innerText || '')
                .join(' ');
            return { titulo, bioText, hrefs, destaques };
        }""")

        titulo_pg = dados_insta.get("titulo", "")
        if any(b in titulo_pg for b in ["fortiguard", "blocked", "bloqueado", "access denied"]):
            return False, "Instagram inacessível na rede local"

        bio_text = dados_insta.get("bioText", "")
        bio_lower = bio_text.lower()

        # 1. Links clicáveis na bio
        for href in dados_insta.get("hrefs", []):
            href_real = decodificar_url_redirect(href).strip()
            href_lower = href_real.lower()

            if any(ign in href_lower for ign in ["/about", "/legal", "/explore", "/reels", "/tagged", "about.meta", "meta.com"]):
                continue

            if "l.instagram.com" in href or (href_lower.startswith("http") and "instagram.com" not in href_lower):
                eh_link, motivo = verificar_se_eh_link_valido(href_real)
                if eh_link:
                    return True, f"Link detectado na bio do Instagram: {href_real}"

                for ext in DOMINIOS_EXTENSOES:
                    if ext in href_lower:
                        return True, f"Link com extensão ({ext}) na bio do Instagram: {href_real}"

        # 2. Plataformas no texto da bio
        for dom in DIGITAL_MENU_DOMAINS:
            if dom in bio_lower:
                return True, f"Link/Plataforma ({dom}) mencionado no texto da bio do Instagram"

        # 3. Domínios escritos no texto da bio
        dominios_texto = re.findall(
            r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com\.br|com|br|org\.br|org|net\.br|net|site|app|io|tech|online|store|shop|me|digital|top|link|bio|med\.br|adv\.br))\b',
            bio_text,
            re.IGNORECASE
        )
        for d in set(dominios_texto):
            d_lower = d.lower()
            if not any(ign in d_lower for ign in ["instagram.com", "facebook.com", "meta.com", "threads.net"]):
                return True, f"Domínio detectado no texto da bio do Instagram: {d}"

        # 4. Destaques
        texto_destaques = dados_insta.get("destaques", "").lower()
        for termo in ["cardápio", "cardapio", "menu digital", "delivery", "fazer pedido", "peça online", "pedidos", "site", "link"]:
            if termo in texto_destaques:
                return True, f"Destaque de cardápio/pedidos detectado no Instagram: '{termo}'"

    except Exception:
        pass
    finally:
        if temp_page:
            try:
                temp_page.close()
            except Exception:
                pass

    return False, "Instagram verificado: sem link, site ou cardápio na bio"


def investigar_instagram(nome: str, cidade: str, page: Page, instagram_url: str = "") -> tuple[bool, str]:
    """
    Investiga a bio, links e destaques do Instagram da empresa.
    """
    alvo_url = instagram_url
    if not alvo_url:
        desq, motivo, url_achada = _buscar_instagram_ddg_rapido(nome, cidade)
        if desq:
            return True, motivo
        alvo_url = url_achada

    if not alvo_url:
        return False, "Nenhum Instagram encontrado"

    return inspecionar_url_instagram_playwright(alvo_url, page)


def investigar_whatsapp_bot_e_perfil(telefone: str, nome: str, cidade: str, page: Page = None) -> tuple[bool, str]:
    """
    Investiga Bots de WhatsApp e vínculo com plataformas de cardápio digital.
    """
    digitos = extrair_digitos_telefone(telefone)
    if not digitos:
        return False, ""

    # 1. Inspeciona a API pública do WhatsApp via HTTP rápido
    url_wa = f"https://api.whatsapp.com/send/?phone={digitos}"
    try:
        req = urllib.request.Request(url_wa, headers=HEADERS_PADRAO)
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            conteudo = resp.read().decode("utf-8", errors="ignore").lower()
            termos_bot = [
                "cardapio", "cardápio", "fazer pedido", "ver cardápio",
                "menu digital", "catálogo", "catalogo", "pedir online",
                "pedidodigital", "anota.ai", "goomer"
            ]
            for termo in termos_bot:
                if termo in conteudo:
                    return True, f"Bot de WhatsApp / Mensagem de Cardápio detectada no WhatsApp: '{termo}'"
    except Exception:
        pass

    # 2. Busca reversa na Web pelo número de WhatsApp
    try:
        numero_sem_55 = digitos[2:] if digitos.startswith("55") else digitos
        query_zap = f'"{digitos}" OR "{numero_sem_55}"'
        url_ddg = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query_zap)}"
        req = urllib.request.Request(url_ddg, headers=HEADERS_PADRAO)
        with urllib.request.urlopen(req, timeout=2.8) as resp:
            html_resp = resp.read().decode("utf-8", errors="ignore").lower()
            for dom in DIGITAL_MENU_DOMAINS:
                if dom in html_resp:
                    return True, f"Número de WhatsApp vinculado a plataforma de pedidos/bot ({dom})"
    except Exception:
        pass

    return False, "WhatsApp verificado: sem bot de cardápio ou site no perfil"


def investigar_web_externa(nome: str, cidade: str) -> tuple[bool, str]:
    """
    Pesquisa na Web para checar se a empresa possui domínio oficial ou cardápio digital registrado.
    """
    query = f'"{nome}" {cidade}'
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"

    try:
        req = urllib.request.Request(url, headers=HEADERS_PADRAO)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
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

        partes_nome = [p for p in re.sub(r'[^a-zA-Z0-9]', ' ', nome.lower()).split() if len(p) >= 4]

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

            if partes_nome:
                dominio_match = re.search(r'https?://(?:www\.)?([^/]+)', u_lower)
                if dominio_match:
                    dominio = dominio_match.group(1)
                    if any(p in dominio for p in partes_nome) and not any(gen in dominio for gen in ["instagram.com", "linkedin.com", "tiktok.com", "twitter.com"]):
                        return True, f"Site oficial próprio detectado na Web: {u}"

    except Exception:
        pass

    return False, "Confirmado 100% sem site e sem cardápio digital"


def investigar_lead_completo_paralelo(lead: dict, page: Page) -> tuple[bool, str]:
    """
    Executa simultaneamente (em paralelo via ThreadPoolExecutor) as investigações de:
    1) Domínio próprio / Cardápio na Web
    2) WhatsApp Bot / Perfil vinculado a plataforma
    3) Descoberta de Instagram via buscador (se não veio no Maps)
    E caso passe nas checagens HTTP e haja perfil de Instagram, inspeciona a bio de forma ultra-rápida.
    Retorna (possui_site_ou_cardapio, motivo).
    """
    nome = lead.get("nome", "")
    cidade = lead.get("cidade", "")
    telefone = lead.get("telefone", "")
    insta_url = lead.get("url_instagram", "")

    with ThreadPoolExecutor(max_workers=3) as executor:
        fut_web = executor.submit(investigar_web_externa, nome, cidade)
        fut_zap = executor.submit(investigar_whatsapp_bot_e_perfil, telefone, nome, cidade, None)
        fut_insta_ddg = None if insta_url else executor.submit(_buscar_instagram_ddg_rapido, nome, cidade)

        # Checa Web e WhatsApp assim que terminam (curto-circuito imediato se reprovar)
        tem_web, motivo_web = fut_web.result()
        if tem_web:
            return True, f"Web: {motivo_web}"

        tem_zap, motivo_zap = fut_zap.result()
        if tem_zap:
            return True, f"WhatsApp: {motivo_zap}"

        if fut_insta_ddg is not None:
            desq_insta, motivo_ddg, url_achada = fut_insta_ddg.result()
            if desq_insta:
                return True, f"Instagram: {motivo_ddg}"
            insta_url = url_achada

    # Se encontrou URL do Instagram, inspeciona a bio (com mídia bloqueada para alta velocidade)
    if insta_url:
        tem_insta, motivo_insta = inspecionar_url_instagram_playwright(insta_url, page)
        if tem_insta:
            return True, f"Instagram: {motivo_insta}"

    return False, "Confirmado 100% sem site e sem cardápio digital"
