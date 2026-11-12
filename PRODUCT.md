# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Frontend em **Angular + TypeScript + HTML5 + CSS3**, Backend em **Java 25 + Spring Boot 3** rodando na porta `8090`, banco de dados relacional local em **SQLite** (`Planilhas/zin_leads.db`) e motor analítico/coletor em **Python 3.10+** (`pandas`, `numpy`, `selenium`, `fpdf2`).

## Users

Consultores comerciais, agências B2B e equipes de prospecção de vendas no Brasil que precisam identificar, qualificar e abordar empresas locais com lacunas reais de presença digital (ausência de site próprio, baixa conversão em canais digitais ou presença subotimizada no Google Maps) sem desperdiçar tempo com listas brutas ou contatos desqualificados.

## Product Purpose

**Zin** transforma a prospecção comercial no Google Maps em um fluxo de inteligência analítica e acionável. Em vez de despejar planilhas brutas, o produto executa coleta regional automatizada em duas fases, filtra os dados por um **Funil Eliminatório Sequencial de 6 Etapas** vetorizado (`pandas` + `numpy`) e entrega tanto uma base viva de leads qualificados no SQLite quanto relatórios executivos em PDF agrupados em lotes semanais, acompanhados de *scripts* (copies) consultivos prontos para abordagem via WhatsApp.

O sucesso do produto significa reduzir drasticamente o tempo entre escolher um mercado-alvo (até 10 regiões/nichos) e iniciar conversas comerciais de alta conversão com decisores qualificados.

## Positioning

Diferente de scrapers genéricos que apenas extraem telefones crus, o **Zin** opera como um funil estatístico determinístico:
1. Elimina ruído em 6 estágios sequenciais (Deduplicação → Higienização → Filtro de Qualidade Mínima → Corte de Presença Digital → Score Estatístico por Percentil `numpy` → Seleção da Elite Top N);
2. Acelera buscas em estados de extensão continental por meio de **particionamento geográfico transparente em 4 quadrantes (Norte, Sul, Leste, Oeste)** nos bastidores, consolidando apenas a elite de cada sub-região sem sobrecarregar a interface do usuário;
3. Separa claramente a **operação diária de abordagem** (visão *Leads* alimentada pelo SQLite, sem poluição de arquivos PDF) da **auditoria e histórico gerencial** (visão *Relatórios* organizada por Lotes Semanais de PDFs).

## Operating Context

- O operador autentica-se na plataforma web (`http://localhost:8090`) ou opera o menu de terminal Python (`main.py`).
- Na plataforma web, o usuário configura um lote escolhendo **até 10 regiões do Brasil** (cidades ou estados inteiros) e os nichos de negócio desejados.
- Enquanto o motor Python executa a coleta e o funil eliminatório, o backend Spring Boot acompanha o progresso em tempo real (`SSE`) e persiste os leads aprovados no banco SQLite (`Planilhas/zin_leads.db`), além de catalogar os relatórios PDF gerados na pasta `Planilhas/`.
- Na aba **Leads**, o operador filtra os leads do SQLite por região, prioridade (`Prioridade Máxima`, `Alta Prioridade`, `Qualificado`), diagnóstico digital e dispara ou copia a *copy* personalizada de WhatsApp com 1 clique.
- Na aba **Relatórios**, o operador consulta os dossiês PDF gerados pelo motor Python agrupados em **Lotes Semanais**, com data e horário exatos de geração.

## Capabilities and Constraints

- **Cobertura Nacional com Limite de 10 Regiões por Lote**: O usuário pode selecionar até 10 regiões brasileiras (municípios ou estados) por execução.
- **Divisão Transparente em 4 Quadrantes para Estados Gigantes**: Quando o usuário seleciona **Amazonas (AM), Piauí (PI), Pará (PA), Bahia (BA), Mato Grosso (MT) ou Minas Gerais (MG)**, o sistema divide internamente a busca em 4 macrorregiões (**Norte, Sul, Leste e Oeste**), processa uma por vez e mescla apenas os principais leads nos dados finais. Essa divisão é estritamente um mecanismo interno de aceleração e **não deve ser exibida na interface do usuário**.
- **Separação Estrita entre Leads (SQLite) e Relatórios (PDFs Semanais)**:
  - A visão **Leads** exibe exclusivamente os registros armazenados na tabela `leads` do SQLite (sem misturar listagem de PDFs).
  - O menu de terminal do Python (`main.py`) continua gerando e salvando os relatórios `.pdf` normalmente.
  - A visão **Relatórios** da interface web lista os PDFs organizados por **Lotes Semanais**, exibindo o dia e horário em que cada PDF foi gerado.
- **Autenticação Completa e Tabela `usuario` no SQLite**:
  - Telas obrigatórias: **Login**, **Cadastro** e **Alterar Senha**.
  - A tabela `usuario` no SQLite possui exatamente as colunas: `id_usuario`, `username`, `email`, `senha` e `token`.
  - A coluna `token` armazena um código temporário para alteração de senha com **validade estrita de 5 minutos (TTL = 300s)**: assim que utilizado ou após transcorridos os 5 minutos, o token deve ser apagado (`NULL`).
