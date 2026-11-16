import { Component, inject, input, signal } from '@angular/core';
import { Sessao } from '../conta/sessao';
import { consultar, Execucao, mensagemErro } from './api';
import { rotulos } from './form-vagas';

interface Salario { min: number | null; max: number | null; moeda: string | null; periodo: string | null; }
interface Vaga {
  execucao: number;
  coletadoEm: string;
  dados: {
    idFonte: string; fonte: string; cargo: string; empresa: string; localidade?: string; pais?: string;
    modalidade?: string; publicadaEm?: string; urlOrigem?: string; urlCandidatura?: string;
    salario?: Salario; descricao?: string;
  };
}

interface Lead {
  execucao: number;
  coletadoEm?: string;
  dados?: {
    nome?: string; cidade?: string; nicho?: string; url_maps?: string;
    telefone?: string; score_potencial?: number;
    sinais_sociais?: { instagramVerificado?: boolean | null; seguidores?: number | null; whatsappLinkPublicado?: boolean | null };
  };
}

@Component({ selector: 'urwork-buscas', templateUrl: './buscas.html' })
export class Buscas {
  private sessao = inject(Sessao);
  private revisao = 0;
  execucoes = signal<Execucao[]>([]);
  vagas = input(false);
  anuncios = signal<Vaga[]>([]);
  rotulos = rotulos;
  leads = signal<Lead[]>([]);
  carregando = signal(true);
  erro = signal('');
  erroLista = signal('');
  filtro = '';

  ngOnInit() { this.atualizar(); }
  ngOnDestroy() { ++this.revisao; }

  atualizar() {
    void this.listarExecucoes();
    void this.filtrar(this.filtro);
  }

  private async listarExecucoes() {
    try {
      this.execucoes.set(await consultar<Execucao[]>('/api/prospeccoes'));
      this.erroLista.set('');
    } catch (erro) { this.erroLista.set(mensagemErro(erro, this.sessao)); }
  }

  async filtrar(id: string) {
    const revisao = ++this.revisao;
    this.filtro = id;
    this.carregando.set(true);
    this.erro.set('');
    try {
      const filtro = id ? '?execucao=' + encodeURIComponent(id) : '';
      if (this.vagas()) {
        const lista = await consultar<Vaga[]>('/api/vagas' + filtro);
        if (revisao === this.revisao) this.anuncios.set(lista);
      } else {
        const lista = await consultar<Lead[]>('/api/leads' + filtro);
        if (revisao === this.revisao) this.leads.set(lista);
      }
    } catch (erro) {
      if (revisao === this.revisao) this.erro.set(mensagemErro(erro, this.sessao));
    } finally { if (revisao === this.revisao) this.carregando.set(false); }
  }

  data(valor?: string) {
    if (!valor) return '';
    const data = new Date(valor);
    return Number.isNaN(data.getTime()) ? '' : data.toLocaleString('pt-BR');
  }

  link(url?: string) { return url && /^https?:\/\//i.test(url) ? url : undefined; }

  salario(s?: Salario) {
    if (s?.min == null && s?.max == null) return 'Salário não informado';
    const formatar = (valor: number) => valor.toLocaleString('pt-BR', { maximumFractionDigits: 2 });
    const faixa = s.min == null ? 'Até ' + formatar(s.max!) : s.max == null ? 'A partir de ' + formatar(s.min)
      : s.min === s.max ? formatar(s.min) : formatar(s.min) + ' a ' + formatar(s.max);
    return faixa + (s.moeda ? ' ' + s.moeda : '') + (s.periodo ? ' por ' + rotulos[s.periodo].toLowerCase() : '');
  }
}
