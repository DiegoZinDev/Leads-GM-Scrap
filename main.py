"""
Painel Principal do Bot de Captação de Leads (Google Maps).
Filtra estabelecimentos sem site, com verificação profunda na web (anti-cardápio digital/anti-site),
permite digitar nichos livres sem limite (resetados a cada nova busca) e gera planilha Excel + Relatório Executivo em PDF.
"""

import sys
import os
import re
import time
from datetime import datetime

# Garante suporte UTF-8 no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.sync_api import sync_playwright
from config import (
    NICHOS,
    NICHOS_ATUAIS,
    REGIOES,
    FILTROS,
    META_MINIMA_LEADS,
    PASTA_PERFIL_NAVEGADOR,
    definir_nichos_busca,
    resetar_nichos_busca,
)
from scraper import buscar_leads_google_maps
from exporter import salvar_planilha_excel
from historico import carregar_historico
from verifier import interceptar_novas_abas_whatsapp


def mostrar_banner():
    print("""
================================================================================
 🚀 BOT PROSPECTOR: LEADS QUALIFICADOS (GOOGLE MAPS + INVESTIGAÇÃO WEB)
    Nichos 100% Dinâmicos e Sem Limite | Regiões Configuráveis
    Filtro Rigoroso: 100% Sem Site | Sem Cardápio Digital | Alta Reputação
    Exportação Automática: Planilha Excel (.xlsx) e Relatório Executivo (.pdf)
    Anti-Duplicação: Leads já prospectados NUNCA são repetidos!
================================================================================
    """)


def solicitar_nichos_usuario() -> dict:
    """
    Solicita ao usuário que digite livremente quantos nichos desejar (sem limite).
    Aceita múltiplos nichos separados por vírgula/ponto-e-vírgula ou adicionados linha a linha.
    Popula a variável dinâmica de nichos para a pesquisa atual.
    """
    resetar_nichos_busca()
    lista_nichos = []

    print("\n" + "=" * 80)
    print(" 🎯 DEFINIÇÃO DE NICHOS DA PESQUISA (VARIÁVEL DINÂMICA - SEM LIMITE)")
    print("=" * 80)
    print(" • Digite qualquer nicho que deseja prospectar agora (ex: Barbearia, Pet Shop,")
    print("   Clínica Odontológica, Pizzaria, Oficina Mecânica, Contabilidade, etc.).")
    print(" • Você pode digitar vários de uma vez separados por vírgula (,) ou um por vez.")
    print(" • Digite 'sugestoes' se quiser ver exemplos ou 'todos' para usar os 10 modelos base.")
    print("-" * 80)

    while True:
        if not lista_nichos:
            prompt = "\n👉 Digite o(s) nicho(s) desejado(s): "
        else:
            print(f"\n📋 Nichos na fila atual ({len(lista_nichos)}): {', '.join(lista_nichos)}")
            prompt = "👉 Digite mais nichos para adicionar ou pressione [ENTER] para iniciar a busca: "

        entrada = input(prompt).strip()

        if not entrada:
            if lista_nichos:
                break
            print("[!] Você precisa digitar pelo menos 1 nicho para iniciar a pesquisa.")
            continue

        if entrada.lower() in ["sugestoes", "sugestões", "?"]:
            print("\n💡 Exemplos de nichos pré-otimizados (você pode digitar qualquer outro livremente):")
            for idx, k in enumerate(NICHOS.keys(), 1):
                print(f"   {idx}. {k}")
            continue

        if entrada.lower() == "todos":
            for k in NICHOS.keys():
                if k.lower() not in [n.lower() for n in lista_nichos]:
                    lista_nichos.append(k)
            print(f"[+] {len(NICHOS)} nichos base adicionados à fila!")
            break

        # Separa por vírgula ou ponto e vírgula, permitindo vários nichos de uma só vez
        partes = [p.strip() for p in re.split(r"[,;]+", entrada) if p.strip()]
        adicionados_agora = []
        for p in partes:
            if p.lower() not in [n.lower() for n in lista_nichos]:
                lista_nichos.append(p)
                adicionados_agora.append(p)

        if adicionados_agora:
            print(f"   ✅ Adicionado(s): {', '.join(adicionados_agora)}")
        else:
            print("   [i] Este(s) nicho(s) já estava(m) na lista.")

    nichos_configurados = definir_nichos_busca(lista_nichos)
    print(f"\n🔥 Total de {len(nichos_configurados)} nicho(s) configurado(s) para esta pesquisa!")
    return nichos_configurados


