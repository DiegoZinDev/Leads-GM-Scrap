CREATE TABLE IF NOT EXISTS usuario (
  id_usuario INTEGER PRIMARY KEY,
  username TEXT NOT NULL,
  email TEXT NOT NULL COLLATE NOCASE UNIQUE,
  senha TEXT NOT NULL,
  token TEXT,
  cpf TEXT UNIQUE,
  finalidade TEXT,
  empresa TEXT,
  ramo TEXT,
  servico TEXT,
  localidade TEXT,
  cargo TEXT,
  modalidade TEXT
);
