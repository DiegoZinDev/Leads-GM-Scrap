"""Fluxos Angular de vagas com anúncios e API controlados, após o build."""
from contextlib import ExitStack
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest import TestCase, main

from playwright.sync_api import expect, sync_playwright


class VagasWebTest(TestCase):
    def test_criterios_curriculo_e_ordem(self):
        dist = Path(__file__).resolve().parents[1] / "frontend/dist"
        with ExitStack() as stack:
            server = stack.enter_context(ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=dist)))
            Thread(target=server.serve_forever, daemon=True).start()
            stack.callback(server.shutdown)
            pw = stack.enter_context(sync_playwright())
            browser = pw.chromium.launch()
            stack.callback(browser.close)
            p = browser.new_page(viewport={"width": 390, "height": 844})
            pedidos, curriculos = [], []
            historico = [dict(id=7, tipo="LEADS", nicho="Oficinas", regiao="Campinas - SP", meta=3, total=2, estado="CONCLUIDA")]
            def anuncio(i, cargo, salario):
                return dict(execucao=8, coletadoEm="2026-11-15T12:00:00Z", dados=dict(idFonte=str(i), fonte="Lever",
                    cargo=cargo, empresa="CI&T", localidade="Toronto", pais="CA", modalidade="REMOTO", publicadaEm=None,
                    salario=salario, urlOrigem=f"https://jobs.lever.co/ciandt/{i}", urlCandidatura=f"https://jobs.lever.co/ciandt/{i}/apply"))
            a = anuncio(1, "Com faixa", dict(min=0, max=None, moeda="CAD", periodo="HORA"))
            b = anuncio(2, "Sem faixa", None)
            c = anuncio(3, "Com teto", dict(min=None, max=50, moeda="CAD", periodo="HORA"))
            def api(r):
                url = r.request.url.split("/api/")[1]
                if url == "auth/sessao":
                    r.fulfill(json=dict(username="Ana", email="teste@example.com", perfilCompleto=True))
                elif url == "conexoes": r.fulfill(json=[])
                elif url == "auth/csrf": r.fulfill(json=dict(headerName="X-CSRF-TOKEN", token="teste"))
                elif url == "vagas/curriculo":
                    assert r.request.headers["x-csrf-token"] == "teste" and "multipart/form-data" in r.request.headers["content-type"]
                    curriculos.append(url)
                    r.fulfill(json=dict(habilidades=["Python", "SQL"]))
                elif url == "prospeccoes" and r.request.method == "POST":
                    pedido = r.request.post_data_json
                    pedidos.append(pedido)
                    e = dict(**pedido, id=7+len(pedidos), total=1, estado="CONCLUIDA", estadoPdf="SEM_PDF")
                    historico.insert(0,e)
                    r.fulfill(status=202,json=e)
                elif url == "prospeccoes": r.fulfill(json=historico)
                elif url == "vagas": r.fulfill(json=[b,c,a])
                elif url == "vagas?execucao=8": r.fulfill(json=[a,b,c])
                elif url == "leads": r.fulfill(json=[])
                else: raise AssertionError(url)

            p.route("**/api/**",api)
            p.goto(f"http://127.0.0.1:{server.server_port}/#nova-prospeccao")
            p.get_by_role("radio",name="Vagas").check()
            p.get_by_label("Meta de vagas",exact=True).fill("3")
            gerar = p.get_by_role("button",name="Gerar prospecção")
            def gerar_vagas():
                with p.expect_response(lambda r: r.request.method=="POST" and r.url.endswith("/api/prospeccoes")):
                    gerar.click()
            gerar_vagas()
            assert pedidos[-1]["vagas"] == {} and not curriculos and "regiao" not in pedidos[-1]
            p.locator('[name="modalidade"]').select_option("REMOTO")
            p.locator('[name="pais"]').fill("ca")
            p.locator('[name="exterior"]').select_option("true")
            p.locator('[name="experienciaAnos"]').fill("3")
            expect(p.locator('[name="nivel"]')).to_have_value("PLENO")
            p.locator('[name="nivel"]').select_option("SENIOR")
            p.locator('[type="file"]').set_input_files({"name":"curriculo.docx","mimeType":"application/octet-stream","buffer":b"simulado"})
            habilidades = p.get_by_label("Habilidades para priorizar", exact=False)
            expect(habilidades).to_have_value("Python, SQL")
            habilidades.fill("SQL, Angular")
            p.get_by_label("Salário mínimo").fill("0")
            p.locator('[name="moeda"]').fill("cad")
            p.locator('[name="periodo"]').select_option("HORA")
            gerar_vagas()
            assert pedidos[-1]["vagas"] == dict(modalidade="REMOTO", pais="CA", exterior=True,
                experienciaAnos=3,nivel="SENIOR", habilidades=["SQL","Angular"], salarioMin=0,moeda="CAD",periodo="HORA")
            assert len(curriculos) == 1
            p.get_by_role("link",name="Ver vagas em Buscas").click()
            expect(p.locator("article h3")).to_have_text(["Sem faixa","Com teto","Com faixa"])
            expect(p.get_by_text("Salário não informado",exact=True)).to_be_visible()
            expect(p.get_by_text("A partir de 0 CAD por hora")).to_be_visible()
            expect(p.get_by_text("Até 50 CAD por hora")).to_be_visible()
            expect(p.get_by_text("Data de publicação não informada")).to_have_count(3)
            p.get_by_label("Filtrar por execução").select_option("8")
            expect(p.locator("article h3")).to_have_text(["Com faixa","Sem faixa","Com teto"])
            expect(p.get_by_role("link",name="Candidatar-se").first).to_have_attribute("href",a["dados"]["urlCandidatura"])
            assert p.evaluate("document.documentElement.scrollWidth<=innerWidth")
            p.get_by_role("link",name="Buscas",exact=True).click()
            expect(p.get_by_text("Nenhum lead coletado")).to_be_visible()


if __name__ == "__main__":
    main()
