import { defineConfig } from 'vite';

export default defineConfig({preview: {proxy: {'/api': 'http://127.0.0.1:8090'}}});
