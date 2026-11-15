import { Injectable, signal } from '@angular/core';

export interface Conta {
  username: string;
  email: string;
  perfilCompleto: boolean;
}

@Injectable({ providedIn: 'root' })
export class Sessao {
  conta = signal<Conta | null | undefined>(undefined);
  indisponivel = signal(false);
  private revisao = 0;

  async consultar() {
    const revisao = ++this.revisao;
    try {
      const res = await fetch('/api/auth/sessao', { cache: 'no-store' });
      if (!res.ok && res.status !== 401) throw new Error();
      const conta: Conta | null = res.ok ? await res.json() : null;
      if (revisao === this.revisao) {
        this.conta.set(conta);
        this.indisponivel.set(false);
      }
      return conta;
    } catch {
      if (revisao === this.revisao) this.indisponivel.set(true);
      return undefined;
    }
  }

  async enviar(acao: string, corpo?: BodyInit, json = false) {
    const csrf = await fetch('/api/auth/csrf', { cache: 'no-store' });
    if (!csrf.ok) throw new Error();
    const { headerName, token } = await csrf.json();
    const headers = new Headers({ [headerName]: token });
    if (json) headers.set('Content-Type', 'application/json');
    return fetch('/api/auth/' + acao, { method: 'POST', headers, body: corpo });
  }

  async sair() {
    const res = await this.enviar('logout');
    if (!res.ok) throw new Error();
    ++this.revisao;
    this.indisponivel.set(false);
    this.conta.set(null);
  }
}
