# UrWork

O UrWork está em construção. O site oferece cadastro por perfil, login e consulta da conta. O operador já pode prospectar empresas pelo terminal. As buscas de leads e vagas pelo navegador são as próximas entregas.

| Para trabalhar em | Comece por |
|---|---|
| Telas e navegação | [Início](frontend/src/app/inicio), [formulários e sessão](frontend/src/app/conta) e [navegação](frontend/src/app/app.ts) |
| API e banco | [Contas](backend/src/main/java/br/com/urwork/contas), [dados locais](backend/src/main/java/br/com/urwork/dados) e [esquema SQLite](backend/src/main/resources/schema.sql) |
| Coleta, qualificação e exportação | [main.py](main.py) abre o [menu do terminal](engine/cli.py), que usa a [coleta por lotes](engine/prospeccao.py) |
| Requisitos, entregas e diretórios | [Produto aprovado](PRODUCT.md), [arquitetura e etapas](docs/arquitetura.md) e [inventário de limpeza](docs/relatorio-de-limpeza.md) |

## Executar o sistema web

Antes do primeiro build, prepare a `.venv` e o Chromium conforme **Executar o coletor**. O Maven testa a ponte com um processo Python real e uma fonte controlada. Para usar outro interpretador com as dependências instaladas, configure `URWORK_PYTHON` com o caminho do executável.

Use JDK 25, com JAVA_HOME apontando para o JDK, e Node.js com npm. Na raiz do repositório, execute no PowerShell:

```powershell
npm --prefix frontend ci
npm --prefix frontend run build
.\backend\mvnw.cmd -f backend/pom.xml clean package
java -jar backend/target/urwork-0.1.0.jar
```

Abra o [site local](http://localhost:8090). O JAR serve o Angular e a API na mesma origem. O cadastro aceita nome completo, e-mail, CPF, senha e os dados da finalidade escolhida. Entre por e-mail e senha para abrir **Minha conta**. Quem já tinha cadastro completa o CPF e o perfil após entrar com a senha que usava.

O backend escuta em `127.0.0.1:8090`. O SQLite da instalação fica em **`dtb/UrWork.db`**. Use a raiz como diretório de execução. Para escolher outro banco, defina `URWORK_DB_PATH` com um caminho absoluto antes de iniciar. `ZIN_DB_PATH` continua aceito quando a variável nova está ausente. Os caminhos antigos e a política de migração estão na [arquitetura](docs/arquitetura.md).

Durante o desenvolvimento, mantenha o backend na porta 8090 e execute `npm run dev` em `frontend/`. O servidor Angular encaminha `/api` ao Spring Boot. Para rodar os testes do backend, use `.\backend\mvnw.cmd -f backend/pom.xml test`.

## Executar o coletor

Na raiz do projeto, usando PowerShell e uma instalação de Python compatível com as dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r engine/requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe main.py
```

Os testes da varredura podem ser executados com `.\.venv\Scripts\python.exe -m unittest discover -s engine/tests -v`. O teste usa lotes controlados. O histórico e os PDFs do terminal ficam em `Planilhas/`; o Chromium guarda as sessões do operador em `perfil_navegador/`. Preserve esses diretórios ao reinstalar o ambiente.

## Documentação

- [Arquitetura e mapa do repositório](docs/arquitetura.md) — componentes, dependências e fluxo de dados atual.
- [Catálogo de telas em Word](docs/Documentacao_Oficial_UrWork.docx) — início, login, cadastro, conclusão do perfil e Minha conta.
- [Auditoria do protótipo anterior](docs/auditoria-frontend.md) — registro histórico das telas Zin.
- [Relatório de limpeza](docs/relatorio-de-limpeza.md) — volume, impacto e condições de remoção.
- [Produto](PRODUCT.md) — público, regras de negócio e requisitos previstos.
- [Design](DESIGN.md) — identidade, tipografia, cores e movimento.

Ao alterar uma tela, revise a seção correspondente no catálogo Word. Confira a rota no protótipo, refaça a captura com dados fictícios e registre a revisão. Para acrescentar uma tela, use a mesma sequência de objetivo, campos, ações, estados, prévia e integrações pendentes.
