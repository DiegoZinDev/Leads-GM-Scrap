"""Teste do Angular após o build, com respostas HTTP e provedor de autorização controlados."""
from contextlib import ExitStack
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest import TestCase, main

from playwright.sync_api import expect, sync_playwright


class ConexoesWebTest(TestCase):
    def test_permissoes_conflitos_e_desvinculacao(self):
        dist = Path(__file__).resolve().parents[1] / "frontend/dist"
        with ExitStack() as stack:
            servidor = stack.enter_context(ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=dist)))
            Thread(target=servidor.serve_forever, daemon=True).start()
            stack.callback(servidor.shutdown)
            pw = stack.enter_context(sync_playwright())
            browser = pw.chromium.launch()
            stack.callback(browser.close)
            p = browser.new_page()
            inicio = f"http://127.0.0.1:{servidor.server_port}/#nova-prospeccao"
            ig = dict(rede="INSTAGRAM", estado="DESCONECTADA", capacidades=[])
            wa = dict(rede="WHATSAPP", estado="CONECTADA", capacidades=["WHATSAPP_LINK_PUBLICADO"])
            pedidos, consultas = [], []
            falha = [409, "EXPIRADA"]

            def api(rota):
                req = rota.request
                url = req.url.split("/api/")[1]
                if req.method in ["POST", "DELETE"]:
                    assert req.headers["x-csrf-token"] == "teste"
                if url == "auth/sessao":
                    rota.fulfill(json=dict(email="teste@example.com", username="Ana", perfilCompleto=True))
                elif url == "auth/csrf":
                    rota.fulfill(json=dict(headerName="X-CSRF-TOKEN", token="teste"))
                elif url == "conexoes":
                    consultas.append(url)
                    rota.fulfill(json=[ig, wa])
                elif url == "conexoes/INSTAGRAM/autorizar" and req.method == "POST":
                    rota.fulfill(json=dict(url="https://provedor.test/autorizar"))
                elif url == "conexoes/WHATSAPP" and req.method == "DELETE":
                    wa.update(estado="DESCONECTADA", capacidades=[])
                    rota.fulfill(status=204)
                elif url == "prospeccoes" and req.method == "POST":
                    pedidos.append(req.post_data_json)
                    status, motivo = falha
                    rota.fulfill(status=status, headers={"UrWork-Conexao-Social": motivo} if motivo else {})
                elif url == "prospeccoes":
                    rota.fulfill(json=[])
                elif url == "leads":
                    rota.fulfill(json=[dict(execucao=1, dados=dict(nome="Lote antigo")),
                        dict(execucao=2, dados=dict(nome="Lote atual", sinais_sociais=dict(
                            instagramVerificado=None, seguidores=0, whatsappLinkPublicado=False)))])
                else:
                    raise AssertionError(url)

            p.route("**/api/**", api)
            p.route("https://provedor.test/autorizar", lambda r: r.fulfill(content_type="text/html", body=f'<a href="{inicio}">Voltar</a>'))
            p.goto(inicio)
            p.get_by_role("button", name="Conectar Instagram", exact=True).click()
            expect(p).to_have_url("https://provedor.test/autorizar")
            ig.update(estado="CONECTADA", capacidades=["INSTAGRAM_VERIFICADO", "SEGUIDORES_MINIMOS"])
            p.get_by_role("link", name="Voltar").click()
            expect(p.get_by_text("Conectada", exact=True)).to_have_count(2)
            assert len(p.context.pages) == 1 and len(consultas) == 2

            instagram = p.get_by_label("Com perfil de Instagram identificado")
            seguidores = p.get_by_label("Mínimo de seguidores")
            whatsapp = p.get_by_label("Com link público de WhatsApp")
            instagram.check()
            seguidores.fill("0")
            whatsapp.check()
            p.get_by_label("Nicho", exact=True).fill("Oficinas")
            p.get_by_role("combobox").first.select_option("SP")
            p.get_by_role("combobox").nth(1).select_option("Campinas")
            p.get_by_label("Meta de leads", exact=True).fill("3")
            gerar = p.get_by_role("button", name="Gerar prospecção")
            gerar.click()
            expect(p.get_by_role("alert")).to_contain_text("estava expirada")
            assert len(consultas) == 3
            expect(instagram).to_be_checked()
            assert pedidos[-1]["filtrosSociais"] == dict(instagramVerificado=True, seguidoresMinimos=0, whatsappLinkPublicado=True)
            falha[:] = [409, None]
            gerar.click()
            expect(p.get_by_role("alert")).to_contain_text("outra coleta")
            assert pedidos[0] == pedidos[1] and len(consultas) == 3

            ig.update(estado="INDISPONIVEL", capacidades=[])
            falha[:] = [503, "INDISPONIVEL"]
            gerar.click()
            expect(p.get_by_role("alert")).to_contain_text("fonte social estava indisponível")
            expect(instagram).not_to_be_checked()
            expect(seguidores).to_have_value("")
            expect(seguidores).to_be_disabled()
            expect(whatsapp).to_be_checked()
            expect(p.get_by_text("Eles foram removidos", exact=False)).to_be_visible()
            ig.update(estado="EXPIRADA")
            p.get_by_role("button", name="Atualizar conexões").click()
            expect(p.get_by_role("button", name="Reconectar Instagram")).to_be_visible()
            ig.update(estado="CONECTADA", capacidades=["INSTAGRAM_VERIFICADO"])
            p.get_by_role("button", name="Atualizar conexões").click()
            expect(instagram).to_be_enabled()
            expect(seguidores).to_be_disabled()
            expect(instagram).not_to_be_checked()
            p.get_by_role("button", name="Desvincular WhatsApp").click()
            expect(whatsapp).to_be_disabled()
            expect(whatsapp).not_to_be_checked()
            with p.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/api/prospeccoes")):
                gerar.click()
            assert "filtrosSociais" not in pedidos[-1] and pedidos[-1]["chave"] != pedidos[0]["chave"]

            p.get_by_role("link", name="Buscas", exact=True).click()
            p.get_by_text("Sinais sociais").click()
            atual = p.get_by_role("article").filter(has_text="Lote atual")
            assert atual.locator("dd").all_text_contents() == ["Desconhecido", "0", "Não"]
            expect(p.get_by_role("article").filter(has_text="Lote antigo").locator("details")).to_have_count(0)


if __name__ == "__main__":
    main()
