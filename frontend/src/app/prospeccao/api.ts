import { Sessao } from '../conta/sessao';

export interface FiltrosSociais {
  instagramVerificado?: boolean;
  seguidoresMinimos?: number | null;
  whatsappLinkPublicado?: boolean;
}

export interface Execucao {
  id: number;
  nicho: string;
  regiao: string;
  meta: number;
  total: number;
  estado: 'EM_ANDAMENTO' | 'CONCLUIDA' | 'INTERROMPIDA';
  criadaEm: string;
  tituloPdf?: string | null;
  filtrosSociais?: FiltrosSociais;
  estadoPdf?: 'SEM_PDF' | 'PENDENTE' | 'DISPONIVEL' | 'FALHOU';
}

export async function consultar<T>(url: string): Promise<T> {
  const resposta = await fetch(url, { cache: 'no-store' });
  if (!resposta.ok) throw resposta;
  return resposta.json();
}

export function mensagemErro(erro: unknown, sessao: Sessao) {
  if (erro instanceof Response) {
    if ([401, 403].includes(erro.status)) void sessao.consultar();
    switch (erro.status) {
      case 400: return 'Confira o nicho, a região e a meta da busca.';
      case 401: return 'Sua sessão expirou. Entre novamente.';
      case 403: return 'Confira se o perfil está completo e tente novamente para renovar a autorização.';
      case 404: return 'Execução indisponível para esta conta. Atualize a lista.';
      case 409: return 'Há outra coleta em andamento ou a chave já foi usada com critérios diferentes. Confira as buscas antes de tentar novamente.';
    }
  }
  return 'Não foi possível confirmar a operação. Confira a conexão e tente novamente.';
}
