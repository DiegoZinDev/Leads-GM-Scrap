import { Component, DestroyRef, inject, input, signal } from '@angular/core';
import { Sessao } from '../conta/sessao';
import { CriteriosVagas, mensagemErro } from './api';

export const rotulos: Record<string, string> = {
  REMOTO: 'Remoto', HIBRIDO: 'Híbrido', PRESENCIAL: 'Presencial', INTEGRAL: 'Integral', PARCIAL: 'Parcial',
  CLT: 'CLT', PJ: 'PJ', ESTAGIO: 'Estágio', TEMPORARIO: 'Temporário', JUNIOR: 'Júnior', PLENO: 'Pleno',
  SENIOR: 'Sênior', ESPECIALISTA: 'Especialista', MANHA: 'Manhã', TARDE: 'Tarde', NOITE: 'Noite',
  ANO: 'Ano', MES: 'Mês', HORA: 'Hora'
};

@Component({ selector: 'urwork-form-vagas', templateUrl: './form-vagas.html' })
export class FormVagas {
  inicial = input<CriteriosVagas>();
  private sessao = inject(Sessao);
  private vida = inject(DestroyRef);
  enviando = signal(false);
  aviso = signal('');
  habilidades = signal('');
  nivel = signal('');
  comSalario = signal(false);
  rotulos = rotulos;
  grupos = [
    { campo: 'modalidade', nome: 'Modalidade', opcoes: ['REMOTO', 'HIBRIDO', 'PRESENCIAL'] },
    { campo: 'jornada', nome: 'Jornada', opcoes: ['INTEGRAL', 'PARCIAL'] },
    { campo: 'vinculo', nome: 'Vínculo', opcoes: ['CLT', 'PJ', 'ESTAGIO', 'TEMPORARIO'] },
    { campo: 'turno', nome: 'Turno', opcoes: ['MANHA', 'TARDE', 'NOITE'] }
  ] as const;

  ngOnInit() {
    const anterior = this.inicial();
    this.habilidades.set(anterior?.habilidades?.join(', ') ?? '');
    this.nivel.set(anterior?.nivel ?? '');
    this.comSalario.set(anterior?.salarioMin != null || anterior?.salarioMax != null);
  }

  sugerirNivel(anos: string) {
    this.nivel.set(anos === '' ? '' : Number(anos) < 2 ? 'JUNIOR' : Number(anos) < 5 ? 'PLENO' : 'SENIOR');
  }

  async lerArquivo(campo: HTMLInputElement) {
    const arquivo = campo.files?.[0];
    if (!arquivo) return;
    campo.value = '';
    if (!/\.(pdf|docx)$/i.test(arquivo.name) || arquivo.size > 1024 * 1024 || !arquivo.size) {
      this.aviso.set('Escolha um PDF ou DOCX de até 1 MiB com conteúdo.');
      return;
    }
    this.enviando.set(true);
    this.aviso.set('Lendo o currículo…');
    try {
      const corpo = new FormData();
      corpo.append('arquivo', arquivo);
      const res = await this.sessao.comCsrf('/api/vagas/curriculo', 'POST', corpo);
      if (!res.ok) throw res;
      const { habilidades }: { habilidades: string[] } = await res.json();
      if (this.vida.destroyed) return;
      const atuais = this.listaHabilidades();
      this.habilidades.set([...new Set([...atuais, ...habilidades])].join(', '));
      this.aviso.set(habilidades.length ? 'Revise as habilidades sugeridas antes de iniciar.' : 'Nenhuma habilidade sugerida. Você pode preencher o campo abaixo.');
    } catch (erro) {
      this.aviso.set(erro instanceof Response && [401,403].includes(erro.status) ? mensagemErro(erro, this.sessao)
        : 'Não foi possível ler o currículo. Você pode preencher as habilidades ou prosseguir sem o arquivo.');
    } finally { this.enviando.set(false); }
  }

  private listaHabilidades() {
    const habilidades = this.habilidades().split(',').map(h => h.trim()).filter(Boolean);
    return [...new Map(habilidades.map(h => [h.toLowerCase(), h])).values()];
  }

  criterios(campos: FormData): CriteriosVagas {
    const vagas: CriteriosVagas = {};
    for (const campo of ['cargo','pais','modalidade','jornada','vinculo','nivel','turno','escolaridade','moeda','periodo'] as const) {
      const valor = String(campos.get(campo) ?? '').trim();
      if (valor) vagas[campo] = campo === 'pais' || campo === 'moeda' ? valor.toUpperCase() : valor;
    }
    for (const campo of ['experienciaAnos','salarioMin','salarioMax'] as const) {
      const valor = campos.get(campo);
      if (valor != null && valor !== '') vagas[campo] = Number(valor);
    }
    const exterior = campos.get('exterior');
    if (exterior) vagas.exterior = exterior === 'true';
    const habilidades = this.listaHabilidades();
    if (habilidades.length) vagas.habilidades = habilidades;
    return vagas;
  }
}
