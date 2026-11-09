"""
Investigação de perfis do Instagram.

Coleta, para um perfil, todos os pontos onde um negócio costuma divulgar site/sistema:
  * Link externo da bio e lista de links ("bio_links")
  * Texto da biografia (domínios escritos sem link)
  * E-mail comercial (domínio próprio indica site)
  * Links dos DESTAQUES (stickers de link nos stories fixados)

Estratégia:
  1. Endpoints JSON do próprio web app do Instagram, usando a sessão logada do perfil
     persistente do navegador (mesmo acesso que o usuário tem ao abrir o site).
  2. Fallback por DOM (abre o perfil e os destaques no navegador) caso a API falhe.

Também localiza o perfil de um negócio quando o Google Maps não informa o Instagram,
validando a identidade (telefone, nome e cidade) para evitar analisar o perfil errado.
"""

from __future__ import annotations

import random
import re
import time
import unicodedata
import urllib.parse
from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher

from links import REGEX_URL, eh_host_infra, extrair_host, host_corresponde, normalizar_url

IG_APP_ID = "936619743392459"
URL_BASE = "https://www.instagram.com"
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


class InstagramIndisponivel(Exception):
    """Instagram bloqueado na rede, sem login ou com limite de requisições atingido."""


@dataclass
class PerfilInstagram:
    username: str
    acessivel: bool = False
    fonte: str = ""                 # "api" | "dom"
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
        return f"{URL_BASE}/{self.username}/"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["url"] = self.url
        return d


# --------------------------------------------------------------------------------------
# Funções puras (testáveis sem rede)
# --------------------------------------------------------------------------------------

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
        u = item.get("url") or item.get("lynx_url") or ""
        u = normalizar_url(u)
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


_CHAVES_LINK = {"url", "weburi", "web_uri", "link", "story_link", "external_url", "link_url", "destination_url"}


def _coletar_urls_recursivo(obj, saida: list[str], chave_pai: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            _coletar_urls_recursivo(v, saida, k.lower())
    elif isinstance(obj, list):
        for v in obj:
            _coletar_urls_recursivo(v, saida, chave_pai)
    elif isinstance(obj, str) and chave_pai in _CHAVES_LINK and obj.lower().startswith(("http", "www.")):
        url = normalizar_url(obj)  # já decodifica l.instagram.com/?u=...
        host = extrair_host(url)
        if url and not eh_host_infra(url) and not host_corresponde(host, "instagram.com") and url not in saida:
            saida.append(url)


def parse_reels_media(dados: dict) -> list[str]:
    """
    Extrai URLs externas de stickers de link/CTA dos stories de destaques
    (resposta de /api/v1/feed/reels_media/). Busca recursiva para tolerar
    mudanças de schema (story_link_stickers, story_cta, link...).
    """
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
    """Remove palavras genéricas do nicho, deixando o 'nome de marca' (ex.: 'nacional')."""
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
    """
    Pontua (0-100+) a probabilidade de um perfil pertencer ao negócio do Maps.
    Telefone igual é a prova mais forte; nome e cidade complementam.
    """
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


# --------------------------------------------------------------------------------------
# Cliente (rede)
# --------------------------------------------------------------------------------------

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

    # ---------------- infraestrutura ----------------
    def _aguardar(self) -> None:
        espera = random.uniform(*self.intervalo) - (time.time() - self._ultimo_acesso)
        if espera > 0:
            time.sleep(espera)
        self._ultimo_acesso = time.time()

    def _headers(self) -> dict:
        csrftoken = ""
        try:
            for c in self.context.cookies(URL_BASE):
                if c["name"] == "csrftoken":
                    csrftoken = c["value"]
        except Exception:
            pass
        return {
            "x-ig-app-id": IG_APP_ID,
            "x-requested-with": "XMLHttpRequest",
            "x-csrftoken": csrftoken,
            "referer": URL_BASE + "/",
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
            resp = self.context.request.get(URL_BASE + "/", timeout=self.timeout_ms, fail_on_status_code=False)
            if self._pagina_bloqueada(resp.text()) or resp.status == 403:
                self.disponivel, self.motivo_indisponivel = False, "Instagram bloqueado pela rede/firewall (HTTP 403)"
                return False, False, self.motivo_indisponivel
        except Exception as e:
            self.disponivel, self.motivo_indisponivel = False, f"Instagram inacessível ({str(e)[:60]})"
            return False, False, self.motivo_indisponivel
        try:
            self.logado = any(c["name"] == "sessionid" and c["value"] for c in self.context.cookies(URL_BASE))
        except Exception:
            self.logado = False
        self.disponivel = True
        msg = "Instagram acessível e logado" if self.logado else "Instagram acessível, mas SEM login (destaques não serão lidos)"
        return True, self.logado, msg

    # ---------------- coleta de perfil ----------------
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
            dados = self._get_json(f"{URL_BASE}/api/v1/users/web_profile_info/?username={urllib.parse.quote(username)}")
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
            tray = self._get_json(f"{URL_BASE}/api/v1/highlights/{perfil.user_id}/highlights_tray/").get("tray") or []
            perfil.titulos_destaques = [t.get("title") or "" for t in tray]
            ids = [t["id"] for t in tray if t.get("id")][: self.max_destaques]
            for i in range(0, len(ids), 5):
                lote = "&".join(f"reel_ids={urllib.parse.quote(str(x))}" for x in ids[i:i + 5])
                dados = self._get_json(f"{URL_BASE}/api/v1/feed/reels_media/?{lote}")
                for u in parse_reels_media(dados):
                    if u not in perfil.links_destaques:
                        perfil.links_destaques.append(u)
            perfil.destaques_verificados = True
        except (InstagramIndisponivel, LookupError, KeyError) as e:
            self._destaques_via_dom(perfil, motivo_api=str(e))

    # ---------------- fallback por DOM ----------------
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
            page = self._abrir_pagina(f"{URL_BASE}/{username}/")
            if "/accounts/login" in page.url:
                raise InstagramIndisponivel("Instagram exigiu login — faça login (opção 0)")
            header = page.locator("header").first
            if not header.count():
                raise InstagramIndisponivel("Perfil não carregou (sem header)")
            texto = header.inner_text(timeout=5000)
            perfil.biografia = texto
            perfil.nome_completo = (page.title() or "").split("(")[0].strip()
            hrefs = page.locator('header a[href], a[href*="l.instagram.com"]').evaluate_all("els => els.map(e => e.href)")
            # Botão "e mais N" abre um diálogo com todos os links da bio
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

    # ---------------- localização de perfil ----------------
    def buscar_candidatos(self, nome: str, cidade: str, buscador=None) -> list[str]:
        """Busca @s candidatos pelo nome (busca do próprio Instagram + buscador web opcional)."""
        candidatos: list[str] = []
        if self.disponivel is not False:
            for consulta in (nome, f"{nome} {cidade.split()[0] if cidade else ''}".strip()):
                try:
                    dados = self._get_json(f"{URL_BASE}/web/search/topsearch/?context=blended&query={urllib.parse.quote(consulta)}")
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
        """Retorna (perfil, pontuação, motivos) do melhor candidato validado, ou (None, 0, [])."""
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
        # Agora que a identidade foi validada, coleta também os destaques
        if perfil.qtd_destaques and not perfil.destaques_verificados and not perfil.privado:
            self._coletar_destaques(perfil)
        return perfil, melhor[1], melhor[2]
