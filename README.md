# Zin — Plataforma de Inteligência & Captação de Leads B2B

```
███████╗██╗███╗   ██╗
╚══███╔╝██║████╗  ██║
  ███╔╝ ██║██╔██╗ ██║
 ███╔╝  ██║██║╚██╗██║
███████╗██║██║ ╚████║
╚══════╝╚═╝╚═╝  ╚═══╝
```

> **Sistema Integrado de Prospecção Territorial no Google Maps, Funil Sequencial Eliminatório de 6 Etapas e Gestão de Oportunidades B2B.**

---

## 📌 Visão Geral do Sistema

O **Zin** é uma plataforma corporativa projetada para transformar a prospecção comercial via Google Maps em um fluxo estatístico determinístico de alta conversão. Em vez de despejar planilhas brutas desordenadas, o sistema executa varredura territorial inteligente, aplica um **Funil Sequencial de 6 Etapas (`pandas` + `numpy`)** para descartar contatos sem telefone ou com nota baixa e isola negócios em ascensão com lacunas digitais reais (empresas sem website ou com presença subotimizada).

Os resultados são persistidos em banco de dados local **SQLite (`Planilhas/zin_leads.db`)** para consulta operacional rápida na web e organizados em **Lotes Semanais de Dossiês PDF Executivos** com *scripts* (copies) consultivos prontos para abordagem via WhatsApp.

---

## 🏛️ Arquitetura Técnica & Stack Tecnológica

O projeto adota uma arquitetura híbrida de alto desempenho:

| Camada | Tecnologia | Responsabilidade |
|---|---|---|
| **Frontend Web** | **Angular 19+ (TypeScript, HTML5, CSS3)** | Interface reativa sob o Design System *Carteira Jet-Age*, com Dark Mode padrão, controle de lotes, tabelas e relatórios. |
| **Backend API** | **Java 25 + Spring Boot 3 (Porta 8090)** | API RESTful, controle de autenticação/sessão, orquestração de processos Python, SSE (Server-Sent Events) e persistência JDBC. |
| **Banco de Dados** | **SQLite 3 (`Planilhas/zin_leads.db`)** | Armazenamento relacional local das tabelas `usuario`, `leads`, `lotes_semanais` e `relatorios_pdf`. |
| **Motor Analítico** | **Python 3.10+ (`pandas`, `numpy`, `selenium`)** | Coleta automatizada em 2 fases no Google Maps, vetorização estatística e geração de PDFs executivos via `fpdf2`. |

---

## 🎨 Design System: Carteira Jet-Age de Viagem (`vernacular-ephemera-jet-age-ticket-wallet`)

Homologado através das heurísticas do framework **Impeccable**, o design rompe com os clichês de SaaS genérico (cards flutuantes soltos e sombras excessivas). O layout trata cada lote de prospecção como um bilhete oficial de despacho e as 6 etapas do funil como estações e portões auditados.

- **Tema Padrão**: **Modo Escuro (Dark Mode Inverso)** ativo por padrão com alternador fluido para Modo Claro.
- **Paleta Oficial**:
  - 🔵 **Carrier Navy** (`#0B192C`): Estrutura primária, shell de navegação e cabeçalhos.
  - 📜 **Coupon Ivory** (`#FAF8F5`): Superfície de cartões, bilhetes e pranchas de leitura.
  - 🔴 **Seal Red** (`#D62828` / `#E63946` no dark): Ações primárias de disparo e chancelas de corte.
  - 🟣 **Carbon Purple** (`#49306B` / `#B598DC` no dark): Destaque de scores numéricos e métricas tabulares.
  - 🔘 **Steel Muted** (`#8D99AE`): Fios de grade, picotes e legendas auxiliares.
