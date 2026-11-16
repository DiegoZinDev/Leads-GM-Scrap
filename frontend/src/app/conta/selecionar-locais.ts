import { Component, input } from '@angular/core';
import estados from './localidades.json';

@Component({
  selector: 'urwork-locais', standalone: true, templateUrl: './selecionar-locais.html',
  host: { class: 'linha-inteira' }
})
export class SelecionarLocais {
  titulo = input.required<string>();
  unico = input(false);
  estados = estados;
  locais = [{ uf: '', cidade: '' }];

  cidades(uf: string) {
    return estados.find(estado => estado.uf === uf)?.cidades ?? [];
  }

  ocupada(uf: string, cidade: string, atual: number) {
    return this.locais.some((local, i) => i !== atual && local.uf === uf && local.cidade === cidade);
  }
}
