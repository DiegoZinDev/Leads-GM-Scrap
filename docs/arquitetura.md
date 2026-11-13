# Arquitetura do Zin

## Duas entradas independentes

| Fronteira | Entrada | Fluxo observado |
|---|---|---|
| Aplicação web | `frontend/index.html` → `src/main.ts` | Angular 20 e Vite. O fragmento da URL seleciona a tela. Empresas e estado da demonstração vivem em memória no navegador. |
| Operação de terminal | `python main.py` → `zin/cli.py` | O menu recebe região e nicho, abre Chromium via Playwright, coleta candidatos, qualifica empresas e exporta resultados. |

O navegador da aplicação web não chama o coletor. A API Spring Boot, a base SQLite de contas, as sessões web e as atualizações de lotes em tempo real são requisitos previstos em PRODUCT.md. Nesta versão, abrir a demonstração não exige conta.

## Responsabilidades no repositório

| Caminho | Responsabilidade |
|---|---|
| `frontend/src/main.ts`, `app.html` | Navegação, estado local, formulários, filtro e interação com a fila de empresas. |
| `frontend/src/map.ts`, `style.css` | Mapa ilustrativo, tipografia, temas, layout e movimento. |
| `frontend/package.json`, `package-lock.json` | Scripts e dependências reproduzíveis da web. |
| `zin/config.py` | Regiões, nichos, critérios e configuração da sessão do navegador. |
| `zin/scraper.py`, `verifier.py` | Coleta de candidatos e verificação de presença digital. |
| `zin/qualifier.py` | Funil de seleção com pandas e NumPy. |
| `zin/exporter.py` | Histórico e deduplicação em JSON, composição do relatório e geração de PDF com Chromium. |
| `Planilhas/` | PDFs e histórico usados na operação. Caminho relativo à raiz do projeto. |
| `perfil_navegador/` | Perfil persistente do Chromium, com cookies e sessões do operador. |
| `docs/` | Arquitetura atual, inventário de limpeza e catálogo Word das telas. |
| `PRODUCT.md`, `DESIGN.md`, `.impeccable/` | Requisitos do produto, decisões visuais e contexto da ferramenta de design. |

## Fluxo de uma execução local

1. O operador inicia o menu e informa os parâmetros.
2. A CLI abre o perfil persistente e chama a coleta. O coletor usa as verificações de presença digital e o funil de qualificação.
3. O exportador consulta o histórico, grava as saídas locais e produz o PDF. A interface web continua mostrando a amostra demonstrativa.

## Manutenção dos protótipos

Cada tela tem uma seção no catálogo Word. Identifique a rota e a data da revisão, descreva o comportamento observável e as dependências ainda pendentes. Teste o formulário vazio, o formato dos campos, o envio válido e os destinos dos links. Incorpore a captura da versão testada ao documento para que ela continue disponível offline. Atualize a seção existente a cada revisão.
