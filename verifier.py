"""
Verificação de Presença Digital (Site / Sistema próprio / Landing Page).

Pipeline por lead:
  1. Google Maps  – lê SOMENTE o painel de informações (campo Website, botões de
                    reserva/pedido, perfis sociais), ignorando avaliações de clientes.
  2. Instagram    – bio, link externo, lista de links, domínios escritos na bio,
                    e-mail comercial e stickers de link nos DESTAQUES.
  3. Web          – domínios prováveis do nome e busca web, aceitando apenas sites
                    COMPROVADAMENTE do negócio (telefone, @ do Instagram ou nome+cidade).

Cada link é classificado (links.py). Agregadores (Linktree) são abertos e seus links
internos inspecionados; encurtadores são resolvidos. Sites declarados são acessados para
diferenciar "site ativo" de "domínio inativo/estacionado" (este último é OPORTUNIDADE).

wa.me, WhatsApp, Instagram e demais redes sociais NUNCA contam como site.
"""

from __future__ import annotations

import base64
import re
import urllib.parse
from dataclasses import dataclass, field
from enum import Enum

from playwright.sync_api import Page

from instagram import (
    ClienteInstagram, PerfilInstagram, extrair_username, nome_distintivo, normalizar_nome,
    similaridade_nomes, telefones_no_texto,
)
from links import (
    TipoLink, classificar_link, extrair_dominios_de_email, extrair_dominios_de_texto,
    extrair_host, extrair_urls_de_html, host_corresponde,
)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

