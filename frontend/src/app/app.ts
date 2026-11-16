import { ChangeDetectionStrategy, Component, computed, HostListener, inject, signal } from '@angular/core';
import { Inicio } from './inicio/inicio';
import { FormularioConta } from './conta/formulario';
import { Sessao } from './conta/sessao';
import { NovaProspeccao } from './prospeccao/nova';
import { Buscas } from './prospeccao/buscas';
import { Relatorios } from './prospeccao/relatorios';

function rotaAtual() {
  switch (location.hash.slice(1)) {
    case 'cadastro': return 'cadastro';
    case 'senha':
    case 'entrar': return 'entrar';
    case 'leads':
    case 'buscas': return 'buscas';
    case 'buscas/vagas': return 'vagas';
    case 'nova-prospeccao': return 'nova-prospeccao';
    case 'relatorios': return 'relatorios';
    case 'conta': return 'conta';
    default: return 'inicio';
  }
}

@Component({
  selector: 'urwork-app', standalone: true, imports: [Inicio, FormularioConta, NovaProspeccao, Buscas, Relatorios],
  templateUrl: './app.html', changeDetection: ChangeDetectionStrategy.OnPush
})
export class App {
  sessao = inject(Sessao);
  rota = signal(rotaAtual());
  mensagem = signal('');
  saindo = signal(false);
  animar = true;
  pagina = computed(() => {
    const rota = this.rota();
    if (rota === 'inicio') return rota;
    const conta = this.sessao.conta();
    const privada = rota === 'conta' || rota === 'nova-prospeccao' || rota === 'buscas' || rota === 'vagas' || rota === 'relatorios';
    if (conta) return conta.perfilCompleto ? (privada ? rota : 'conta') : 'perfil';
    if (privada) return conta === undefined ? 'aguardar' : 'entrar';
    return rota;
  });

  ngOnInit() { void this.sessao.consultar(); }

  @HostListener('document:visibilitychange')
  visibilidade() { if (!document.hidden) void this.sessao.consultar(); }

  @HostListener('window:hashchange')
  navegar() {
    this.animar = false;
    this.rota.set(rotaAtual());
    this.mensagem.set('');
    window.scrollTo(0, 0);
    setTimeout(() => document.querySelector<HTMLElement>('h1')?.focus());
  }

  async sair() {
    if (this.saindo()) return;
    this.saindo.set(true);
    try {
      await this.sessao.sair();
      location.hash = 'inicio';
    } catch {
      this.mensagem.set('Não foi possível sair. Confira a conexão e tente novamente.');
    } finally { this.saindo.set(false); }
  }
}
