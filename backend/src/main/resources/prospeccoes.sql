CREATE TABLE IF NOT EXISTS prospeccao (
    id INTEGER PRIMARY KEY,
    dono INTEGER NOT NULL REFERENCES usuario(id_usuario),
    chave TEXT NOT NULL,
    nicho TEXT NOT NULL,
    regiao TEXT NOT NULL,
    meta INTEGER NOT NULL CHECK(meta > 0),
    estado TEXT NOT NULL CHECK(estado IN ('EM_ANDAMENTO','CONCLUIDA','INTERROMPIDA')),
    criada_em TEXT NOT NULL,
    UNIQUE(dono, chave)
);
CREATE UNIQUE INDEX IF NOT EXISTS prospeccao_unica_ativa ON prospeccao(estado) WHERE estado='EM_ANDAMENTO';
CREATE TABLE IF NOT EXISTS resultado_prospeccao (
    execucao INTEGER NOT NULL REFERENCES prospeccao(id),
    ordem INTEGER NOT NULL,
    identidade TEXT NOT NULL,
    coletado_em TEXT NOT NULL,
    dados TEXT NOT NULL,
    PRIMARY KEY(execucao, ordem)
);
CREATE TABLE IF NOT EXISTS relatorio (
    id INTEGER PRIMARY KEY,
    execucao INTEGER NOT NULL UNIQUE REFERENCES prospeccao(id),
    titulo TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'PENDENTE' CHECK(estado IN ('PENDENTE','DISPONIVEL','FALHOU')),
    gerado_em TEXT,
    semana TEXT,
    nome_arquivo TEXT,
    pdf BLOB
);
CREATE TABLE IF NOT EXISTS conexao_social (
    dono INTEGER NOT NULL REFERENCES usuario(id_usuario),
    rede TEXT NOT NULL,
    token TEXT NOT NULL,
    PRIMARY KEY(dono,rede)
);
CREATE TABLE IF NOT EXISTS filtro_social (
    execucao INTEGER PRIMARY KEY REFERENCES prospeccao(id),
    instagram INTEGER NOT NULL,
    whatsapp INTEGER NOT NULL,
    seguidores INTEGER
);
