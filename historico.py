"""
Módulo para gerenciamento de histórico e desduplicação de leads.
Garante que leads já coletados nunca sejam repetidos nas próximas execuções.
"""

import os
import json
import re
from datetime import datetime

PASTA_PLANILHAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Planilhas")
ARQUIVO_HISTORICO = os.path.join(PASTA_PLANILHAS, "historico_leads.json")

def garantir_pasta_planilhas() -> str:
    """Cria o diretório Planilhas se ainda não existir."""
    os.makedirs(PASTA_PLANILHAS, exist_ok=True)
    return PASTA_PLANILHAS

def normalizar_texto(texto: str) -> str:
    """Remove caracteres especiais e converte para minúsculas."""
    if not texto:
        return ""
    texto = texto.lower().strip()
    texto = re.sub(r"[^\w\s]", "", texto)
    return re.sub(r"\s+", " ", texto)

def extrair_apenas_digitos(telefone: str) -> str:
    """Extrai somente os números do telefone."""
    if not telefone:
        return ""
    digitos = re.sub(r"\D", "", telefone)
    if digitos.startswith("0"):
        digitos = digitos[1:]
    return digitos

def carregar_historico() -> dict:
    """Carrega o banco de dados de leads já coletados."""
    garantir_pasta_planilhas()
    
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Aviso ao carregar histórico: {e}. Criando novo.")

    return {
        "telefones": {},
        "nomes_cidade": {},
        "urls_maps": {},
        "total_coletados": 0
    }

def lead_ja_existe(lead_ou_card: dict, historico: dict) -> tuple[bool, str]:
    """
    Verifica se o lead já foi coletado anteriormente por URL, telefone ou nome+cidade.
    Retorna (True/False, motivo).
    """
    # 1. Checagem por URL do Maps
    url = lead_ou_card.get("url_maps") or lead_ou_card.get("href")
    if url:
        # Pega a parte fixa da URL antes de interrogações ou parâmetros longos
        url_base = url.split("?")[0]
        if url_base in historico.get("urls_maps", {}):
            return True, "URL do Google Maps já cadastrada"

    # 2. Checagem por telefone
    tel = lead_ou_card.get("telefone")
    if tel:
        digitos = extrair_apenas_digitos(tel)
        if digitos and digitos in historico.get("telefones", {}):
            nome_anterior = historico["telefones"][digitos].get("nome", "")
            return True, f"Telefone ({tel}) já cadastrado para '{nome_anterior}'"

    # 3. Checagem por Nome + Cidade
    nome = lead_ou_card.get("nome")
    cidade = lead_ou_card.get("cidade", "")
    if nome:
        chave = f"{normalizar_texto(nome)}_{normalizar_texto(cidade)}"
        if chave in historico.get("nomes_cidade", {}):
            return True, f"Nome da empresa ('{nome}') já cadastrado nesta cidade"

    return False, ""

def salvar_no_historico(novos_leads: list, id_planilha: str):
    """Atualiza o arquivo JSON de histórico com os novos leads coletados."""
    historico = carregar_historico()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    adicionados = 0
    for lead in novos_leads:
        nome = lead.get("nome", "")
        cidade = lead.get("cidade", "")
        tel = lead.get("telefone", "")
        url = lead.get("url_maps", "")

        info_registro = {
            "nome": nome,
            "cidade": cidade,
            "data_coleta": agora,
            "id_planilha": id_planilha
        }

        # Registra telefone
        if tel:
            digitos = extrair_apenas_digitos(tel)
            if digitos:
                historico["telefones"][digitos] = info_registro

        # Registra Nome + Cidade
        if nome:
            chave = f"{normalizar_texto(nome)}_{normalizar_texto(cidade)}"
            historico["nomes_cidade"][chave] = info_registro

        # Registra URL
        if url:
            url_base = url.split("?")[0]
            historico["urls_maps"][url_base] = info_registro

        adicionados += 1

    historico["total_coletados"] = len(historico["telefones"])
    historico["ultima_atualizacao"] = agora

    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)

    print(f"[*] Histórico atualizado: {adicionados} novos leads registrados (Total no banco: {historico['total_coletados']}).")
