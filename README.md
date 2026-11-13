# Zin

Ferramenta de prospecção de empresas locais. O repositório reúne o coletor de terminal e o protótipo web. Hoje os dois têm entradas independentes.

## Executar a interface

Na pasta `frontend/`, execute `npm ci` e `npm run dev`. Abra o endereço exibido pelo Vite. Use **Entrar** ou **Criar conta** para explorar os formulários e **Ver demonstração** para abrir a fila de empresas fictícias. Para compilar a distribuição, execute `npm run build`.

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
- [Catálogo de telas em Word](docs/Documentacao_Oficial_Zin.docx) — funcionalidades, estados e capturas de login e cadastro.
- [Relatório de limpeza](docs/relatorio-de-limpeza.md) — volume, impacto e condições de remoção.
- [Produto](PRODUCT.md) — público, regras de negócio e requisitos previstos.
- [Design](DESIGN.md) — identidade, tipografia, cores e movimento.

Ao alterar uma tela, revise a seção correspondente no catálogo Word. Confira a rota no protótipo, refaça a captura com dados fictícios e registre a revisão. Para acrescentar uma tela, use a mesma sequência de objetivo, campos, ações, estados, prévia e integrações pendentes.
