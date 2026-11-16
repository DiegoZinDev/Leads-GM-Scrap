# Arquitetura do UrWork

## Plano de execução aprovado

O primeiro marco é configurar uma prospecção pelo site, acompanhar o motor Python e encontrar os resultados reais em **Buscas → Leads** após reiniciar o sistema. O terminal continua disponível para o operador durante a transição. As seções após o plano descrevem a implementação atual do UrWork.

### Responsabilidades de destino

| Componente | Contrato |
|---|---|
| Angular e TypeScript | Selecionar Leads ou Vagas, configurar filtros, acompanhar a execução e consultar resultados e relatórios da conta autenticada. |
| Spring Boot | Validar a configuração e as permissões, atribuir a execução à conta e persistir resultados. Na primeira versão, iniciar um processo Python por execução e admitir uma coleta web ativa por instalação. |
| Motor Python | Receber a configuração em JSON e emitir eventos estruturados, um por linha, para progresso, resultados e término. A CLI e o site usam as mesmas funções de coleta. O texto do menu continua exclusivo do terminal. |
| Atualização da interface | O Spring envia eventos ao Angular por SSE. Ao recarregar, o cliente consulta o estado persistido antes de retomar o acompanhamento. Resultados já confirmados sobrevivem a interrupções do processo. |
| SQLite local | O Spring grava contas, perfis, execuções, resultados, vínculos entre buscas e PDFs binários. Cada acesso verifica o dono. O histórico e o perfil de navegador privados do terminal conservam seus caminhos até uma migração verificada. |

O processo Python local permite distribuir esta primeira versão sem operar um segundo servidor ou uma fila. O custo é instalar Python e Chromium junto ao backend e serializar as coletas. Um serviço de workers pode ser avaliado quando houver demanda por execução concorrente ou remota. Manter a escrita dos dados web no Spring concentra as migrações, inclusive se o banco vier a mudar para MySQL. A migração futura ainda exige testar identidade, índices de unicidade e conteúdo binário.

### Entregas e critérios de saída

| Etapa | Entrega | Dependência | Verificação |
|---|---|---|---|
| 1. Inventário | Entradas oficiais, diretórios classificados e proteção dos dados locais. | Aprovação do plano | Abrir e sair do terminal, testar login em banco isolado, verificar o site e comparar os dados locais antes/depois. |
| 2. Contas UrWork | Marca, retirada das demonstrações da navegação e perfil condicional com CPF. | Inventário e banco identificado | Conta existente mantém senha e completa CPF no próximo acesso. Homônimos com CPFs distintos entram. E-mail ou CPF duplicado é rejeitado. Verificar os três perfis e logout entre abas. |
| 3. Motor compartilhado | Funções de coleta separadas da interação de terminal, com entrada JSON e eventos. | Inventário | Comparar leads, deduplicação e exportação sobre a mesma amostra controlada. Testar ausência de resultados e falha da fonte. Preservar `python main.py` ao mover o pacote para `engine/`. |
| 4. Leads pelo site | Prospecção, progresso e resultados individuais por conta. | Contas e motor compartilhado | Iniciar uma busca, reabrir a aba, reiniciar o backend e consultar os resultados. Testar duplo clique, meta parcial, interrupção e isolamento entre contas. |
| 5. Relatórios | PDF opcional por execução com título, data, hora e ID, guardado no SQLite e agrupado por semana. | Leads persistidos | Comparar o PDF com o lote e conferir virada de semana. PDF desativado ou com falha preserva os leads. |
| 6. Conexões e filtros | Instagram e WhatsApp por conta, com filtros dependentes da capacidade disponível. | Coleta web e verificação de cada fonte | Testar redes desconectadas, uma conectada, ambas e sessão expirada. Distinguir dado desconhecido de ausência confirmada. |
| 7. Vagas | Primeiro conector, filtros de contratação e localização, ranking e currículo opcional. | Execuções persistidas e fonte validada | Conferir anúncio de origem, deduplicação, vaga remota no exterior e vaga sem salário. Executar com e sem currículo e repetir o fluxo de Leads. |
| 8. Consolidação | Catálogo DOCX das telas reais, restauração local e avaliação de uso do terminal. | Fluxos anteriores validados | Instalar do zero, restaurar cópia de teste e percorrer cadastro, busca, resultado e PDF. |


### Telas da etapa 4

Validação integrada em 15/11/2026: o formulário iniciou uma execução no Spring e recuperou o progresso após recarregar a aba. Com SQLite temporário e fonte controlada, Buscas exibiu o lead parcial da execução e a tela de progresso indicou esgotamento com 1 de 3 leads. O teste de reinício do backend preservou o resultado parcial e marcou a execução aberta como interrompida.

Em **Nova prospecção**, a pessoa autenticada escolhe nicho, região e meta. Um duplo clique em **Gerar prospecção** deve iniciar uma única execução. A tela mostra o total de leads obtidos e a meta solicitada. Se a fonte se esgotar antes da meta, a tela informa o motivo do término e o total parcial.

