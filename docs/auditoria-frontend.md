# Auditoria técnica final do Zin
13 de novembro de 2026 · Build Angular de produção · Impeccable audit

**Veredito: bom para demonstração, 14/20.** A implementação comunica prospecção territorial e priorização de empresas de forma coerente. O principal ajuste antes de liberar o protótipo para um público maior é tornar perceptíveis os limites dos campos. O resultado anterior de 25/40 avaliava dez heurísticas de usabilidade; esta nota técnica usa cinco dimensões diferentes.

| Dimensão | Nota | Evidência |
|---|---:|---|
| Acessibilidade | 2/4 | Rótulos associados, navegação por teclado, foco no título nas transições testadas e resposta a movimento reduzido. A borda que identifica os campos tem contraste baixo. |
| Desempenho | 4/4 | Compilação antecipada reproduzível; 176.439 bytes de JS. LCP mediano local de 1,32 s no início e 1,13 s no login. |
| Temas | 2/4 | Tokens de texto legíveis nos dois temas da área de trabalho. A escolha de tema se perde ao recarregar; a borda dos campos precisa de um token próprio. |
| Responsividade | 3/4 | Sete rotas em quatro larguras sem rolagem horizontal. Em 390 px, legenda e nome de cidade se sobrepõem. |
| Integridade da implementação | 3/4 | Os fluxos simulados têm desfechos específicos. Há diretrizes contraditórias nos documentos com marcadores de merge. |

## Achados priorizados
Quatro achados: zero P0, um P1, dois P2 e um P3.

1. **P1 · Identificação visual dos campos.** Em frontend/src/style.css, linha 3, inputs e divisores compartilham a cor de borda. No login, a relação da borda com o preenchimento é 1,71:1; o painel adjacente também é escuro. No filtro de leads em tema claro, borda e fundo adjacente dão 1,86:1 e o campo usa a mesma cor de fundo da página. Os rótulos estão visíveis, mas localizar a área de digitação é difícil antes do foco. Criar um token de borda de controle por tema, distinto dos divisores decorativos, e verificar pelo menos 3:1 com a superfície adjacente. Referência: contraste não textual, WCAG 1.4.11. Comando: impeccable colorize.
2. **P2 · Sobreposição no mapa.** Em frontend/src/app.html, linha 19, a legenda absoluta compete com Porto Alegre. Em 390 × 780, a interseção das caixas renderizadas mede cerca de 74 × 10 px. Mover a legenda para uma linha própria abaixo do SVG no breakpoint móvel e rever as larguras intermediárias. Comando: impeccable adapt.
3. **P2 · Documentação conflitante.** README.md:1, DESIGN.md:1 e PRODUCT.md:11 contêm marcadores literais de conflito. Conservam versões incompatíveis da identidade e da arquitetura, o que compromete a referência usada nas próximas mudanças. Conciliar as versões com o produto renderizado e validar a remoção dos marcadores. Comando: impeccable document.
4. **P3 · Tema volta ao escuro após recarregar.** Em frontend/src/main.ts, o tema vive apenas no estado do componente. Selecionar tema claro na fila de empresas e atualizar reproduz o comportamento. Persistir apenas essa preferência e aplicá-la ao iniciar a área de trabalho. Comando: impeccable harden.

## Reteste após a crítica e o polish
- Início: Ver demonstração é a ação principal. A onda de fundo manteve a posição durante a rolagem em 390 px. A preferência de movimento reduzido interrompeu as animações observadas.
- Login e cadastro: envio vazio bloqueado, exemplo fictício preenchido por teclado e confirmação própria com foco no título.
- Recuperação: código incorreto, expiração após cinco minutos, geração de outro código, verificação, nova senha e confirmação exercitados no navegador.
- O texto secundário sobre o fundo-base apresentou 10,33:1 no escuro e 7,84:1 no claro. O texto do CTA verde apresentou 14,09:1. São pares de cores específicos.
- Detector estático: uma ocorrência de fonte frequente, Space Grotesk. A fonte pertence ao sistema escolhido e o alerta estilístico ficou fora da contagem de defeitos.

## Método e limites
Edge/Chromium local. Rotas inicio, entrar, cadastro, senha, leads, buscas e relatorios em 320, 390, 768 e 1440 px. Toque sintetizado no alternador de tema; teclado nos formulários. Nenhuma exceção JavaScript não tratada observada no percurso. Build novo em pasta temporária com mesmo hash SHA-256 do JS servido. JS comprimido localmente com gzip: 61.222 bytes. Na crítica eram 1.023.707 bytes brutos, redução de 82,8%. LCP por três cargas com contextos novos, 390 × 844, CPU 4× e rede local: início 1.668/1.292/1.316 ms; login 1.076/1.196/1.132 ms. Resultados de laboratório; a auditoria não incluiu dispositivos físicos, Safari, leitores de tela reais, telemetria de campo ou backend. Os testes de autenticação exercitam a simulação local. Prioridade de execução: corrigir P1, adaptar a legenda, reconciliar as referências e concluir com impeccable polish e novo audit.

## Reteste após as correções

- **Bordas dos campos:** no login escuro, 4,75:1 contra o preenchimento e 4,40:1 contra o painel. No filtro claro, 4,15:1 contra o campo e o fundo adjacente.
- **Mapa:** a legenda ocupa uma linha abaixo do SVG até 760 px. Em 320, 390, 600, 760, 768 e 1440 px, nenhuma caixa de nome de cidade interceptou a legenda e não houve rolagem horizontal.
- **Documentação:** as referências descrevem o frontend Angular compilado antecipadamente, o mapa nacional e a operação integrada prevista. Os marcadores de conflito foram removidos das referências e da configuração associada.
- **Tema:** as escolhas clara e escura permaneceram após recarregar a área de trabalho. A página pública manteve sua identidade escura.

Verificação no build de produção, em Edge local. Os quatro achados foram retestados; a pontuação acima registra a auditoria original.
