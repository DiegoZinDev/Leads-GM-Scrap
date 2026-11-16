import { Component, DestroyRef, HostListener, inject, signal } from '@angular/core';
import { Sessao } from '../conta/sessao';
import { consultar, FiltrosSociais, mensagemErro } from './api';

type Rede = 'INSTAGRAM' | 'WHATSAPP';
type Capacidade = 'INSTAGRAM_VERIFICADO' | 'SEGUIDORES_MINIMOS' | 'WHATSAPP_LINK_PUBLICADO';
const estados = {
  NAO_CONFIGURADA: 'Sem configuração nesta instalação', DESCONECTADA: 'Desconectada',
  CONECTADA: 'Conectada', EXPIRADA: 'Autorização expirada', INDISPONIVEL: 'Indisponível'
};
interface Conexao { rede: Rede; estado: keyof typeof estados; capacidades: Capacidade[]; }

@Component({ selector: 'urwork-conexoes', templateUrl: './conexoes.html' })
export class Conexoes {
  private sessao = inject(Sessao);
  private vida = inject(DestroyRef);
  private revisao = 0;
  redes: Rede[] = ['INSTAGRAM', 'WHATSAPP'];
  nomes = { INSTAGRAM: 'Instagram', WHATSAPP: 'WhatsApp' };
  estados = estados;
  lista = signal<Conexao[]>([]);
  consultando = signal(true);
  alterando = signal(false);
  erro = signal('');
  aviso = signal('');
  instagram = signal(false);
  seguidores = signal<number | null>(null);
  whatsapp = signal(false);

  ngOnInit() { void this.atualizar(); }

  @HostListener('window:pageshow', ['$event'])
  voltar(evento: PageTransitionEvent) { if (evento.persisted) void this.atualizar(); }

  conexao(rede: Rede) { return this.lista().find(item => item.rede === rede); }

  permite(capacidade: Capacidade) {
    return this.lista().some(item => item.estado === 'CONECTADA' && item.capacidades.includes(capacidade));
  }

  restaurar(filtros: FiltrosSociais) {
    this.instagram.set(!!filtros.instagramVerificado);
    this.seguidores.set(filtros.seguidoresMinimos ?? null);
    this.whatsapp.set(!!filtros.whatsappLinkPublicado);
    if (!this.consultando()) this.limparIndisponiveis();
  }

  selecionados(): FiltrosSociais | undefined {
    const filtros: FiltrosSociais = {};
    if (this.instagram() && this.permite('INSTAGRAM_VERIFICADO')) filtros.instagramVerificado = true;
    if (this.seguidores() !== null && this.permite('SEGUIDORES_MINIMOS')) filtros.seguidoresMinimos = this.seguidores();
    if (this.whatsapp() && this.permite('WHATSAPP_LINK_PUBLICADO')) filtros.whatsappLinkPublicado = true;
    return Object.keys(filtros).length ? filtros : undefined;
  }

  private limparIndisponiveis() {
    const removidos = [];
    if (this.instagram() && !this.permite('INSTAGRAM_VERIFICADO')) {
      this.instagram.set(false);
      removidos.push('perfil de Instagram identificado');
    }
    if (this.seguidores() !== null && !this.permite('SEGUIDORES_MINIMOS')) {
      this.seguidores.set(null);
      removidos.push('mínimo de seguidores');
    }
    if (this.whatsapp() && !this.permite('WHATSAPP_LINK_PUBLICADO')) {
      this.whatsapp.set(false);
      removidos.push('link público de WhatsApp');
    }
    if (removidos.length)
      this.aviso.set('A conexão deixou de disponibilizar os filtros de ' + removidos.join(', ') + '. Eles foram removidos desta busca.');
  }

  async atualizar() {
    const revisao = ++this.revisao;
    this.consultando.set(true);
    this.erro.set('');
    try {
      const lista = await consultar<Conexao[]>('/api/conexoes');
      if (revisao === this.revisao) this.lista.set(lista);
    } catch (erro) {
      if (revisao !== this.revisao) return;
      this.lista.set([]);
      this.erro.set(erro instanceof Response && [401,403].includes(erro.status) ? mensagemErro(erro, this.sessao)
        : 'Não foi possível consultar as conexões. Você pode buscar sem filtros sociais.');
    } finally {
      if (revisao === this.revisao) {
        this.limparIndisponiveis();
        this.consultando.set(false);
      }
    }
  }

  async alterar(rede: Rede, remover: boolean) {
    if (this.alterando() || this.consultando()) return;
    this.alterando.set(true);
    this.erro.set('');
    try {
      const url = '/api/conexoes/' + rede;
      const resposta = await this.sessao.comCsrf(remover ? url : url + '/autorizar', remover ? 'DELETE' : 'POST');
      if (!resposta.ok) throw resposta;
      if (remover) await this.atualizar();
      else {
        const destino = new URL((await resposta.json()).url);
        if (destino.protocol !== 'https:') throw new Error();
        if (!this.vida.destroyed) location.assign(destino.href);
      }
    } catch (erro) {
      await this.atualizar();
      this.erro.set(erro instanceof Response && [401,403].includes(erro.status) ? mensagemErro(erro, this.sessao)
        : 'Não foi possível alterar a conexão de ' + this.nomes[rede] + '. Confira o estado e tente novamente.');
    } finally { this.alterando.set(false); }
  }
}
