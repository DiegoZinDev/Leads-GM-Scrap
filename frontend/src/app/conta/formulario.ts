import { Component, DestroyRef, inject, input, signal } from '@angular/core';
import { DomSanitizer } from '@angular/platform-browser';
import { drawMap } from '../inicio/map';
import { SelecionarLocais } from './selecionar-locais';
import { Sessao } from './sessao';

@Component({ selector: 'urwork-formulario', standalone: true, imports: [SelecionarLocais], templateUrl: './formulario.html' })
export class FormularioConta {
  modo = input.required<'entrar' | 'cadastro' | 'perfil'>();
  readonly dominios = ['gmail.com', 'outlook.com', 'outlook.com.br', 'hotmail.com', 'hotmail.com.br',
    'yahoo.com', 'yahoo.com.br', 'live.com', 'icloud.com', 'uol.com.br', 'bol.com.br', 'terra.com.br'];
  readonly regraSenha = String.raw`(?=.*\p{Lu})(?=.*[\p{P}\p{S}])(?=(?:[^0-9]*[0-9]){2}).*`;
  finalidade = signal('');
  pendente = signal(false);
  criada = signal(false);
  mensagem = signal('');
  mapa = inject(DomSanitizer).bypassSecurityTrustHtml(drawMap());
  private sessao = inject(Sessao);
  private componente = inject(DestroyRef);

  async enviar(event: SubmitEvent) {
    event.preventDefault();
    if (this.pendente()) return;
    const form = event.currentTarget as HTMLFormElement;
    const dados = new FormData(form);
    const email = String(dados.get('email') ?? '').trim();
    if (this.modo() === 'cadastro' && !this.dominios.includes(email.split('@').pop()!.toLowerCase())) {
      this.mensagem.set('Use um dos domínios de e-mail aceitos no cadastro.');
      form.querySelector<HTMLInputElement>('input[name=email]')?.focus();
      return;
    }
    const password = String(dados.get('password') ?? '');
    const modo = this.modo();
    this.pendente.set(true);
    this.mensagem.set('');
    try {
      let resposta: Response;
      if (modo === 'entrar') {
        resposta = await this.sessao.enviar('login', new URLSearchParams({ email, password }));
      } else {
        dados.delete('email');
        dados.delete('password');
        const username = String(dados.get('username') ?? '').trim();
        dados.delete('username');
        const locais = dados.getAll('localidade');
        if (locais.length) dados.set('localidade', locais.join('\n'));
        const perfil = Object.fromEntries(dados);
        const corpo = modo === 'cadastro' ? { username, email, password, perfil } : perfil;
        resposta = await this.sessao.enviar(modo, JSON.stringify(corpo), true);
      }
      if (!resposta.ok) {
        const erros: Record<number,string> = {
          400: 'Confira o CPF e os campos obrigatórios do perfil.',
          401: modo === 'entrar' ? 'E-mail ou senha incorretos.' : 'Sua sessão expirou. Entre novamente.',
          403: 'Sua sessão mudou. Tente novamente.',
          409: modo === 'cadastro' ? 'E-mail ou CPF já cadastrado.' : 'Não foi possível salvar o perfil. Confira o CPF.'
        };
        if (modo === 'perfil' && [401, 409].includes(resposta.status)) await this.sessao.consultar();
        this.mensagem.set(erros[resposta.status] ?? 'Serviço de contas indisponível.');
        return;
      }
      if (modo === 'cadastro') {
        form.reset();
        this.criada.set(true);
        setTimeout(() => document.querySelector<HTMLElement>('.formBox h1')?.focus());
      } else {
        const mesmaTela = !this.componente.destroyed;
        if (!await this.sessao.consultar()) throw new Error();
        if (mesmaTela && (location.hash === '#entrar' || location.hash === '#perfil')) location.hash = 'conta';
      }
    } catch {
      this.mensagem.set('Não foi possível confirmar a operação. Confira a conexão e tente novamente.');
    } finally { this.pendente.set(false); }
  }
}
