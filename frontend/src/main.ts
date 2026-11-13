import 'zone.js';
import { Component, HostListener, ChangeDetectorRef } from '@angular/core';
import { bootstrapApplication, DomSanitizer } from '@angular/platform-browser';
import { inject } from '@angular/core';
import {drawMap, mapRibbons} from './map';

const companies = [
  {name:'Clínica Aurora',segment:'Saúde',region:'Bela Vista',score:96,reason:'Sem site próprio'},
  {name:'Studio Botânica',segment:'Beleza',region:'Consolação',score:91,reason:'Apenas redes sociais'},
  {name:'Café do Pátio',segment:'Alimentação',region:'Jardins',score:87,reason:'Sem site próprio'}
];
const pages = ['inicio','entrar','cadastro','senha','leads','buscas','relatorios'];
@Component({selector:'zin-app',standalone:true,templateUrl:"./app.html"})
class App {
  readonly headline = ['Encontre todos', 'os seus clientes,', 'em apenas um lugar'];
  readonly headlineText = this.headline.join(' ');
  readonly headlineWords = this.headline.map(line => line.split(' '));
  readonly wordOffsets = this.headlineWords.flat().reduce<Record<string, number>>((offsets, word) => {
    offsets[word] = this.headlineText.indexOf(word);
    return offsets;
  }, {});
  authStep: 'form' | 'code' | 'password' | 'done' = 'form';
  demoCode = '';
  expiresAt = 0;

  account: {username: string; email: string} | null = null;
  pending = false;
  private sessionRevision = 0;
  private readonly changes = inject(ChangeDetectorRef);

  ngOnInit() {
    void this.refreshSession();
  }

  private async refreshSession() {
    const revision = ++this.sessionRevision;
    const response = await fetch('/api/auth/sessao', {cache: 'no-store'}).catch(() => null);
    const profile = response?.ok ? await response.json().catch(() => null) : null;
    if (revision === this.sessionRevision) {
      this.account = profile;
      this.changes.markForCheck();
    }
    return profile;
  }

  private async postAccount(action: string, body?: BodyInit, contentType?: string) {
    const csrf = await fetch('/api/auth/csrf', {cache: 'no-store'});
    if (!csrf.ok) throw new Error('Serviço de contas indisponível.');
    const protection = await csrf.json();
    const headers = new Headers({[protection.headerName]: protection.token});
    if (contentType) headers.set('Content-Type', contentType);
    return fetch('/api/auth/' + action, {method: 'POST', headers, body});
  }

  async logout() {
    if (this.pending) return;
    this.pending = true;
    try {
      const res = await this.postAccount('logout');
      if (!res.ok) throw new Error();
      ++this.sessionRevision;
      this.account = null;
      location.hash = 'inicio';
    } catch {
      this.message = 'Não foi possível encerrar a sessão. Tente novamente.';
    } finally {
      this.pending = false;
      this.changes.markForCheck();
    }
  }

  private async submitAccount(form: HTMLFormElement) {
    if (this.pending) return;
    this.pending = true;
    this.message = '';
    const route = this.page;
    const values = new FormData(form);
    const email = String(values.get('email')).trim();
    const password = String(values.get('password'));
    try {
      const registering = route === 'cadastro';
      const res = registering
        ? await this.postAccount('cadastro', JSON.stringify({username: String(values.get('username')).trim(), email, password}), 'application/json')
        : await this.postAccount('login', new URLSearchParams({email, password}));
      if (res.ok && !registering && !await this.refreshSession()) throw new Error();
      if (!form.isConnected || this.page !== route) return;
      if (!res.ok) {
        const errors: Record<number,string> = {400:'Confira o nome, o e-mail e o tamanho da senha.', 401:'E-mail ou senha incorretos.', 403:'Sua sessão mudou. Tente novamente.', 409:'Esse nome de usuário ou e-mail já está em uso.'};
        this.message = errors[res.status] ?? 'Serviço de contas indisponível. Tente novamente.';
        return;
      }
      form.reset();
      if (registering) {
        this.authStep = 'done';
        this.focusStep();
      } else {
        location.hash = 'leads';
      }
    } catch {
      if (form.isConnected && this.page === route) this.message = 'Não foi possível confirmar a operação. Confira a conexão e tente entrar.';
    } finally {
      this.pending = false;
      this.changes.markForCheck();
    }
  }

