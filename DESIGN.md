<<<<<<< HEAD
---
name: Zin
colors:
  canvas: "#100d16"
  surface: "#1b1522"
  text: "#faf7ff"
  secondary: "#c5bacc"
  border: "#413747"
  action: "#bcff80"
---
# Zin · Identidade cartográfica

A página pública mostra a relação entre território e oportunidade. Um ponto verde marca a origem em um mapa esquemático roxo. Quatro trajetos aparecem em sequência até estabelecimentos locais. O mapa é ilustrativo e dispensa localização do visitante.

## Tipografia e composição

Space Grotesk para títulos e marca, DM Sans para texto e controles. Na página pública, o título ocupa o lado esquerdo no desktop. No celular, título e ações antecedem o mapa. Reserve verde para origem, rotas, prioridade e ação principal. As fichas operacionais usam listas e divisores para facilitar comparações.

## Navegação e estados

A página inicial oferece cadastro, login e demonstração. A área de trabalho começa em **Quem abordar hoje**, com empresas ordenadas por pontuação, filtro textual e mensagem de abordagem. Buscas e relatórios têm telas próprias. O estado vazio permite limpar a busca. Dados ilustrativos e integrações pendentes recebem indicação no contexto da ação.

## Movimento e acesso

Rotas aparecem em sequência, em 1,55 s cada. A troca de seção usa uma entrada curta de 260 ms. A preferência de movimento reduzido preserva o mapa completo e elimina as animações. Mantenha foco visível no teclado, foco no título após a navegação e anúncio textual do resultado das ações.
=======
# Design System — Zin (Carteira Jet-Age de Viagem)

<!-- impeccable:design-schema 1 -->

## Visual Authority & Principles

O sistema visual da plataforma **Zin** adota a direção **Carteira Jet-Age de Viagem (`vernacular-ephemera-jet-age-ticket-wallet`)**, aprovada via heurísticas do Impeccable. O design rompe com os clichês de SaaS genérico (cards flutuantes com sombras suaves excessivas e espaços vazios) em favor de uma superfície operacional densa, onde cada lote de prospecção funciona como um livreto de passagens e cupons auditados, com chancela física e rigor estatístico.

### 1. Paleta de Cores Oficial

| Papel Semântico | Cor (Hex) | Função no Sistema |
|---|---|---|
| **Carrier Navy** | `#0B192C` | Shell primário, cabeçalhos, barra superior de comando e tipografia de alto contraste |
| **Coupon Ivory** | `#FAF8F5` | Superfície de trabalho, fundos de formulários, bilhetes e pranchas de leitura |
| **Seal Red** | `#D62828` | Botões de ação primária (Disparar Lote), chancelas de corte e marcadores prioritários |
| **Carbon Purple** | `#49306B` | Destaque numérico dos scores dos leads (0–100) e algarismos tabulares |
| **Steel Muted** | `#8D99AE` | Linhas estruturais de 1px, divisores pontilhados/picotados e legendas técnicas |

### 2. Modo Noturno (Teoria de Cores Inversa)

| Token Noturno | Cor (Hex) | Função |
|---|---|---|
| **Deep Canvas** | `#050B14` | Fundo imersivo escuro |
| **Surface Navy** | `#0B192C` | Superfícies de cartões e blocos estruturais |
| **Elevated Navy**| `#11223B` | Cabeçalhos e barras de ferramentas elevadas |
| **Active Seal**  | `#E63946` | Ação primária e destaques de alta visibilidade |
| **Carbon Violet**| `#B598DC` | Numerais e scores em fundo escuro |
| **Muted Steel**  | `#8D99AE` | Bordas e legendas secundárias |

### 3. Tipografia

- **Família Principal**: `Inter` / `Plus Jakarta Sans`, sans-serif operacional com legibilidade industrial.
- **Numerais e Métricas**: `monospace` / `font-feature-settings: "tnum"` para garantir alinhamento tabular perfeito de scores, taxas de retenção e contadores de leads.
- **Identidade da Marca**: Banner em arte de blocos ASCII (`ZIN`) renderizado com proporção estrita em fontes monoespaçadas.

### 4. Componentes e Estrutura

- **Sem Sombras Desnecessárias**: Bordas nítidas de `1px solid var(--border-subtle)` substituem sombras difusas artificiais.
- **Cantos Vivos/Discretos**: Raio de borda controlado (`4px` a `6px`) evocando cartões e documentos oficiais.
- **Funil de 6 Estações**: Apresentado como uma esteira contínua de cupons auditados com indicação percentual clara de passagem entre etapas.
>>>>>>> 331b6cc02bb76a942784057947e0a26e4c6053bd
