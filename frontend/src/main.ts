import 'zone.js';
import '@angular/compiler';
import { Component, HostListener } from '@angular/core';
import { bootstrapApplication, DomSanitizer } from '@angular/platform-browser';
import { inject } from '@angular/core';
import '@fontsource-variable/space-grotesk/index.css';
import '@fontsource-variable/dm-sans/index.css';
import './style.css';
import {drawMap} from './map';
import template from './app.html?raw';

const companies = [
  {name:'Clínica Aurora',segment:'Saúde',region:'Bela Vista',score:96,reason:'Sem site próprio'},
  {name:'Studio Botânica',segment:'Beleza',region:'Consolação',score:91,reason:'Apenas redes sociais'},
  {name:'Café do Pátio',segment:'Alimentação',region:'Jardins',score:87,reason:'Sem site próprio'}
];
const pages = ['inicio','entrar','cadastro','senha','leads','buscas','relatorios'];
@Component({selector:'zin-app',standalone:true,template})
class App {
  map = inject(DomSanitizer).bypassSecurityTrustHtml(drawMap());
  page=this.current(); companies=companies; query=''; selected=''; message=''; searchRegion=''; searchNiche=''; demoRun=false; light=false;
  get list(){ const term=this.query.trim().toLocaleLowerCase('pt-BR');return companies.filter(c=>[c.name,c.segment,c.region,c.reason].join(' ').toLocaleLowerCase('pt-BR').includes(term));}
  get workspace(){return ['leads','buscas','relatorios'].includes(this.page);}
  get login(){return ['entrar','cadastro','senha'].includes(this.page);}
  current(){const p=location.hash.slice(1);return pages.includes(p)?p:'inicio';}
  @HostListener('window:hashchange') navigate(){if(this.login) document.querySelector<HTMLFormElement>('.formBox form')?.reset();this.page=this.current();this.selected='';this.message='';window.scrollTo(0,0);setTimeout(()=>document.querySelector<HTMLElement>('h1')?.focus(),0);}
  text(e:Event){return (e.target as HTMLInputElement).value;}
  auth(e:Event){e.preventDefault();this.message='Esta versão de demonstração não está conectada ao serviço de contas. Você pode explorar a fila de empresas em “Abrir demonstração”.';}
  run(e:Event){e.preventDefault();this.demoRun=true;this.message='Simulação concluída. Nenhuma coleta externa foi iniciada.';}
  async copy(name:string){const msg=this.pitch(name);try{await navigator.clipboard.writeText(msg);this.message='Mensagem copiada.';}catch{this.message='Selecione o texto da mensagem para copiá-lo.';}}
  pitch(name:string){return 'Olá, equipe '+name+'! Encontrei a empresa no Google Maps. Com quem posso conversar sobre como os clientes encontram seus serviços pela internet?';}
}
bootstrapApplication(App).catch(console.error);