CONFIG_PADRAO = {
    "desqualificar_marketplace": False,  # iFood/Doctoralia NÃO são site próprio
    "rejeitar_inconclusivos": True,      # Link que não pôde ser inspecionado => rejeita (conservador)
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
    fonte: str          # Ex.: "Google Maps (Website)", "Instagram (bio)", "Instagram (destaques)"
    url: str
    tipo: str           # TipoLink.value
    motivo: str
    desqualifica: bool

    def __str__(self) -> str:
        return f"[{self.fonte}] {self.motivo} — {self.url}"


@dataclass
class ResultadoPresencaDigital:
    evidencias: list[Evidencia] = field(default_factory=list)
    observacoes: list[str] = field(default_factory=list)
    inconclusivos: list[str] = field(default_factory=list)
    url_instagram: str = ""
    perfil_instagram: PerfilInstagram | None = None
    status_instagram: str = "nao_verificado"   # verificado | nao_encontrado | inacessivel | nao_verificado
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


# --------------------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------------------

@dataclass
class RespostaHttp:
    status: int = 0
    url: str = ""
    texto: str = ""
    erro: str = ""


class ClienteHttp:
    """GET simples sobre o APIRequestContext do Playwright (compartilha proxy/certificados do navegador)."""

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


def _texto_visivel(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html or "")
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", html)).strip()


def avaliar_site(url: str, http: ClienteHttp) -> tuple[StatusSite, str, str]:
    """
    Acessa a URL e decide se é um site ATIVO, INATIVO (não resolve, 404, estacionado,
    em construção, redireciona para rede social) ou INCONCLUSIVO (bloqueio/timeout).
    Retorna (status, detalhe, html).
    """
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


def pagina_pertence_ao_negocio(html: str, nome: str, telefone: str, cidade: str, username: str = "") -> tuple[bool, str]:
    """Confirma a autoria de um site encontrado em busca: telefone, @ do Instagram ou título+cidade."""
    if not html:
        return False, ""
    alvo = re.sub(r"\D", "", telefone or "")[-8:]
    if len(alvo) == 8:
        for tel in telefones_no_texto(html):
            if tel[-8:] == alvo:
                return True, "telefone do Google Maps encontrado no site"
    if username and re.search(rf"instagram\.com/{re.escape(username)}(?![\w.])", html, re.IGNORECASE):
        return True, f"site aponta para o Instagram @{username}"
    titulo = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    titulo_txt = titulo.group(1) if titulo else ""
    texto = normalizar_nome(_texto_visivel(html)[:20000])
    cidade_tokens = [t for t in normalizar_nome(cidade).split() if len(t) > 3]
    distintivo = nome_distintivo(nome)
    if titulo_txt and similaridade_nomes(nome, titulo_txt) >= 0.85 and (not cidade_tokens or any(t in texto for t in cidade_tokens)):
        if len(distintivo.replace(" ", "")) >= 4:
            return True, "nome do negócio no título do site e cidade no conteúdo"
    return False, ""


# --------------------------------------------------------------------------------------
# Google Maps
# --------------------------------------------------------------------------------------

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


# --------------------------------------------------------------------------------------
# Busca web
# --------------------------------------------------------------------------------------

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
    """Ex.: 'Barbearia Nacional' -> barbearianacional.com.br / .com (confirmação obrigatória depois)."""
    completo = normalizar_nome(nome).replace(" ", "")
    distintivo = nome_distintivo(nome).replace(" ", "")
    slugs = [s for s in dict.fromkeys([completo, distintivo]) if len(s) >= 6 and len(s) <= 40]
    return [f"https://{s}{tld}" for s in slugs[:2] for tld in (".com.br", ".com")]


# --------------------------------------------------------------------------------------
# Verificador
# --------------------------------------------------------------------------------------

class VerificadorPresencaDigital:
    def __init__(self, context, cliente_instagram: ClienteInstagram | None = None, config: dict | None = None):
        self.config = {**CONFIG_PADRAO, **(config or {})}
        self.http = ClienteHttp(context.request, self.config["timeout_http_ms"])
        self.instagram = cliente_instagram or ClienteInstagram(context)

    # ---------- avaliação de um link ----------
    def avaliar_url(self, url: str, fonte: str, resultado: ResultadoPresencaDigital, lead: dict,
                    origem: str = "declarado", profundidade: int = 0) -> None:
        """
        origem: 'declarado' (link explícito no Maps/Instagram), 'texto' (domínio escrito na bio),
                'email' (domínio de e-mail próprio) ou 'busca' (encontrado na web).
        """
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
                self.avaliar_url(destino, f"{fonte} → {cls.host}", resultado, lead, origem, profundidade + 1)
                return
            internos = extrair_urls_de_html(resp.texto, ignorar_host=cls.host)[: self.config["max_links_agregador"]]
            antes = len(resultado.evidencias)
            for u in internos:
                self.avaliar_url(u, f"{fonte} → {cls.host}", resultado, lead, origem, profundidade + 1)
            if len(resultado.evidencias) == antes:
                resultado.observar(f"{cls.host} inspecionado: contém apenas redes sociais/WhatsApp")
            return

        # CONSTRUTOR ou SITE_PROPRIO → confirmar se o site está realmente no ar
        status, detalhe, html = avaliar_site(cls.url, self.http)
        if origem == "busca":
            if status == StatusSite.ATIVO:
                pertence, prova = pagina_pertence_ao_negocio(html, lead.get("nome", ""), lead.get("telefone", ""),
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
        # declarado / texto
        if status == StatusSite.INATIVO:
            resultado.adicionar([Evidencia(fonte, cls.url, tipo.value, f"{cls.motivo} — INATIVO: {detalhe}", False)])
            resultado.observar(f"Divulga {cls.host}, mas o site está inativo ({detalhe}) — oportunidade quente")
        elif status == StatusSite.ATIVO or origem == "declarado":
            resultado.adicionar([Evidencia(fonte, cls.url, tipo.value, f"{cls.motivo} ({detalhe})", True)])
        else:
            resultado.inconclusivos.append(f"{fonte}: domínio citado no texto não pôde ser verificado ({cls.host}: {detalhe})")

    # ---------- etapa 1: Google Maps ----------
    def analisar_maps(self, page: Page, lead: dict) -> ResultadoPresencaDigital:
        resultado = ResultadoPresencaDigital()
        for link in coletar_links_maps(page):
            self.avaliar_url(link.get("href", ""), rotular_link_maps(link), resultado, lead, "declarado")
        return resultado

    # ---------- etapa 2: Instagram ----------
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

    # ---------- etapa 3: Web ----------
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

    # ---------- pipeline completo ----------
    def verificar(self, page: Page, lead: dict, resultado_maps: ResultadoPresencaDigital | None = None) -> ResultadoPresencaDigital:
        resultado = resultado_maps or self.analisar_maps(page, lead)
        if resultado.tem_site:
            return resultado
        self.analisar_instagram(resultado, lead)
        if resultado.tem_site:
            return resultado
        self.analisar_web(resultado, lead)
        return resultado


# --------------------------------------------------------------------------------------
# WhatsApp Web (aba única) — utilitários usados pelo main
# --------------------------------------------------------------------------------------

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
    """
    Mantém uma ÚNICA aba dedicada ao WhatsApp Web no contexto.
    Se já houver uma aba aberta, reutiliza e navega direto na mesma aba.
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
