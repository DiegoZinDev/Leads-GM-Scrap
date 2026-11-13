"""
Módulo Unificado de Verificação de Presença Digital e Redes Sociais.

Concentra em um único módulo coeso:
  1. Classificador determinístico de URLs (por sufixo exato de host):
     - wa.me, api.whatsapp.com, instagram.com e demais redes sociais NUNCA são site.
     - Sistemas próprios (AppBarber, Trinks, Anota AI, Goomer, Calendly...),
       construtores/landing pages (Canva, Wix, Google Sites, Carrd...) e domínios
       próprios (.com.br, .com, .adv.br, .med.br...) SÃO considerados site/sistema.
     - Agregadores (Linktree, Beacons, Taplink...) e encurtadores (bit.ly...) são
       abertos e seus links internos inspecionados individualmente.
  2. Cliente de inspeção de perfis do Instagram (Bio, Links externos, E-mail comercial
     e Stickers de Link nos Destaques / Highlights, via API Web + Fallback DOM).
  3. Verificador de Presença Digital (Google Maps + Instagram + Web + Validação de Site Ativo).
"""

from __future__ import annotations

import base64
import random
import re
import time
import unicodedata
import urllib.parse
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from enum import Enum

from playwright.sync_api import Page

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


# ======================================================================================
# 1. CLASSIFICADOR DE LINKS E EXTRAÇÃO DE DOMÍNIOS
# ======================================================================================

class TipoLink(str, Enum):
    INVALIDO = "invalido"
    CONTATO = "contato"                # tel:, mailto:
    INTERNO_GOOGLE = "interno_google"  # Maps, suporte, políticas do Google
    REDE_SOCIAL = "rede_social"
    MENSAGEIRO = "mensageiro"          # WhatsApp, Telegram, Messenger
    AGREGADOR = "agregador"            # Linktree, Beacons... (precisa expandir)
    ENCURTADOR = "encurtador"          # bit.ly, tinyurl... (precisa resolver)
    MARKETPLACE = "marketplace"        # iFood, Doctoralia... (perfil em plataforma de terceiros)
    FERRAMENTA = "ferramenta"          # Google Forms, links de pagamento
    PORTAL = "portal"                  # Portais de notícia/governo
    SISTEMA = "sistema"                # Agendamento, cardápio digital, pedidos, app próprio
    CONSTRUTOR = "construtor_site"     # Wix, Canva Sites, Google Sites, lojas virtuais
    SITE_PROPRIO = "site_proprio"      # Domínio próprio


TIPOS_DESQUALIFICANTES = {TipoLink.SISTEMA, TipoLink.CONSTRUTOR, TipoLink.SITE_PROPRIO}
TIPOS_A_EXPANDIR = {TipoLink.AGREGADOR, TipoLink.ENCURTADOR}

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
    "anota.ai", "goomer.app", "goomer.com.br", "ola.click", "deliverydireto.com.br",
    "instadelivery.com.br", "cardapioweb.com", "cardapio.menu", "menudigital.com",
    "menudino.com", "saipos.com", "pedir.digital", "hubt.com.br", "neemo.com.br",
    "kyte.site", "kyte.com.br", "takeat.app", "cardapio.ai", "cardapio.delivery",
    "cardapio.live", "pedido.delivery", "consumer.com.br", "menu.ifood.com.br",
    "delivery.much.com.br", "vitrine.digital", "minhaloja.app",
    "trinks.com", "booksy.com", "agendapro.com", "simplybook.me", "simplybook.it",
    "calendly.com", "appbarber.com.br", "avec.app", "avec.beauty", "salaovip.com.br",
    "beautydate.com.br", "fresha.com", "vagaro.com", "setmore.com", "acuityscheduling.com",
    "as.me", "youcanbook.me", "squareup.com", "bestbarbers.app", "inbarber.com.br",
    "cashbarber.com.br", "nextfit.com.br", "tecnofit.com.br", "w12app.com.br",
    "clinicorp.com", "feegow.com", "iclinic.com.br", "simplesdental.com", "calendar.app.google",
    "zcal.co", "cal.com", "tidycal.com", "koalendar.com", "agendasalao.com.br",
    "agendamento.app", "reservio.com", "getinapp.com.br", "tagme.com.br", "reservafacil.com.br",
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

HOSTS_INFRA = {
    "cdninstagram.com", "fbcdn.net", "fbsbx.com", "akamaihd.net", "cloudfront.net",
    "googleapis.com", "gstatic.com", "googletagmanager.com", "google-analytics.com",
    "doubleclick.net", "jsdelivr.net", "unpkg.com", "cloudflare.com", "cloudflareinsights.com",
    "sentry.io", "segment.com", "hotjar.com", "w3.org", "schema.org", "ogp.me",
    "typekit.net", "fontawesome.com", "bootstrapcdn.com", "jquery.com",
}

EXTENSOES_ARQUIVOS = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".mp4", ".mp3", ".json", ".xml", ".map",
)

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
    url: str
    host: str
    tipo: TipoLink
    motivo: str

    @property
    def desqualifica(self) -> bool:
        return self.tipo in TIPOS_DESQUALIFICANTES

    @property
    def precisa_expandir(self) -> bool:
        return self.tipo in TIPOS_A_EXPANDIR


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
    """Extrai a URL de destino de redirecionadores do Google, Instagram e Facebook."""
    if not url:
        return ""
    url = url.strip()
    for _ in range(3):
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
    if any(host_corresponde(host, h) for h in HOSTS_INFRA):
        return True
    return caminho.endswith(EXTENSOES_ARQUIVOS)


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

    if re.fullmatch(r"(?:[a-z0-9-]+\.)+[a-z]{2,24}", host) or re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host):
        return c(TipoLink.SITE_PROPRIO, f"Domínio próprio ({host})")
    return c(TipoLink.INVALIDO, f"Host não reconhecido ({host})")


