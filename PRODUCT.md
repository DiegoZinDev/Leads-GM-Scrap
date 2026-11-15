# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Angular com TypeScript na interface, Spring Boot com Spring Web, Spring Security e Spring Data JPA/Hibernate no backend, e Python com Playwright, pandas e NumPy no motor de busca. A instalação usa `dtb/UrWork.db` na máquina que executa o Spring. O backend controla o acesso aos dados web. Uma migração para MySQL pode ser avaliada quando houver hospedagem.

## Users

O UrWork atende freelancers que procuram clientes para os serviços que prestam, empresas B2B que buscam compradores e pessoas que procuram emprego no Brasil ou no exterior. O perfil escolhido sugere critérios iniciais. A mesma pessoa pode alternar entre Leads e Vagas.

## Experiência web disponível

A navegação do UrWork oferece início, login, cadastro e Minha conta. O cadastro aceita homônimos e solicita CPF, e-mail e os campos da finalidade escolhida. Após o login, pessoas com cadastro anterior preenchem o perfil uma vez para acessar Minha conta. A tela de conta exibe nome e e-mail. O terminal continua responsável pelas buscas de empresas, com histórico de deduplicação e PDFs em `Planilhas/`.

O fluxo de prospecção web, os filtros de vagas e as conexões sociais por usuário descritos a seguir fazem parte do escopo aprovado para desenvolvimento.

## Product Purpose

Encontrar empresas que possam comprar um serviço ou vagas compatíveis com o candidato. O primeiro marco será configurar uma prospecção no site, acompanhar o motor Python em execução e consultar os resultados reais após reabrir o navegador. O terminal continuará disponível durante a transição.

## Positioning

Em **Nova prospecção**, a pessoa define o que considera uma oportunidade qualificada. Em **Buscas**, examina cada resultado e sua origem. Em **Relatórios**, recupera os documentos das execuções para as quais pediu PDF.

## Operating Context — operação integrada prevista

1. A pessoa entra com e-mail e senha, escolhe **Leads** ou **Vagas** em Nova prospecção e revisa os valores sugeridos pelo perfil.
2. As conexões de Instagram e WhatsApp aparecem antes dos filtros sociais. A pessoa escolhe os filtros disponíveis, a quantidade desejada e, se quiser um PDF, o título do documento.
3. Ao acionar **Gerar prospecção**, o Spring salva os critérios da execução e inicia o motor Python. A instalação local aceita uma coleta ativa de cada vez. Os filtros e o botão ficam desabilitados enquanto o trabalho está em andamento.
4. O painel de progresso à direita recebe eventos do Spring por SSE e mostra etapa, candidatos analisados, resultados qualificados e percentual da meta, por exemplo, “18 de 30 qualificados · 60% da meta”. Se as fontes se esgotarem, a execução termina com a quantidade alcançada. Ao recarregar a página, a pessoa pode recuperar o estado salvo.
5. Os resultados confirmados permanecem disponíveis se houver uma interrupção ou falha no PDF. **Buscas** abre na aba **Leads** e oferece **Vagas** ao lado. Ambas reúnem os resultados de todas as buscas da conta, com detalhe, fonte, data e filtro por execução. A mesma oportunidade encontrada em várias buscas mantém o vínculo com cada execução e aparece uma vez na listagem geral.

## Capabilities and Constraints

### Conta e perfil

O cadastro solicita nome completo, e-mail, CPF, senha e finalidade. O nome completo aceita homônimos. O e-mail de login e o CPF são únicos por conta. O backend normaliza o CPF para 11 dígitos e valida seus dígitos verificadores. A verificação de titularidade é um procedimento distinto. As contas existentes preservam senha e acesso, e completam o perfil e o CPF antes da primeira prospecção.

| Finalidade | Campos complementares |
|---|---|
| Freelancer em busca de clientes | Serviço prestado e localidades onde atende. |
| Empresa própria (B2B) | Nome da empresa e ramo. O nicho dos clientes procurados é configurado por busca. O CPF é o da pessoa responsável pela conta. |
| Busca por emprego | Tipo de vaga, ramo, localidades e modalidade presencial, híbrida ou remota. |

A conta autenticada determina o acesso a conexões, execuções, resultados e relatórios. O perfil de navegador usado hoje pelo operador do terminal continua separado das conexões do site. O CPF aparece mascarado quando for necessário exibi-lo. Logs, eventos de progresso e PDFs omitem esse dado.