def solicitar_regioes_customizadas(regioes_atuais: list) -> list:
    """Permite escolher a abrangência geográfica ou digitar cidades/bairros sem limite."""
    print("\n" + "-" * 80)
    print(" 📍 CONFIGURAÇÃO DE REGIÕES / CIDADES DE BUSCA")
    print("-" * 80)
    print(f" Regiões atuais selecionadas ({len(regioes_atuais)}): {', '.join(regioes_atuais[:5])}{'...' if len(regioes_atuais) > 5 else ''}")
    print("\n Escolha uma opção de abrangência:")
    print("  1 - Todas as regiões padrão (Brasília DF + Valparaíso GO - 13 sub-regiões)")
    print("  2 - Apenas Brasília e Regiões Administrativas do DF")
    print("  3 - Apenas Valparaíso de Goiás e Entorno (GO)")
    print("  4 - Digitar Cidades / Bairros personalizados livremente (Sem Limite)")
    print("  Enter - Manter configuração atual")

    op = input("\nSua escolha [Padrão: Manter atual]: ").strip()
    if op == "1":
        return list(REGIOES)
    elif op == "2":
        return [r for r in REGIOES if "DF" in r]
    elif op == "3":
        return [r for r in REGIOES if "Valparaíso" in r or "GO" in r]
    elif op == "4":
        cidades_custom = []
        print("\nDigite as cidades/bairros + UF separados por vírgula (ex: Goiânia GO, Anápolis GO, Águas Claras DF):")
        while True:
            ent = input("👉 Cidade(s)/Região(ões) (ou ENTER para concluir): ").strip()
            if not ent:
                if cidades_custom:
                    break
                print("[!] Digite pelo menos uma cidade/região.")
                continue
            partes = [p.strip() for p in re.split(r"[,;]+", ent) if p.strip()]
            for p in partes:
                if p.lower() not in [c.lower() for c in cidades_custom]:
                    cidades_custom.append(p)
            print(f"   ✅ Regiões na lista ({len(cidades_custom)}): {', '.join(cidades_custom)}")
        return cidades_custom

    return regioes_atuais


