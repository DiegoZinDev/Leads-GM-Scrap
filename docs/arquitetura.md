# Arquitetura do Zin

## Duas entradas independentes

| Fronteira | Entrada | Fluxo observado |
|---|---|---|
| Aplicação web | `frontend/index.html` → `src/main.ts` | Angular 20 com templates compilados antecipadamente pelo Angular CLI. O fragmento da URL seleciona a tela. Empresas e estado dos fluxos vivem em memória. A preferência de tema da área de trabalho é salva localmente na chave zin-workspace-theme. |
| Operação de terminal | `python main.py` → `zin/cli.py` | O menu recebe região e nicho, abre Chromium via Playwright, coleta candidatos, qualifica empresas e exporta resultados. |

O Angular acessa a API de contas na mesma origem. Spring Boot 3 (Java 25) combina Spring Web, Spring Security e Spring Data JPA com Hibernate ORM e o dialeto SQLite. O coletor Python continua independente.

| Método | Endpoint | Comportamento |
|---|---|---|
| GET | /api/auth/csrf | Entrega nome do cabeçalho e token CSRF da sessão. |
| POST | /api/auth/cadastro | Valida o JSON e grava a conta. Retorna 201, 400 para dados inválidos ou 409 para duplicidade. |
| POST | /api/auth/login | Recebe e-mail e senha como formulário. Retorna 204 com sessão autenticada ou 401. |
| GET | /api/auth/sessao | Retorna nome e e-mail da conta autenticada ou 401. |
| POST | /api/auth/logout | Invalida a sessão e remove o cookie. |

As operações POST exigem o token CSRF. A sessão HTTP usa cookie HttpOnly, SameSite=Lax e expira após 30 minutos de inatividade. A tabela usuario mantém id_usuario, username, email, senha e token; o campo senha contém um hash PBKDF2 com sal. A recuperação demonstrativa não escreve nessa tabela. Os leads exibidos continuam sendo exemplos públicos.

## Responsabilidades no repositório

| Caminho | Responsabilidade |
|---|---|
| `frontend/src/main.ts`, `app.html` | Navegação, estado local, formulários, filtro e interação com a fila de empresas. |
| `frontend/src/map.ts`, `brazil-outline.ts`, `style.css` | Mapa ilustrativo, tipografia, temas, layout e movimento. |
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
