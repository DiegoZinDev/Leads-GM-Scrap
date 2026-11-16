"""Vagas publicadas pela CI&T na Lever. Somente consultas à API pública."""
import json
import re
import unicodedata
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from uuid import UUID


def normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto or "").casefold() if not unicodedata.combining(c))


def contem(texto_normalizado, termo):
    return bool(re.search(r"(?<!\w)" + re.escape(normalizar(termo)) + r"(?!\w)", texto_normalizado))


def consultar():
    inicio, vistos = 0, set()
    while True:
        url = f"https://api.lever.co/v0/postings/ciandt?mode=json&limit=100&skip={inicio}"
        with urlopen(Request(url, headers={"User-Agent": "UrWork/0.1"}), timeout=20) as resposta:
            pagina = json.load(resposta)
        if not isinstance(pagina, list):
            raise ValueError("Resposta inesperada da Lever")
        novos = [item for item in pagina if item["id"] not in vistos]
        for item in novos:
            if item["id"] not in vistos:
                vistos.add(item["id"])
                yield item
        if len(pagina) < 100:
            return
        if not novos:
            raise ValueError("Paginação repetida pela Lever")
        inicio += len(pagina)


ROTULOS = {
    "nivel": {"JUNIOR": ("junior", "jr", "entry level"), "PLENO": ("pleno", "plena", "mid level", "mid-level"),
              "SENIOR": ("senior", "sr"), "ESPECIALISTA": ("specialist", "especialista", "staff", "principal engineer")},
    "vinculo": {"CLT": ("clt",), "PJ": ("pj", "pessoa juridica"), "ESTAGIO": ("estagio", "internship", "intern"),
                "TEMPORARIO": ("temporario", "temporary")},
    "jornada": {"INTEGRAL": ("integral", "full time", "full-time"), "PARCIAL": ("meio periodo", "part time", "part-time")},
    "turno": {"MANHA": ("turno da manha", "morning shift"), "TARDE": ("turno da tarde", "afternoon shift"),
              "NOITE": ("turno da noite", "night shift")},
}


def rotulos(campo, texto):
    return [nome for nome, termos in ROTULOS[campo].items() if any(contem(texto, termo) for termo in termos)]


def qualificar(item, pedido):
    f = pedido["vagas"]
    cat = item.get("categories") or {}
    cargo = item.get("text", "")
    descricao = item.get("descriptionPlain") or ""
    local = cat.get("location") or ""
    locais = " / ".join(cat.get("allLocations") or [local])
    pais = item.get("country")
    modalidade = {"remote": "REMOTO", "hybrid": "HIBRIDO", "on-site": "PRESENCIAL"}.get(item.get("workplaceType"))
    texto = normalizar(" ".join([cargo, descricao, cat.get("department") or "", cat.get("team") or ""]))
    if (not cargo or (f.get("pais") and f["pais"] != pais) or (f.get("exterior") is False and pais != "BR")
            or (f.get("modalidade") and f["modalidade"] != modalidade)):
        return None
    regiao = pedido.get("regiao")
    if regiao and (pais != "BR" or not contem(normalizar(locais), regiao.rsplit(" - ", 1)[0])):
        return None
    if any(not contem(normalizar(cargo), termo) for termo in f.get("cargo", "").split()):
        return None
    if any(not contem(texto, termo) for termo in pedido.get("nicho", "").split()):
        return None
    compromisso = cat.get("commitment") or ""
    contrato = normalizar(" ".join([cargo, compromisso, descricao]))
    senioridade = normalizar(cargo + " " + (cat.get("level") or ""))
    campos = {k: rotulos(k, senioridade if k == "nivel" else contrato) for k in ROTULOS}
    if any(f.get(k) and f[k] not in valores for k, valores in campos.items()):
        return None
    # Links canônicos são reconstruídos apenas para identificadores da fonte validada.
    id_fonte = str(UUID(item["id"]))
    origem = "https://jobs.lever.co/ciandt/" + id_fonte
    salario = item.get("salaryRange") or {}
    publicado = item.get("createdAt")
    habilidades = [s for s in f.get("habilidades", []) if contem(texto, s)]
    periodo = {"per-year": "ANO", "per-month": "MES", "per-hour": "HORA",
               "yearly": "ANO", "monthly": "MES", "hourly": "HORA"}.get(salario.get("interval"))
    informado = any(isinstance(salario.get(k), (int, float)) for k in ("min", "max"))
    menor, maior = salario.get("min"), salario.get("max")
    menor_conhecido = menor if menor is not None else maior
    maior_conhecido = maior if maior is not None else menor
    compativel = (informado and bool(f.get("moeda")) and f["moeda"] == salario.get("currency")
                  and periodo == f.get("periodo")
                  and (f.get("salarioMin") is None or maior_conhecido >= f["salarioMin"])
                  and (f.get("salarioMax") is None or menor_conhecido <= f["salarioMax"]))
    escolaridade = bool(f.get("escolaridade") and contem(normalizar(descricao), f["escolaridade"]))
    anos = f.get("experienciaAnos")
    nivel_sugerido = None if anos is None else "JUNIOR" if anos < 2 else "PLENO" if anos < 5 else "SENIOR"
    rank = (int(compativel), len(habilidades), escolaridade, nivel_sugerido in campos["nivel"], informado, publicado or 0, id_fonte)
    return rank, dict(idFonte=id_fonte, fonte="Lever", cargo=cargo, empresa="CI&T", localidade=local or None,
                      pais=pais, modalidade=modalidade, publicadaEm=datetime.fromtimestamp(publicado/1000, timezone.utc).isoformat() if publicado else None,
                      urlOrigem=origem, urlCandidatura=origem+"/apply", salario={"min": salario.get("min"), "max": salario.get("max"),
                      "moeda": salario.get("currency"), "periodo": periodo} if informado else None,
                      descricao=descricao[:24000], habilidadesEncontradas=habilidades, **campos)


def buscar(pedido):
    resultados = []
    falha = None
    try:
        for item in consultar():
            resultado = qualificar(item, pedido)
            if resultado:
                resultados.append(resultado)
    except (OSError, ValueError, KeyError) as erro:
        falha = erro
    resultados.sort(key=lambda r: r[0], reverse=True)
    for _, vaga in resultados[:pedido["meta"]]:
        yield vaga
    if falha is not None:
        raise falha
