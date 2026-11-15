import { Component, inject, input } from '@angular/core';
import { DomSanitizer } from '@angular/platform-browser';
import { drawMap, mapRibbons } from './map';

@Component({
  selector: 'urwork-inicio',
  standalone: true,
  templateUrl: './inicio.html',
  host: { 'data-page': 'inicio', style: 'display:block' }
})
export class Inicio {
  conectado = input(false);
  animar = input(true);
  private sanitizer = inject(DomSanitizer);
  map = this.sanitizer.bypassSecurityTrustHtml(drawMap());
  waves = this.sanitizer.bypassSecurityTrustHtml(mapRibbons());
  readonly headline = ['Encontre todo', 'o seu futuro,', 'em um só lugar'];
  readonly headlineText = this.headline.join(' ');
  readonly headlineWords = this.headline.map(line => line.split(' '));
  readonly wordOffsets = this.headlineWords.flat().reduce<Record<string, number>>((offsets, word) => {
    offsets[word] = (' ' + this.headlineText + ' ').indexOf(' ' + word + ' ');
    return offsets;
  }, {});
}