  startCode() {
    this.demoCode = String(100000 + Math.floor(Math.random() * 900000));
    this.expiresAt = Date.now() + 300000;
    this.authStep = 'code';
    this.message = '';
    this.focusStep();
  }

  focusStep() {
    setTimeout(() => document.querySelector<HTMLElement>('.formBox h1')?.focus(), 0);
  }

  fillExample(form: HTMLFormElement) {
    for (const input of Array.from(form.querySelectorAll('input'))) {
      const examples: Record<string,string> = {username: 'Ana Silva', email: 'ana@example.com', password: 'Amostra-Zin-2026'};
      input.value = examples[input.name] ?? '';
    }
  }

  submitAuth(event: Event) {
    event.preventDefault();
    const form = event.target as HTMLFormElement;
    if (this.page !== 'senha') {
      void this.submitAccount(form);
      return;
    }
    if (this.authStep === 'form') {
      this.startCode();
      return;
    }
    if (this.authStep === 'code') {
      if (Date.now() >= this.expiresAt || new FormData(form).get('code') !== this.demoCode) {
        this.message = Date.now() >= this.expiresAt ? 'Código expirado. Gere outro para continuar.' : 'O código não confere. Verifique os seis dígitos.';
        form.querySelector('input')?.focus();
        return;
      }
      this.demoCode = '';
      this.authStep = 'password';
    } else {
      this.authStep = 'done';
    }
    form.reset();
    this.message = '';
    this.focusStep();
  }
  animateHeadline = true;
  waves = inject(DomSanitizer).bypassSecurityTrustHtml(mapRibbons());
  map = inject(DomSanitizer).bypassSecurityTrustHtml(drawMap());
  page=this.current(); companies=companies; query=''; selected=''; message=''; searchRegion=''; searchNiche=''; demoRun=false; light=this.readLightPreference();

  private readLightPreference(): boolean {
    try {
      return localStorage.getItem('zin-workspace-theme') === 'light';
    } catch {
      return false;
    }
  }

  toggleTheme() {
    this.light = !this.light;
    try {
      localStorage.setItem('zin-workspace-theme', this.light ? 'light' : 'dark');
    } catch {
      // A escolha continua válida nesta sessão quando o navegador bloqueia o armazenamento.
    }
  }

  get list(){ const term=this.query.trim().toLocaleLowerCase('pt-BR');return companies.filter(c=>[c.name,c.segment,c.region,c.reason].join(' ').toLocaleLowerCase('pt-BR').includes(term));}
  get workspace(){return ['leads','buscas','relatorios'].includes(this.page);}
  get login(){return ['entrar','cadastro','senha'].includes(this.page);}
  current(){const p=location.hash.slice(1);return pages.includes(p)?p:'inicio';}
  @HostListener('window:hashchange') navigate(){if(this.page==='inicio' && this.current()!=='inicio') this.animateHeadline=false;if(this.login) document.querySelector<HTMLFormElement>('.formBox form')?.reset();this.authStep="form";this.demoCode="";this.expiresAt=0;this.page=this.current();this.selected='';this.message='';window.scrollTo(0,0);setTimeout(()=>document.querySelector<HTMLElement>('h1')?.focus(),0);}
  text(e:Event){return (e.target as HTMLInputElement).value;}
  run(e:Event){e.preventDefault();this.demoRun=true;this.message='Simulação concluída. Nenhuma coleta externa foi iniciada.';}
  async copy(name:string){const msg=this.pitch(name);try{await navigator.clipboard.writeText(msg);this.message='Mensagem copiada.';}catch{this.message='Selecione o texto da mensagem para copiá-lo.';}}
  pitch(name:string){return 'Olá, equipe '+name+'! Encontrei a empresa no Google Maps. Com quem posso conversar sobre como os clientes encontram seus serviços pela internet?';}
}
bootstrapApplication(App).catch(console.error);

