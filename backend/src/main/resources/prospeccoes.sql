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
