"""
Motor de Triagem Minuciosa e Funil Eliminatório Sequencial (Implementações 4, 5 e Item 6).

Utiliza `pandas` e `numpy` para estruturar o funil de dados em lote:
  - Primeiro recebe TODOS os leads possíveis coletados na região escolhida;
  - Aplica cada critério de qualificação SEQUENCIALMENTE sobre todo o lote,
    eliminando todos os candidatos que não se encaixam antes de passar ao próximo critério;
  - Gera telemetria completa do funil e estatísticas vetorizadas (prontas para futura
    integração com interface gráfica em Java).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from verifier import (
    ClienteHttp,
    PerfilInstagram,
    ResultadoPresencaDigital,
    VerificadorPresencaDigital,
    normalizar_nome,
    telefones_no_texto,
)

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
    numero_e164: str = ""
    numero_formatado: str = ""
    link_wa: str = ""
    origem: str = ""
    metodo_validacao: str = ""
    motivo_falha: str = ""


@dataclass
class PerfilEmpreendedor:
    categoria: str = "Micro-empreendedor em Ascensão 🔥"
    segmento: str = "micro_ascensao"
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


@dataclass
class EtapaFunil:
    numero: int
    codigo: str
    nome_criterio: str
    entrada: int
    eliminados: int
    sobreviventes: int
    taxa_aprovacao: float
    motivos_eliminacao: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RelatorioFunilRegiao:
    regiao: str
    nicho: str
    total_bruto_coletado: int
    total_qualificados: int
    etapas: list[EtapaFunil] = field(default_factory=list)
    estatisticas_numpy: dict = field(default_factory=dict)
    leads_aprovados: list[dict] = field(default_factory=list)
    dataframe_final: pd.DataFrame | None = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            "regiao": self.regiao,
            "nicho": self.nicho,
            "total_bruto_coletado": self.total_bruto_coletado,
            "total_qualificados": self.total_qualificados,
            "etapas": [e.to_dict() for e in self.etapas],
            "estatisticas": self.estatisticas_numpy,
        }


# --------------------------------------------------------------------------------------
# Normalização e Validação de Telefone / WhatsApp
# --------------------------------------------------------------------------------------

def normalizar_numero_br(telefone: str) -> str:
    """Normaliza um telefone brasileiro para E.164 sem '+' (55 + DDD + número)."""
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
    if ddd not in DDDS_VALIDOS_BR or len(set(assinante)) == 1:
        return ""
    return "55" + nacional


def eh_celular_br(numero_e164: str) -> bool:
    n = normalizar_numero_br(numero_e164)
    return len(n) == 13 and n[4] == "9" and n[5] in "6789"


def eh_fixo_br(numero_e164: str) -> bool:
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
    if not url:
        return ""
    u = url.lower()
    if not any(h in u for h in ("wa.me/", "whatsapp.com/send", "api.whatsapp.com", "web.whatsapp.com")):
        return ""
    m = re.search(r"(?:wa\.me/|phone=)(\+?55?\d{10,11}|\d{10,13})", url, re.IGNORECASE)
    return normalizar_numero_br(m.group(1)) if m else ""


def testar_numero_whatsapp_http(numero_e164: str, http: ClienteHttp | None = None) -> tuple[bool, str]:
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
            if f"+55 {n[2:4]}" in resp.texto:
                return True, "celular brasileiro validado na API do WhatsApp"

    return True, "celular brasileiro válido (padrão ANATEL 9 dígitos)"


def extrair_candidatos_whatsapp_instagram(
    perfil: PerfilInstagram | None,
    links_extras: list[str] | None = None,
) -> list[tuple[str, str, bool]]:
    if perfil is None or not perfil.acessivel:
        return []

    candidatos: list[tuple[str, str, bool]] = []
    vistos: set[str] = set()

    def adicionar(num_bruto: str, origem: str, eh_wame: bool):
        n = normalizar_numero_br(num_bruto)
        if n and n not in vistos:
            vistos.add(n)
            candidatos.append((n, origem, eh_wame))

    for u in perfil.links_bio:
        if n := extrair_numero_de_link_whatsapp(u):
            adicionar(n, "Instagram (wa.me na bio)", True)
    for u in perfil.links_destaques:
        if n := extrair_numero_de_link_whatsapp(u):
            adicionar(n, "Instagram (wa.me nos destaques)", True)
    for u in links_extras or []:
        if n := extrair_numero_de_link_whatsapp(u):
            adicionar(n, "Instagram (wa.me em agregador da bio)", True)
    if perfil.telefone_comercial:
        adicionar(perfil.telefone_comercial, "Instagram (telefone comercial)", False)
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
    """Testa WhatsApp no Maps e faz fallback automático no perfil do Instagram se necessário."""
    for u in links_maps or []:
        if n_wa := extrair_numero_de_link_whatsapp(u):
            return ResultadoWhatsapp(
                possui_whatsapp=True,
                numero_e164=n_wa,
                numero_formatado=formatar_numero_br(n_wa),
                link_wa=f"https://wa.me/{n_wa}",
                origem="Google Maps (link oficial wa.me)",
                metodo_validacao="link wa.me explícito na ficha do Google Maps",
            )

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

    for n_ig, origem_ig, veio_de_wame in extrair_candidatos_whatsapp_instagram(perfil_instagram, links_agregador_instagram):
        if veio_de_wame:
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
    texto = normalizar_nome(f"{nome} {categoria_maps}")
    for termo in GRANDES_REDES_IGNORAR:
        if re.search(rf"\b{re.escape(termo)}\b", texto):
            return True, f"Franquia/rede nacional ou órgão público ('{termo}')"
    return False, ""


def classificar_perfil_empreendedor(lead: dict) -> PerfilEmpreendedor:
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
    score = 0
    if not lead.get("tem_site", False):
        score += 30

    if perfil.segmento in ("autonomo_ascensao", "micro_ascensao"):
        score += 25
    elif perfil.segmento == "startup":
        score += 20
    else:
        score += 14

    if whatsapp.possui_whatsapp:
        score += 15

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
        score += 5

    if 15 <= qtd_av <= 90 or qtd_escritas >= 15:
        score += 8
    elif qtd_av >= 10:
        score += 6

    if lead.get("tem_fotos"):
        score += 4
    if lead.get("url_instagram"):
        score += 3
    dono = str(lead.get("dono_gerente", "") or "")
    if dono and "confirmar" not in dono.lower() and "consultar" not in dono.lower():
        score += 3

    return min(100, max(15, score))


def avaliar_reputacao_e_avaliacoes(
    nota: float,
    qtd_avaliacoes: int,
    qtd_avaliacoes_escritas: int,
    min_avaliacoes_escritas: int = 10,
    nota_minima: float = 4.0,
    avaliacoes_ocultas_pela_rede: bool = False,
) -> tuple[bool, bool, str]:
    if nota <= 0:
        return False, False, "Estabelecimento sem nota/avaliações no Google Maps"

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
    """Executa a triagem completa de um único lead e enriquece seus campos."""
    cfg = config_filtros or {}
    min_escritas = int(cfg.get("min_avaliacoes_escritas", 10))
    nota_minima = float(cfg.get("nota_minima", 4.0))

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

    if presenca.tem_site:
        return ResultadoTriagem(
            aprovado=False,
            etapa_reprovacao="possui_site_ou_sistema",
            motivo_reprovacao=f"Possui site/sistema/landing page: {presenca.motivo}",
        )

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

    res_zap = verificar_e_obter_whatsapp(
        telefone_maps=lead.get("telefone", ""),
        links_maps=lead.get("links_brutos_maps", []) or presenca.links_maps_brutos,
        perfil_instagram=presenca.perfil_instagram,
        links_agregador_instagram=lead.get("links_agregador_instagram", []) or presenca.links_expandidos,
        http=http,
    )
    if not res_zap.possui_whatsapp:
        return ResultadoTriagem(
            aprovado=False,
            etapa_reprovacao="whatsapp_obrigatorio",
            motivo_reprovacao=f"Sem WhatsApp confirmado ({res_zap.motivo_falha})",
            whatsapp=res_zap,
        )

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


# --------------------------------------------------------------------------------------
# 5. MOTOR DE FUNIL ELIMINATÓRIO SEQUENCIAL EM LOTE (PANDAS + NUMPY) — ITEM 5
# --------------------------------------------------------------------------------------

def executar_funil_sequencial(
    leads_brutos: list[dict],
    regiao: str = "",
    nicho: str = "",
    verificador: VerificadorPresencaDigital | None = None,
    page=None,
    config_filtros: dict | None = None,
    config_verificacao: dict | None = None,
    callback_investigacao: Callable[[dict], ResultadoPresencaDigital] | None = None,
    silencioso: bool = False,
) -> RelatorioFunilRegiao:
    """
    Executa o algoritmo de funil sequencial em lote (Item 5):
      1. Recebe TODOS os leads possíveis coletados na região escolhida;
      2. Aplica UM critério específico por vez sobre todos os candidatos restantes,
         eliminando quem não se encaixa antes de avançar para o critério subsequente;
      3. Utiliza `pandas.DataFrame` e `numpy` para filtragem tabular, priorização de
         autônomos/micro-empreendedores em ascensão e geração de métricas estatísticas.
    """
    cfg = config_filtros or {}
    cfg_ver = config_verificacao or {}
    min_escritas = int(cfg.get("min_avaliacoes_escritas", 10))
    nota_minima = float(cfg.get("nota_minima", 4.0))
    exigir_sem_site = bool(cfg.get("exigir_sem_site", True))
    exigir_ig = bool(cfg_ver.get("exigir_instagram_verificado", False))
    rejeitar_inconc = bool(cfg_ver.get("rejeitar_inconclusivos", True))

    total_inicial = len(leads_brutos)
    relatorio = RelatorioFunilRegiao(
        regiao=regiao,
        nicho=nicho,
        total_bruto_coletado=total_inicial,
        total_qualificados=0,
    )

    if not leads_brutos:
        relatorio.dataframe_final = pd.DataFrame()
        return relatorio

    def log(msg: str) -> None:
        if not silencioso:
            print(msg)

    log(f"\n┌──────────────────────────────────────────────────────────────────────────────┐")
    log(f"│ 🧪 FUNIL SEQUENCIAL DE TRIAGEM • {nicho.upper()} — {regiao} ({total_inicial} leads brutos)")
    log(f"└──────────────────────────────────────────────────────────────────────────────┘")

    # Mantemos os dicionários originais sincronizados com um DataFrame pandas pelo índice `_idx_funil`
    candidatos = list(leads_brutos)
    for i, item in enumerate(candidatos):
        item["_idx_funil"] = i

    def _registrar_etapa(num: int, codigo: str, nome_crit: str, antes: list[dict], depois: list[dict], motivos: list[str]):
        n_in = len(antes)
        n_out = len(depois)
        n_elim = n_in - n_out
        taxa = round((n_out / n_in) * 100.0, 1) if n_in > 0 else 0.0
        etapa = EtapaFunil(
            numero=num,
            codigo=codigo,
            nome_criterio=nome_crit,
            entrada=n_in,
            eliminados=n_elim,
            sobreviventes=n_out,
            taxa_aprovacao=taxa,
            motivos_eliminacao=motivos[:15],
        )
        relatorio.etapas.append(etapa)
        log(f"  [Critério {num}] {nome_crit}")
        log(f"     ↳ Entrada: {n_in} | ❌ Eliminados: {n_elim} | ✅ Sobreviventes: {n_out} ({taxa}%)")
        for m in motivos[:4]:
            log(f"       • {m}")

    # =========================================================================
    # CRITÉRIO 1: Integridade Operacional & Exclusão de Grandes Redes/Franquias
    # =========================================================================
    antes_1 = list(candidatos)
    sobreviventes_1: list[dict] = []
    motivos_1: list[str] = []
    for lead in antes_1:
        if lead.get("fechado_permanentemente") or lead.get("fechado_temporariamente"):
            motivos_1.append(f"'{lead.get('nome')}': estabelecimento fechado no Google Maps")
            continue
        eh_rede, mot_rede = eh_grande_rede_ou_orgao_publico(lead.get("nome", ""), lead.get("categoria_maps", ""))
        if eh_rede:
            motivos_1.append(f"'{lead.get('nome')}': {mot_rede}")
            continue
        sobreviventes_1.append(lead)
    candidatos = sobreviventes_1
    _registrar_etapa(1, "integridade_e_perfil", "Empresas/Autônomos ativos (sem franquias nacionais ou fechados)", antes_1, candidatos, motivos_1)

    # =========================================================================
    # CRITÉRIO 2: Mínimo de 10 Avaliações Escritas no Google Maps (via Pandas)
    # =========================================================================
    antes_2 = list(candidatos)
    sobreviventes_2: list[dict] = []
    motivos_2: list[str] = []
    if antes_2:
        df_2 = pd.DataFrame(antes_2)
        qtd_av_arr = pd.to_numeric(df_2.get("qtd_avaliacoes", 0), errors="coerce").fillna(0).to_numpy(dtype=int)
        qtd_esc_arr = pd.to_numeric(df_2.get("qtd_avaliacoes_escritas", 0), errors="coerce").fillna(0).to_numpy(dtype=int)
        ocultas_arr = df_2.get("avaliacoes_ocultas_pela_rede", pd.Series([False] * len(df_2))).fillna(False).to_numpy(dtype=bool)
        nota_arr = pd.to_numeric(df_2.get("nota", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)

        mascara_2 = (nota_arr > 0) & (ocultas_arr | ((qtd_av_arr >= min_escritas) & (qtd_esc_arr >= min_escritas)))
        for idx_row, passou in enumerate(mascara_2):
            lead = antes_2[idx_row]
            if passou:
                sobreviventes_2.append(lead)
            else:
                motivos_2.append(
                    f"'{lead.get('nome')}': {int(qtd_esc_arr[idx_row])} avaliações escritas / {int(qtd_av_arr[idx_row])} totais (mínimo: {min_escritas})"
                )
    candidatos = sobreviventes_2
    _registrar_etapa(2, "minimo_avaliacoes_escritas", f"Mínimo de {min_escritas} avaliações escritas no Google Maps", antes_2, candidatos, motivos_2)

    # =========================================================================
    # CRITÉRIO 3: 4.0 de Estrelas (ou < 4.0 caso possua > 10 avaliações)
    # =========================================================================
    antes_3 = list(candidatos)
    sobreviventes_3: list[dict] = []
    motivos_3: list[str] = []
    for lead in antes_3:
        nota = float(lead.get("nota", 0.0) or 0.0)
        qtd_av = int(lead.get("qtd_avaliacoes", 0) or 0)
        qtd_esc = int(lead.get("qtd_avaliacoes_escritas", 0) or 0)
        ocultas = bool(lead.get("avaliacoes_ocultas_pela_rede", False))
        ok_rep, excecao, msg = avaliar_reputacao_e_avaliacoes(nota, qtd_av, qtd_esc, min_escritas, nota_minima, ocultas)
        if ok_rep:
            lead["_excecao_nota"] = excecao
            lead["_msg_reputacao"] = msg
            sobreviventes_3.append(lead)
        else:
            motivos_3.append(f"'{lead.get('nome')}': {msg}")
    candidatos = sobreviventes_3
    _registrar_etapa(3, "estrelas_e_reputacao", f"Nota >= {nota_minima:.1f}★ (ou < {nota_minima:.1f}★ com > {min_escritas} avaliações)", antes_3, candidatos, motivos_3)

    # =========================================================================
    # CRITÉRIO 4 [OBRIGATÓRIO]: Não possuir Site, Sistema Próprio ou Landing Page
    # =========================================================================
    antes_4 = list(candidatos)
    sobreviventes_4: list[dict] = []
    motivos_4: list[str] = []
    for lead in antes_4:
        # 4a. Já detectado com site/sistema próprio direto na ficha do Google Maps
        if exigir_sem_site and lead.get("tem_site"):
            motivos_4.append(f"'{lead.get('nome')}': site/sistema no Google Maps ({lead.get('url_site')})")
            continue

        # 4b. Investigação profunda no Instagram (bio + destaques + agregadores) e Web
        res_presenca: ResultadoPresencaDigital | None = lead.get("_presenca_digital")
        if callback_investigacao is not None:
            res_presenca = callback_investigacao(lead)
        elif verificador is not None and (res_presenca is None or res_presenca.status_instagram == "nao_verificado"):
            res_presenca = verificador.verificar(page, lead, resultado_maps=res_presenca)

        if res_presenca is None:
            res_presenca = ResultadoPresencaDigital()

        lead["_presenca_digital"] = res_presenca
        lead["tem_site"] = res_presenca.tem_site
        lead["url_site"] = res_presenca.motivo
        lead["evidencias_site"] = [str(e) for e in res_presenca.evidencias]
        lead["links_brutos_maps"] = list(res_presenca.links_maps_brutos or lead.get("links_brutos_maps", []))
        lead["links_agregador_instagram"] = list(res_presenca.links_expandidos or lead.get("links_agregador_instagram", []))
        lead["url_instagram"] = res_presenca.url_instagram or lead.get("url_instagram", "")
        lead["status_instagram"] = res_presenca.status_instagram
        lead["detalhe_instagram"] = res_presenca.detalhe_instagram
        if res_presenca.perfil_instagram and res_presenca.perfil_instagram.acessivel:
            lead["instagram"] = res_presenca.perfil_instagram.to_dict()

        if exigir_sem_site:
            if res_presenca.tem_site:
                motivos_4.append(f"'{lead.get('nome')}': {res_presenca.motivo}")
                continue
            if res_presenca.status_instagram == "inacessivel" and exigir_ig:
                motivos_4.append(f"'{lead.get('nome')}': Instagram inacessível ({res_presenca.detalhe_instagram})")
                continue
            if res_presenca.inconclusivos and rejeitar_inconc:
                motivos_4.append(f"'{lead.get('nome')}': link inconclusivo ({res_presenca.inconclusivos[0]})")
                continue

        sobreviventes_4.append(lead)
    candidatos = sobreviventes_4
    _registrar_etapa(4, "obrigatorio_sem_site", "[OBRIGATÓRIO] 100% Sem Site, Sistema Próprio ou Landing Page (Maps + Instagram + Web)", antes_4, candidatos, motivos_4)

    # =========================================================================
    # CRITÉRIO 5 [OBRIGATÓRIO]: Número de WhatsApp (Maps -> Fallback Instagram)
    # =========================================================================
    antes_5 = list(candidatos)
    sobreviventes_5: list[dict] = []
    motivos_5: list[str] = []
    http_client = verificador.http if verificador is not None else None
    for lead in antes_5:
        res_presenca: ResultadoPresencaDigital = lead.get("_presenca_digital") or ResultadoPresencaDigital()
        res_zap = verificar_e_obter_whatsapp(
            telefone_maps=lead.get("telefone", ""),
            links_maps=lead.get("links_brutos_maps", []),
            perfil_instagram=res_presenca.perfil_instagram,
            links_agregador_instagram=lead.get("links_agregador_instagram", []),
            http=http_client,
        )
        if not res_zap.possui_whatsapp:
            motivos_5.append(f"'{lead.get('nome')}': {res_zap.motivo_falha}")
            continue

        lead["_res_whatsapp"] = res_zap
        lead["telefone"] = res_zap.numero_formatado
        lead["telefone_e164"] = res_zap.numero_e164
        lead["link_whatsapp"] = res_zap.link_wa
        lead["whatsapp_confirmado"] = True
        lead["origem_whatsapp"] = res_zap.origem
        sobreviventes_5.append(lead)
    candidatos = sobreviventes_5
    _registrar_etapa(5, "obrigatorio_whatsapp", "[OBRIGATÓRIO] Número de WhatsApp válido (Maps ou fallback Instagram)", antes_5, candidatos, motivos_5)

    # =========================================================================
    # CRITÉRIO 6 [PRIORIDADE]: Classificação e Priorização de Autônomos/Micro em Ascensão
    # =========================================================================
    antes_6 = list(candidatos)
    for lead in antes_6:
        res_presenca: ResultadoPresencaDigital = lead.get("_presenca_digital") or ResultadoPresencaDigital()
        res_zap: ResultadoWhatsapp = lead.get("_res_whatsapp") or ResultadoWhatsapp(possui_whatsapp=True)
        perfil = classificar_perfil_empreendedor(lead)
        score = calcular_score_conversao(lead, perfil, res_zap)

        insights: list[str] = [perfil.justificativa]
        if lead.get("_excecao_nota") and lead.get("_msg_reputacao"):
            insights.append(lead["_msg_reputacao"])
        qtd_esc = int(lead.get("qtd_avaliacoes_escritas", 0) or 0)
        if qtd_esc >= min_escritas:
            insights.append(f"{qtd_esc} avaliações escritas verificadas no Google Maps")
        if "Instagram" in res_zap.origem:
            insights.append(f"WhatsApp recuperado via {res_zap.origem}: {res_zap.numero_formatado}")
        else:
            insights.append(f"WhatsApp confirmado via {res_zap.origem}")
        for obs in res_presenca.observacoes:
            if obs not in insights:
                insights.append(obs)

        lead["porte_classificacao"] = perfil.categoria
        lead["segmento_empreendedor"] = perfil.segmento
        lead["em_ascensao"] = perfil.em_ascensao
        lead["prioridade_maxima"] = perfil.prioridade_maxima
        lead["score_potencial"] = score
        lead["observacoes"] = insights

        # Remove chaves internas temporárias de trabalho
        for ch_temp in ("_idx_funil", "_presenca_digital", "_res_whatsapp", "_excecao_nota", "_msg_reputacao"):
            lead.pop(ch_temp, None)

    # Ordena priorizando: 1º) Autônomos/Micro em ascensão (prioridade_maxima), 2º) Maior Score, 3º) Maior Nota
    candidatos.sort(
        key=lambda x: (
            1 if x.get("prioridade_maxima") else 0,
            int(x.get("score_potencial", 0)),
            float(x.get("nota", 0.0)),
        ),
        reverse=True,
    )
    _registrar_etapa(6, "prioridade_ascensao", "[PRIORIDADE] Triagem de Porte e Priorização de Autônomos/Micro em Ascensão", antes_6, candidatos, [])

    # Estatísticas vetorizadas com NumPy e Pandas (prontas para relatórios e futura GUI em Java)
    if candidatos:
        df_final = pd.DataFrame(candidatos)
        scores_np = df_final["score_potencial"].to_numpy(dtype=float)
        notas_np = df_final["nota"].to_numpy(dtype=float)
        av_np = df_final["qtd_avaliacoes"].to_numpy(dtype=float)
        ascensao_count = int(np.sum(df_final["em_ascensao"].to_numpy(dtype=bool)))

        relatorio.estatisticas_numpy = {
            "score_medio": round(float(np.mean(scores_np)), 1),
            "score_mediana": round(float(np.median(scores_np)), 1),
            "score_max": int(np.max(scores_np)),
            "nota_media": round(float(np.mean(notas_np)), 2),
            "avaliacoes_media": round(float(np.mean(av_np)), 1),
            "total_em_ascensao": ascensao_count,
            "percentual_em_ascensao": round((ascensao_count / len(candidatos)) * 100.0, 1),
        }
        relatorio.dataframe_final = df_final
    else:
        relatorio.dataframe_final = pd.DataFrame()

    relatorio.leads_aprovados = candidatos
    relatorio.total_qualificados = len(candidatos)

    log(f"  🏁 [RESULTADO DO FUNIL] {len(candidatos)}/{total_inicial} leads aprovados em todos os 6 critérios!\n")
    return relatorio
