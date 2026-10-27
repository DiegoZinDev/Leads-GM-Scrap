"""
Módulo de Verificação Profunda na Web, Redes Sociais e WhatsApp.
Garante que o candidato NÃO possui site próprio, cardápio digital, biolink,
ou link registrado no perfil do Google Maps ou na bio do Instagram.
Filtro rigoroso: identifica qualquer link, especialmente com finais .com, .br, .org, etc.
"""

import urllib.parse
import urllib.request
import re
from playwright.sync_api import Page

# Extensões e sufixos de domínios que caracterizam sites próprios e páginas na web
DOMINIOS_EXTENSOES = (
    ".com.br", ".com", ".br", ".org.br", ".org", ".net.br", ".net",
    ".site", ".online", ".tech", ".digital", ".app", ".io", ".dev",
    ".store", ".shop", ".med.br", ".adv.br", ".odo.br", ".arq.br",
    ".eng.br", ".vet.br", ".bio", ".link", ".page", ".live", ".menu",
    ".delivery", ".pro", ".top", ".me"
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
    # Redirecionamento Google: /url?q=... ou google.com/url?q=... ou url?sa=...&url=...
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
    # Redirecionamento Instagram: l.instagram.com/?u=...
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

    # Ignora domínios internos do Google e esquemas não-web
    if any(ign in url_lower for ign in DOMINIOS_INTERNOS_IGNORAR):
        return False, ""
    if url_lower.startswith(("tel:", "mailto:", "javascript:", "#")):
        return False, ""

    # Ignora redes sociais padrão no Maps se forem apenas os perfis
    if any(soc in url_lower for soc in ["facebook.com", "linkedin.com", "twitter.com", "x.com", "youtube.com"]):
        return False, ""
    if "instagram.com" in url_lower:
        # Se for o próprio perfil do Instagram no Maps, não conta como site do Maps (será inspecionado na bio)
        return False, ""

    # 1. Checa plataformas conhecidas de cardápio digital / biolink / agendamento
    for plat in PLATAFORMAS_BIOLINKS_CARDAPIOS:
        if plat in url_lower:
            return True, f"Plataforma/Biolink detectado ({plat}): {url_real}"

    # 2. Extrai o hostname / domínio principal
    try:
        parsed = urllib.parse.urlparse(url_real if "://" in url_real else f"http://{url_real}")
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
    except Exception:
        host = url_lower

    if not host or host in ["google.com", "google.com.br"]:
        return False, ""

    # 3. Checa se o domínio termina com alguma das extensões solicitadas (.com, .br, .org, etc.)
    for ext in DOMINIOS_EXTENSOES:
        if host.endswith(ext) or f"{ext}/" in url_lower or f"{ext}?" in url_lower:
            return True, f"Site oficial com domínio ({host}): {url_real}"

    # 4. Checa qualquer URL http/https com formato de domínio válido
    if re.search(r'https?://[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}', url_real):
        return True, f"Link de website detectado: {url_real}"

    return False, ""

def verificar_detalhes_google_maps(page: Page) -> tuple[bool, str, str]:
    """
    Varre o painel do Google Maps do estabelecimento em busca de qualquer tipo de link:
    Website oficial, Cardápio, Pedidos, Agendamentos e perfil do Instagram.
    Filtra rigorosamente links terminados em .com, .br, .org, etc.
    Retorna (tem_site_ou_cardapio, motivo, url_instagram_encontrada).
    """
    instagram_url = ""
    try:
        # Localiza o painel ativo de detalhes do estabelecimento (que contém o h1 com o nome da empresa)
        painel = page.locator('div[role="main"]').filter(has=page.locator('h1.DUwDvf')).first
        if painel.count() == 0:
            painel = page.locator('div[role="main"]').last
        if painel.count() == 0:
            painel = page

        # 1. Verifica botões e links oficiais de Website / Authority
        site_links = painel.locator(
            'a[data-item-id="authority"], '
            'a[data-tooltip*="website" i], '
            'a[data-tooltip*="site" i], '
            'a[aria-label*="website" i], '
            'a[aria-label*="acessar o site" i], '
            'a[aria-label*="abrir website" i]'
        ).all()
        for s in site_links:
            href = s.get_attribute("href") or ""
            eh_link, motivo = verificar_se_eh_link_valido(href)
            if eh_link:
                return True, motivo, instagram_url

        # 1.1 Verifica botões do Maps (ex: "Copiar website", "Abrir website")
        botoes_site = painel.locator('button[aria-label*="website" i], button[aria-label*="site" i], button[data-tooltip*="website" i]').all()
        for b in botoes_site:
            aria = b.get_attribute("aria-label") or ""
            # Se tiver botão de website no painel do Maps, indica que há site cadastrado
            if any(term in aria.lower() for term in ["website", "copiar website", "abrir website", "acessar o site"]):
                return True, f"Botão oficial de Website detectado no perfil do Google Maps ({aria})", instagram_url

        # 2. Verifica links de Cardápio / Menu / Pedidos / Agendamento (ex: Doctoralia, Goomer, Anota AI)
        menu_order_links = painel.locator(
            'a[data-item-id="menu"], '
            'a[data-item-id*="order"], '
            'a[data-item-id*="action:"], '
            'a[aria-label*="cardápio" i], '
            'a[aria-label*="menu" i], '
            'a[aria-label*="pedido" i], '
            'a[aria-label*="agendamento" i]'
        ).all()
        for m in menu_order_links:
            href = m.get_attribute("href") or ""
            eh_link, motivo = verificar_se_eh_link_valido(href)
            if eh_link:
                return True, motivo, instagram_url

        # 3. Verifica TODOS os links <a> no painel do Maps
        todos_links = painel.locator('a[href]').all()
        for l in todos_links:
            href = l.get_attribute("href") or ""
            # Captura perfil do Instagram se presente na seção de redes sociais
            if "instagram.com/" in href and not any(x in href for x in ["/p/", "/reel/", "/explore/"]):
                url_limpa_insta = decodificar_url_redirect(href)
                if not instagram_url:
                    instagram_url = url_limpa_insta

            eh_link, motivo = verificar_se_eh_link_valido(href)
            if eh_link:
                return True, motivo, instagram_url

        # 4. Verifica textos do painel (descrição, sobre, informações adicionais) buscando menção a domínios
        texto_painel = painel.inner_text()
        match_dom = re.search(
            r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com\.br|com|br|org\.br|org|net\.br|net|site|app|io|tech|online|store|shop|me|digital|top|link|bio|med\.br|adv\.br))\b',
            texto_painel,
            re.IGNORECASE
        )
        if match_dom:
            dom_achado = match_dom.group(1).lower()
            if not any(ign in dom_achado for ign in ["google.com", "google.com.br", "instagram.com", "facebook.com", "gstatic.com"]):
                return True, f"Domínio detectado no texto do perfil do Google Maps ({dom_achado})", instagram_url

    except Exception as e:
        pass

    return False, "", instagram_url