def extrair_dominios_de_texto(texto: str) -> list[str]:
    """Encontra domínios/URLs escritos em texto livre, ignorando e-mails e notas decimais."""
    if not texto:
        return []
    encontrados: list[str] = []
    for m in REGEX_DOMINIO_TEXTO.finditer(texto):
        dominio = m.group(1)
        caminho = m.group(2) or ""
        candidato = (dominio + caminho).rstrip(".,;:!?)")
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


def extrair_urls_de_html(html_str: str, ignorar_host: str = "") -> list[str]:
    """Extrai URLs externas de um HTML (href e JSON embutido), sem assets/CDN."""
    if not html_str:
        return []
    texto = html_str.replace("\\/", "/").replace("\\u002F", "/").replace("&amp;", "&")
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


# ======================================================================================
# 2. INSPEÇÃO DE PERFIS DO INSTAGRAM (BIO, LINKS E DESTAQUES)
# ======================================================================================

IG_APP_ID = "936619743392459"
URL_BASE_IG = "https://www.instagram.com"
ROTAS_NAO_PERFIL = {
    "p", "reel", "reels", "explore", "stories", "accounts", "direct", "about", "legal",
    "developer", "tv", "web", "api", "challenge", "privacy", "emails", "session", "s",
}
PALAVRAS_GENERICAS = {
    "barbearia", "barber", "shop", "salao", "salão", "beleza", "studio", "estudio", "espaco",
    "espaço", "clinica", "clínica", "odontologia", "odonto", "advocacia", "advogados",
    "advogado", "escritorio", "escritório", "restaurante", "bar", "nail", "designer", "hair",
    "academia", "fisioterapia", "estetica", "estética", "centro", "de", "da", "do", "das",
    "dos", "e", "&", "the", "and", "ltda", "me", "eireli", "df", "brasilia", "brasília",
}
_CHAVES_LINK_IG = {"url", "weburi", "web_uri", "link", "story_link", "external_url", "link_url", "destination_url"}


class InstagramIndisponivel(Exception):
    """Instagram bloqueado na rede, sem login ou com limite de requisições atingido."""


@dataclass
class PerfilInstagram:
    username: str
    acessivel: bool = False
    fonte: str = ""
    erro: str = ""
    user_id: str = ""
    nome_completo: str = ""
    biografia: str = ""
    url_externa: str = ""
    links_bio: list[str] = field(default_factory=list)
    telefone_comercial: str = ""
    email_comercial: str = ""
    conta_comercial: bool = False
    categoria: str = ""
    seguidores: int = 0
    seguindo: int = 0
    publicacoes: int = 0
    privado: bool = False
    verificado: bool = False
    qtd_destaques: int = 0
    destaques_verificados: bool = False
    titulos_destaques: list[str] = field(default_factory=list)
    links_destaques: list[str] = field(default_factory=list)
    urls_destaques_dom: list[str] = field(default_factory=list, repr=False)

    @property
    def url(self) -> str:
        return f"{URL_BASE_IG}/{self.username}/"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["url"] = self.url
        return d


def extrair_username(url: str) -> str:
    """Extrai o @ de qualquer variação de URL do Instagram. Retorna '' se não for perfil."""
    if not url:
        return ""
    url = normalizar_url(url)
    host = extrair_host(url)
    if not (host_corresponde(host, "instagram.com") or host_corresponde(host, "instagr.am")):
        return ""
    partes = [p for p in urllib.parse.urlparse(url).path.split("/") if p]
    if not partes:
        return ""
    if partes[0].lower() == "stories" and len(partes) >= 2 and partes[1].lower() != "highlights":
        partes = partes[1:]
    usuario = partes[0].lstrip("@")
    if usuario.lower() in ROTAS_NAO_PERFIL or not re.fullmatch(r"[A-Za-z0-9._]{1,30}", usuario):
        return ""
    return usuario.lower()


def _int(valor) -> int:
    try:
        return int(valor or 0)
    except (TypeError, ValueError):
        return 0


def parse_web_profile_info(dados: dict, username: str = "") -> PerfilInstagram:
    """Converte a resposta de /api/v1/users/web_profile_info/ em PerfilInstagram."""
    user = (dados or {}).get("data", {}).get("user") or {}
    if not user:
        raise ValueError("Resposta sem dados de usuário")
    links_bio = []
    for item in user.get("bio_links") or []:
        u = normalizar_url(item.get("url") or item.get("lynx_url") or "")
        if u and u not in links_bio:
            links_bio.append(u)
    externa = normalizar_url(user.get("external_url") or "")
    if externa and externa not in links_bio:
        links_bio.insert(0, externa)
    return PerfilInstagram(
        username=(user.get("username") or username).lower(),
        acessivel=True,
        fonte="api",
        user_id=str(user.get("id") or ""),
        nome_completo=user.get("full_name") or "",
        biografia=user.get("biography") or "",
        url_externa=externa,
        links_bio=links_bio,
        telefone_comercial=(user.get("business_phone_number") or "").strip(),
        email_comercial=(user.get("business_email") or "").strip(),
        conta_comercial=bool(user.get("is_business_account") or user.get("is_professional_account")),
        categoria=user.get("category_name") or user.get("business_category_name") or "",
        seguidores=_int((user.get("edge_followed_by") or {}).get("count")),
        seguindo=_int((user.get("edge_follow") or {}).get("count")),
        publicacoes=_int((user.get("edge_owner_to_timeline_media") or {}).get("count")),
        privado=bool(user.get("is_private")),
        verificado=bool(user.get("is_verified")),
        qtd_destaques=_int(user.get("highlight_reel_count")),
    )


