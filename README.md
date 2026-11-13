# Zin

Ferramenta de prospecção de empresas locais. O repositório reúne o coletor de terminal e o protótipo web. Hoje os dois têm entradas independentes.

## Executar o sistema web

Use JDK 25, com JAVA_HOME apontando para o JDK, e Node.js com npm. Na raiz do repositório, execute no PowerShell:

```powershell
npm --prefix frontend ci
npm --prefix frontend run build
.\backend\mvnw.cmd -f backend/pom.xml clean package
java -jar backend/target/zin-0.1.0.jar
```

Abra [Zin local](http://localhost:8090). O JAR serve a interface Angular e a API de contas na mesma origem. Crie uma conta com nome, e-mail e senha (8 a 128 caracteres), entre pelo e-mail e use **Sair** para encerrar a sessão. O banco padrão é `Planilhas/zin_leads.db` relativo ao diretório de execução. Para usar outro arquivo, configure `ZIN_DB_PATH`. O backend cria a pasta e a tabela na inicialização.

Durante o desenvolvimento, mantenha o backend na porta 8090 e execute `npm run dev` em `frontend/`. O servidor Angular encaminha `/api` ao Spring Boot. Para rodar apenas os testes do backend, use `.\backend\mvnw.cmd -f backend/pom.xml test`. Leads, buscas, relatórios e recuperação de senha continuam demonstrativos.

## Executar o coletor

Na raiz do projeto, usando PowerShell e uma instalação de Python compatível com as dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe main.py
```

A sessão do navegador e o histórico de leads são locais. Guarde-os ao reinstalar o ambiente.

## Documentação

- [Arquitetura e mapa do repositório](docs/arquitetura.md) — componentes, dependências e fluxo de dados atual.
- [Catálogo de telas em Word](docs/Documentacao_Oficial_Zin.docx) — sete telas com capturas e fluxos de início, login, cadastro, recuperação, leads, buscas e relatórios; inclui a página inicial no celular.
- [Auditoria do frontend](docs/auditoria-frontend.md) — achados e reteste das correções.
- [Relatório de limpeza](docs/relatorio-de-limpeza.md) — volume, impacto e condições de remoção.
- [Produto](PRODUCT.md) — público, regras de negócio e requisitos previstos.
- [Design](DESIGN.md) — identidade, tipografia, cores e movimento.

Ao alterar uma tela, revise a seção correspondente no catálogo Word. Confira a rota no protótipo, refaça a captura com dados fictícios e registre a revisão. Para acrescentar uma tela, use a mesma sequência de objetivo, campos, ações, estados, prévia e integrações pendentes.