- **Porta do Servidor Backend**: O servidor Spring Boot deve rodar na porta **`8090`** (`http://localhost:8090`).

## Brand Commitments

- **Nome da Marca**: **`Zin`** (sem sufixos técnicos como `:8090` ou `ZinLeads` na navegação principal).
- **Assinatura Visual ASCII `ZIN`**: O banner em arte de blocos (`███████╗██╗███╗   ██╗...`) é a marca oficial tanto no menu de terminal (`main.py`) quanto nos cabeçalhos das telas de autenticação (Login, Cadastro, Alterar Senha) e no canto superior esquerdo da aplicação web, em versão levemente reduzida.
- **Paleta Oficial Escolhida (Direção Carteira Jet-Age de Viagem)**:
  - **Carrier Navy**: `#0B192C` (Estrutura primária, shell de navegação e cabeçalho)
  - **Coupon Ivory**: `#FAF8F5` (Superfície limpa de trabalho, leitura e fichas)
  - **Seal Red**: `#D62828` (Chancela de aprovação/corte e ações primárias de execução)
  - **Carbon Purple**: `#49306B` (Destaque de scores numéricos e algarismos tabulares)
  - **Steel Muted**: `#8D99AE` (Linhas de grade, picotes e legendas contextuais)
  - **Tema Padrão**: **Modo Escuro (Dark Mode Inverso)** ativo por padrão: `#050B14` (Fundo profundo), `#0B192C` (Superfície Navy), `#11223B` (Superfície elevada), `#FAF8F5` (Texto de alto contraste), `#B598DC` (Numerais/Scores) e `#E63946` (Chancela ativa/CTA).
- **Modo Claro e Modo Escuro**: A interface deve possuir alternância fluida entre os dois modos com conformidade WCAG AA estrita, iniciando por padrão no Modo Escuro.
- **Interface Limpa de Jargões de Infraestrutura**: Não exibir rótulos de arquitetura interna na UI final (como *"Protótipos de Engenharia Web • Angular + Spring Boot (:8090) + SQLite"*, *"Persistência Automática"* no formulário do Dashboard ou cards técnicos *"Motor Python + SQLite"* na barra lateral).

## Evidence on Hand

- Motor Python funcional e testado (`23/23` testes unitários passando em `tests/test_funil_sequencial.py`), consolidado em 6 módulos principais: `config.py`, `scraper.py`, `processador_dados.py`, `classificador.py`, `gerador_relatorios.py`, `gerenciador_historico.py` e `main.py`.
- Histórico real de lotes e leads já processados em `Planilhas/historico_leads.json` e `Planilhas/analytics_lotes.json`, além de relatórios executivos `.pdf` gerados em `Planilhas/`.
- Documentação arquitetural estruturada em `docs/` seguindo **arc42 + C4 Model + Diátaxis + ADRs**.
- Protótipos interativos de 6 telas validados e sincronizados no Figma (`fileKey: v2nPbeJYBXsmR1OWsUlnLw`, `node-id=11-3`).
- Nenhum depoimento externo de clientes, precificação comercial de planos ou integrações com CRMs de terceiros foram definidos — trabalhos futuros não devem fabricar essas alegações.

## Product Principles

1. **Rigor Estatístico Antes do Volume Bruto**: Cada lead exibido ao operador precisa justificar sua presença por meio de métricas auditáveis (Score 0–100, percentil no lote, estrelas, volume de avaliações e diagnóstico digital).
2. **Complexidade Geográfica Invisível**: Acelerações de engenharia (como a divisão em 4 quadrantes para estados continentais ou o pipeline assíncrono Python ↔ SQLite) acontecem de forma transparente, mantendo a decisão do usuário simples e direta.
3. **Separação Clara entre Ação Comercial e Arquivo Gerencial**: Operar leads no dia a dia (tabela viva SQLite + WhatsApp copy) e auditar relatórios históricos (lotes semanais de PDFs) são tarefas distintas e têm superfícies dedicadas.
4. **Sobriedade Editorial sem Poluição Técnica**: A interface fala a língua da operação comercial B2B, ocultando detalhes de infraestrutura, portas de servidor ou nomes de bancos de dados da superfície de uso.

## Accessibility & Inclusion

- **Conformidade WCAG 2.1 AA Estrita**: Contraste mínimo de `4.5:1` para texto normal e `3:1` para componentes de interface e textos grandes, tanto no modo Light Editorial quanto no Dark Mode Inverso.
- **Navegação Completa por Teclado**: Todas as tabelas de leads (`Leads`), acordeões de lotes semanais (`Relatórios`), seletores de regiões (até 10 tags), modais/drawers de copy e fluxos de autenticação (`Login`, `Cadastro`, `Alterar Senha` com input de código de 6 dígitos) devem possuir `focus-visible` nítido, ordem de tabulação lógica e suporte a atalhos de teclado (`Tab`, `Shift+Tab`, `Enter`, `Space`, `Escape`).