def obter_ou_reutilizar_aba_whatsapp(context, telefone: str = "") -> Page:
    """
    Mantém uma ÚNICA aba dedicada ao WhatsApp Web no contexto.
    Se já houver uma aba aberta, reutiliza e navega direto na mesma aba.
    Nunca abre novas abas nem passa pela tela de convite intermediária.
    """
    digitos = extrair_digitos_telefone(telefone) if telefone else ""
    url_alvo = f"https://web.whatsapp.com/send/?phone={digitos}" if digitos else "https://web.whatsapp.com"

    for p in context.pages:
        try:
            if "web.whatsapp.com" in p.url or "whatsapp.com" in p.url:
                p.bring_to_front()
                if digitos and f"phone={digitos}" not in p.url:
                    p.goto(url_alvo, wait_until="domcontentloaded", timeout=20000)
                return p
        except Exception:
            pass

    nova_zap = context.new_page()
    try:
        nova_zap.goto(url_alvo, wait_until="domcontentloaded", timeout=30000)
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
            new_page.wait_for_timeout(600)
            url_atual = new_page.url.lower()
            if "whatsapp.com" in url_atual or "wa.me" in url_atual:
                outras = [p for p in context.pages if "web.whatsapp.com" in p.url and p != new_page]
                if outras:
                    aba_principal = outras[0]
                    match_tel = re.search(r'(?:phone=|wa\.me/)(\d+)', url_atual)
                    if match_tel:
                        aba_principal.goto(f"https://web.whatsapp.com/send/?phone={match_tel.group(1)}", wait_until="domcontentloaded", timeout=20000)
                    aba_principal.bring_to_front()
                    new_page.close()
        except Exception:
            pass

    context.on("page", on_page_opened)