Ao reabrir a aba, a pessoa recupera o estado da execução. Em **Buscas → Leads**, ela consulta os resultados persistidos da própria conta, inclusive após reiniciar o backend.

#### Contrato do Angular com o Spring

As chamadas usam a sessão por cookie. O snapshot de uma execução contém `id`, `nicho`, `regiao`, `meta`, `total`, `estado` e `criadaEm`.

| Chamada | Comportamento |
|---|---|
| `POST /api/prospeccoes` | Enviar o token CSRF vigente e o JSON com `chave` (UUID por intenção, reutilizado ao repetir a mesma tentativa), `nicho`, `regiao` (ex. `Campinas - SP`) e `meta` (inteiro positivo). Retorna o snapshot com 202 ao criar ou 200 ao repetir o mesmo pedido. |
| `GET /api/prospeccoes` | Lista as execuções da conta, da mais recente à mais antiga. Ao reabrir, localizar a execução em andamento e retomar o acompanhamento. |
| `GET /api/prospeccoes/{id}` | Retorna o snapshot. Execução inexistente ou de outra conta retorna 404. |
| `GET /api/prospeccoes/{id}/eventos` | O EventSource recebe o evento nomeado `estado` com snapshot integral na conexão, na reconexão e a cada atualização. Substituir o estado local pelo recebido. Fechar o EventSource ao sair de `EM_ANDAMENTO`. |
| `GET /api/leads` | Lista os resultados da conta. O filtro opcional `?execucao={id}` restringe a busca. Cada item contém `execucao`, `coletadoEm` e `dados`, com campos do motor como `nome`, `cidade`, `nicho`, `url_maps`, `telefone` e `score_potencial`; a disponibilidade varia por fonte. |

Os estados terminais são `CONCLUIDA` e `INTERROMPIDA`. Uma execução concluída com total inferior à meta indica esgotamento das fontes. O POST usa 400 para entrada inválida, 401 para ausência de login, 403 para perfil incompleto ou falha de CSRF e 409 para instalação ocupada ou reutilização da chave com dados diferentes.

### Telas da etapa 5

Validação integrada: em quatro execuções no navegador contra o Spring, o estado final por SSE coincidiu com a consulta HTTP (uma sem PDF, duas com PDF disponível e uma com falha induzida). A falha preservou o lead em Buscas. Os dois downloads corresponderam aos documentos por ID e a listagem agrupou corretamente registros de domingo e segunda-feira no horário de Brasília. Os testes usaram SQLite temporário e coletor controlado.

Em **Nova prospecção**, a pessoa pode marcar a opção de gerar PDF e preencher o título. O POST de prospecções aceita `tituloPdf` com 1 a 100 caracteres. O título deve excluir caracteres de controle e os caracteres de nome de arquivo `< > : " / \ | ? *`. Omitir o campo ou enviar `null` desativa o PDF. Uma repetição da mesma intenção preserva a chave e o título. Reutilizar a chave com outro título retorna 409.

O snapshot HTTP/SSE inclui `tituloPdf` e `estadoPdf` (`SEM_PDF`, `PENDENTE`, `DISPONIVEL` ou `FALHOU`). O término normal pode gerar documento inclusive para lote vazio ou abaixo da meta. Uma interrupção não publica PDF. Se a geração falhar, a coleta concluída conserva seu estado e os resultados individuais.

Em **Relatórios**, `GET /api/relatorios` lista os PDFs disponíveis da conta, do mais recente ao mais antigo. Cada item traz `id`, `execucao`, `titulo`, `geradoEm` (UTC), `semana` (segunda-feira da geração em America/Sao_Paulo) e `nomeArquivo`. Agrupar pelo campo `semana`. O filtro opcional `?semana=2026-11-09` exige a data ISO de uma segunda-feira e retorna 400 para valor inválido. **Baixar relatório** usa `GET /api/relatorios/{id}/pdf`, com nome de arquivo no cabeçalho de download. Documento inexistente, indisponível ou de outra conta retorna 404.

### Nova prospecção na etapa 6

Validação: com SQLite temporário e as duas redes sem configuração, o navegador iniciou a busca sem filtros e recuperou o lead pelo backend real. Os cenários controlados cobriram expiração, indisponibilidade, remoção de filtros e recuperação das capacidades. Os arquivos do build Angular testado foram conferidos no JAR de distribuição. A autorização com contas empresariais reais ainda depende da configuração Meta descrita no README.

