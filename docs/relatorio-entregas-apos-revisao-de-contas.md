# UrWork | Entregas desde a revisão de login e cadastro

## Ponto de partida

A revisão consolidou o cadastro para empresa, freelancer e pessoa em busca de emprego. O sistema aceita homônimos com CPFs distintos, valida o município com a UF e permite que contas antigas mantenham a senha e completem o perfil no próximo acesso. A sessão por cookie identifica a conta nas consultas e o token CSRF protege as operações que alteram dados. A navegação autenticada passou a usar dados da conta em lugar das telas demonstrativas.

## O que foi acrescentado

| Entrega | O que a pessoa consegue fazer | O que foi verificado |
|---|---|---|
| Motor compartilhado | Usar o coletor pelo terminal ou iniciar uma execução pelo site. O Spring envia um pedido ao Python e recebe resultados e progresso. | Divisão correta da meta em lotes, esgotamento antes da meta, falha do processo e recusa de uma segunda coleta simultânea. O histórico, os PDFs e o perfil de navegador do operador continuam separados da operação web. |
| Nova prospecção e Buscas → Leads | Escolher nicho, município e meta, acompanhar o total, reabrir a aba e consultar os leads da própria conta. A listagem geral deduplica resultados e permite filtrar por execução. | Envio duplicado, reconexão dos eventos, isolamento entre duas contas, esgotamento e recuperação após reiniciar o backend. Uma execução interrompida preservou o lead já gravado. |
| Relatórios | Solicitar PDF opcional com título, consultar por semana e baixar os documentos da conta. O SQLite guarda o conteúdo do lote, inclusive quando ele termina abaixo da meta. | Downloads conferidos por ID, PDFs com resultados e vazio, agrupamento na virada da semana em Brasília e recusa de download por outra conta. Uma falha induzida na geração preservou a coleta concluída e seus leads. |
| Instagram e WhatsApp | Vincular ou desvincular a conta empresarial e usar os filtros liberados pela conexão: perfil de Instagram identificado, mínimo de seguidores e link público de WhatsApp. A busca funciona sem conexões sociais. | A interface explicou a perda de capacidade, limpou filtros afetados e distinguiu sessão expirada de coleta já em andamento. Com a API real e as redes sem configuração, uma busca sem filtros entregou um lead. O fluxo empresarial com a Meta ainda depende de credenciais. |
| Nova prospecção e Buscas → Vagas | Consultar o mural da CI&T na Lever por cargo, localidade, modalidade e critérios de contratação. Experiência sugere nível editável. Salário e habilidades ajudam a ordenar resultados. Anúncios sem salário continuam elegíveis. É possível abrir o anúncio original e a candidatura. | Verificação de fechamento descrita abaixo. |

Em Vagas, a pessoa também pode anexar um currículo PDF ou DOCX de até 1 MiB para receber sugestões de habilidades, revisá-las e iniciar a busca. O serviço descarta o arquivo. O fluxo também aceita uma busca sem anexo.

## Operação e limites

**Fechamento da etapa 7.** Passaram 31 testes (15 Java, 12 Python e 4 de navegador). Com a Lever ao vivo, o navegador iniciou uma busca sem currículo, alcançou a meta de uma vaga e exibiu o anúncio persistido com o link de candidatura. Em outra execução, o backend encontrou uma vaga remota brasileira e gerou um PDF conferido contra o lote.

Com anúncios controlados e SQLite temporário, duas buscas remotas no exterior exercitaram o fluxo com e sem currículo, leitura de DOCX, edição de habilidades, recuperação após recarregar a aba, ranking e término com 2 de 3 vagas. Outros testes cobriram deduplicação, salário unilateral ou zero, ausência de salário ou data e regressões de Leads, Relatórios e conexões. A interface foi conferida nas larguras de 390 e 1280 pixels. O JAR final contém o Angular testado e o backend empacotado com JDK 25.

A busca de Vagas cobre o mural da CI&T. Currículos digitalizados apenas como imagem exigem preenchimento manual das habilidades. Os testes de Leads usaram fonte controlada; para Vagas houve também consulta real à Lever. As instâncias temporárias foram encerradas. A etapa 8 (consolidação, catálogo de telas e restauração) ficou para a próxima sessão.

O Spring mantém as execuções e os resultados por conta no SQLite. A instalação local admite uma coleta ativa por vez. O planejamento e os contratos usados pelos dois agentes estão na [arquitetura do projeto](arquitetura.md). A preparação do ambiente, o empacotamento e a configuração das conexões empresariais estão no [README](../README.md).
