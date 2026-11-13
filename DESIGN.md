---
name: Zin
description: "Sistema visual da prospecção territorial do Zin"
colors:
  canvas: "#100d16"
  surface: "#1b1522"
  text: "#faf7ff"
  secondary: "#c5bacc"
  border: "#413747"
  controlBorderDark: "#897895"
  controlBorderLight: "#81738c"
  light-canvas: "#faf7fd"
  light-surface: "#eee8f3"
  light-text: "#21132b"
  light-secondary: "#564962"
  action-ink: "#17210e"
  focus: "#a586fa"
  action: "#bcff80"
typography:
  display:
    fontFamily: "Space Grotesk Variable, sans-serif"
    fontWeight: 620
    lineHeight: 0.96
  body:
    fontFamily: "DM Sans Variable, sans-serif"
    fontSize: "16px"
    lineHeight: 1.55
rounded:
  control: "6px"
  panel: "12px"
spacing:
  field: "8px"
  form: "18px"
components:
  button-primary:
    backgroundColor: "{colors.action}"
    textColor: "{colors.action-ink}"
    rounded: "{rounded.control}"
  input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
---
# Zin · Identidade cartográfica

## Overview

A página pública mostra a relação entre território e oportunidade. Nove cidades brasileiras enviam trajetos tracejados ao marcador verde do usuário em Brasília. O mapa é ilustrativo e dispensa localização do visitante.

## Colors

O verde identifica a ação principal e o destino das rotas. As faixas roxas permanecem abaixo do conteúdo. Os divisores separam grupos; as bordas dos campos têm tokens próprios para garantir contraste nos dois temas. A área pública usa o tema escuro. A área de trabalho oferece tema claro e guarda a preferência no navegador.

## Typography

Space Grotesk para títulos e marca, DM Sans para texto e controles. O título de entrada tem entre 47 e 80 px no desktop e entre 30 e 59 px no celular. A pontuação das empresas usa algarismos tabulares.

## Layout

Na página pública, o título ocupa o lado esquerdo no desktop. No celular, título e ações antecedem o mapa. Reserve verde para o marcador, rotas, prioridade e ação principal. As fichas operacionais usam listas e divisores para facilitar comparações.

Até 760 px, a legenda passa para uma linha própria abaixo do mapa e as etapas da página pública formam uma coluna. A navegação operacional pode quebrar para uma segunda linha.

## Elevation & Depth

Os painéis se distinguem por superfície e borda. A onda ocupa a largura da janela e permanece centralizada ao rolar, com altura limitada a 850 px. Sua opacidade é de 32% no desktop e 24% no celular.

## Shapes

Controles usam cantos de 6 px. O painel de acesso usa 12 px e uma borda fina. O marcador, os pontos das cidades e as rotas tracejadas pertencem ao mapa.

## Components

A página inicial oferece cadastro, login e demonstração. A área de trabalho começa em **Quem abordar hoje**, com empresas ordenadas por pontuação, filtro textual e mensagem de abordagem. Buscas e relatórios têm telas próprias. O estado vazio permite limpar a busca. Dados ilustrativos e integrações pendentes recebem indicação no contexto da ação.

### Movimento e acesso

As nove rotas se desenham em sequência escalonada e convergem no marcador. A troca de seção usa uma entrada curta de 260 ms. A preferência de movimento reduzido preserva o mapa completo e elimina as animações. Mantenha foco visível no teclado, foco no título após a navegação e anúncio textual do resultado das ações.

Quatro faixas roxas se dobram independentemente e formam uma onda de fundo fixa no centro da janela durante a rolagem. Com movimento reduzido, as ondas ficam estáticas.

Na primeira entrada na página inicial, o título aparece letra por letra, com cursor breve e as linhas já dimensionadas. Ao voltar de outra tela ou usar movimento reduzido, a frase aparece inteira. Os controles ficam disponíveis durante a entrada.

## Do's and Don'ts

- Mantenha o rótulo do campo visível durante a digitação e o foco perceptível ao usar teclado.
- Reserve ao botão verde a ação principal da tela. Em Início, ele conduz à demonstração.
- Identifique a localização como ilustrativa e as operações simuladas no contexto da ação.
