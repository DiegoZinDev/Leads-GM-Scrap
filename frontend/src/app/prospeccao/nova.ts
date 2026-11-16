import { Component, DestroyRef, inject, signal, viewChild } from '@angular/core';
import { Sessao } from '../conta/sessao';
import { SelecionarLocais } from '../conta/selecionar-locais';
import { consultar, Execucao, mensagemErro } from './api';

@Component({ selector: 'urwork-nova', imports: [SelecionarLocais], templateUrl: './nova.html' })
export class NovaProspeccao {
  private sessao = inject(Sessao);
  private vida = inject(DestroyRef);
  private armazenamento = 'urwork:tentativa:' + this.sessao.conta()?.email;
  private fonte?: EventSource;
  private timer?: number;
  private seletor = viewChild.required(SelecionarLocais);
  criteriosRecuperados?: Execucao;
  gerarPdf = signal(false);
  tituloPdf = signal('');
  percentual = (total: number, meta: number) => Math.round(100 * total / meta);
  execucao = signal<Execucao | undefined>(undefined);
  erro = signal('');
  carregando = signal(true);
  pronto = signal(false);
  enviando = signal(false);
  reconectando = signal(false);

  ngOnInit() { void this.recuperar(); }

  ngOnDestroy() {
    this.fonte?.close();
    clearTimeout(this.timer);
  }

  async recuperar() {
    this.carregando.set(true);
    this.erro.set('');
    try {
      const lista = await consultar<Execucao[]>('/api/prospeccoes');
      const atual = lista.find(item => item.estado === 'EM_ANDAMENTO') ?? lista[0];
      if (this.vida.destroyed) return;
      if (atual?.estado === 'EM_ANDAMENTO') {
        this.criteriosRecuperados = atual;
        this.gerarPdf.set(!!atual.tituloPdf);
        this.tituloPdf.set(atual.tituloPdf ?? '');
        const separador = atual.regiao.lastIndexOf(' - ');
        if (separador >= 0) this.seletor().locais = [{
          cidade: atual.regiao.slice(0, separador), uf: atual.regiao.slice(separador + 3)
        }];
      }
      if (atual) this.acompanhar(atual);
      this.pronto.set(true);
    } catch (erro) { this.erro.set(mensagemErro(erro, this.sessao)); }
    finally { this.carregando.set(false); }
  }

  async gerar(evento: SubmitEvent) {
    evento.preventDefault();
    if (!this.pronto() || this.enviando() || this.execucao()?.estado === 'EM_ANDAMENTO') return;
    const campos = new FormData(evento.currentTarget as HTMLFormElement);
    const titulo = this.tituloPdf();
    if (this.gerarPdf() && (!titulo.trim() || titulo.length > 100 || /[<>:"/\\|?*\u0000-\u001f\u007f-\u009f]/u.test(titulo))) {
      this.erro.set('Use de 1 a 100 caracteres no título, sem caracteres de controle nem < > : " / \\ | ? *.');
      return;
    }
    const criterios = { nicho: String(campos.get('nicho')).trim(), regiao: String(campos.get('localidade')),
      meta: Number(campos.get('meta')), ...(this.gerarPdf() ? { tituloPdf: titulo.trim() } : {}) };
    if (!criterios.nicho || !criterios.regiao || !Number.isSafeInteger(criterios.meta) || criterios.meta < 1) {
      this.erro.set('Informe o nicho, a região e uma meta inteira maior que zero.');
      return;
    }
    this.enviando.set(true);
    this.erro.set('');
    try {
      const assinatura = JSON.stringify(criterios);
      const anterior = JSON.parse(sessionStorage.getItem(this.armazenamento) ?? 'null');
      const chave = anterior?.assinatura === assinatura ? anterior.chave : crypto.randomUUID();
      sessionStorage.setItem(this.armazenamento, JSON.stringify({ assinatura, chave }));
      const resposta = await this.sessao.post('/api/prospeccoes', JSON.stringify({ chave, ...criterios }), true);
      if (!resposta.ok) throw resposta;
      const atual: Execucao = await resposta.json();
      if (JSON.parse(sessionStorage.getItem(this.armazenamento) ?? 'null')?.chave === chave)
        sessionStorage.removeItem(this.armazenamento);
      this.acompanhar(atual);
    } catch (erro) { this.erro.set(mensagemErro(erro, this.sessao)); }
    finally { this.enviando.set(false); }
  }

  private acompanhar(atual: Execucao) {
    if (this.vida.destroyed) return;
    this.execucao.set(atual);
    this.fonte?.close();
    clearTimeout(this.timer);
    this.reconectando.set(false);
    const url = '/api/prospeccoes/' + atual.id;
    if (atual.estado !== 'EM_ANDAMENTO') {
      if (atual.estadoPdf === 'PENDENTE') this.timer = window.setTimeout(() => void this.retomar(url), 1500);
      return;
    }
    const fonte = this.fonte = new EventSource(url + '/eventos');
    fonte.addEventListener('estado', (evento: MessageEvent<string>) => {
      const estado: Execucao = JSON.parse(evento.data);
      this.execucao.set(estado);
      this.reconectando.set(false);
      if (estado.estado !== 'EM_ANDAMENTO') this.acompanhar(estado);
    });
    fonte.onerror = () => {
      this.reconectando.set(true);
      if (fonte.readyState === EventSource.CLOSED)
        this.timer = window.setTimeout(() => void this.retomar(url), 3000);
    };
  }

  private async retomar(url: string) {
    try {
      const atual = await consultar<Execucao>(url);
      if (this.execucao()?.id === atual.id) this.acompanhar(atual);
    } catch (erro) {
      if (this.vida.destroyed) return;
      if (erro instanceof Response && [401, 403, 404].includes(erro.status)) {
        this.erro.set(mensagemErro(erro, this.sessao));
        this.pronto.set(false);
        this.execucao.set(undefined);
        this.reconectando.set(false);
      } else this.timer = window.setTimeout(() => void this.retomar(url), 3000);
    }
  }
}
