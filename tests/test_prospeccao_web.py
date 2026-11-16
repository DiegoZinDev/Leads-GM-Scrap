"""Após npm run build em frontend, execute com o Python do projeto."""
import json
from contextlib import ExitStack
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest import TestCase, main

from playwright.sync_api import expect, sync_playwright


class ProspeccaoWebTest(TestCase):
    def test_repeticao_eventos_e_resultados_parciais(self):
        dist = Path(__file__).resolve().parents[1] / "frontend/dist"
        with ExitStack() as stack:
            servidor = stack.enter_context(ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=dist)))
            Thread(target=servidor.serve_forever, daemon=True).start()
            stack.callback(servidor.shutdown)
            with sync_playwright() as playwright:
                navegador = playwright.chromium.launch()
                pagina = navegador.new_page(viewport={"width": 390, "height": 844})
                estado = dict(id=12, nicho="Oficinas", regiao="Campinas - SP", meta=3,
                              total=1, estado="EM_ANDAMENTO", criadaEm="2026-11-15T10:00:00Z")
                pedidos, filtros, conexoes = [], [], []

                def api(rota):
                    req = rota.request
                    url = req.url.split("/api/")[1]
                    if url == "auth/sessao":
                        rota.fulfill(json=dict(email="teste@example.com", username="Ana", perfilCompleto=True))
                    elif url == "auth/csrf":
                        rota.fulfill(json=dict(headerName="X-CSRF-TOKEN", token="token"))
                    elif req.method == "POST" and url == "prospeccoes":
                        pedidos.append(req.post_data_json)
                        assert req.headers["x-csrf-token"] == "token"
                        if len(pedidos) == 1:
                            rota.abort()
                        else:
                            rota.fulfill(status=200, json=estado)
                    elif url == "prospeccoes":
                        rota.fulfill(json=[estado] if len(pedidos) >= 2 else [])
                    elif url.startswith("leads"):
                        filtros.append(url)
                        rota.fulfill(json=[dict(execucao=12, dados=dict(nome="Oficina Central"))])
                    elif url.endswith("/eventos"):
                        conexoes.append(url)
                        rota.fulfill(content_type="text/event-stream",
                                     body="retry: 100\nevent: estado\ndata: " + json.dumps(estado) + "\n\n")
                    else:
                        raise AssertionError(url)

                pagina.route("**/api/**", api)
                pagina.goto(f"http://127.0.0.1:{servidor.server_port}/#nova-prospeccao")
                pagina.get_by_label("Nicho", exact=True).fill("Oficinas")
                pagina.get_by_role("combobox").first.select_option("SP")
                pagina.get_by_role("combobox").nth(1).select_option("Campinas")
                pagina.get_by_label("Meta de leads").fill("3")
                botao = pagina.get_by_role("button", name="Gerar prospecção")
                botao.evaluate("(el) => { el.click(); el.click(); }")
                expect(pagina.get_by_role("alert")).to_be_visible()
                assert len(pedidos) == 1
                botao.click()
                expect(botao).to_be_disabled()
                assert pedidos[0] == pedidos[1] and pedidos[1]["regiao"] == "Campinas - SP"
                pagina.reload()
                expect(pagina.get_by_text("1 de 3 qualificados")).to_be_visible()
                expect(pagina.get_by_role("combobox").nth(1)).to_have_value("Campinas")
                expect(botao).to_be_disabled()
                pagina.get_by_role("link", name="Buscas", exact=True).click()
                pagina.get_by_label("Filtrar por execução").select_option("12")
                expect(pagina.get_by_text("Telefone não informado")).to_be_visible()
                assert filtros[-1] == "leads?execucao=12"
                pagina.get_by_role("link", name="Nova prospecção").click()
                expect(botao).to_be_disabled()
                estado.update(estado="CONCLUIDA")
                expect(pagina.get_by_text("Fontes esgotadas", exact=False)).to_be_visible()
                expect(botao).to_be_enabled()
                assert len(conexoes) >= 2
                estado.update(estado="INTERROMPIDA")
                pagina.reload()
                expect(pagina.get_by_text("Coleta interrompida.", exact=False)).to_be_visible()
                for largura in [390, 1280]:
                    pagina.set_viewport_size({"width": largura, "height": 844})
                    assert pagina.evaluate("document.documentElement.scrollWidth <= innerWidth")
                navegador.close()


if __name__ == "__main__":
    main()