def executar_prospeccao(nichos_selecionados: dict, regioes_selecionadas: list, meta_leads: int = 50, headless: bool = False):
    """
    Executa o ciclo de prospecção nos nichos informados pelo usuário e,
    ao finalizar, reseta automaticamente a variável de nichos para a próxima busca.
    """
    todos_os_leads = []
    inicio_tempo = time.time()
    historico = carregar_historico()

    print(f"\n[CONFIGURAÇÃO DA PROSPECÇÃO ATUAL]")
    print(f"- Nichos da Busca ({len(nichos_selecionados)}): {', '.join(nichos_selecionados.keys())}")
    print(f"- Regiões mapeadas ({len(regioes_selecionadas)}): {', '.join(regioes_selecionadas[:4])}{'...' if len(regioes_selecionadas) > 4 else ''}")
    print(f"- Meta Mínima de Leads: {meta_leads} leads 100% verificados sem site/cardápio")
    print(f"- Filtros: Nota >= {FILTROS.get('nota_minima', 4.0)}⭐ | Mín. {FILTROS.get('min_avaliacoes', 5)} avaliações | Exigir Tel: {'Sim' if FILTROS.get('exigir_telefone', True) else 'Não'}")
    print(f"- Histórico Ativo: {historico.get('total_coletados', 0)} leads já salvos (não serão repetidos)")
    print(f"- Saídas: Planilha Excel (.xlsx) + Relatório Executivo (.pdf)")
    print(f"- Modo Visual: {'Ativado (janela visível)' if not headless else 'Invisível (Headless)'}")
    print(f"--------------------------------------------------------------------------------\n")

    os.makedirs(PASTA_PERFIL_NAVEGADOR, exist_ok=True)
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=PASTA_PERFIL_NAVEGADOR,
                headless=headless,
                locale="pt-BR",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                args=["--disable-blink-features=AutomationControlled", "--start-maximized", "--window-size=1600,900"],
                viewport={"width": 1600, "height": 900} if headless else None,
                ignore_https_errors=True
            )
            # Garante redirecionamento inteligente de abas do WhatsApp para aba única
            interceptar_novas_abas_whatsapp(context)
            page = context.pages[0] if context.pages else context.new_page()

            atingiu_meta = False
            # Percorre nichos e regiões até bater a meta de leads
            while len(todos_os_leads) < meta_leads and not atingiu_meta:
                houve_novos = False
                for nicho_nome, dados_nicho in nichos_selecionados.items():
                    if len(todos_os_leads) >= meta_leads:
                        atingiu_meta = True
                        break

                    print(f"\n>>> NICHO ATUAL: [{nicho_nome.upper()}] | Progresso: {len(todos_os_leads)}/{meta_leads} leads <<<")

                    termos_nicho = dados_nicho.get("termos", [nicho_nome])
                    copy_nicho = dados_nicho.get("copy_base", "")

                    for regiao in regioes_selecionadas:
                        if len(todos_os_leads) >= meta_leads:
                            atingiu_meta = True
                            break

                        for termo in termos_nicho:
                            if len(todos_os_leads) >= meta_leads:
                                atingiu_meta = True
                                break

                            falta = meta_leads - len(todos_os_leads)
                            limite_busca = min(10, max(2, falta))

                            novos_leads = buscar_leads_google_maps(
                                page=page,
                                nicho_nome=nicho_nome,
                                termo_busca=termo,
                                cidade=regiao,
                                limite_leads=limite_busca,
                                historico=historico,
                                copy_base=copy_nicho
                            )

                            if novos_leads:
                                houve_novos = True
                                todos_os_leads.extend(novos_leads)
                                print(f"[*] Progresso do lote: {len(todos_os_leads)}/{meta_leads} leads qualificados.")

                # Se rodou todas as combinações sem encontrar nada novo, encerra para evitar loop infinito
                if not houve_novos:
                    print("\n[!] Varredura completa finalizada em todas as regiões e termos disponíveis.")
                    break

            # Salva a planilha e gera o PDF reutilizando a sessão ativa do Playwright
            if todos_os_leads:
                caminho_excel, caminho_pdf, id_planilha = salvar_planilha_excel(todos_os_leads, page=page)
            else:
                caminho_excel, caminho_pdf, id_planilha = "", "", ""

            context.close()

        tempo_total = round((time.time() - inicio_tempo) / 60, 2)
        print(f"\n================================================================================")
        print(f"🏁 PROSPECÇÃO CONCLUÍDA EM {tempo_total} MINUTOS!")
        print(f"Total de leads inéditos e 100% verificados: {len(todos_os_leads)}")
        print(f"================================================================================")

        if todos_os_leads:
            com_zap = sum(1 for l in todos_os_leads if l.get("telefone"))
            alta_prioridade = sum(1 for l in todos_os_leads if l.get("score_potencial", 0) >= 85)

            print(f"\n📊 RESUMO DOS ARQUIVOS GERADOS:")
            print(f"  • ID do Lote: {id_planilha}")
            print(f"  • Nichos Prospectados: {', '.join(nichos_selecionados.keys())}")
            print(f"  • Total de Leads: {len(todos_os_leads)} (Meta: {meta_leads})")
            print(f"  • Com Telefone / WhatsApp: {com_zap}")
            print(f"  • Alta Prioridade (Score >= 85%): {alta_prioridade}")
            print(f"  • Planilha Excel: {caminho_excel}")
            if caminho_pdf:
                print(f"  • Relatório PDF: {caminho_pdf}")
            print(f"\nArquivos salvos no diretório 'Planilhas/' prontos para prospecção!\n")
        else:
            print("[!] Nenhum lead inédito atendeu a todos os critérios restritos nesta rodada.")

    finally:
        # Reseta a variável de nichos ao final da pesquisa para os próximos nichos que o usuário for buscar
        resetar_nichos_busca()
        nichos_selecionados.clear()
        print("🔄 [RESET AUTOMÁTICO] Os nichos desta pesquisa foram resetados. Variável limpa para a próxima busca!")


def fazer_login_manual():
    """
    Abre o navegador visível com o perfil persistente para o usuário realizar
    o login manual no Instagram e escanear o QR Code do WhatsApp Web.
    Todas as sessões são salvas permanentemente em 'perfil_navegador/'.
    """
    print("\n" + "=" * 80)
    print(" 🔑 CONECTAR CONTAS (LOGIN MANUAL NO INSTAGRAM E WHATSAPP WEB)")
    print("================================================================================")
    print(" Instruções:")
    print(" 1. O navegador será aberto agora com 2 abas: Instagram e WhatsApp Web.")
    print(" 2. No Instagram: Faça login na sua conta para liberar a visualização de bios,")
    print("    links e destaques de cardápios dos estabelecimentos.")
    print(" 3. No WhatsApp Web: Escaneie o QR Code com seu celular (se desejar manter conectado).")
    print(" 4. Ao concluir seus logins, volte aqui no terminal e pressione [ENTER].")
    print("================================================================================\n")

    os.makedirs(PASTA_PERFIL_NAVEGADOR, exist_ok=True)

    with sync_playwright() as p:
        print("[*] Abrindo navegador para login manual...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=PASTA_PERFIL_NAVEGADOR,
            headless=False,
            locale="pt-BR",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            no_viewport=True,
            ignore_https_errors=True
        )

        page_insta = context.pages[0] if context.pages else context.new_page()
        try:
            page_insta.goto("https://www.instagram.com", wait_until="domcontentloaded")
        except Exception:
            pass

        page_zap = context.new_page()
        try:
            page_zap.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
        except Exception:
            pass

        print("👉 Janela aberta! Faça seus logins no Instagram e no WhatsApp Web.")
        input("\n[Pressione ENTER após terminar os logins para salvar a sessão e voltar ao menu]: ")

        print("\n💾 Salvando sessão e cookies em 'perfil_navegador/'...")
        context.close()
        print("✅ Sessão salva com sucesso! Suas buscas agora utilizarão as contas conectadas.\n")
        time.sleep(1.5)


