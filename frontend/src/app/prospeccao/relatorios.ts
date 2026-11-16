import { Component, DestroyRef, inject, signal } from '@angular/core';
import { Sessao } from '../conta/sessao';
import { consultar, mensagemErro } from './api';

interface Relatorio {
  id: number;
  execucao: number;
  titulo: string;
  geradoEm: string;
  semana: string;
  nomeArquivo: string;
}

@Component({ selector: 'urwork-relatorios', templateUrl: './relatorios.html' })
export class Relatorios {
  private sessao = inject(Sessao);
  private vida = inject(DestroyRef);
  semanas = signal(new Map<string, Relatorio[]>());
  carregando = signal(true);
  erro = signal('');
  erroDownload = signal('');
  baixando = signal<number | null>(null);
  horario = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo' });

  ngOnInit() { void this.listar(); }

  async listar() {
    this.carregando.set(true);
    this.erro.set('');
    this.erroDownload.set('');
    try {
      const documentos = await consultar<Relatorio[]>('/api/relatorios');
      const grupos = new Map<string, Relatorio[]>();
      for (const documento of documentos) {
        const grupo = grupos.get(documento.semana);
        if (grupo) grupo.push(documento);
        else grupos.set(documento.semana, [documento]);
      }
      this.semanas.set(grupos);
    } catch (erro) { this.erro.set(mensagemErro(erro, this.sessao)); }
    finally { this.carregando.set(false); }
  }

  async baixar(documento: Relatorio) {
    if (this.baixando() !== null) return;
    this.baixando.set(documento.id);
    this.erroDownload.set('');
    try {
      const resposta = await fetch('/api/relatorios/' + documento.id + '/pdf', { cache: 'no-store' });
      if (!resposta.ok) throw resposta;
      const pdf = await resposta.blob();
      if (this.vida.destroyed) return;
      const link = document.createElement('a');
      link.href = URL.createObjectURL(pdf);
      link.download = documento.nomeArquivo;
      link.click();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    } catch (erro) {
      this.erroDownload.set(erro instanceof Response && erro.status === 404
        ? 'Esse relatório está indisponível. Atualize a lista.' : mensagemErro(erro, this.sessao));
    } finally { this.baixando.set(null); }
  }

  dataLocal(valor: string) { return this.horario.format(new Date(valor)); }
}