### Critérios de prospecção

| Grupo | Configurações e comportamento |
|---|---|
| Comuns | Nicho ou palavras-chave, termos a excluir, localidade e quantidade desejada. O conjunto de filtros disponível acompanha os dados observáveis de cada fonte. |
| Leads | Categoria, município ou região, raio quando disponível, estrelas mínimas, faixa de quantidade de avaliações, presença de site próprio, canal de contato, autônomo ou empresa e tempo de atividade. Um filtro de presença oferece “indiferente”, “com” e “sem”. Um sinal inconclusivo fica registrado como desconhecido. A data da primeira evidência de atividade tem rótulo próprio e distingue-se da fundação comprovada. |
| Conexões sociais | Sem conexão, os filtros dependentes ficam desabilitados. A conexão de Instagram libera presença, seguidores ou engajamento conforme as permissões e os dados acessíveis. A de WhatsApp libera os sinais de contato que a fonte oferece. O backend verifica as condições ao iniciar a coleta, inclusive se a sessão tiver expirado. |
| Vagas | Cargo, nicho, senioridade, jornada integral ou parcial, turno, vínculo (por exemplo, CLT, estágio ou PJ), localidade, modalidade, país e interesse em trabalhar no exterior. Experiência na área sugere um nível que a pessoa pode alterar. Filtros sobre a empresa contratante dependem dos dados da fonte. |
| Preferências do candidato | Escolaridade, graduação concluída ou em andamento, faixa salarial e moeda. Vagas compatíveis com salário divulgado ganham destaque. Anúncios sem salário informado continuam elegíveis. Um currículo opcional em PDF ou DOCX pode sugerir critérios para a pessoa revisar. A busca também funciona sem anexo. |

Cada fonte de vagas precisa ser validada quanto a identificador, cargo, empresa, localidade, data e link de candidatura. Catho, Gupy e LinkedIn são fontes candidatas, com cobertura a confirmar por plataforma.

### PDF e lote semanal

Uma prospecção pode gerar um PDF com os resultados daquele lote. O nome combina título escolhido pelo usuário, data, hora e ID atribuído pelo banco, por exemplo, `Clientes de Campinas - 2026-11-14 - 14h35 - 42.pdf`. O backend armazena o documento no SQLite local e o organiza em **Relatórios** pela semana de geração. O relatório registra a data e o horário da coleta. Os resultados individuais ficam disponíveis em Buscas mesmo quando a opção de PDF está desmarcada.

## Brand Commitments

A marca aprovada é **UrWork**. A página inicial conserva o mapa ilustrativo em roxo escuro, as rotas em verde-neon, a base preta e a tipografia branca. O movimento de fundo mantém o conteúdo legível. A área de trabalho oferece tema claro e escuro. As ações usam o vocabulário do operador, como “Gerar prospecção”, “Ver vaga” e “Baixar relatório”. As decisões visuais existentes estão em [DESIGN.md](DESIGN.md).

## Evidence on Hand

A arquitetura e o catálogo registram a versão disponível. O motor já separa a varredura por lotes da interface de terminal. [Arquitetura](docs/arquitetura.md) · [Catálogo de telas](docs/Documentacao_Oficial_UrWork.docx) · [Coleta por lotes](engine/prospeccao.py) · [Qualificação](engine/qualifier.py) · [Exportação](engine/exporter.py)

## Product Principles

1. Cada resultado traz evidência suficiente para a pessoa decidir se vale a abordagem ou candidatura.
2. Uma execução conserva os critérios usados e as fontes consultadas para explicar o resultado mesmo depois de o perfil mudar.
3. A pessoa escolhe o nível de investigação e os dados adicionais que deseja fornecer, inclusive conexões e currículo.
4. Recursos em construção ficam fora da navegação pública até oferecerem um fluxo utilizável.

## Accessibility & Inclusion

A interface tem como alvo WCAG 2.1 AA, com contraste mínimo de 4,5:1 para texto normal e 3:1 para texto grande e componentes. Os formulários, abas, listas e relatórios devem permitir navegação por teclado, com ordem lógica, rótulos claros e foco visível. Filtros indisponíveis explicam qual conexão é necessária. O estado da coleta também é comunicado por texto, e as animações respeitam a preferência de movimento reduzido.
