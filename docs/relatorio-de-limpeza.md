# Inventário do repositório · 14 de novembro de 2026

## Resultado da primeira etapa

O índice do Git continha 4.233 entradas de `venv/`, 7.038 de `frontend/node_modules/` e uma de `frontend/dist/`. As 11.272 entradas saíram do índice. O ambiente `venv/` antigo já estava ausente do disco. As dependências e os arquivos compilados do frontend permanecem disponíveis no computador. A retirada do índice aparece como exclusão preparada para o próximo commit e conserva o histórico anterior.

Uma instalação isolada com `npm ci`, usando os manifestos do projeto, reproduziu o build do Angular. Em um novo checkout, compile o frontend antes do empacotamento Maven conforme o [README](../README.md).

## Código, ferramentas e material de projeto

| Local | Função observada | Decisão |
|---|---|---|
| `main.py`, `engine/`, `engine/requirements.txt` | Entrada, implementação e dependências Python do terminal. O perfil e os relatórios têm caminhos derivados da posição do pacote. | Manter a entrada principal e o motor compartilhado. |
| `frontend/` | Angular e TypeScript. `angular.json` define o build e o servidor de desenvolvimento. O script `preview` usa Vite; os dois servidores têm configuração de proxy para a API. | Manter fontes, manifestos, lockfile e configurações. |
| `backend/` | API, segurança, JPA, esquema SQLite, teste de integração e Maven Wrapper. | Manter fontes e wrapper. O Maven empacota o conteúdo de `frontend/dist/`. |
| `docs/`, `PRODUCT.md`, `DESIGN.md`, `README.md` | Inventário, arquitetura, requisitos aprovados, design e instruções de execução. O catálogo UrWork retrata as telas atuais; o documento Zin é histórico. | Manter. Atualizar as capturas ao entregar telas reais do UrWork. |
| `.impeccable/`, `.skills.json`, `.gemini/`, `.vscode/` | Recursos de design, seleção de ferramentas e configuração local do editor. O VS Code usa o interpretador em `.venv/`. | Manter as configurações em uso. Reavaliar as específicas de ferramenta se o fluxo de trabalho mudar. |
| `.git/` e arquivos `.gitignore` | Histórico, índice e regras para dependências, caches e dados de execução. | Manter. |

## Dados do operador

| Local | Conteúdo e origem | Decisão |
|---|---|---|
| `dtb/UrWork.db` | Banco oficial local da instalação UrWork. | Preservar fora do Git. |
| Bancos anteriores | As cópias de zin_leads.db em DTB e Planilhas eram idênticas. Uma foi renomeada; a outra foi arquivada fora do projeto, em %LOCALAPPDATA%/UrWork/backups/. | Preservar o backup anterior à migração. |
| `Planilhas/historico_leads.json` e PDFs | Histórico usado para deduplicação e três relatórios locais. O terminal grava o histórico após o sucesso da geração do PDF. | Preservar o conjunto. Reinstalar o Python não recupera esses dados. |
| `perfil_navegador/` | Perfil persistente do Chromium usado pelo operador, incluindo suas sessões externas. | Manter fora do Git e separado de futuras conexões dos usuários do site. |

## Diretórios recriáveis e resíduos

| Local | Situação | Ação possível |
|---|---|---|
| `.venv/` | Ambiente Python ativo no computador. | Recriar pelos requisitos se necessário; para a operação atual, manter. |
| `frontend/node_modules/`, `frontend/.angular/`, `frontend/dist/`, `backend/target/` | Dependências e saídas de compilação. | Reinstalar ou recompilar com o README. Limpar somente com os consumidores parados. |
| `__pycache__/` e caches nos pacotes | Bytecode local gerado pelo Python. | Dispensáveis para executar as fontes. |
| `tests/__pycache__/` | Três arquivos compilados, sem fontes atuais nessa pasta. Há fontes anteriores no commit `250ddfc`. | Avaliar os testes históricos ao extrair o motor; o cache não é uma suíte executável de referência. |
| `frontend/public/` | Vazia e sem entrada de recursos correspondente no build Angular. | Pode ser removida enquanto vazia. |
| `frontend/.impeccable/live/` | Diretórios locais vazios de sessões e anotações. | Podem ser recriados pela ferramenta. O contexto de design do projeto fica na raiz. |

## Verificações operacionais

- O terminal abriu pela entrada oficial, exibiu o menu e encerrou pela opção 5.
- O teste de integração executou cadastro, login, consulta de sessão e logout em um banco temporário.
- O JAR empacotado, iniciado em uma porta isolada com outro banco temporário, serviu a página e o JavaScript (HTTP 200). A consulta de sessão sem credenciais retornou HTTP 401.