Antes dos filtros, consultar `GET /api/conexoes`. Cada item identifica a `rede` (INSTAGRAM ou WHATSAPP), o `estado` (NAO_CONFIGURADA, DESCONECTADA, CONECTADA, EXPIRADA ou INDISPONIVEL) e a lista de `capacidades`. Para conectar, enviar `POST /api/conexoes/{rede}/autorizar` com CSRF e abrir a URL recebida na mesma aba. Ao voltar a `/#nova-prospeccao`, consultar as conexões novamente. Para desvincular localmente, enviar `DELETE /api/conexoes/{rede}` com CSRF (204).

| Capacidade | Controle | Campo opcional de `filtrosSociais` |
|---|---|---|
| INSTAGRAM_VERIFICADO | Com perfil de Instagram identificado | `instagramVerificado` (booleano) |
| SEGUIDORES_MINIMOS | Mínimo de seguidores | `seguidoresMinimos` (inteiro ≥ 0 ou nulo) |
| WHATSAPP_LINK_PUBLICADO | Com link público de WhatsApp | `whatsappLinkPublicado` (booleano) |

Habilitar cada controle conforme as capacidades retornadas. Se perder a capacidade, limpar o filtro e explicar o motivo. Se o início da busca indicar conflito de conexão ou permissão (409) ou fonte indisponível (503), consultar o estado antes de uma nova tentativa. A busca sem filtros sociais continua disponível. Os sinais vêm da coleta pública; um perfil identificado indica que o motor encontrou o perfil. Valores nulos em `dados.sinais_sociais` são desconhecidos e registros anteriores podem omitir esse campo.

Quando o POST de prospecção recusa um filtro social, o cabeçalho `UrWork-Conexao-Social` identifica a causa na própria resposta: 409 com `NAO_CONFIGURADA`, `DESCONECTADA` ou `EXPIRADA`, ou 503 com `INDISPONIVEL`. Conflitos de chave ou de instalação ocupada retornam 409 sem esse cabeçalho. A tela usa a resposta do POST para explicar a falha e a consulta seguinte de conexões para atualizar os controles.

## Implementação disponível

O backend grava cada lead antes de contá-lo no snapshot. Na consulta geral, resultados repetidos entre buscas da mesma conta aparecem pela ocorrência mais recente (URL do Maps ou, na ausência, nome e cidade). Após um reinício, buscas abertas passam a `INTERROMPIDA`, com acesso aos resultados já gravados. O SSE consulta o estado persistido a cada segundo enquanto há um assinante e pode agrupar vários leads no mesmo snapshot. Execute uma instância Spring por arquivo SQLite.

| Diretório | Responsabilidade |
|---|---|
| `frontend/src/app/inicio/` | Página inicial, mapa e ondas. |
| `frontend/src/app/conta/` | Cadastro, login, conclusão do perfil e consulta de sessão. A navegação fica em `app.ts`. |
| `backend/src/main/java/br/com/urwork/contas/` | Autenticação, validação de CPF, perfis e migração do esquema anterior. |
| `backend/src/main/java/br/com/urwork/dados/` | Resolução do caminho do banco e importação de instalações antigas. |
| `dtb/UrWork.db` | SQLite ativo da instalação. O Git ignora este diretório. |
| `engine/` | Configuração, coleta com Playwright, qualificação e exportação. A varredura por lotes está em `prospeccao.py`; o menu em `cli.py`. |
| `Planilhas/` e `perfil_navegador/` | Histórico, PDFs e sessões locais utilizados pelo terminal. |

O cadastro recebe e-mail, senha, nome completo e perfil. O backend valida CPF e finalidade, protege os POSTs com CSRF e armazena o hash da senha. O login cria uma sessão por cookie. A consulta de sessão retorna nome, e-mail e indicação de perfil completo. Contas anteriores completam o perfil por POST autenticado em `/api/auth/perfil`. As telas de demonstração foram retiradas.

Ao iniciar da raiz ou da pasta backend do projeto, o Spring abre `dtb/UrWork.db`. Um caminho explícito em `URWORK_DB_PATH` prevalece sobre `ZIN_DB_PATH`. Quando o banco padrão ainda não existe, o inicializador verifica os caminhos legados em Planilhas, dtb/DTB e backend/Planilhas. Ele importa uma cópia consistente pelo SQLite e interrompe a seleção automática se encontrar cópias divergentes.

O terminal continua disponível por `python main.py`. O serviço interno `MotorPython.executar` inicia `python -m engine.worker` com um pedido JSON UTF-8 no stdin, por exemplo `{"nicho":"Oficina","regiao":"Campinas - SP","meta":36}`. O stdout traz um objeto JSON por linha: `inicio` informa a meta, cada `lead` traz o registro e o total cumulativo, e `fim` informa o total efetivo. O Spring confirma a conclusão após saída com sucesso. A fonte pode se esgotar antes da meta.

O serviço admite uma coleta por instância e encerra o processo depois de duas horas. Cada execução usa um contexto Chromium temporário e histórico em memória. A API autenticada persiste os resultados no SQLite e transmite o estado por SSE. O perfil e os relatórios do terminal continuam separados.
