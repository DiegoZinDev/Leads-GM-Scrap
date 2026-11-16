import { Component, inject, signal } from '@angular/core';
import { Sessao } from '../conta/sessao';
import { consultar, Execucao, mensagemErro } from './api';

interface Lead {
  execucao: number;
  coletadoEm?: string;
  dados?: {
    nome?: string; cidade?: string; nicho?: string; url_maps?: string;
    telefone?: string; score_potencial?: number;
  };
}

@Component({ selector: 'urwork-buscas', templateUrl: './buscas.html' })
export class Buscas {
  private sessao = inject(Sessao);
  private revisao = 0;
  execucoes = signal<Execucao[]>([]);
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
      const lista = await consultar<Lead[]>('/api/leads' + (id ? '?execucao=' + encodeURIComponent(id) : ''));
      if (revisao === this.revisao) this.leads.set(lista);
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
}