def menu_configuracoes_avancadas(config_sessao: dict):
    """Submenu para aumentar o controle sobre filtros, regiões, metas e navegador."""
    while True:
        print("\n" + "=" * 80)
        print(" ⚙️ CONFIGURAÇÕES AVANÇADAS DA PROSPECÇÃO")
        print("=" * 80)
        print(f"  1 - Alterar Meta Mínima de Leads por Lote     [Atual: {config_sessao['meta_leads']} leads]")
        print(f"  2 - Configurar Regiões / Cidades Alvo         [Atual: {len(config_sessao['regioes'])} região(ões)]")
        print(f"  3 - Ajustar Nota Mínima no Google Maps        [Atual: {FILTROS['nota_minima']} ⭐]")
        print(f"  4 - Ajustar Mínimo de Avaliações Exigidas     [Atual: {FILTROS['min_avaliacoes']} avaliações]")
        print(f"  5 - Exigir Telefone Cadastrado                [Atual: {'Sim' if FILTROS['exigir_telefone'] else 'Não'}]")
        print(f"  6 - Modo da Janela do Navegador               [Atual: {'Invisível (Headless)' if config_sessao['headless'] else 'Visível na Tela'}]")
        print(f"  7 - Restaurar Todas as Configurações Padrão")
        print(f"  0 - Voltar ao Menu Principal")
        print("-" * 80)

        op = input("\nEscolha o item que deseja configurar [0-7]: ").strip()

        if op == "0" or not op:
            break
        elif op == "1":
            val = input(f"Digite a nova meta mínima de leads (ex: 20, 50, 100, 200) [Atual: {config_sessao['meta_leads']}]: ").strip()
            if val.isdigit() and int(val) > 0:
                config_sessao["meta_leads"] = int(val)
                print(f"✅ Meta atualizada para {config_sessao['meta_leads']} leads!")
            else:
                print("[!] Valor inválido.")
        elif op == "2":
            config_sessao["regioes"] = solicitar_regioes_customizadas(config_sessao["regioes"])
            print(f"✅ Regiões atualizadas ({len(config_sessao['regioes'])} selecionadas)!")
        elif op == "3":
            val = input(f"Digite a nota mínima de 0.0 a 5.0 (ex: 3.5, 4.0, 4.5) [Atual: {FILTROS['nota_minima']}]: ").strip().replace(",", ".")
            try:
                nota = float(val)
                if 0.0 <= nota <= 5.0:
                    FILTROS["nota_minima"] = nota
                    print(f"✅ Nota mínima atualizada para {nota} ⭐!")
                else:
                    print("[!] Digite um valor entre 0.0 e 5.0.")
            except ValueError:
                print("[!] Valor inválido.")
        elif op == "4":
            val = input(f"Digite o mínimo de avaliações no Google Maps (ex: 1, 5, 10, 30) [Atual: {FILTROS['min_avaliacoes']}]: ").strip()
            if val.isdigit() and int(val) >= 0:
                FILTROS["min_avaliacoes"] = int(val)
                print(f"✅ Mínimo de avaliações atualizado para {FILTROS['min_avaliacoes']}!")
            else:
                print("[!] Valor inválido.")
        elif op == "5":
            FILTROS["exigir_telefone"] = not FILTROS["exigir_telefone"]
            print(f"✅ Exigir telefone alterado para: {'Sim' if FILTROS['exigir_telefone'] else 'Não'}!")
        elif op == "6":
            config_sessao["headless"] = not config_sessao["headless"]
            print(f"✅ Modo do navegador alterado para: {'Invisível (Headless)' if config_sessao['headless'] else 'Visível na Tela'}!")
        elif op == "7":
            config_sessao["meta_leads"] = META_MINIMA_LEADS
            config_sessao["regioes"] = list(REGIOES)
            config_sessao["headless"] = False
            FILTROS["nota_minima"] = 4.0
            FILTROS["min_avaliacoes"] = 5
            FILTROS["exigir_telefone"] = True
            print("✅ Configurações restauradas para o padrão!")
        else:
            print("[!] Opção inválida.")


