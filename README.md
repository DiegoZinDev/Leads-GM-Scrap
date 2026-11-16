# UrWork

O UrWork oferece cadastro por perfil, login e prospecção de empresas. O operador pode usar o terminal ou a API autenticada, que mantém execuções e leads por conta. Uma execução pode gerar um relatório PDF, disponível por semana de geração e para download pelo dono. As rotas e exemplos de integração estão no [contrato da aplicação](docs/arquitetura.md).

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

### Conexões sociais da prospecção

Configure o Facebook Login for Business no aplicativo Meta e registre a URL exata de retorno do site. Em desenvolvimento, use uma origem aceita pela Meta que encaminhe `/api` ao Spring e preserve o cookie da sessão. O retorno usa `/api/conexoes/retorno`. As configurações de login são independentes para Instagram e WhatsApp.

| Variável do backend | Valor |
| --- | --- |
| `URWORK_META_APP_ID`, `URWORK_META_APP_SECRET` | Credenciais do aplicativo empresarial. |
| `URWORK_META_VERSAO` | Versão da Graph API habilitada no aplicativo, no formato `vNN.0`. |
| `URWORK_META_CALLBACK` | URL absoluta de retorno registrada, na mesma origem da interface. |
| `URWORK_META_CONFIG_INSTAGRAM` | ID da configuração de login com a permissão `instagram_basic`. |
| `URWORK_META_CONFIG_WHATSAPP` | ID da configuração de login com a permissão `whatsapp_business_management`. |
| `URWORK_META_CHAVE` | Segredo aleatório de pelo menos 32 caracteres, estável entre reinícios, usado para cifrar os tokens no banco local. Guarde-o separadamente do banco. A troca exige reconexão das contas. |

Sem configuração, a prospecção básica permanece disponível. Para homologar, use contas empresariais de teste com acesso ao aplicativo. Para atender contas externas, confira as exigências de aprovação das permissões no painel da Meta. A autorização é revalidada antes de cada nova execução que solicite um filtro social. Desconectar remove a credencial do UrWork. O usuário também pode revogar a permissão nas configurações da Meta. [Referência de inspeção de tokens](https://developers.facebook.com/docs/graph-api/reference/debug_token/).

O motor usa o perfil de Instagram identificado na coleta, a contagem de seguidores quando a fonte a informa e os links de WhatsApp publicados para um número brasileiro. Um resultado inconclusivo recebe `null`. A conexão de WhatsApp não consulta mensagens nem confirma se um número arbitrário está cadastrado. A medição de engajamento continua pendente.

### Busca de vagas

O primeiro conector consulta o mural público da CI&T na Lever. A busca percorre as páginas publicadas, classifica as vagas elegíveis e salva os resultados até a meta escolhida. A quantidade de anúncios e os países disponíveis variam com o mural. O link de candidatura abre a página da empresa. [API pública da Lever](https://github.com/lever/postings-api) · [Mural da CI&T](https://jobs.lever.co/ciandt).

Instale as dependências de `engine/requirements.txt` no mesmo ambiente Python usado pelo Spring. A consulta de vagas usa a biblioteca padrão. A leitura de currículos usa pypdf para PDF com texto e defusedxml para o documento principal de um DOCX. O envio do currículo é opcional. O limite é 1 MiB por arquivo. A leitura de PDF considera até dez páginas e dispensa OCR. Apenas sugestões de habilidades chegam à interface; a pessoa pode editar ou descartar cada uma antes de pesquisar.

Em `POST /api/prospeccoes`, envie `tipo: "VAGAS"`, `chave` (UUID) e `meta` (inteiro positivo). `nicho`, `regiao` (município brasileiro do catálogo), `tituloPdf` e o objeto `vagas` são opcionais. Por exemplo:

```json
{
  "chave": "3aca9da7-dd29-4965-926c-3da690f180ec",
  "tipo": "VAGAS",
  "meta": 10,
  "vagas": {"pais": "BR", "cargo": "Java", "modalidade": "REMOTO", "habilidades": ["Spring Boot"]}
}
```

A busca por país usa o país publicado no anúncio. Uma vaga remota pode exigir residência nesse país. Um município informado exige menção à cidade na localização do anúncio. Cargo e nicho procuram os termos digitados. Senioridade, turno, vínculo e jornada dependem dos termos publicados pela empresa. O motor preserva a ausência de informação. Uma faixa salarial completa ou parcial dá preferência às vagas compatíveis na mesma moeda e período. Escolaridade, experiência e habilidades também influenciam a ordem. Não há conversão monetária.

A sessão autenticada consulta `GET /api/vagas` para as oportunidades distintas da conta e `GET /api/vagas?execucao=ID` para o lote ordenado. O mesmo anúncio em outra execução conserva os dois vínculos. O PDF opcional usa as colunas de vagas e o agrupamento semanal da conta. O endpoint `POST /api/vagas/curriculo` recebe multipart com o campo `arquivo` e devolve `{"habilidades":[...]}`. Ambos os POSTs usam o CSRF da sessão.