- **Protótipo Interativo no Figma**: [Acessar Projeto no Figma (Node 16:3)](https://www.figma.com/design/v2nPbeJYBXsmR1OWsUlnLw?node-id=16-3&autoplay-code-preview=16-3&code-import-attempt-id=1ae11e20ae7512f36d5efdc7072f2c32b00ebf1f8bd74ce01604b8d838e2e6d6&code-import-node-id=16-3&code-import-surface=code_layer)

---

## ⚡ Regras de Negócio e Mecanismos Chave

### 1. Cobertura Nacional & Particionamento Transparente em 4 Quadrantes
- O operador pode selecionar **até 10 regiões** por lote de pesquisa (municípios ou estados inteiros).
- Caso o usuário selecione algum dos 6 estados de extensão continental (**Amazonas, Piauí, Pará, Bahia, Mato Grosso ou Minas Gerais**), o motor divide silenciosamente o estado em **4 quadrantes (Norte, Sul, Leste e Oeste)**, processa individualmente cada sub-região e consolida apenas a elite final. **Essa divisão é estritamente interna e nunca é exposta na UI do usuário.**

### 2. Funil Eliminatório de 6 Etapas
1. **Etapa 1 (Coleta Bruta)**: Varredura de estabelecimentos no Google Maps via Selenium headless;
2. **Etapa 2 (Deduplicação)**: Remoção por nome normalizado e coordenadas geográficas;
3. **Etapa 3 (Higienização)**: Descarte obrigatório de empresas sem telefone válido cadastrado;
4. **Etapa 4 (Qualidade Mínima)**: Corte de nota inferior a 4.2★ ou menos de 10 avaliações escritas;
5. **Etapa 5 (Lacuna Digital)**: Isolamento de empresas sem website ou dependentes apenas de redes sociais;
6. **Etapa 6 (Score & Elite Top N)**: Cálculo vetorial do Score 0–100 via percentil `numpy` e seleção dos Top N contatos por região.

### 3. Separação Estrita de Telas: Leads vs. Relatórios
- **Aba Leads**: Alimentada em tempo real a partir da tabela `leads` do SQLite. Exibe empresas qualificadas, filtros por nicho/região e ação de 1 clique para copiar o script de abordagem para WhatsApp. Não exibe arquivos PDF.
- **Aba Relatórios**: Exibe exclusivamente o histórico de relatórios executivos em PDF organizados em **Lotes Semanais**, informando data, hora de geração e taxa de retenção.

### 4. Segurança e Ciclo de Vida de Credenciais
- Tabela `usuario` no SQLite: `id_usuario`, `username`, `email`, `senha`, `token`.
- O campo `token` armazena um código temporário de redefinição de senha com **validade estrita de 5 minutos (TTL = 300 segundos)**. Após o uso bem-sucedido ou transcorridos os 5 minutos, o token é imediatamente apagado (`NULL`).

---

## 📂 Estrutura do Repositório

```text
Leads-GM-Scrap/
├── docs/                                 # Documentação Técnica e Especificação Oficial
│   ├── Documentacao_Oficial_Zin.docx    # Documentação Executiva Oficial em DOCX (IEEE/ISO)
│   ├── 01-arquitetura-c4-arc42/          # Diagramas de Contexto e Containers C4
│   ├── 02-referencia-tecnica/            # Modelo de Dados SQLite e Design System
│   ├── 03-decisoes-arquitetura-adr/      # Registros de Decisão de Arquitetura (ADRs)
│   └── 04-historico-branches/            # Changelog e esteira de entregas
├── Planilhas/                            # Armazenamento Local de Dados e Relatórios
│   ├── zin_leads.db                      # Banco SQLite relacional do sistema
│   ├── historico_leads.json              # Registro unificado de leads em JSON
│   ├── analytics_lotes.json              # Metadados estatísticos e funis dos lotes
│   └── *.pdf                             # Relatórios executivos semanais gerados
├── tests/                                # Testes Unitários e de Integração
│   └── test_funil_sequencial.py          # 23 testes automatizados (funil e numpy)
├── config.py                             # Constantes globais, caminhos e regras de corte
├── scraper.py                            # Motor Selenium de coleta no Google Maps
├── processador_dados.py                  # Vetorização e Funil de 6 Etapas (pandas/numpy)
├── classificador.py                      # Atribuição de scores, percentis e diagnóstico
├── gerador_relatorios.py                 # Renderizador de PDFs executivos (fpdf2)
├── gerenciador_historico.py              # Camada de persistência local em JSON/SQLite
├── main.py                               # Interface de Terminal CLI com Banner ASCII ZIN
├── PRODUCT.md                            # Fatos duráveis do produto (Impeccable Schema 1)
├── DESIGN.md                             # Especificação formal do Design System
└── README.md                             # Este documento
```

---

## 🚀 Como Executar

### Pré-requisitos
- **Python 3.10+** (Ambiente virtual em `.\venv\`)
- **Java 25 LTS** + Maven
- **Node.js 18+** + Angular CLI
- **Google Chrome** instalado

### 1. Executando o Motor Python via Terminal (CLI)
```powershell
# Ativar o ambiente virtual
.\venv\Scripts\Activate.ps1

# Executar a suíte de testes
pytest tests/test_funil_sequencial.py -v

# Iniciar o Menu Terminal
python main.py
```

### 2. Documentação Complementar
Para consultar a especificação completa de requisitos, dicionário de dados, mapeamento de telas e critérios de aceitação, acesse o documento oficial:
👉 **[`docs/Documentacao_Oficial_Zin.docx`](file:///c:/Users/diego58072066/Documents/ZinZum/Portfolio/Leads-GM-Scrap/docs/Documentacao_Oficial_Zin.docx)**
