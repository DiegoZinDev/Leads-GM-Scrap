"""
Motor de Triagem Minuciosa e Qualificação de Leads (Implementação 4 & Critérios do Item 6).

Critérios implementados:
  1. Mínimo de 10 avaliações escritas no Google Maps (min_avaliacoes_escritas = 10).
  2. Nota >= 4.0 estrelas — OU, caso possua MAIS de 10 avaliações (qtd_avaliacoes > 10 e
     >= 10 avaliações escritas) e nota < 4.0, também é considerado (exceção por volume comprovado).
  3. [OBRIGATÓRIO] Não possuir nenhum tipo de site, sistema próprio de serviço ou landing page
     (wa.me, WhatsApp e redes sociais são permitidos).
  4. Empresas/empreendedores (micro ou grandes), Startups e Autônomos ativos, com bom histórico
     e reputação (descarta negócios fechados, órgãos públicos ou grandes redes/franquias nacionais).
  5. [PRIORIDADE MÁXIMA] Autônomos ou micro-empreendedores em ascensão que estão crescendo agora
     e precisam urgente de conteúdo digital.
  6. [OBRIGATÓRIO] Número de WhatsApp: testa se o número cadastrado no Maps possui WhatsApp;
     caso não possua (ex.: sem telefone ou telefone fixo comum sem wa.me), verifica dentro do
     perfil do Instagram (links da bio, agregadores, destaques, texto da bio e telefone comercial)
     se há um wa.me ou número de WhatsApp válido.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from instagram import PerfilInstagram, normalizar_nome, telefones_no_texto
from verifier import ClienteHttp, ResultadoPresencaDigital

# DDDs válidos no Brasil (ANATEL)
DDDS_VALIDOS_BR = {
    "11", "12", "13", "14", "15", "16", "17", "18", "19",
    "21", "22", "24", "27", "28",
    "31", "32", "33", "34", "35", "37", "38",
    "41", "42", "43", "44", "45", "46", "47", "48", "49",
    "51", "53", "54", "55",
    "61", "62", "63", "64", "65", "66", "67", "68", "69",
    "71", "73", "74", "75", "77", "79",
    "81", "82", "83", "84", "85", "86", "87", "88", "89",
    "91", "92", "93", "94", "95", "96", "97", "98", "99",
}

# Grandes redes/franquias nacionais ou órgãos públicos que não contratam criação de site local
GRANDES_REDES_IGNORAR = {
    "smart fit", "smartfit", "bluefit", "bodytech", "bio ritmo",
    "oral sin", "oral unic", "odontocompany", "sorridents", "coife odonto", "orthopride",
    "espacolaser", "espaçolaser", "giolaser", "botoclinic", "royal face",
    "drogasil", "droga raia", "pague menos", "drogaria sao paulo", "drogaria rosario",
    "mcdonalds", "mcdonald s", "burger king", "outback", "coco bambu", "madero", "habibs", "giraffas",
    "correios", "banco do brasil", "caixa economica", "bradesco", "itau", "santander", "sicoob", "sicredi",
    "senac", "senai", "sesc", "sesi", "sebrae", "detran", "procon", "tribunal", "defensoria publica",
}

TERMOS_AUTONOMO = (
    "dr ", "dr.", "dra ", "dra.", "advogado", "advogada", "dentista", "fisioterapeuta",
    "nutricionista", "psicologo", "psicologa", "nail designer", "hair designer", "hair stylist",
    "visagista", "cabeleireiro", "cabeleireira", "manicure", "esteticista", "barbeiro",
    "serralheiro", "personal", "consultor", "consultora",
)

TERMOS_MICRO_ASCENSAO = (
    "studio", "estudio", "estúdio", "espaco", "espaço", "atelie", "ateliê", "boutique",
    "concept", "prime", "lounge", "lab", "oficina", "barbearia", "salao", "salão",
    "clinica", "clínica", "consultorio", "consultório", "escritorio", "escritório",
)

TERMOS_STARTUP_OU_CONSOLIDADA = (
    "startup", "tech", "hub", "digital", "group", "grupo", "associados", "integrada",
    "centro medico", "centro odontologico", "hospital", "instituto", "corporacao", "ltda", "s/a",
)


@dataclass
class ResultadoWhatsapp:
    possui_whatsapp: bool = False
    numero_e164: str = ""          # Ex.: "5561999887766"
    numero_formatado: str = ""     # Ex.: "(61) 99988-7766"
    link_wa: str = ""              # Ex.: "https://wa.me/5561999887766"
    origem: str = ""               # "Google Maps (link wa.me)", "Google Maps (celular)", "Instagram (wa.me/bio)", etc.
    metodo_validacao: str = ""
    motivo_falha: str = ""


@dataclass
class PerfilEmpreendedor:
    categoria: str = "Micro-empreendedor em Ascensão"   # Rótulo principal exibido no PDF
    segmento: str = "micro_ascensao"                    # autonomo_ascensao | micro_ascensao | startup | consolidada
    em_ascensao: bool = True
    prioridade_maxima: bool = True
    justificativa: str = ""


@dataclass
class ResultadoTriagem:
    aprovado: bool = False
    etapa_reprovacao: str = ""
    motivo_reprovacao: str = ""
    score_potencial: int = 0
    prioridade_label: str = "MÉDIA"
    excecao_nota_por_volume: bool = False
    whatsapp: ResultadoWhatsapp = field(default_factory=ResultadoWhatsapp)
    perfil: PerfilEmpreendedor = field(default_factory=PerfilEmpreendedor)
    insights: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------------------
# Normalização e validação de números de telefone / WhatsApp
# --------------------------------------------------------------------------------------

def normalizar_numero_br(telefone: str) -> str:
    """
    Normaliza um telefone brasileiro para o formato E.164 sem '+' (55 + DDD + número).
    Retorna '' se não tiver quantidade válida de dígitos (10 ou 11 dígitos nacionais).
    """
    if not telefone:
        return ""
    digitos = re.sub(r"\D", "", str(telefone))
    while digitos.startswith("0"):
        digitos = digitos[1:]
    if digitos.startswith("55") and len(digitos) in (12, 13):
        nacional = digitos[2:]
    elif len(digitos) in (10, 11):
        nacional = digitos
    else:
        return ""

    ddd = nacional[:2]
    assinante = nacional[2:]
    if ddd not in DDDS_VALIDOS_BR:
        return ""
    # Rejeita sequências repetidas óbvias (ex.: 999999999, 00000000)
    if len(set(assinante)) == 1:
        return ""
    return "55" + nacional


def eh_celular_br(numero_e164: str) -> bool:
    """True se for celular brasileiro válido (55 + DDD + 9 + 8 dígitos)."""
    n = normalizar_numero_br(numero_e164)
    return len(n) == 13 and n[4] == "9" and n[5] in "6789"


def eh_fixo_br(numero_e164: str) -> bool:
    """True se for telefone fixo brasileiro (55 + DDD + [2-5] + 7 dígitos)."""
    n = normalizar_numero_br(numero_e164)
    return len(n) == 12 and n[4] in "2345"


def formatar_numero_br(numero_e164: str) -> str:
    n = normalizar_numero_br(numero_e164)
    if len(n) == 13:
        return f"({n[2:4]}) {n[4:9]}-{n[9:]}"
    if len(n) == 12:
        return f"({n[2:4]}) {n[4:8]}-{n[8:]}"
    return numero_e164 or ""


def extrair_numero_de_link_whatsapp(url: str) -> str:
    """Extrai o telefone normalizado de links wa.me/..., api.whatsapp.com/send?phone=..."""
    if not url:
        return ""
    u = url.lower()
    if not any(h in u for h in ("wa.me/", "whatsapp.com/send", "api.whatsapp.com", "web.whatsapp.com")):
        return ""
    m = re.search(r"(?:wa\.me/|phone=)(\+?55?\d{10,11}|\d{10,13})", url, re.IGNORECASE)
    if not m:
        return ""
    return normalizar_numero_br(m.group(1))


def testar_numero_whatsapp_http(numero_e164: str, http: ClienteHttp | None = None) -> tuple[bool, str]:
    """
    Testa se um número brasileiro possui WhatsApp válido.
    Regras:
      - Celular válido (ANATEL 11 dígitos iniciando com 9): verifica endpoint da API do WhatsApp
        (quando http disponível) para confirmar que o número é reconhecido e formatado pelo WhatsApp
        e não retorna erro de número inválido.
      - Telefone fixo (10 dígitos): só é aceito como WhatsApp se vier de link oficial wa.me
        (tratado em nível superior) porque linhas fixas comuns não possuem WhatsApp sem cadastro Business.
    """
    n = normalizar_numero_br(numero_e164)
    if not n:
        return False, "formato de telefone inválido"

    if eh_fixo_br(n):
        return False, "telefone fixo sem link wa.me confirmado"

    if not eh_celular_br(n):
        return False, "número não corresponde a celular brasileiro válido"

    if http is not None:
        resp = http.get(f"https://api.whatsapp.com/send/?phone={n}")
        if not resp.erro and resp.status == 200 and resp.texto:
            baixo = resp.texto.lower()
            sinais_invalido = (
                "phone number shared via url is invalid",
                "número de telefone compartilhado por url é inválido",
                "numero de telefone compartilhado por url e invalido",
            )
            if any(s in baixo for s in sinais_invalido):
                return False, "API do WhatsApp informou número inválido"
            # O WhatsApp formata números válidos reconhecidos com '+55 DD ...'
            if f"+55 {n[2:4]}" in resp.texto:
                return True, "celular brasileiro validado na API do WhatsApp"

    return True, "celular brasileiro válido (padrão ANATEL 9 dígitos)"


def extrair_candidatos_whatsapp_instagram(
    perfil: PerfilInstagram | None,
    links_extras: list[str] | None = None,
) -> list[tuple[str, str, bool]]:
    """
    Procura dentro do perfil do Instagram (links da bio, destaques, texto da bio,
    telefone comercial e links extras de agregadores) números de WhatsApp ou telefone.
    Retorna lista de tuplas: (numero_e164, origem, veio_de_link_wame).
    """
    if perfil is None or not perfil.acessivel:
        return []

    candidatos: list[tuple[str, str, bool]] = []
    vistos: set[str] = set()

    def adicionar(num_bruto: str, origem: str, eh_wame: bool):
        n = normalizar_numero_br(num_bruto)
        if n and n not in vistos:
            vistos.add(n)
            candidatos.append((n, origem, eh_wame))

    # 1. Links diretos wa.me / api.whatsapp.com na bio
    for u in perfil.links_bio:
        n = extrair_numero_de_link_whatsapp(u)
        if n:
            adicionar(n, "Instagram (wa.me na bio)", True)

    # 2. Links diretos wa.me nos Destaques
    for u in perfil.links_destaques:
        n = extrair_numero_de_link_whatsapp(u)
        if n:
            adicionar(n, "Instagram (wa.me nos destaques)", True)

    # 3. Links wa.me encontrados dentro de agregadores (Linktree/Beacons)
    for u in links_extras or []:
        n = extrair_numero_de_link_whatsapp(u)
        if n:
            adicionar(n, "Instagram (wa.me em agregador da bio)", True)

    # 4. Telefone comercial cadastrado no perfil profissional do Instagram
    if perfil.telefone_comercial:
        adicionar(perfil.telefone_comercial, "Instagram (telefone comercial)", False)

    # 5. Números de telefone ou wa.me escritos no texto da biografia
    for m in re.finditer(r"(?:wa\.me/|phone=)(\+?55?\d{10,11}|\d{10,13})", perfil.biografia or "", re.IGNORECASE):
        adicionar(m.group(1), "Instagram (wa.me no texto da bio)", True)

    for tel_txt in telefones_no_texto(perfil.biografia or ""):
        adicionar(tel_txt, "Instagram (telefone escrito na bio)", False)

    return candidatos


def verificar_e_obter_whatsapp(
    telefone_maps: str,
    links_maps: list[str] | None = None,
    perfil_instagram: PerfilInstagram | None = None,
    links_agregador_instagram: list[str] | None = None,
    http: ClienteHttp | None = None,
) -> ResultadoWhatsapp:
    """
    Cumpre o critério obrigatório de WhatsApp:
      1. Verifica se há link direto wa.me no próprio Google Maps (confirma inclusive WhatsApp Business em fixo).
      2. Testa se o número cadastrado no Google Maps possui WhatsApp válido.
      3. Caso NÃO possua (sem número ou número fixo sem wa.me), busca dentro do perfil do Instagram
         (links da bio, destaques, agregadores, telefone comercial e texto da bio) um wa.me ou telefone com WhatsApp.
    """
    # 1. Checa se o próprio Google Maps já traz um link wa.me / api.whatsapp.com explícito
    for u in links_maps or []:
        n_wa = extrair_numero_de_link_whatsapp(u)
        if n_wa:
            return ResultadoWhatsapp(
                possui_whatsapp=True,
                numero_e164=n_wa,
                numero_formatado=formatar_numero_br(n_wa),
                link_wa=f"https://wa.me/{n_wa}",
                origem="Google Maps (link oficial wa.me)",
                metodo_validacao="link wa.me explícito na ficha do Google Maps",
            )

    # 2. Testa o telefone cadastrado no Google Maps
    motivo_maps = "sem telefone no Google Maps"
    if telefone_maps:
        ok_maps, detalhe_maps = testar_numero_whatsapp_http(telefone_maps, http=http)
        if ok_maps:
            n_maps = normalizar_numero_br(telefone_maps)
            return ResultadoWhatsapp(
                possui_whatsapp=True,
                numero_e164=n_maps,
                numero_formatado=formatar_numero_br(n_maps),
                link_wa=f"https://wa.me/{n_maps}",
                origem="Google Maps",
                metodo_validacao=detalhe_maps,
            )
        motivo_maps = f"número do Maps ({telefone_maps}) reprovado: {detalhe_maps}"

    # 3. Fallback obrigatório: verifica dentro do perfil do Instagram se há wa.me ou número com WhatsApp
    candidatos_ig = extrair_candidatos_whatsapp_instagram(perfil_instagram, links_agregador_instagram)
    for n_ig, origem_ig, veio_de_wame in candidatos_ig:
        if veio_de_wame:
            # Link wa.me explícito no Instagram confirma WhatsApp (mesmo que seja WhatsApp Business em número fixo)
            return ResultadoWhatsapp(
                possui_whatsapp=True,
                numero_e164=n_ig,
                numero_formatado=formatar_numero_br(n_ig),
                link_wa=f"https://wa.me/{n_ig}",
                origem=origem_ig,
                metodo_validacao="link wa.me explícito no perfil do Instagram",
            )
        ok_ig, detalhe_ig = testar_numero_whatsapp_http(n_ig, http=http)
        if ok_ig:
            return ResultadoWhatsapp(
                possui_whatsapp=True,
                numero_e164=n_ig,
                numero_formatado=formatar_numero_br(n_ig),
                link_wa=f"https://wa.me/{n_ig}",
                origem=origem_ig,
                metodo_validacao=detalhe_ig,
            )

    return ResultadoWhatsapp(
        possui_whatsapp=False,
        motivo_falha=f"{motivo_maps}; nenhum WhatsApp válido encontrado no Instagram",
    )


# --------------------------------------------------------------------------------------
# Classificação de Perfil, Reputação e Detecção de Ascensão
# --------------------------------------------------------------------------------------

def eh_grande_rede_ou_orgao_publico(nome: str, categoria_maps: str = "") -> tuple[bool, str]:
    """Identifica franquias nacionais gigantes ou órgãos públicos que devem ser descartados."""
    texto = normalizar_nome(f"{nome} {categoria_maps}")
    for termo in GRANDES_REDES_IGNORAR:
        if re.search(rf"\b{re.escape(termo)}\b", texto):
            return True, f"Franquia/rede nacional ou órgão público ('{termo}')"
    return False, ""


def classificar_perfil_empreendedor(lead: dict) -> PerfilEmpreendedor:
    """
    Classifica o lead entre:
      - Autônomo em Ascensão (PRIORIDADE MÁXIMA)
      - Micro-empreendedor em Ascensão (PRIORIDADE MÁXIMA)
      - Startup / Negócio Inovador em Crescimento
      - Empresa Consolidada com Boa Reputação
    """
    nome_norm = normalizar_nome(lead.get("nome", ""))
    nicho_norm = normalizar_nome(lead.get("nicho", ""))
    cat_maps = normalizar_nome(lead.get("categoria_maps", ""))
    texto_geral = f"{nome_norm} {nicho_norm} {cat_maps}"

    qtd_av = int(lead.get("qtd_avaliacoes", 0) or 0)
    nota = float(lead.get("nota", 0.0) or 0.0)
    dono = str(lead.get("dono_gerente", "") or "")
    tem_dono_identificado = bool(dono and "confirmar" not in dono.lower() and "consultar" not in dono.lower())

    sinais_autonomo = any(t in texto_geral for t in TERMOS_AUTONOMO) or any(
        k in nicho_norm for k in ("nail", "hair", "advocacia", "odontologia", "fisioterapia", "serralheria")
    )
    sinais_micro = any(t in texto_geral for t in TERMOS_MICRO_ASCENSAO)
    sinais_consolidada = any(t in texto_geral for t in TERMOS_STARTUP_OU_CONSOLIDADA)

    # Faixa de ascensão: negócios que já provaram qualidade (10 a 90 avaliações, boa nota)
    # e estão crescendo no boca-a-boca / Instagram sem ainda ter site próprio.
    faixa_crescimento = 10 <= qtd_av <= 90 and nota >= 4.2

    if (sinais_autonomo and not sinais_consolidada) and (faixa_crescimento or qtd_av <= 120):
        just = f"Profissional/autônomo com excelente reputação ({nota:.1f}★ e {qtd_av} avaliações) sem presença web própria"
        if tem_dono_identificado:
            just += f" • Decisor ativo ({dono})"
        return PerfilEmpreendedor(
            categoria="Autônomo em Ascensão 🔥",
            segmento="autonomo_ascensao",
            em_ascensao=True,
            prioridade_maxima=True,
            justificativa=just,
        )

    if (sinais_micro or faixa_crescimento) and qtd_av <= 150 and not sinais_consolidada:
        just = f"Micro-empreendimento em expansão ({nota:.1f}★ e {qtd_av} avaliações) precisando urgente de posicionamento digital"
        return PerfilEmpreendedor(
            categoria="Micro-empreendedor em Ascensão 🔥",
            segmento="micro_ascensao",
            em_ascensao=True,
            prioridade_maxima=True,
            justificativa=just,
        )

    if "startup" in texto_geral or "tech" in texto_geral:
        return PerfilEmpreendedor(
            categoria="Startup / Negócio em Crescimento",
            segmento="startup",
            em_ascensao=True,
            prioridade_maxima=True,
            justificativa=f"Startup/negócio moderno com {qtd_av} avaliações e sem site institucional ativo",
        )

    return PerfilEmpreendedor(
        categoria="Empresa Consolidada • Alta Reputação",
        segmento="consolidada",
        em_ascensao=False,
        prioridade_maxima=False,
        justificativa=f"Empresa estabelecida com forte histórico ({qtd_av} avaliações, {nota:.1f}★) operando sem site próprio",
    )


def calcular_score_conversao(lead: dict, perfil: PerfilEmpreendedor, whatsapp: ResultadoWhatsapp) -> int:
    """
    Calcula o Score de Potencial de Conversão (0 a 100%) priorizando fortemente:
      - Autônomos e Micro-empreendedores em ascensão (+25 pts)
      - Ausência confirmada de site/sistema/landing page (+30 pts)
      - WhatsApp validado e direto (+15 pts)
      - Volume de avaliações escritas e reputação (+20 pts)
      - Qualidade de sinais comerciais: fotos, decisor identificado, Instagram ativo (+10 pts)
    """
    score = 0

    # 1. Ausência de site/sistema (Obrigatório)
    if not lead.get("tem_site", False):
        score += 30

    # 2. Prioridade máxima: Autônomos e Micro-empreendedores em ascensão
    if perfil.segmento in ("autonomo_ascensao", "micro_ascensao"):
        score += 25
    elif perfil.segmento == "startup":
        score += 20
    else:
        score += 14

    # 3. WhatsApp verificado (Obrigatório)
    if whatsapp.possui_whatsapp:
        score += 15

    # 4. Reputação e Avaliações Escritas
    nota = float(lead.get("nota", 0.0) or 0.0)
    qtd_av = int(lead.get("qtd_avaliacoes", 0) or 0)
    qtd_escritas = int(lead.get("qtd_avaliacoes_escritas", 0) or 0)

    if nota >= 4.7:
        score += 12
    elif nota >= 4.3:
        score += 10
    elif nota >= 4.0:
        score += 8
    elif qtd_av > 10:
        # Considerado pela regra de mais de 10 avaliações com nota < 4.0
        score += 5

    if 15 <= qtd_av <= 90 or qtd_escritas >= 15:
        score += 8  # Sweet spot de crescimento urgente
    elif qtd_av >= 10:
        score += 6

    # 5. Sinais extras de maturidade e conversão
    if lead.get("tem_fotos"):
        score += 4
    if lead.get("url_instagram"):
        score += 3
    dono = str(lead.get("dono_gerente", "") or "")
    if dono and "confirmar" not in dono.lower() and "consultar" not in dono.lower():
        score += 3

    return min(100, max(15, score))


# --------------------------------------------------------------------------------------
# Triagem Completa de um Lead
# --------------------------------------------------------------------------------------

def avaliar_reputacao_e_avaliacoes(
    nota: float,
    qtd_avaliacoes: int,
    qtd_avaliacoes_escritas: int,
    min_avaliacoes_escritas: int = 10,
    nota_minima: float = 4.0,
    avaliacoes_ocultas_pela_rede: bool = False,
) -> tuple[bool, bool, str]:
    """
    Aplica os critérios de avaliações e estrelas:
      - Mínimo de 10 avaliações escritas no Google Maps.
      - 4.0 de estrelas (caso possua MAIS de 10 avaliações e tiver menos de 4.0, também pode ser considerado).
    Retorna (aprovado, usou_excecao_nota, motivo).
    """
    if nota <= 0:
        return False, False, "Estabelecimento sem nota/avaliações no Google Maps"

    # Se a rede corporativa não ocultou o módulo de avaliações do Google Maps:
    if not avaliacoes_ocultas_pela_rede:
        if qtd_avaliacoes < min_avaliacoes_escritas:
            return (
                False,
                False,
                f"Possui apenas {qtd_avaliacoes} avaliações no Google Maps (mínimo exigido: {min_avaliacoes_escritas} avaliações escritas)",
            )
        if qtd_avaliacoes_escritas < min_avaliacoes_escritas:
            return (
                False,
                False,
                f"Possui apenas {qtd_avaliacoes_escritas} avaliações escritas no Google Maps (mínimo exigido: {min_avaliacoes_escritas})",
            )

    # Critério de estrelas: >= 4.0 OU (nota < 4.0 mas com MAIS de 10 avaliações)
    if nota >= nota_minima:
        return True, False, ""

    if qtd_avaliacoes > min_avaliacoes_escritas and qtd_avaliacoes_escritas >= min_avaliacoes_escritas:
        return (
            True,
            True,
            f"Nota {nota:.1f}★ (< {nota_minima:.1f}), mas aprovado por possuir {qtd_avaliacoes} avaliações ({qtd_avaliacoes_escritas} escritas)",
        )

    return (
        False,
        False,
        f"Nota {nota:.1f}★ abaixo de {nota_minima:.1f} e sem volume superior a {min_avaliacoes_escritas} avaliações",
    )


def realizar_triagem_minuciosa(
    lead: dict,
    presenca: ResultadoPresencaDigital,
    http: ClienteHttp | None = None,
    config_filtros: dict | None = None,
) -> ResultadoTriagem:
    """
    Executa a triagem completa e minuciosa do lead garantindo veracidade e alta conversão.
    Atualiza o dicionário `lead` in-place com os metadados enriquecidos e retorna ResultadoTriagem.
    """
    cfg = config_filtros or {}
    min_escritas = int(cfg.get("min_avaliacoes_escritas", 10))
    nota_minima = float(cfg.get("nota_minima", 4.0))

    # 1. Veracidade operacional: negócio aberto e não pertencente a grande franquia/órgão público
    if lead.get("fechado_permanentemente") or lead.get("fechado_temporariamente"):
        return ResultadoTriagem(
            aprovado=False,
            etapa_reprovacao="status_operacional",
            motivo_reprovacao="Estabelecimento consta como fechado no Google Maps",
        )

    eh_rede, motivo_rede = eh_grande_rede_ou_orgao_publico(lead.get("nome", ""), lead.get("categoria_maps", ""))
    if eh_rede:
        return ResultadoTriagem(
            aprovado=False,
            etapa_reprovacao="perfil_empresa",
            motivo_reprovacao=motivo_rede,
        )

    # 2. Critério OBRIGATÓRIO: Não possuir nenhum tipo de site, sistema próprio ou landing page
    if presenca.tem_site:
        return ResultadoTriagem(
            aprovado=False,
            etapa_reprovacao="possui_site_ou_sistema",
            motivo_reprovacao=f"Possui site/sistema/landing page: {presenca.motivo}",
        )

    # 3. Critério de Avaliações Escritas (>= 10) e Nota (>= 4.0 ou > 10 avaliações se < 4.0)
    nota = float(lead.get("nota", 0.0) or 0.0)
    qtd_av = int(lead.get("qtd_avaliacoes", 0) or 0)
    qtd_escritas = int(lead.get("qtd_avaliacoes_escritas", 0) or 0)
    ocultas_rede = bool(lead.get("avaliacoes_ocultas_pela_rede", False))

    ok_rep, excecao_nota, msg_rep = avaliar_reputacao_e_avaliacoes(
        nota=nota,
        qtd_avaliacoes=qtd_av,
        qtd_avaliacoes_escritas=qtd_escritas,
        min_avaliacoes_escritas=min_escritas,
        nota_minima=nota_minima,
        avaliacoes_ocultas_pela_rede=ocultas_rede,
    )
    if not ok_rep:
        return ResultadoTriagem(
            aprovado=False,
            etapa_reprovacao="avaliacoes_e_reputacao",
            motivo_reprovacao=msg_rep,
        )

    # 4. Critério OBRIGATÓRIO: Número de WhatsApp (Maps -> fallback Instagram)
    res_zap = verificar_e_obter_whatsapp(
        telefone_maps=lead.get("telefone", ""),
        links_maps=lead.get("links_brutos_maps", []),
        perfil_instagram=presenca.perfil_instagram,
        links_agregador_instagram=lead.get("links_agregador_instagram", []),
        http=http,
    )
    if not res_zap.possui_whatsapp:
        return ResultadoTriagem(
            aprovado=False,
            etapa_reprovacao="whatsapp_obrigatorio",
            motivo_reprovacao=f"Sem WhatsApp confirmado ({res_zap.motivo_falha})",
            whatsapp=res_zap,
        )

    # 5. Classificação de Perfil Empreendedor (Prioridade: Autônomos e Micro em Ascensão)
    perfil = classificar_perfil_empreendedor(lead)
    score = calcular_score_conversao(lead, perfil, res_zap)
    prioridade_label = "PRIORIDADE MÁXIMA" if (perfil.prioridade_maxima and score >= 85) else ("ALTA" if score >= 85 else "MÉDIA")

    insights: list[str] = [perfil.justificativa]
    if excecao_nota and msg_rep:
        insights.append(msg_rep)
    if qtd_escritas >= min_escritas:
        insights.append(f"{qtd_escritas} avaliações escritas verificadas no Google Maps")
    if "Instagram" in res_zap.origem:
        insights.append(f"WhatsApp recuperado via {res_zap.origem}: {res_zap.numero_formatado}")
    else:
        insights.append(f"WhatsApp confirmado via {res_zap.origem}")
    for obs in presenca.observacoes:
        if obs not in insights:
            insights.append(obs)

    # Atualiza os campos do lead
    lead["telefone"] = res_zap.numero_formatado
    lead["telefone_e164"] = res_zap.numero_e164
    lead["link_whatsapp"] = res_zap.link_wa
    lead["whatsapp_confirmado"] = True
    lead["origem_whatsapp"] = res_zap.origem
    lead["porte_classificacao"] = perfil.categoria
    lead["segmento_empreendedor"] = perfil.segmento
    lead["em_ascensao"] = perfil.em_ascensao
    lead["prioridade_maxima"] = perfil.prioridade_maxima
    lead["score_potencial"] = score
    lead["observacoes"] = insights

    return ResultadoTriagem(
        aprovado=True,
        score_potencial=score,
        prioridade_label=prioridade_label,
        excecao_nota_por_volume=excecao_nota,
        whatsapp=res_zap,
        perfil=perfil,
        insights=insights,
    )
