"""
Configurações, Nichos, Regiões e Modelos de Abordagem para o Scraper de Leads
"""

import os

# Diretório para perfil persistente do navegador (armazena cookies, login do Instagram e sessão do WhatsApp Web)
PASTA_PERFIL_NAVEGADOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perfil_navegador")

# Regiões e Cidades alvo (expandidas para garantir volume mínimo de 50 leads)
REGIOES = [
    "Brasília DF",
    "Valparaíso de Goiás",
    "Águas Claras DF",
    "Taguatinga DF",
    "Asa Sul Brasília DF",
    "Asa Norte Brasília DF",
    "Sudoeste Brasília DF",
    "Guará DF",
    "Vicente Pires DF",
    "Ceilândia DF",
    "Lago Sul Brasília DF",
    "Jardim Céu Azul Valparaíso GO",
    "Etapa A Valparaíso GO"
]

META_MINIMA_LEADS = 50  # Meta padrão exigida por lote/planilha

# Nichos e termos de busca específicos
NICHOS = {
    "Advocacia": {
        "termos": [
            "escritorio de advocacia",
            "advogado civil trabalhista empresarial",
        ],
        "ticket": "alto",
        "copy_base": (
            "Olá! Tudo bem? Encontrei o escritório de vocês no Google Maps com excelentes avaliações. "
            "Notei que vocês ainda não possuem um site institucional oficial conectado à sua ficha. "
            "Hoje, a maioria dos clientes de alto valor pesquisa no Google antes de fechar contrato e busca a credibilidade de uma página própria com agendamento direto. "
            "Trabalho desenvolvendo páginas de alta conversão para escritórios jurídicos. Poderíamos conversar 5 minutinhos para eu mostrar como podemos atrair clientes mais qualificados sem depender apenas de indicações?"
        )
    },
    "Odontologia": {
        "termos": [
            "clinica odontologica",
            "dentista implantes e estetica",
        ],
        "ticket": "alto",
        "copy_base": (
            "Olá, equipe da {nome}! Tudo bem? Estava pesquisando clínicas odontológicas de referência na região e vi que a nota de vocês é ótima no Google! "
            "Reparei que vocês não têm um site cadastrado para agendamento online e apresentação dos tratamentos (como implantes/invisalign/estética). "
            "Criamos sites e páginas de captação que direcionam pacientes particulares qualificados diretamente para o WhatsApp da sua secretária. "
            "Teria 5 minutos para conversarmos sobre como transformar as pesquisas do Google em consultas agendadas?"
        )
    },
    "Fisioterapia": {
        "termos": [
            "clinica de fisioterapia pilates",
            "fisioterapia ortopedica e desportiva",
        ],
        "ticket": "medio-alto",
        "copy_base": (
            "Olá! Tudo bem? Vi que a clínica {nome} é super recomendada no Google com ótimas avaliações. "
            "Notei que vocês ainda não têm um site próprio destacando os métodos de tratamento, equipe e agendamento. "
            "Hoje, quem busca fisioterapia e reabilitação quer conhecer a estrutura antes de ir. "
            "Posso te apresentar uma estrutura simples de site com botão de WhatsApp integrado que já aumentou os agendamentos de clínicas parecidas?"
        )
    },
    "Cirurgia Plástica / Estética": {
        "termos": [
            "clinica de cirurgia plastica",
            "clinica de estetica avancada e harmonizacao",
        ],
        "ticket": "muito_alto",
        "copy_base": (
            "Olá, Dr(a). / equipe da {nome}! Parabéns pelo posicionamento e excelentes avaliações no Google. "
            "Percebi que a clínica ainda não conta com um site próprio exclusivo para passar a autoridade e o luxo que procedimentos estéticos de alto padrão exigem. "
            "Pacientes de procedimentos de alto valor exigem um site impecável com dúvidas frequentes e contato direto com a consultora. "
            "Gostaria de agendar uma breve demonstração de um layout sob medida para elevar a percepção de valor da sua clínica?"
        )
    },
    "Academias (Recentes/Novas)": {
        "termos": [
            "academia nova",
            "crossfit centro de treinamento",
            "academia boutique fitness",
        ],
        "ticket": "recorrente",
        "copy_base": (
            "Olá! Tudo bem? Acompanhei o espaço da {nome} no Google e a estrutura é sensacional! "
            "Notei que vocês ainda não possuem um site com tabela de planos, tour virtual e matrícula online direto pelo WhatsApp. "
            "Uma landing page rápida para novos alunos pode dobrar as adesões no início do mês. "
            "Podemos bater um papo rápido para eu mostrar como estruturar isso para vocês?"
        )
    },
    "Serralheria": {
        "termos": [
            "serralheria esquadrias de aluminio e ferro",
            "serralheiro estruturas metalicas portoes",
        ],
        "ticket": "medio-alto",
        "copy_base": (
            "Olá! Tudo bem? Vi o trabalho e as excelentes avaliações da {nome} no Google Maps. "
            "Notei que vocês não têm um site/catálogo digital para mostrar as fotos das obras e portões já feitos. "
            "Muitos clientes de condomínio e construção civil preferem orçar com empresas que têm um site com portfólio profissional. "
            "Construímos catálogos online simples e diretos para o WhatsApp. Teria interesse em conhecer?"
        )
    },
    "Restaurantes de Alto Custo": {
        "termos": [
            "restaurante alta gastronomia",
            "restaurante bistrot contemporaneo",
            "restaurante fino recem aberto",
        ],
        "ticket": "alto",
        "copy_base": (
            "Olá! Tudo bem? Vi a repercussão e as fotos incríveis dos pratos da {nome} no Google Maps! "
            "Notei que vocês ainda não têm um site próprio com cardápio digital interativo e sistema de reservas direto. "
            "Depender apenas de redes sociais ou aplicativos terceiros faz você perder margem e clientes executivos que reservam pelo Google. "
            "Desenvolvemos páginas exclusivas para restaurantes de alta gastronomia com cardápio otimizado para celular. Posso te enviar uma prévia sem compromisso?"
        )
    }
}

# Critérios e filtros de qualidade
FILTROS = {
    "exigir_sem_site": True,          # Focar prioritariamente em quem NÃO tem site
    "nota_minima": 4.0,              # Somente negócios bem avaliados
    "min_avaliacoes": 5,             # Pelo menos 5 avaliações para garantir que tem clientela ativa
    "exigir_telefone": True,         # Deve ter telefone para poder abordar
}
