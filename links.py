"""
Classificador de Links.

Responsável por decidir, de forma determinística, o que cada URL representa:
rede social, mensageiro (WhatsApp/Telegram), agregador de links (Linktree),
encurtador, marketplace, sistema de serviço (agendamento/cardápio/pedidos),
construtor de sites/landing pages ou site próprio.

Regras-chave:
  * A comparação de domínios é feita por SUFIXO DE HOST (nunca por substring),
    evitando falsos positivos como "linx.com.br" ser confundido com "x.com".
  * wa.me, api.whatsapp.com, instagram.com e demais redes sociais NUNCA são site.
  * Agregadores (Linktree etc.) e encurtadores (bit.ly etc.) não são site por si só:
    precisam ser expandidos/resolvidos para inspecionar o destino real.
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from enum import Enum


class TipoLink(str, Enum):
    INVALIDO = "invalido"
    CONTATO = "contato"                # tel:, mailto:
    INTERNO_GOOGLE = "interno_google"  # Maps, suporte, políticas do Google
    REDE_SOCIAL = "rede_social"
    MENSAGEIRO = "mensageiro"          # WhatsApp, Telegram, Messenger
    AGREGADOR = "agregador"            # Linktree, Beacons... (precisa expandir)
    ENCURTADOR = "encurtador"          # bit.ly, tinyurl... (precisa resolver)
    MARKETPLACE = "marketplace"        # iFood, Doctoralia... (perfil em plataforma de terceiros)
    FERRAMENTA = "ferramenta"          # Google Forms, links de pagamento, e-mail gratuito
    PORTAL = "portal"                  # Portais de notícia/governo (não é site do negócio)
    SISTEMA = "sistema"                # Agendamento, cardápio digital, pedidos, app próprio
    CONSTRUTOR = "construtor_site"     # Wix, Canva Sites, Google Sites, lojas virtuais
    SITE_PROPRIO = "site_proprio"      # Domínio próprio


# Tipos que, por definição, representam "site / sistema próprio / landing page"
TIPOS_DESQUALIFICANTES = {TipoLink.SISTEMA, TipoLink.CONSTRUTOR, TipoLink.SITE_PROPRIO}

# Tipos que exigem uma segunda etapa de inspeção (expandir / resolver redirecionamento)
TIPOS_A_EXPANDIR = {TipoLink.AGREGADOR, TipoLink.ENCURTADOR}

# --------------------------------------------------------------------------------------
# Bases de conhecimento (comparação por sufixo de host)
# --------------------------------------------------------------------------------------

REDES_SOCIAIS = {
    "instagram.com", "instagr.am", "facebook.com", "fb.com", "fb.me", "fb.watch",
    "tiktok.com", "youtube.com", "youtu.be", "twitter.com", "x.com", "linkedin.com",
    "lnkd.in", "pinterest.com", "pinterest.com.br", "pin.it", "threads.net", "threads.com",
    "kwai.com", "kw.ai", "snapchat.com", "tumblr.com", "behance.net", "flickr.com",
    "vimeo.com", "twitch.tv", "discord.gg", "discord.com", "reddit.com", "spotify.com",
    "soundcloud.com", "deezer.com", "medium.com", "substack.com", "bsky.app",
}

MENSAGEIROS = {
    "wa.me", "whatsapp.com", "whatsapp.net", "wa.link", "whatsapp.link", "t.me",
    "telegram.me", "telegram.org", "telegram.dog", "m.me", "ig.me", "messenger.com",
    "signal.me", "wpp.link",
}

AGREGADORES = {
    "linktr.ee", "linktree.com", "beacons.ai", "beacons.page", "instabio.cc", "bio.link",
    "biolink.info", "campsite.bio", "heylink.me", "taplink.cc", "taplink.at", "taplink.ws",
    "lnk.bio", "linkin.bio", "solo.to", "linkbio.co", "milkshake.app", "msha.ke",
    "allmylinks.com", "linkme.bio", "linkr.bio", "linkfly.to", "bio.site", "hoo.be",
    "tap.bio", "about.me", "linkpop.com", "koji.to", "wpp.bio", "zaap.bio", "linklist.bio",
    "lynk.id", "flow.page", "direct.me", "manylink.co", "biolinky.co", "bio.fm", "pop.bio",
    "linkbio.me", "link.me", "linkz.ai", "contate.me",
}

ENCURTADORES = {
    "bit.ly", "bitly.com", "tinyurl.com", "cutt.ly", "is.gd", "ow.ly", "rebrand.ly",
    "shorturl.at", "encurtador.com.br", "t.co", "goo.gl", "tiny.cc", "rb.gy", "s.id",
    "l.ead.me", "bl.ink", "abre.ai", "encr.pw", "u.to", "shre.ink", "short.io", "v.gd",
}

# Domínios do Google que NÃO são site do negócio (host, prefixo_de_caminho)
INTERNOS_GOOGLE = [
    ("google.com", "/maps"), ("google.com.br", "/maps"), ("maps.google.com", ""),
    ("maps.google.com.br", ""), ("maps.app.goo.gl", ""), ("goo.gl", "/maps"), ("g.page", ""),
    ("g.co", ""), ("support.google.com", ""), ("accounts.google.com", ""),
    ("policies.google.com", ""), ("google.com", "/intl"), ("google.com.br", "/intl"),
    ("google.com", "/contributionpolicy"), ("google.com", "/search"), ("google.com.br", "/search"),
    ("google.com", "/local"), ("gstatic.com", ""), ("googleusercontent.com", ""),
    ("business.google.com", ""), ("business.site", ""), ("negocio.site", ""),
    ("google.com", "/travel"), ("google.com", "/url"),
]

FERRAMENTAS = [
    ("docs.google.com", ""), ("forms.gle", ""), ("drive.google.com", ""),
    ("photos.app.goo.gl", ""), ("photos.google.com", ""), ("paypal.me", ""), ("paypal.com", ""),
    ("picpay.me", ""), ("mpago.la", ""), ("mercadopago.com.br", ""), ("link.mercadopago.com.br", ""),
    ("nubank.com.br", "/cobrar"), ("pag.ae", ""), ("pagseguro.uol.com.br", ""),
    ("maps.apple.com", ""), ("waze.com", ""), ("ul.waze.com", ""),
]

MARKETPLACES = {
    "ifood.com.br", "rappi.com.br", "aiqfome.com", "99app.com", "ubereats.com",
    "doctoralia.com.br", "boaconsulta.com", "getninjas.com.br", "olx.com.br",
    "mercadolivre.com.br", "mercadolibre.com", "shopee.com.br", "elo7.com.br",
    "amazon.com.br", "magazineluiza.com.br", "magalu.com", "airbnb.com", "airbnb.com.br",
    "booking.com", "tripadvisor.com", "tripadvisor.com.br", "gympass.com", "wellhub.com",
    "totalpass.com.br", "totalpass.com", "jusbrasil.com.br", "habitissimo.com.br",
    "triider.com.br", "guiamais.com.br", "apontador.com.br", "telelistas.net", "yelp.com",
    "classpass.com", "hotmart.com", "kiwify.com.br", "eduzz.com", "sympla.com.br",
    "eventbrite.com.br", "enjoei.com.br", "zapimoveis.com.br", "vivareal.com.br",
    "imovelweb.com.br", "webmotors.com.br", "catalogo.org.br",
}

SISTEMAS = {
    # Cardápio digital / pedidos / delivery próprio
    "anota.ai", "goomer.app", "goomer.com.br", "ola.click", "deliverydireto.com.br",
    "instadelivery.com.br", "cardapioweb.com", "cardapio.menu", "menudigital.com",
    "menudino.com", "saipos.com", "pedir.digital", "hubt.com.br", "neemo.com.br",
    "kyte.site", "kyte.com.br", "takeat.app", "cardapio.ai", "cardapio.delivery",
    "cardapio.live", "pedido.delivery", "consumer.com.br", "menu.ifood.com.br",
    "delivery.much.com.br", "vitrine.digital", "minhaloja.app",
    # Agendamento online
    "trinks.com", "booksy.com", "agendapro.com", "simplybook.me", "simplybook.it",
    "calendly.com", "appbarber.com.br", "avec.app", "avec.beauty", "salaovip.com.br",
    "beautydate.com.br", "fresha.com", "vagaro.com", "setmore.com", "acuityscheduling.com",
    "as.me", "youcanbook.me", "squareup.com", "bestbarbers.app", "inbarber.com.br",
    "cashbarber.com.br", "nextfit.com.br", "tecnofit.com.br", "w12app.com.br",
    "clinicorp.com", "feegow.com", "iclinic.com.br", "simplesdental.com", "calendar.app.google",
    "zcal.co", "cal.com", "tidycal.com", "koalendar.com", "agendasalao.com.br",
    "agendamento.app", "reservio.com", "getinapp.com.br", "tagme.com.br", "reservafacil.com.br",
    # Lojas de aplicativo (app próprio)
    "apps.apple.com",
}
SISTEMAS_COM_CAMINHO = [("play.google.com", "/store/apps")]

CONSTRUTORES = {
    "wixsite.com", "wix.com", "editorx.io", "canva.site", "sites.google.com", "carrd.co",
    "webnode.page", "webnode.com.br", "webnode.com", "wordpress.com", "blogspot.com",
    "weebly.com", "squarespace.com", "square.site", "jimdosite.com", "jimdo.com",
    "strikingly.com", "mystrikingly.com", "godaddysites.com", "site123.me", "webflow.io",
    "framer.website", "framer.ai", "framer.app", "notion.site", "netlify.app", "vercel.app",
    "github.io", "gitlab.io", "pages.dev", "glitch.me", "herokuapp.com", "firebaseapp.com",
    "web.app", "lojaintegrada.com.br", "mitiendanube.com", "nuvemshop.com.br",
    "myshopify.com", "ecwid.com", "lpages.co", "leadpages.net", "unbouncepages.com",
    "elementor.cloud", "hostingersite.com", "zyrosite.com", "ueniweb.com", "wixstudio.io",
    "my.canva.site", "lovable.app", "bolt.host", "replit.app", "durable.co",
}

PORTAIS = {
    "globo.com", "uol.com.br", "terra.com.br", "r7.com", "metropoles.com", "correiobraziliense.com.br",
    "gov.br", "jus.br", "leg.br", "wikipedia.org", "estadao.com.br", "folha.uol.com.br",
    "cnnbrasil.com.br", "band.uol.com.br", "sbt.com.br", "abril.com.br",
}

PROVEDORES_EMAIL_GRATUITOS = {
    "gmail.com", "googlemail.com", "hotmail.com", "hotmail.com.br", "outlook.com",
    "outlook.com.br", "live.com", "msn.com", "yahoo.com", "yahoo.com.br", "ymail.com",
    "icloud.com", "me.com", "mac.com", "bol.com.br", "uol.com.br", "terra.com.br",
    "ig.com.br", "globo.com", "globomail.com", "zipmail.com.br", "protonmail.com",
    "proton.me", "aol.com", "gmx.com", "yandex.com", "r7.com",
}

# Hosts de CDN/infra que aparecem dentro de páginas e NUNCA são link do negócio
HOSTS_INFRA = {
    "cdninstagram.com", "fbcdn.net", "fbsbx.com", "akamaihd.net", "cloudfront.net",
    "googleapis.com", "gstatic.com", "googletagmanager.com", "google-analytics.com",
    "doubleclick.net", "jsdelivr.net", "unpkg.com", "cloudflare.com", "cloudflareinsights.com",
    "sentry.io", "segment.com", "hotjar.com", "w3.org", "schema.org", "ogp.me",
    "linktr.ee/s", "typekit.net", "fontawesome.com", "bootstrapcdn.com", "jquery.com",
}

EXTENSOES_ARQUIVOS = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".woff",
    ".woff2", ".ttf", ".mp4", ".mp3", ".json", ".xml", ".map",
)

# Regex para domínios escritos em texto livre (bio, descrição). Ignora e-mails (prefixo "@").
_TLDS = (
    r"com\.br|net\.br|org\.br|adv\.br|med\.br|odo\.br|arq\.br|eng\.br|vet\.br|psc\.br|"
    r"art\.br|blog\.br|eco\.br|esp\.br|etc\.br|far\.br|fot\.br|ind\.br|inf\.br|nom\.br|"
    r"pro\.br|tur\.br|com|net|org|br|site|online|tech|digital|app|io|dev|store|shop|"
    r"link|page|live|menu|delivery|pro|top|me|bio|co|ai|info|biz|club|studio|space|"
    r"website|art|beauty|salon|hair|clinic|dental|health|law|adv|fit|cafe|bar|pizza"
)
REGEX_DOMINIO_TEXTO = re.compile(
    r"(?<![@\w.-])((?:https?://)?(?:www\.)?[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*\.(?:" + _TLDS + r"))(?![\w@-])(/[^\s]*)?",
    re.IGNORECASE,
)
REGEX_EMAIL = re.compile(r"[\w.+-]+@([a-z0-9-]+(?:\.[a-z0-9-]+)+)", re.IGNORECASE)
REGEX_URL = re.compile(r"https?://[^\s\"'<>\\)]+", re.IGNORECASE)


@dataclass(frozen=True)
class ClassificacaoLink:
    url_original: str
    url: str          # URL real (após decodificar redirecionadores)
    host: str
    tipo: TipoLink
    motivo: str

    @property
    def desqualifica(self) -> bool:
        return self.tipo in TIPOS_DESQUALIFICANTES

    @property
    def precisa_expandir(self) -> bool:
        return self.tipo in TIPOS_A_EXPANDIR


# --------------------------------------------------------------------------------------
# Utilitários de URL
# --------------------------------------------------------------------------------------

def host_corresponde(host: str, dominio: str) -> bool:
    """True se `host` é exatamente `dominio` ou um subdomínio dele."""
    host = (host or "").lower().strip(".")
    dominio = dominio.lower().strip(".")
    return host == dominio or host.endswith("." + dominio)


def _corresponde_algum(host: str, dominios) -> str:
    for d in dominios:
        if host_corresponde(host, d):
            return d
    return ""


def _corresponde_com_caminho(host: str, caminho: str, regras) -> str:
    for dominio, prefixo in regras:
        if host_corresponde(host, dominio) and caminho.startswith(prefixo):
            return dominio + prefixo
    return ""


def decodificar_redirect(url: str) -> str:
    """Extrai a URL de destino de redirecionadores do Google, Instagram, Facebook e Bing."""
    if not url:
        return ""
    url = url.strip()
    for _ in range(3):  # redirecionadores podem estar aninhados
        try:
            parsed = urllib.parse.urlparse(url if "://" in url else "https://" + url)
        except ValueError:
            return url
        host = (parsed.hostname or "").lower()
        qs = urllib.parse.parse_qs(parsed.query)
        destino = ""
        if host_corresponde(host, "l.instagram.com") and "u" in qs:
            destino = qs["u"][0]
        elif (host_corresponde(host, "l.facebook.com") or host_corresponde(host, "lm.facebook.com")) and "u" in qs:
            destino = qs["u"][0]
        elif (host.startswith("google.") or ".google." in host or host.startswith("www.google.")) and parsed.path == "/url":
            destino = (qs.get("q") or qs.get("url") or [""])[0]
        if not destino:
            return url
        url = urllib.parse.unquote(destino)
    return url


def normalizar_url(url: str) -> str:
    """Remove espaços, decodifica redirecionadores e garante esquema http(s)."""
    url = decodificar_redirect((url or "").strip().strip("\"'<>()[]{}.,;"))
    if not url:
        return ""
    if url.lower().startswith(("tel:", "mailto:", "javascript:", "#", "data:", "intent:", "sms:")):
        return url
    if "://" not in url:
        url = "https://" + url.lstrip("/")
    return url


def extrair_host(url: str) -> str:
    try:
        host = (urllib.parse.urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def eh_host_infra(url: str) -> bool:
    host = extrair_host(url)
    caminho = urllib.parse.urlparse(url).path.lower() if url else ""
    if any(host_corresponde(host, h) for h in HOSTS_INFRA if "/" not in h):
        return True
    return caminho.endswith(EXTENSOES_ARQUIVOS)


# --------------------------------------------------------------------------------------
# Classificação
# --------------------------------------------------------------------------------------

def classificar_link(url_original: str) -> ClassificacaoLink:
    """Classifica uma URL em um TipoLink, com o motivo legível."""
    url = normalizar_url(url_original)
    if not url:
        return ClassificacaoLink(url_original, "", "", TipoLink.INVALIDO, "Link vazio")

    baixo = url.lower()
    if baixo.startswith(("tel:", "mailto:", "sms:")):
        return ClassificacaoLink(url_original, url, "", TipoLink.CONTATO, "Link de contato (telefone/e-mail)")
    if baixo.startswith(("javascript:", "#", "data:", "intent:")):
        return ClassificacaoLink(url_original, url, "", TipoLink.INVALIDO, "Link interno de página")

    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return ClassificacaoLink(url_original, url, "", TipoLink.INVALIDO, "URL malformada")

    host = extrair_host(url)
    caminho = parsed.path or ""
    if not host or "." not in host:
        return ClassificacaoLink(url_original, url, host, TipoLink.INVALIDO, "Host inválido")

    def c(tipo: TipoLink, motivo: str) -> ClassificacaoLink:
        return ClassificacaoLink(url_original, url, host, tipo, motivo)

    # Ordem importa: regras com caminho e mais específicas primeiro.
    if m := _corresponde_com_caminho(host, caminho, INTERNOS_GOOGLE):
        return c(TipoLink.INTERNO_GOOGLE, f"Link interno do Google ({m})")
    if m := _corresponde_algum(host, MENSAGEIROS):
        return c(TipoLink.MENSAGEIRO, f"Link de mensageiro ({m}) — não é site")
    if m := _corresponde_algum(host, REDES_SOCIAIS):
        return c(TipoLink.REDE_SOCIAL, f"Rede social ({m}) — não é site")
    if m := _corresponde_com_caminho(host, caminho, FERRAMENTAS):
        return c(TipoLink.FERRAMENTA, f"Ferramenta de terceiros ({m}) — não é site")
    if m := _corresponde_algum(host, SISTEMAS) or _corresponde_com_caminho(host, caminho, SISTEMAS_COM_CAMINHO):
        return c(TipoLink.SISTEMA, f"Sistema de serviço (agendamento/cardápio/pedidos/app) em {m}")
    if m := _corresponde_algum(host, CONSTRUTORES):
        return c(TipoLink.CONSTRUTOR, f"Site/landing page em construtor ({m})")
    if m := _corresponde_algum(host, AGREGADORES):
        return c(TipoLink.AGREGADOR, f"Agregador de links ({m}) — precisa inspecionar o conteúdo")
    if m := _corresponde_algum(host, ENCURTADORES):
        return c(TipoLink.ENCURTADOR, f"Link encurtado ({m}) — precisa resolver o destino")
    if m := _corresponde_algum(host, MARKETPLACES):
        return c(TipoLink.MARKETPLACE, f"Perfil em marketplace/plataforma de terceiros ({m})")
    if m := _corresponde_algum(host, PORTAIS):
        return c(TipoLink.PORTAL, f"Portal de terceiros ({m}) — não é site do negócio")
    if host.startswith("google.") or ".google." in host:
        return c(TipoLink.INTERNO_GOOGLE, "Domínio do Google")

    # Qualquer outro host com TLD válido é considerado domínio próprio.
    if re.fullmatch(r"(?:[a-z0-9-]+\.)+[a-z]{2,24}", host) or re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host):
        return c(TipoLink.SITE_PROPRIO, f"Domínio próprio ({host})")
    return c(TipoLink.INVALIDO, f"Host não reconhecido ({host})")


def extrair_dominios_de_texto(texto: str) -> list[str]:
    """
    Encontra domínios/URLs escritos em texto livre (ex.: bio "acesse meusite.com.br").
    Ignora e-mails ("contato@gmail.com" não gera "gmail.com").
    """
    if not texto:
        return []
    encontrados: list[str] = []
    for m in REGEX_DOMINIO_TEXTO.finditer(texto):
        dominio = m.group(1)
        caminho = m.group(2) or ""
        candidato = (dominio + caminho).rstrip(".,;:!?)")
        # Descarta números decimais/horários soltos como "4.5" (sem letras no host)
        if not re.search(r"[a-z]", dominio.split(".")[0], re.IGNORECASE):
            continue
        if candidato.lower() not in (e.lower() for e in encontrados):
            encontrados.append(candidato)
    return encontrados


def extrair_dominios_de_email(texto: str) -> list[str]:
    """Retorna domínios de e-mails que NÃO são provedores gratuitos (indício de domínio próprio)."""
    dominios = []
    for m in REGEX_EMAIL.finditer(texto or ""):
        dom = m.group(1).lower().rstrip(".")
        if not _corresponde_algum(dom, PROVEDORES_EMAIL_GRATUITOS) and dom not in dominios:
            dominios.append(dom)
    return dominios


def extrair_urls_de_html(html: str, ignorar_host: str = "") -> list[str]:
    """Extrai URLs externas de um HTML (href e JSON embutido), sem assets/CDN."""
    if not html:
        return []
    texto = html.replace("\\/", "/").replace("\\u002F", "/").replace("&amp;", "&")
    urls: list[str] = []
    candidatos = re.findall(r'href=["\']([^"\']+)["\']', texto, re.IGNORECASE) + REGEX_URL.findall(texto)
    for bruto in candidatos:
        url = normalizar_url(bruto)
        if not url.lower().startswith("http"):
            continue
        host = extrair_host(url)
        if not host or eh_host_infra(url):
            continue
        if ignorar_host and host_corresponde(host, ignorar_host):
            continue
        if url not in urls:
            urls.append(url)
    return urls