def _coletar_urls_recursivo(obj, saida: list[str], chave_pai: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            _coletar_urls_recursivo(v, saida, k.lower())
    elif isinstance(obj, list):
        for v in obj:
            _coletar_urls_recursivo(v, saida, chave_pai)
    elif isinstance(obj, str) and chave_pai in _CHAVES_LINK_IG and obj.lower().startswith(("http", "www.")):
        url = normalizar_url(obj)
        host = extrair_host(url)
        if url and not eh_host_infra(url) and not host_corresponde(host, "instagram.com") and url not in saida:
            saida.append(url)


def parse_reels_media(dados: dict) -> list[str]:
    """Extrai URLs externas de stickers de link/CTA dos stories de destaques."""
    urls: list[str] = []
    reels = (dados or {}).get("reels") or {}
    if not reels and isinstance((dados or {}).get("reels_media"), list):
        reels = {str(i): r for i, r in enumerate(dados["reels_media"])}
    for reel in reels.values():
        for item in reel.get("items") or []:
            for chave in ("story_link_stickers", "story_cta", "link", "story_link", "ad_link", "story_bloks_stickers"):
                if chave in item:
                    _coletar_urls_recursivo(item[chave], urls, chave)
            caption = item.get("caption")
            texto = caption.get("text", "") if isinstance(caption, dict) else ""
            for u in REGEX_URL.findall(texto or ""):
                u = normalizar_url(u)
                if u not in urls:
                    urls.append(u)
    return urls


def normalizar_nome(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^a-z0-9 ]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def nome_distintivo(nome: str) -> str:
    tokens = [t for t in normalizar_nome(nome).split() if t not in PALAVRAS_GENERICAS and len(t) > 1]
    return " ".join(tokens)


def similaridade_nomes(a: str, b: str) -> float:
    a_n, b_n = normalizar_nome(a), normalizar_nome(b)
    if not a_n or not b_n:
        return 0.0
    compacto_a, compacto_b = a_n.replace(" ", ""), b_n.replace(" ", "")
    base = SequenceMatcher(None, compacto_a, compacto_b).ratio()
    dist_a = nome_distintivo(a).replace(" ", "")
    if dist_a and len(dist_a) >= 4 and dist_a in compacto_b:
        base = max(base, 0.85)
    return round(base, 3)


def _ultimos_digitos(telefone: str, n: int = 8) -> str:
    d = re.sub(r"\D", "", telefone or "")
    return d[-n:] if len(d) >= n else ""


def telefones_no_texto(texto: str) -> list[str]:
    """Extrai números de telefone brasileiros de um texto livre, links wa.me inclusos."""
    achados = []
    for m in re.finditer(r"(?:wa\.me/|phone=)(\d{10,13})", texto or ""):
        achados.append(m.group(1))
    for m in re.finditer(r"(?:\+?55[\s.-]?)?\(?\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}", texto or ""):
        d = re.sub(r"\D", "", m.group(0))
        if 10 <= len(d) <= 13:
            achados.append(d)
    return list(dict.fromkeys(achados))


def pontuar_correspondencia(perfil: PerfilInstagram, nome: str, telefone: str, cidade: str) -> tuple[int, list[str]]:
    """Pontua (0-100+) a probabilidade de um perfil pertencer ao negócio do Maps."""
    pontos, motivos = 0, []
    alvo = _ultimos_digitos(telefone)
    if alvo:
        textos = " ".join([perfil.telefone_comercial, perfil.biografia, " ".join(perfil.links_bio)])
        if any(_ultimos_digitos(t) == alvo for t in telefones_no_texto(textos) + [perfil.telefone_comercial]):
            pontos += 60
            motivos.append("telefone idêntico ao do Google Maps")
    sim = max(similaridade_nomes(nome, perfil.nome_completo), similaridade_nomes(nome, perfil.username))
    if sim >= 0.85:
        pontos += 40
        motivos.append(f"nome muito semelhante ({sim:.0%})")
    elif sim >= 0.7:
        pontos += 25
        motivos.append(f"nome semelhante ({sim:.0%})")
    cidade_tokens = [t for t in normalizar_nome(cidade).split() if len(t) > 2 and t not in {"df", "go"}]
    bio_n = normalizar_nome(perfil.biografia + " " + perfil.nome_completo)
    if cidade_tokens and any(t in bio_n for t in cidade_tokens):
        pontos += 15
        motivos.append("cidade/região citada no perfil")
    return pontos, motivos


class ClienteInstagram:
    """Acessa o Instagram usando o contexto persistente (sessão logada) do Playwright."""

    PONTUACAO_MINIMA = 60

    def __init__(self, context, max_destaques: int = 12, max_stories_dom: int = 12,
                 intervalo: tuple[float, float] = (1.5, 3.5), timeout_ms: int = 15000):
        self.context = context
        self.max_destaques = max_destaques
        self.max_stories_dom = max_stories_dom
        self.intervalo = intervalo
        self.timeout_ms = timeout_ms
        self._cache: dict[str, PerfilInstagram] = {}
        self._ultimo_acesso = 0.0
        self.disponivel: bool | None = None
        self.logado: bool = False
        self.motivo_indisponivel = ""

    def _aguardar(self) -> None:
        espera = random.uniform(*self.intervalo) - (time.time() - self._ultimo_acesso)
        if espera > 0:
            time.sleep(espera)
        self._ultimo_acesso = time.time()

    def _headers(self) -> dict:
        csrftoken = ""
        try:
            for c in self.context.cookies(URL_BASE_IG):
                if c["name"] == "csrftoken":
                    csrftoken = c["value"]
        except Exception:
            pass
        return {
            "x-ig-app-id": IG_APP_ID,
            "x-requested-with": "XMLHttpRequest",
            "x-csrftoken": csrftoken,
            "referer": URL_BASE_IG + "/",
            "accept": "*/*",
        }

    @staticmethod
    def _pagina_bloqueada(texto: str) -> bool:
        t = (texto or "")[:3000].lower()
        return any(s in t for s in ("has been blocked", "fortiguard", "web page blocked", "access denied", "acesso negado"))

    def _get_json(self, url: str) -> dict:
        self._aguardar()
        try:
            resp = self.context.request.get(url, headers=self._headers(), timeout=self.timeout_ms)
        except Exception as e:
            raise InstagramIndisponivel(f"Falha de rede: {str(e)[:80]}")
        texto = resp.text()
        if self._pagina_bloqueada(texto):
            raise InstagramIndisponivel("Instagram bloqueado pela rede/firewall")
        if resp.status == 404:
            raise LookupError("Perfil inexistente")
        if resp.status in (401, 403):
            raise InstagramIndisponivel(f"Acesso negado pelo Instagram (HTTP {resp.status}) — faça login (opção 0)")
        if resp.status == 429:
            raise InstagramIndisponivel("Limite de requisições do Instagram atingido (HTTP 429)")
        if resp.status >= 400:
            raise InstagramIndisponivel(f"HTTP {resp.status}")
        try:
            return resp.json()
        except Exception:
            if "login" in resp.url or "accounts/login" in texto[:5000]:
                raise InstagramIndisponivel("Instagram exigiu login — faça login (opção 0)")
            raise InstagramIndisponivel("Resposta não-JSON do Instagram")

    def verificar_sessao(self) -> tuple[bool, bool, str]:
        """Retorna (acessivel, logado, mensagem). Usado no pré-check antes da prospecção."""
        try:
            resp = self.context.request.get(URL_BASE_IG + "/", timeout=self.timeout_ms, fail_on_status_code=False)
            if self._pagina_bloqueada(resp.text()) or resp.status == 403:
                self.disponivel, self.motivo_indisponivel = False, "Instagram bloqueado pela rede/firewall (HTTP 403)"
                return False, False, self.motivo_indisponivel
        except Exception as e:
            self.disponivel, self.motivo_indisponivel = False, f"Instagram inacessível ({str(e)[:60]})"
            return False, False, self.motivo_indisponivel
        try:
            self.logado = any(c["name"] == "sessionid" and c["value"] for c in self.context.cookies(URL_BASE_IG))
        except Exception:
            self.logado = False
        self.disponivel = True
        msg = "Instagram acessível e logado" if self.logado else "Instagram acessível, mas SEM login (destaques não serão lidos)"
        return True, self.logado, msg

    def obter_perfil(self, username: str, com_destaques: bool = True) -> PerfilInstagram:
        username = (username or "").lower().strip("@/ ")
        if username in self._cache:
            perfil = self._cache[username]
            if com_destaques and perfil.acessivel and perfil.qtd_destaques and not perfil.destaques_verificados and not perfil.privado:
                self._coletar_destaques(perfil)
            return perfil
        if self.disponivel is False:
            perfil = PerfilInstagram(username=username, erro=self.motivo_indisponivel)
            self._cache[username] = perfil
            return perfil

        try:
            dados = self._get_json(f"{URL_BASE_IG}/api/v1/users/web_profile_info/?username={urllib.parse.quote(username)}")
            perfil = parse_web_profile_info(dados, username)
        except LookupError as e:
            perfil = PerfilInstagram(username=username, erro=str(e))
        except (InstagramIndisponivel, ValueError) as e:
            perfil = self._perfil_via_dom(username, motivo_api=str(e))

        if perfil.acessivel and com_destaques and perfil.qtd_destaques and not perfil.privado:
            self._coletar_destaques(perfil)
        self._cache[username] = perfil
        return perfil

    def _coletar_destaques(self, perfil: PerfilInstagram) -> None:
        try:
            if not perfil.user_id:
                raise InstagramIndisponivel("Sem user_id para consultar destaques")
            tray = self._get_json(f"{URL_BASE_IG}/api/v1/highlights/{perfil.user_id}/highlights_tray/").get("tray") or []
            perfil.titulos_destaques = [t.get("title") or "" for t in tray]
            ids = [t["id"] for t in tray if t.get("id")][: self.max_destaques]
            for i in range(0, len(ids), 5):
                lote = "&".join(f"reel_ids={urllib.parse.quote(str(x))}" for x in ids[i:i + 5])
                dados = self._get_json(f"{URL_BASE_IG}/api/v1/feed/reels_media/?{lote}")
                for u in parse_reels_media(dados):
                    if u not in perfil.links_destaques:
                        perfil.links_destaques.append(u)
            perfil.destaques_verificados = True
        except (InstagramIndisponivel, LookupError, KeyError) as e:
            self._destaques_via_dom(perfil, motivo_api=str(e))

    def _abrir_pagina(self, url: str):
        page = self.context.new_page()
        page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        if self._pagina_bloqueada(page.title() + " " + page.content()[:3000]):
            page.close()
            raise InstagramIndisponivel("Instagram bloqueado pela rede/firewall")
        for texto in ("Agora não", "Not Now", "Recusar cookies opcionais", "Decline optional cookies"):
            try:
                btn = page.get_by_role("button", name=texto).first
                if btn.count() and btn.is_visible():
                    btn.click(timeout=2000)
            except Exception:
                pass
        return page

    def _perfil_via_dom(self, username: str, motivo_api: str = "") -> PerfilInstagram:
        perfil = PerfilInstagram(username=username, fonte="dom")
        page = None
        try:
            self._aguardar()
            page = self._abrir_pagina(f"{URL_BASE_IG}/{username}/")
            if "/accounts/login" in page.url:
                raise InstagramIndisponivel("Instagram exigiu login — faça login (opção 0)")
            header = page.locator("header").first
            if not header.count():
                raise InstagramIndisponivel("Perfil não carregou (sem header)")
            perfil.biografia = header.inner_text(timeout=5000)
            perfil.nome_completo = (page.title() or "").split("(")[0].strip()
            hrefs = page.locator('header a[href], a[href*="l.instagram.com"]').evaluate_all("els => els.map(e => e.href)")
            try:
                mais = header.locator('button:has-text("e mais"), button:has-text("and "), div[role=button]:has-text("e mais")').first
                if mais.count():
                    mais.click(timeout=3000)
                    page.wait_for_timeout(1200)
                    hrefs += page.locator('div[role="dialog"] a[href]').evaluate_all("els => els.map(e => e.href)")
                    page.keyboard.press("Escape")
            except Exception:
                pass
            for h in hrefs:
                u = normalizar_url(h)
                if u and not host_corresponde(extrair_host(u), "instagram.com") and u not in perfil.links_bio:
                    perfil.links_bio.append(u)
            perfil.url_externa = perfil.links_bio[0] if perfil.links_bio else ""
            destaques = page.locator('a[href*="/stories/highlights/"]').evaluate_all("els => els.map(e => e.href)")
            perfil.urls_destaques_dom = list(dict.fromkeys(destaques))
            perfil.qtd_destaques = len(perfil.urls_destaques_dom)
            perfil.acessivel = True
        except InstagramIndisponivel as e:
            perfil.erro = f"{motivo_api} | DOM: {e}" if motivo_api else str(e)
            if "bloqueado" in str(e).lower():
                self.disponivel, self.motivo_indisponivel = False, str(e)
        except Exception as e:
            perfil.erro = f"{motivo_api} | DOM: {str(e)[:80]}"
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass
        return perfil

    def _destaques_via_dom(self, perfil: PerfilInstagram, motivo_api: str = "") -> None:
        urls = perfil.urls_destaques_dom if perfil.fonte == "dom" else None
        page = None
        try:
            if urls is None:
                self._aguardar()
                page = self._abrir_pagina(perfil.url)
                urls = list(dict.fromkeys(page.locator('a[href*="/stories/highlights/"]').evaluate_all("els => els.map(e => e.href)")))
            if not urls:
                perfil.destaques_verificados = perfil.qtd_destaques == 0
                return
            page = page or self.context.new_page()
            for url_destaque in urls[: self.max_destaques]:
                self._aguardar()
                page.goto(url_destaque, timeout=self.timeout_ms, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                for _ in range(self.max_stories_dom):
                    for h in page.locator('a[href*="l.instagram.com"], section a[href^="http"]').evaluate_all("els => els.map(e => e.href)"):
                        u = normalizar_url(h)
                        if u and not host_corresponde(extrair_host(u), "instagram.com") and u not in perfil.links_destaques:
                            perfil.links_destaques.append(u)
                    url_antes = page.url
                    proximo = page.locator('button[aria-label="Avançar"], button[aria-label="Next"]').first
                    if proximo.count():
                        proximo.click(timeout=2000)
                    else:
                        page.keyboard.press("ArrowRight")
                    page.wait_for_timeout(1200)
                    if page.url == url_antes or "/stories/highlights/" not in page.url:
                        break
            perfil.destaques_verificados = True
        except Exception as e:
            perfil.erro = (perfil.erro + " | " if perfil.erro else "") + f"Destaques: {motivo_api or ''} {str(e)[:60]}".strip()
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass

    def buscar_candidatos(self, nome: str, cidade: str, buscador=None) -> list[str]:
        candidatos: list[str] = []
        if self.disponivel is not False:
            for consulta in (nome, f"{nome} {cidade.split()[0] if cidade else ''}".strip()):
                try:
                    dados = self._get_json(f"{URL_BASE_IG}/web/search/topsearch/?context=blended&query={urllib.parse.quote(consulta)}")
                    for u in dados.get("users") or []:
                        user = (u.get("user") or {}).get("username")
                        if user and user.lower() not in candidatos:
                            candidatos.append(user.lower())
                except (InstagramIndisponivel, LookupError):
                    break
                if candidatos:
                    break
        if buscador is not None:
            for url in buscador(f'site:instagram.com "{nome}" {cidade}'):
                user = extrair_username(url)
                if user and user not in candidatos:
                    candidatos.append(user)
        return candidatos[:6]

    def localizar_perfil(self, nome: str, telefone: str, cidade: str, buscador=None,
                         max_candidatos: int = 3) -> tuple[PerfilInstagram | None, int, list[str]]:
        melhor: tuple[PerfilInstagram | None, int, list[str]] = (None, 0, [])
        for user in self.buscar_candidatos(nome, cidade, buscador)[:max_candidatos]:
            perfil = self.obter_perfil(user, com_destaques=False)
            if not perfil.acessivel:
                continue
            pontos, motivos = pontuar_correspondencia(perfil, nome, telefone, cidade)
            if pontos > melhor[1]:
                melhor = (perfil, pontos, motivos)
        if melhor[0] is None or melhor[1] < self.PONTUACAO_MINIMA:
            return None, melhor[1], melhor[2]
        perfil = melhor[0]
        if perfil.qtd_destaques and not perfil.destaques_verificados and not perfil.privado:
            self._coletar_destaques(perfil)
        return perfil, melhor[1], melhor[2]


# ======================================================================================
# 3. VERIFICADOR DE PRESENÇA DIGITAL (GOOGLE MAPS + INSTAGRAM + WEB)
# ======================================================================================

CONFIG_PADRAO = {
    "desqualificar_marketplace": False,
    "rejeitar_inconclusivos": True,
    "busca_web": True,
    "adivinhar_dominios": True,
    "max_links_agregador": 25,
    "timeout_http_ms": 9000,
}

SINAIS_PAGINA_BLOQUEADA = ("has been blocked", "fortiguard", "web page blocked", "web filter", "acesso negado pela política")
SINAIS_DOMINIO_INATIVO = (
    "domain is for sale", "this domain is for sale", "buy this domain", "domínio está à venda",
    "dominio esta a venda", "este domínio pode estar à venda", "compre este domínio", "parked free",
    "parkingcrew", "sedoparking", "domain parking", "hugedomains", "dan.com", "afternic",
    "em construção", "em construcao", "under construction", "coming soon", "site em breve",
    "página em construção", "estamos construindo", "account suspended", "conta suspensa",
    "apache2 ubuntu default page", "welcome to nginx", "it works!", "index of /",
    "default web site page", "domínio registrado", "dominio registrado", "registro.br",
    "this site can’t be reached", "website is no longer available", "site desativado",
)
HOSTS_ESTACIONAMENTO = ("sedoparking.com", "hugedomains.com", "dan.com", "afternic.com", "parkingcrew.net", "bodis.com")


class StatusSite(str, Enum):
    ATIVO = "ativo"
    INATIVO = "inativo"
    INCONCLUSIVO = "inconclusivo"


@dataclass
class Evidencia:
    fonte: str
    url: str
    tipo: str
    motivo: str
    desqualifica: bool

    def __str__(self) -> str:
        return f"[{self.fonte}] {self.motivo} — {self.url}"


@dataclass
class ResultadoPresencaDigital:
    evidencias: list[Evidencia] = field(default_factory=list)
    observacoes: list[str] = field(default_factory=list)
    inconclusivos: list[str] = field(default_factory=list)
    links_maps_brutos: list[str] = field(default_factory=list)
    links_expandidos: list[str] = field(default_factory=list)
    url_instagram: str = ""
    perfil_instagram: PerfilInstagram | None = None
    status_instagram: str = "nao_verificado"
    detalhe_instagram: str = ""

    @property
    def tem_site(self) -> bool:
        return any(e.desqualifica for e in self.evidencias)

    @property
    def motivo(self) -> str:
        for e in self.evidencias:
            if e.desqualifica:
                return str(e)
        return ""

    def adicionar(self, evidencias: list[Evidencia]) -> None:
        for e in evidencias:
            if not any(x.url == e.url and x.fonte == e.fonte for x in self.evidencias):
                self.evidencias.append(e)

    def observar(self, texto: str) -> None:
        if texto and texto not in self.observacoes:
            self.observacoes.append(texto)


@dataclass
class RespostaHttp:
    status: int = 0
    url: str = ""
    texto: str = ""
    erro: str = ""


class ClienteHttp:
    """GET simples sobre o APIRequestContext do Playwright."""

    def __init__(self, request_context, timeout_ms: int = 9000):
        self.request = request_context
        self.timeout_ms = timeout_ms

    def get(self, url: str, max_redirects: int = 8) -> RespostaHttp:
        try:
            resp = self.request.get(
                url, timeout=self.timeout_ms, max_redirects=max_redirects, fail_on_status_code=False,
                headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"},
            )
            try:
                texto = resp.text()
            except Exception:
                texto = ""
            return RespostaHttp(resp.status, resp.url, texto)
        except Exception as e:
            return RespostaHttp(erro=str(e)[:200])


def pagina_bloqueada(texto: str) -> bool:
    t = (texto or "")[:4000].lower()
    return any(s in t for s in SINAIS_PAGINA_BLOQUEADA)


def _texto_visivel(html_str: str) -> str:
    html_str = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html_str or "")
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", html_str)).strip()


def avaliar_site(url: str, http: ClienteHttp) -> tuple[StatusSite, str, str]:
    """Acessa a URL e decide se o site está ATIVO, INATIVO ou INCONCLUSIVO."""
    resp = http.get(url)
    if resp.erro:
        e = resp.erro.lower()
        if any(s in e for s in ("enotfound", "name_not_resolved", "getaddrinfo", "econnrefused", "eai_again", "connection refused")):
            return StatusSite.INATIVO, "domínio não resolve / servidor inexistente", ""
        return StatusSite.INCONCLUSIVO, f"falha de acesso ({resp.erro[:60]})", ""
    if pagina_bloqueada(resp.texto):
        return StatusSite.INCONCLUSIVO, "acesso bloqueado pela rede local", ""
    if resp.status in (404, 410):
        return StatusSite.INATIVO, f"página inexistente (HTTP {resp.status})", ""
    if resp.status in (401, 403, 429):
        return StatusSite.ATIVO, f"servidor ativo com proteção (HTTP {resp.status})", resp.texto
    if resp.status >= 500:
        return StatusSite.INCONCLUSIVO, f"erro no servidor (HTTP {resp.status})", ""

    final = classificar_link(resp.url or url)
    if not final.desqualifica and final.tipo not in (TipoLink.AGREGADOR, TipoLink.ENCURTADOR):
        return StatusSite.INATIVO, f"redireciona para {final.host} ({final.tipo.value})", ""
    if any(host_corresponde(final.host, h) for h in HOSTS_ESTACIONAMENTO):
        return StatusSite.INATIVO, "domínio estacionado/à venda", ""

    visivel = _texto_visivel(resp.texto)
    baixo = visivel.lower()[:6000]
    if any(s in baixo for s in SINAIS_DOMINIO_INATIVO) and len(visivel) < 2500:
        return StatusSite.INATIVO, "domínio estacionado / página em construção", ""
    if len(visivel) < 40 and "<script" not in resp.texto.lower():
        return StatusSite.INATIVO, "página vazia", ""
    return StatusSite.ATIVO, f"site respondendo (HTTP {resp.status})", resp.texto


def pagina_pertence_ao_negocio(html_str: str, nome: str, telefone: str, cidade: str, username: str = "") -> tuple[bool, str]:
    """Confirma a autoria de um site encontrado em busca: telefone, @ do Instagram ou título+cidade."""
    if not html_str:
        return False, ""
    alvo = re.sub(r"\D", "", telefone or "")[-8:]
    if len(alvo) == 8:
        for tel in telefones_no_texto(html_str):
            if tel[-8:] == alvo:
                return True, "telefone do Google Maps encontrado no site"
    if username and re.search(rf"instagram\.com/{re.escape(username)}(?![\w.])", html_str, re.IGNORECASE):
        return True, f"site aponta para o Instagram @{username}"
    titulo = re.search(r"(?is)<title[^>]*>(.*?)</title>", html_str)
    titulo_txt = titulo.group(1) if titulo else ""
    texto = normalizar_nome(_texto_visivel(html_str)[:20000])
    cidade_tokens = [t for t in normalizar_nome(cidade).split() if len(t) > 3]
    distintivo = nome_distintivo(nome)
    if titulo_txt and similaridade_nomes(nome, titulo_txt) >= 0.85 and (not cidade_tokens or any(t in texto for t in cidade_tokens)):
        if len(distintivo.replace(" ", "")) >= 4:
            return True, "nome do negócio no título do site e cidade no conteúdo"
    return False, ""


_JS_LINKS_PAINEL = """
m => Array.from(m.querySelectorAll('a[href]'))
  .filter(a => !a.closest('[data-review-id], .jftiEf, .MyEned, .wiI7pd'))
  .map(a => ({
      href: a.href || '',
      id: a.getAttribute('data-item-id') || '',
      label: (a.getAttribute('aria-label') || a.getAttribute('data-tooltip') || '').trim(),
      texto: (a.innerText || '').trim().slice(0, 80)
  }))
"""


def localizar_painel_maps(page: Page):
    painel = page.locator('div[role="main"]').filter(has=page.locator("h1")).last
    return painel if painel.count() else page.locator("body")


def coletar_links_maps(page: Page) -> list[dict]:
    """Retorna os links do painel de informações do lugar (sem avaliações)."""
    try:
        return localizar_painel_maps(page).evaluate(_JS_LINKS_PAINEL)
    except Exception:
        return []


def rotular_link_maps(link: dict) -> str:
    href, id_, label = link.get("href", ""), link.get("id", ""), link.get("label", "").lower()
    if id_ == "authority" or "website" in label or "site" in label:
        return "Google Maps (Website)"
    if id_.startswith("menu") or "cardápio" in label or "menu" in label:
        return "Google Maps (Cardápio)"
    if "rwg_token" in href or "reserve" in href or "reserv" in label or "agend" in label:
        return "Google Maps (Reserva/Agendamento)"
    if id_.startswith("order") or "pedido" in label or "pedir" in label:
        return "Google Maps (Pedido online)"
    return "Google Maps (Link do perfil)"


def _decodificar_link_bing(href: str) -> str:
    href = href.replace("&amp;", "&")
    if "bing.com/ck/a" not in href:
        return href
    u = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("u", [""])[0]
    if u.startswith("a1"):
        s = u[2:] + "=" * (-len(u[2:]) % 4)
        try:
            return base64.urlsafe_b64decode(s).decode("utf-8", "ignore")
        except Exception:
            return ""
    return ""


def buscar_web(consulta: str, http: ClienteHttp, limite: int = 8) -> list[str]:
    resp = http.get("https://www.bing.com/search?setlang=pt-br&cc=br&q=" + urllib.parse.quote_plus(consulta))
    if resp.erro or resp.status >= 400 or pagina_bloqueada(resp.texto):
        return []
    urls = []
    for m in re.finditer(r'<li class="b_algo".*?<h2[^>]*>\s*<a[^>]+href="([^"]+)"', resp.texto, re.S):
        u = _decodificar_link_bing(m.group(1))
        if u.startswith("http") and u not in urls:
            urls.append(u)
    return urls[:limite]


def gerar_dominios_provaveis(nome: str) -> list[str]:
    completo = normalizar_nome(nome).replace(" ", "")
    distintivo = nome_distintivo(nome).replace(" ", "")
    slugs = [s for s in dict.fromkeys([completo, distintivo]) if 6 <= len(s) <= 40]
    return [f"https://{s}{tld}" for s in slugs[:2] for tld in (".com.br", ".com")]


class VerificadorPresencaDigital:
    def __init__(self, context, cliente_instagram: ClienteInstagram | None = None, config: dict | None = None):
        self.config = {**CONFIG_PADRAO, **(config or {})}
        self.http = ClienteHttp(context.request, self.config["timeout_http_ms"])
        self.instagram = cliente_instagram or ClienteInstagram(context)

    def avaliar_url(self, url: str, fonte: str, resultado: ResultadoPresencaDigital, lead: dict,
                    origem: str = "declarado", profundidade: int = 0) -> None:
        cls = classificar_link(url)
        tipo = cls.tipo

        if tipo in (TipoLink.INVALIDO, TipoLink.CONTATO, TipoLink.INTERNO_GOOGLE, TipoLink.PORTAL, TipoLink.FERRAMENTA):
            return
        if tipo == TipoLink.REDE_SOCIAL:
            user = extrair_username(cls.url)
            if user and not resultado.url_instagram and origem == "declarado":
                resultado.url_instagram = cls.url
            return
        if tipo == TipoLink.MENSAGEIRO:
            return
        if tipo == TipoLink.MARKETPLACE:
            desq = bool(self.config["desqualificar_marketplace"])
            resultado.adicionar([Evidencia(fonte, cls.url, tipo.value, cls.motivo, desq)])
            resultado.observar(f"Presente em plataforma de terceiros: {cls.host}")
            return
        if tipo == TipoLink.SISTEMA:
            if origem in ("declarado", "texto"):
                resultado.adicionar([Evidencia(fonte, cls.url, tipo.value, cls.motivo, True)])
            return

        if tipo in (TipoLink.AGREGADOR, TipoLink.ENCURTADOR):
            if profundidade >= 2:
                resultado.inconclusivos.append(f"{fonte}: cadeia de redirecionamentos longa demais ({cls.url})")
                return
            resp = self.http.get(cls.url)
            if resp.erro or resp.status >= 400 or pagina_bloqueada(resp.texto):
                resultado.inconclusivos.append(f"{fonte}: não foi possível abrir {cls.host} ({resp.erro[:50] or resp.status})")
                return
            if tipo == TipoLink.ENCURTADOR:
                destino = resp.url if resp.url and extrair_host(resp.url) != cls.host else ""
                if not destino:
                    resultado.inconclusivos.append(f"{fonte}: encurtador sem destino resolvido ({cls.url})")
                    return
                if destino not in resultado.links_expandidos:
                    resultado.links_expandidos.append(destino)
                self.avaliar_url(destino, f"{fonte} → {cls.host}", resultado, lead, origem, profundidade + 1)
                return
            internos = extrair_urls_de_html(resp.texto, ignorar_host=cls.host)[: self.config["max_links_agregador"]]
            antes = len(resultado.evidencias)
            for u in internos:
                if u not in resultado.links_expandidos:
                    resultado.links_expandidos.append(u)
                self.avaliar_url(u, f"{fonte} → {cls.host}", resultado, lead, origem, profundidade + 1)
            if len(resultado.evidencias) == antes:
                resultado.observar(f"{cls.host} inspecionado: contém apenas redes sociais/WhatsApp")
            return

        status, detalhe, html_str = avaliar_site(cls.url, self.http)
        if origem == "busca":
            if status == StatusSite.ATIVO:
                pertence, prova = pagina_pertence_ao_negocio(html_str, lead.get("nome", ""), lead.get("telefone", ""),
                                                             lead.get("cidade", ""), extrair_username(resultado.url_instagram))
                if pertence:
                    resultado.adicionar([Evidencia(fonte, cls.url, tipo.value, f"{cls.motivo}: {prova}", True)])
            return
        if origem == "email":
            if status == StatusSite.ATIVO:
                resultado.adicionar([Evidencia(fonte, cls.url, tipo.value, f"Domínio do e-mail comercial possui site ativo ({detalhe})", True)])
            elif status == StatusSite.INATIVO:
                resultado.observar(f"Possui domínio próprio sem site ativo ({cls.host}) — oportunidade")
            return
        if status == StatusSite.INATIVO:
            resultado.adicionar([Evidencia(fonte, cls.url, tipo.value, f"{cls.motivo} — INATIVO: {detalhe}", False)])
            resultado.observar(f"Divulga {cls.host}, mas o site está inativo ({detalhe}) — oportunidade quente")
        elif status == StatusSite.ATIVO or origem == "declarado":
            resultado.adicionar([Evidencia(fonte, cls.url, tipo.value, f"{cls.motivo} ({detalhe})", True)])
        else:
            resultado.inconclusivos.append(f"{fonte}: domínio citado no texto não pôde ser verificado ({cls.host}: {detalhe})")

    def analisar_maps(self, page: Page, lead: dict) -> ResultadoPresencaDigital:
        resultado = ResultadoPresencaDigital()
        for link in coletar_links_maps(page):
            href = link.get("href", "")
            if href and href not in resultado.links_maps_brutos:
                resultado.links_maps_brutos.append(href)
            self.avaliar_url(href, rotular_link_maps(link), resultado, lead, "declarado")
        return resultado

    def analisar_instagram(self, resultado: ResultadoPresencaDigital, lead: dict) -> None:
        nome, telefone, cidade = lead.get("nome", ""), lead.get("telefone", ""), lead.get("cidade", "")
        perfil = None
        username = extrair_username(resultado.url_instagram)
        if username:
            perfil = self.instagram.obter_perfil(username)
            if perfil.acessivel:
                resultado.detalhe_instagram = "perfil informado no Google Maps"
        else:
            buscador = (lambda q: buscar_web(q, self.http)) if self.config["busca_web"] else None
            perfil, pontos, motivos = self.instagram.localizar_perfil(nome, telefone, cidade, buscador=buscador)
            if perfil:
                resultado.url_instagram = perfil.url
                resultado.detalhe_instagram = f"localizado e validado ({pontos} pts: {', '.join(motivos)})"

        if perfil is None:
            if self.instagram.disponivel is False:
                resultado.status_instagram = "inacessivel"
                resultado.detalhe_instagram = self.instagram.motivo_indisponivel
            else:
                resultado.status_instagram = "nao_encontrado"
                resultado.detalhe_instagram = "nenhum perfil confirmado para este negócio"
            return
        resultado.perfil_instagram = perfil
        if not perfil.acessivel:
            resultado.status_instagram = "inacessivel"
            resultado.detalhe_instagram = perfil.erro or "perfil não pôde ser lido"
            return
        resultado.status_instagram = "verificado"

        for u in perfil.links_bio:
            self.avaliar_url(u, "Instagram (link da bio)", resultado, lead, "declarado")
        for d in extrair_dominios_de_texto(perfil.biografia):
            self.avaliar_url(d, "Instagram (texto da bio)", resultado, lead, "texto")
        for dom in extrair_dominios_de_email(f"{perfil.email_comercial} {perfil.biografia}"):
            self.avaliar_url(f"https://{dom}", "Instagram (e-mail comercial)", resultado, lead, "email")
        for u in perfil.links_destaques:
            self.avaliar_url(u, "Instagram (destaques)", resultado, lead, "declarado")
        if perfil.qtd_destaques and not perfil.destaques_verificados:
            resultado.inconclusivos.append(f"Instagram: {perfil.qtd_destaques} destaques não puderam ser inspecionados")
        if perfil.privado:
            resultado.observar("Perfil do Instagram é privado (bio verificada, destaques indisponíveis)")

    def analisar_web(self, resultado: ResultadoPresencaDigital, lead: dict) -> None:
        nome, cidade = lead.get("nome", ""), lead.get("cidade", "")
        candidatos: list[str] = []
        if self.config["adivinhar_dominios"]:
            candidatos += gerar_dominios_provaveis(nome)
        if self.config["busca_web"]:
            candidatos += buscar_web(f'"{nome}" {cidade}', self.http)
        vistos = set()
        for u in candidatos:
            host = extrair_host(u)
            if host in vistos:
                continue
            vistos.add(host)
            if classificar_link(u).tipo in (TipoLink.SITE_PROPRIO, TipoLink.CONSTRUTOR):
                self.avaliar_url(u, "Busca web", resultado, lead, "busca")
            if resultado.tem_site:
                return

    def verificar(self, page: Page | None, lead: dict, resultado_maps: ResultadoPresencaDigital | None = None) -> ResultadoPresencaDigital:
        resultado = resultado_maps or (self.analisar_maps(page, lead) if page else ResultadoPresencaDigital())
        if resultado.tem_site:
            return resultado
        self.analisar_instagram(resultado, lead)
        if resultado.tem_site:
            return resultado
        self.analisar_web(resultado, lead)
        return resultado


# ======================================================================================
# 4. GERENCIAMENTO DE ABA ÚNICA DO WHATSAPP WEB
# ======================================================================================

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


def obter_ou_reutilizar_aba_whatsapp(context, telefone: str = "") -> Page:
    """Mantém uma ÚNICA aba dedicada ao WhatsApp Web no contexto."""
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
    """Redireciona popups do WhatsApp para a aba única principal, fechando a aba excedente."""
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