def investigar_instagram(nome: str, cidade: str, page: Page, instagram_url: str = "") -> tuple[bool, str]:
    """
    FOCO 1: Investiga a bio, links e destaques do Instagram da empresa.
    Verifica se na biografia, links ou destaques há direcionamento para site, cardápio digital ou qualquer link,
    principalmente aqueles terminados com .com, .br, .org, biolinks e plataformas.
    """
    alvo_url = instagram_url
    
    # Se não temos a URL do Maps, pesquisa de forma rápida
    if not alvo_url:
        try:
            query = f'site:instagram.com "{nome}" {cidade}'
            url_ddg = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            req = urllib.request.Request(url_ddg, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                html_resp = resp.read().decode("utf-8", errors="ignore")
                match_links = re.findall(r'href="[^"]*(https://(?:www\.)?instagram\.com/[^"&/]+)', html_resp)
                if match_links:
                    alvo_url = match_links[0] + "/"

                for dom in DIGITAL_MENU_DOMAINS:
                    if dom in html_resp.lower():
                        return True, f"Bio do Instagram indexada com link de cardápio/site ({dom})"
        except Exception:
            pass

    if not alvo_url:
        return False, "Nenhum Instagram encontrado"

    # Abre com Playwright no contexto com perfil persistente para inspecionar a bio real
    temp_page = None
    try:
        temp_page = page.context.new_page()
        temp_page.goto(alvo_url, timeout=14000, wait_until="domcontentloaded")
        temp_page.wait_for_timeout(2000)

        # Trata possíveis bloqueios de rede/firewall
        titulo_pg = (temp_page.title() or "").lower()
        if any(b in titulo_pg for b in ["fortiguard", "blocked", "bloqueado", "access denied"]):
            return False, "Instagram inacessível na rede local"

        # Lida com possíveis modais de cookies ou notificações ("Agora não")
        try:
            modal_btn = temp_page.locator('button:has-text("Agora não"), button:has-text("Not Now"), button:has-text("Recusar"), button:has-text("Decline")').first
            if modal_btn.count() > 0 and modal_btn.is_visible():
                modal_btn.click()
        except Exception:
            pass

        # 1. Lê todo o texto da bio/header/seção principal
        bio_container = temp_page.locator('header, main section, main').first
        bio_text = bio_container.inner_text() if bio_container.count() > 0 else temp_page.inner_text('body')
        bio_lower = bio_text.lower()

        # 2. Inspeciona todos os links clicáveis na bio (links externos via l.instagram.com ou botões de link)
        links = temp_page.locator('header a, main a, section a, a[role="link"]').all()
        for l in links:
            href = l.get_attribute("href") or ""
            href_real = decodificar_url_redirect(href).strip()
            href_lower = href_real.lower()

            # Ignora links internos do próprio Instagram
            if any(ign in href_lower for ign in ["/about", "/legal", "/explore", "/reels", "/tagged", "about.meta", "meta.com"]):
                continue

            # Se for link via l.instagram.com ou link externo
            if "l.instagram.com" in href or (href_lower.startswith("http") and "instagram.com" not in href_lower):
                # Verifica se é site, biolink ou cardápio
                eh_link, motivo = verificar_se_eh_link_valido(href_real)
                if eh_link:
                    return True, f"Link detectado na bio do Instagram: {href_real}"

                # Checa extensões solicitadas (.com, .br, .org, etc.)
                for ext in DOMINIOS_EXTENSOES:
                    if ext in href_lower:
                        return True, f"Link com extensão ({ext}) na bio do Instagram: {href_real}"

        # 3. Verifica menção a links ou domínios escritos diretamente no texto da bio
        for dom in DIGITAL_MENU_DOMAINS:
            if dom in bio_lower:
                return True, f"Link/Plataforma ({dom}) mencionado no texto da bio do Instagram"

        # Regex para domínios no texto da bio (.com, .com.br, .br, .org, etc.)
        dominios_texto = re.findall(
            r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com\.br|com|br|org\.br|org|net\.br|net|site|app|io|tech|online|store|shop|me|digital|top|link|bio|med\.br|adv\.br))\b',
            bio_text,
            re.IGNORECASE
        )
        for d in set(dominios_texto):
            d_lower = d.lower()
            if not any(ign in d_lower for ign in ["instagram.com", "facebook.com", "meta.com", "threads.net"]):
                return True, f"Domínio detectado no texto da bio do Instagram: {d}"

        # 4. Inspeciona títulos dos Destaques (Highlights)
        try:
            destaques_textos = temp_page.locator('div[role="tablist"] ~ div, section main ul li, div[role="listitem"]').all_inner_texts()
            texto_destaques = " ".join(destaques_textos).lower()
            termos_destaques = ["cardápio", "cardapio", "menu digital", "delivery", "fazer pedido", "peça online", "pedidos", "site", "link"]
            for termo in termos_destaques:
                if termo in texto_destaques:
                    return True, f"Destaque de cardápio/pedidos detectado no Instagram: '{termo}'"
        except Exception:
            pass

    except Exception:
        pass
    finally:
        if temp_page:
            try:
                temp_page.close()
            except Exception:
                pass

    return False, "Instagram verificado: sem link, site ou cardápio na bio"

def investigar_whatsapp_bot_e_perfil(telefone: str, nome: str, cidade: str, page: Page = None) -> tuple[bool, str]:
    """
    FOCO 2 e FOCO 3:
    - Investiga Bots de WhatsApp / mensagens automáticas de pedidos via HTTP rápido.
    - Investiga se o número de WhatsApp está cadastrado em plataformas de cardápio digital (Anota AI, Goomer, Delivery Direto).
    """
    digitos = extrair_digitos_telefone(telefone)
    if not digitos:
        return False, ""

    # 1. Inspeciona a API pública do WhatsApp via requisição HTTP direta
    url_wa = f"https://api.whatsapp.com/send/?phone={digitos}"
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        req = urllib.request.Request(url_wa, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
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
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        req = urllib.request.Request(url_ddg, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
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
        with urllib.request.urlopen(req, timeout=6) as resp:
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
