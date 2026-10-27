"""
Painel Principal do Bot de Captação de Leads (Google Maps).
Filtra estabelecimentos sem site, com verificação profunda na web (anti-cardápio digital/anti-site),
garante um mínimo de 50 leads e gera planilha Excel + Relatório Executivo em PDF.
"""

import sys
import os
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
from config import NICHOS, REGIOES, FILTROS, META_MINIMA_LEADS, PASTA_PERFIL_NAVEGADOR
from scraper import buscar_leads_google_maps
from exporter import salvar_planilha_excel
from historico import carregar_historico
from verifier import interceptar_novas_abas_whatsapp

def mostrar_banner():
    print("""
================================================================================
 🚀 BOT PROSPECTOR: LEADS QUALIFICADOS (GOOGLE MAPS + INVESTIGAÇÃO WEB)
    Brasília DF, Valparaíso de Goiás e Entorno
    Filtro Rigoroso: 100% Sem Site | Sem Cardápio Digital | Alta Reputação
    Garantia: Mínimo de 50 Leads por Lote | Exportação em Excel (.xlsx) e PDF
    Anti-Duplicação: Leads já prospectados NUNCA são repetidos!
================================================================================
    """)

def executar_prospeccao(nichos_selecionados: dict, regioes_selecionadas: list, meta_leads: int = 50, headless: bool = False):
    """Executa o ciclo de prospecção iterando por regiões até atingir a meta mínima de leads."""
    todos_os_leads = []
    inicio_tempo = time.time()
    historico = carregar_historico()

    print(f"\n[CONFIGURAÇÃO DA PROSPECÇÃO]")
    print(f"- Nichos: {', '.join(nichos_selecionados.keys())}")
    print(f"- Regiões mapeadas: {len(regioes_selecionadas)} sub-regiões (DF e Valparaíso)")
    print(f"- Meta Mínima de Leads: {meta_leads} leads 100% verificados sem site/cardápio")
    print(f"- Histórico Ativo: {historico.get('total_coletados', 0)} leads já salvos (não serão repetidos)")
    print(f"- Saídas: Planilha Excel (.xlsx) + Relatório Executivo (.pdf)")
    print(f"- Modo Visual: {'Ativado (janela visível)' if not headless else 'Invisível (Headless)'}")
    print(f"--------------------------------------------------------------------------------\n")

    os.makedirs(PASTA_PERFIL_NAVEGADOR, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PASTA_PERFIL_NAVEGADOR,
            headless=headless,
            locale="pt-BR",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            no_viewport=True
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

                print(f"\n>>> NICHO: [{nicho_nome.upper()}] | Progresso: {len(todos_os_leads)}/{meta_leads} leads <<<")

                for regiao in regioes_selecionadas:
                    if len(todos_os_leads) >= meta_leads:
                        atingiu_meta = True
                        break

                    for termo in dados_nicho.get("termos", []):
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
                            historico=historico
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
        print(f"  • Total de Leads: {len(todos_os_leads)} (Meta: {meta_leads})")
        print(f"  • Com Telefone / WhatsApp: {com_zap}")
        print(f"  • Alta Prioridade (Score >= 85%): {alta_prioridade}")
        print(f"  • Planilha Excel: {caminho_excel}")
        if caminho_pdf:
            print(f"  • Relatório PDF: {caminho_pdf}")
        print(f"\nArquivos salvos no diretório 'Planilhas/' prontos para prospecção!\n")
    else:
        print("[!] Nenhum lead inédito atendeu a todos os critérios restritos nesta rodada.")

def fazer_login_manual():
    """
    Abre o navegador visível com o perfil persistente para o usuário realizar
    o login manual no Instagram e escanear o QR Code do WhatsApp Web.
    Todas as sessões são salvas permanentemente em 'perfil_navegador/'.
    """
    print("\n" + "="*80)
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
            no_viewport=True
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

def menu_interativo():
    while True:
        mostrar_banner()
        perfil_existe = os.path.exists(PASTA_PERFIL_NAVEGADOR) and bool(os.listdir(PASTA_PERFIL_NAVEGADOR))
        status_txt = "✅ Conectado / Ativo" if perfil_existe else "⚠️ Não autenticado (Recomendado logar)"
        print(f"Status do Perfil: {status_txt}")
        print("--------------------------------------------------------------------------------")
        print("Escolha o modo de operação:")
        print("0 - 🔑 Conectar Contas (Fazer Login Manual no Instagram e WhatsApp Web)")
        print("1 - 🚀 Prospecção Padrão (Mínimo de 50 Leads em PDF + Excel de todos os nichos)")
        print("2 - 🎯 Prospecção de 50+ Leads em Nicho Específico (ex: só Odonto, só Restaurantes, etc.)")
        print("3 - ⚙️ Prospecção Personalizada (Definir meta customizada, ex: 80 ou 100 leads)")
        print("4 - ⚡ Teste Rápido (3 leads de demonstração com verificação profunda)")
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

        headless_opt = False # Janela visível para o usuário acompanhar

        if escolha == "1":
            # Prospecção completa de 50 leads distribuídos nos nichos solicitados
            executar_prospeccao(NICHOS, REGIOES, meta_leads=50, headless=headless_opt)
            break

        elif escolha == "2":
            print("\nNichos disponíveis:")
            chaves = list(NICHOS.keys())
            for idx, k in enumerate(chaves, 1):
                print(f"  {idx} - {k}")

            idx_escolhido = input("\nEscolha o número do nicho: ").strip()
            try:
                nicho_key = chaves[int(idx_escolhido) - 1]
                nicho_dict = {nicho_key: NICHOS[nicho_key]}

                cidade = input("Qual abrangência? (1: Brasília DF, 2: Valparaíso de Goiás, 3: Ambas completas) [Padrão: 3]: ").strip()
                if cidade == "1":
                    regs = [r for r in REGIOES if "DF" in r]
                elif cidade == "2":
                    regs = [r for r in REGIOES if "Valparaíso" in r or "GO" in r]
                else:
                    regs = REGIOES

                qtd_str = input(f"Quantidade mínima de leads desejada [Padrão: 50]: ").strip()
                meta = int(qtd_str) if qtd_str.isdigit() else 50

                executar_prospeccao(nicho_dict, regs, meta_leads=meta, headless=headless_opt)
            except Exception as e:
                print(f"Opção inválida ({e}). Executando prospecção padrão...")
                executar_prospeccao(NICHOS, REGIOES, meta_leads=50, headless=headless_opt)
            break

        elif escolha == "3":
            qtd_str = input("Quantos leads mínimos deseja no arquivo final? [Ex: 50, 80, 100]: ").strip()
            meta = int(qtd_str) if qtd_str.isdigit() else 50
            executar_prospeccao(NICHOS, REGIOES, meta_leads=meta, headless=headless_opt)
            break

        elif escolha == "4":
            # Teste rápido de 3 leads
            nichos_teste = {
                "Odontologia": NICHOS["Odontologia"],
                "Restaurantes de Alto Custo": NICHOS["Restaurantes de Alto Custo"]
            }
            executar_prospeccao(nichos_teste, REGIOES[:3], meta_leads=3, headless=headless_opt)
            break

        else:
            print(f"[!] Opção '{escolha}' inválida. Escolha entre 0 e 5.")
            time.sleep(1)

if __name__ == "__main__":
    menu_interativo()