def menu_interativo():
    config_sessao = {
        "meta_leads": META_MINIMA_LEADS,
        "regioes": list(REGIOES),
        "headless": False
    }

    while True:
        mostrar_banner()
        perfil_existe = os.path.exists(PASTA_PERFIL_NAVEGADOR) and bool(os.listdir(PASTA_PERFIL_NAVEGADOR))
        status_txt = "✅ Conectado / Ativo" if perfil_existe else "⚠️ Não autenticado (Recomendado logar)"
        historico_atual = carregar_historico()
        status_nichos = "Limpo / Aguardando digitação" if not NICHOS_ATUAIS else f"{len(NICHOS_ATUAIS)} ativo(s)"

        print(f"Status do Perfil: {status_txt} | Leads no Histórico: {historico_atual.get('total_coletados', 0)}")
        print(f"Configuração Atual: Meta = {config_sessao['meta_leads']} leads | Regiões = {len(config_sessao['regioes'])} | Nota >= {FILTROS['nota_minima']}⭐ ({FILTROS['min_avaliacoes']}+ aval.)")
        print(f"Estado da Variável de Nichos: 🔄 {status_nichos} (Sem limite de nichos por busca)")
        print("--------------------------------------------------------------------------------")
        print("Escolha o modo de operação:")
        print("0 - 🔑 Conectar Contas (Fazer Login Manual no Instagram e WhatsApp Web)")
        print("1 - 🚀 Iniciar Prospecção (Digitar Nichos Livremente + Usar Configuração Atual)")
        print("2 - 🎯 Prospecção Personalizada Completa (Digitar Nichos + Escolher Regiões e Meta)")
        print("3 - ⚙️ Configurações Avançadas do Menu (Ajustar Metas, Cidades, Filtros, Nota e Janela)")
        print("4 - ⚡ Teste Rápido (Digitar Nichos para Captar 3 Leads de Demonstração)")
        print("5 - 🚪 Sair")

        escolha = input("\nDigite o número da opção desejada [Padrão: 1]: ").strip()
        if not escolha:
            escolha = "1"

        if escolha == "0":
            fazer_login_manual()
            continue
        elif escolha == "5":
            print("\nEncerrando o Bot Prospector. Até logo!\n")
            break
        elif escolha == "3":
            menu_configuracoes_avancadas(config_sessao)
            continue

        elif escolha == "1":
            # Usuário digita livremente os nichos que quer buscar agora; reseta após finalizar
            nichos_busca = solicitar_nichos_usuario()
            executar_prospeccao(
                nichos_selecionados=nichos_busca,
                regioes_selecionadas=config_sessao["regioes"],
                meta_leads=config_sessao["meta_leads"],
                headless=config_sessao["headless"]
            )
            input("\n[Pressione ENTER para voltar ao Menu Principal e realizar nova busca...]")

        elif escolha == "2":
            # Fluxo completo: digita quantos nichos quiser, escolhe regiões e define meta de leads
            nichos_busca = solicitar_nichos_usuario()
            regs = solicitar_regioes_customizadas(config_sessao["regioes"])

            qtd_str = input(f"\nQuantidade mínima de leads desejada para este lote [Padrão: {config_sessao['meta_leads']}]: ").strip()
            meta = int(qtd_str) if qtd_str.isdigit() and int(qtd_str) > 0 else config_sessao["meta_leads"]

            executar_prospeccao(
                nichos_selecionados=nichos_busca,
                regioes_selecionadas=regs,
                meta_leads=meta,
                headless=config_sessao["headless"]
            )
            input("\n[Pressione ENTER para voltar ao Menu Principal e realizar nova busca...]")

        elif escolha == "4":
            # Teste rápido de 3 leads com os nichos que o usuário digitar
            print("\n⚡ MODO TESTE RÁPIDO (3 LEADS)")
            nichos_teste = solicitar_nichos_usuario()
            executar_prospeccao(
                nichos_selecionados=nichos_teste,
                regioes_selecionadas=config_sessao["regioes"][:3],
                meta_leads=3,
                headless=config_sessao["headless"]
            )
            input("\n[Pressione ENTER para voltar ao Menu Principal e realizar nova busca...]")

        else:
            print(f"[!] Opção '{escolha}' inválida. Escolha entre 0 e 5.")
            time.sleep(1)


if __name__ == "__main__":
    menu_interativo()
