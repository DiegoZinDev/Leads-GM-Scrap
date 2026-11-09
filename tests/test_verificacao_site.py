"""
Testes unitários e de integração da Implementação 1:
Verificação de Presença Digital (Google Maps + Instagram Bio/Destaques + Agregadores + Web).
"""

import unittest
from unittest.mock import MagicMock

from links import (
    TipoLink,
    classificar_link,
    decodificar_redirect,
    extrair_dominios_de_email,
    extrair_dominios_de_texto,
    extrair_urls_de_html,
)
from instagram import (
    PerfilInstagram,
    extrair_username,
    parse_reels_media,
    parse_web_profile_info,
    pontuar_correspondencia,
)
from verifier import (
    RespostaHttp,
    ResultadoPresencaDigital,
    StatusSite,
    VerificadorPresencaDigital,
    avaliar_site,
    pagina_pertence_ao_negocio,
)


class TestClassificadorLinks(unittest.TestCase):
    def test_whatsapp_nunca_eh_site(self):
        urls_whatsapp = [
            "https://wa.me/5561999999999",
            "https://wa.me/5561984742591?rwg_token=ALcMQY",
            "http://api.whatsapp.com/send?phone=5561999999999",
            "https://web.whatsapp.com/send/?phone=5561999999999",
            "https://chat.whatsapp.com/InviteCode123",
            "https://wa.link/abc123",
            "https://l.instagram.com/?u=https%3A%2F%2Fwa.me%2F5561999999999&e=AT1",
        ]
        for u in urls_whatsapp:
            cls = classificar_link(u)
            self.assertEqual(cls.tipo, TipoLink.MENSAGEIRO, f"Falhou para {u}: {cls}")
            self.assertFalse(cls.desqualifica, f"WhatsApp não pode desqualificar: {u}")

    def test_redes_sociais_nunca_sao_site(self):
        urls_sociais = [
            "https://instagram.com/barbearia_nacional?igshid=YmMyMTA2M2Y=",
            "https://www.instagram.com/studio.unhas/",
            "https://www.facebook.com/minhaempresa",
            "https://fb.watch/xyz/",
            "https://www.tiktok.com/@minhaempresa",
            "https://www.youtube.com/@canal",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://x.com/perfil",
            "https://twitter.com/perfil",
            "https://www.linkedin.com/company/empresa",
            "https://www.threads.net/@perfil",
            "https://br.pinterest.com/perfil/",
            "https://l.instagram.com/?u=https%3A%2F%2Fwww.tiktok.com%2F%40perfil",
        ]
        for u in urls_sociais:
            cls = classificar_link(u)
            self.assertEqual(cls.tipo, TipoLink.REDE_SOCIAL, f"Falhou para {u}: {cls}")
            self.assertFalse(cls.desqualifica, f"Rede social não pode desqualificar: {u}")

    def test_sem_falso_positivo_substring_host(self):
        """Domínios terminados em 'x.com' no meio do nome (ex: linx.com.br, netflix.com) são sites próprios, não Twitter/X."""
        for u in ["https://www.linx.com.br", "https://clinicafenix.com.br", "https://studiomax.com"]:
            cls = classificar_link(u)
            self.assertEqual(cls.tipo, TipoLink.SITE_PROPRIO, f"Host {u} foi confundido com rede social: {cls}")
            self.assertTrue(cls.desqualifica)

    def test_sistemas_e_construtores_desqualificam(self):
        sistemas = [
            "https://sites.appbarber.com.br/barbeariaogean-cobk?source=google_reserve",
            "https://www.trinks.com/salao-x",
            "https://pedido.anota.ai/loja/restaurante-x",
            "https:// restaurante.goomer.app",
            "https://calendly.com/dr-joao/consulta",
            "https://booksy.com/pt-br/12345_barbearia",
        ]
        for u in sistemas:
            cls = classificar_link(u.strip())
            self.assertEqual(cls.tipo, TipoLink.SISTEMA, f"Esperava SISTEMA para {u}: {cls}")
            self.assertTrue(cls.desqualifica)

        construtores = [
            "https://meu-salao.my.canva.site/",
            "https://clinica.wixsite.com/home",
            "https://sites.google.com/view/escritorio-silva",
            "https://estudio.carrd.co",
        ]
        for u in construtores:
            cls = classificar_link(u)
            self.assertEqual(cls.tipo, TipoLink.CONSTRUTOR, f"Esperava CONSTRUTOR para {u}: {cls}")
            self.assertTrue(cls.desqualifica)

    def test_agregadores_e_encurtadores_exigem_expansao(self):
        for u in ["https://linktr.ee/estudiox", "https://beacons.ai/clinica", "https://taplink.cc/salao", "https://bio.link/adv"]:
            cls = classificar_link(u)
            self.assertEqual(cls.tipo, TipoLink.AGREGADOR)
            self.assertFalse(cls.desqualifica)
            self.assertTrue(cls.precisa_expandir)

        for u in ["https://bit.ly/3xyz", "https://tinyurl.com/abc", "https://cutt.ly/123"]:
            cls = classificar_link(u)
            self.assertEqual(cls.tipo, TipoLink.ENCURTADOR)
            self.assertTrue(cls.precisa_expandir)

    def test_extracao_dominios_texto_ignora_emails_e_notas(self):
        bio = (
            " Atendimento seg a sex 9h-18h | Nota 4.9 no Google!\n"
            " Contato: atendimento@gmail.com | suporte@outlook.com\n"
            " Acesse nosso portal: www.escritoriosilva.adv.br ou clinicaodonto.com.br/agendar"
        )
        dominios = extrair_dominios_de_texto(bio)
        self.assertIn("www.escritoriosilva.adv.br", dominios)
        self.assertIn("clinicaodonto.com.br/agendar", dominios)
        self.assertNotIn("gmail.com", dominios)
        self.assertNotIn("outlook.com", dominios)

    def test_extracao_dominio_email_corporativo(self):
        texto = "E-mails: comercial@gmail.com, contato@advocaciasilva.com.br, sac@hotmail.com"
        doms = extrair_dominios_de_email(texto)
        self.assertEqual(doms, ["advocaciasilva.com.br"])


class TestInstagramParsing(unittest.TestCase):
    def test_extrair_username(self):
        self.assertEqual(extrair_username("https://www.instagram.com/Barbearia_Nacional/?igshid=123"), "barbearia_nacional")
        self.assertEqual(extrair_username("https://instagram.com/stories/studio.nail/12345"), "studio.nail")
        self.assertEqual(extrair_username("https://www.instagram.com/p/C12345/"), "")
        self.assertEqual(extrair_username("https://www.instagram.com/reel/C12345/"), "")
        self.assertEqual(extrair_username("https://wa.me/5561999999999"), "")

    def test_parse_web_profile_info_e_destaques(self):
        payload_perfil = {
            "data": {
                "user": {
                    "id": "999",
                    "username": "estudio_bela",
                    "full_name": "Estúdio Bela Unhas",
                    "biography": "Alongamento em gel Taguatinga DF\nAgende pelo link abaixo",
                    "external_url": "https://l.instagram.com/?u=https%3A%2F%2Fwa.me%2F5561999887766",
                    "bio_links": [
                        {"url": "https://wa.me/5561999887766"},
                        {"url": "https://www.instagram.com/estudio_bela"},
                    ],
                    "business_phone_number": "+5561999887766",
                    "business_email": "contato@gmail.com",
                    "is_business_account": True,
                    "highlight_reel_count": 2,
                    "edge_followed_by": {"count": 1850},
                }
            }
        }
        perfil = parse_web_profile_info(payload_perfil)
        self.assertTrue(perfil.acessivel)
        self.assertEqual(perfil.username, "estudio_bela")
        self.assertEqual(perfil.qtd_destaques, 2)
        self.assertIn("https://wa.me/5561999887766", perfil.links_bio)

        # Destaques: um story com link de WhatsApp e outro com site de agendamento
        payload_reels = {
            "reels": {
                "highlight:111": {
                    "items": [
                        {"story_link_stickers": [{"story_link": {"url": "https://l.instagram.com/?u=https%3A%2F%2Fwa.me%2F5561999887766"}}]}
                    ]
                },
                "highlight:222": {
                    "items": [
                        {"story_cta": [{"links": [{"webUri": "https://estudiobela.trinks.com"}]}]}
                    ]
                },
            }
        }
        links_dest = parse_reels_media(payload_reels)
        self.assertIn("https://wa.me/5561999887766", links_dest)
        self.assertIn("https://estudiobela.trinks.com", links_dest)

        pontos, _ = pontuar_correspondencia(perfil, "Estúdio Bela Unhas", "(61) 99988-7766", "Taguatinga DF")
        self.assertGreaterEqual(pontos, 90)


class TestVerificadorFluxosCompletos(unittest.TestCase):
    def _criar_verificador(self, respostas_http: dict[str, RespostaHttp], perfil_ig: PerfilInstagram | None = None):
        ctx = MagicMock()
        verificador = VerificadorPresencaDigital(ctx, config={"busca_web": False, "adivinhar_dominios": False})
        verificador.http.get = lambda url, max_redirects=8: respostas_http.get(
            url, RespostaHttp(status=200, url=url, texto="<html><title>Site Oficial</title><body>Conteúdo completo do site institucional com mais de quarenta caracteres.</body></html>")
        )
        if perfil_ig is not None:
            verificador.instagram.disponivel = True
            verificador.instagram.obter_perfil = lambda u, com_destaques=True: perfil_ig
        return verificador

    def test_lead_com_wame_e_instagram_eh_aprovado(self):
        """Lead com wa.me na bio e nos destaques + Linktree contendo apenas WhatsApp e Instagram NÃO tem site."""
        html_linktree = """
        <html><body>
            <a href="https://wa.me/5561988887777">Fale no WhatsApp</a>
            <a href="https://instagram.com/barbearia_imperial">Siga no Instagram</a>
            <a href="https://www.tiktok.com/@barbearia_imperial">TikTok</a>
        </body></html>
        """
        perfil = PerfilInstagram(
            username="barbearia_imperial",
            acessivel=True,
            biografia="Cortes masculinos em Taguatinga | WhatsApp (61) 98888-7777",
            links_bio=["https://linktr.ee/barbearia_imperial"],
            qtd_destaques=1,
            destaques_verificados=True,
            links_destaques=["https://wa.me/5561988887777"],
        )
        verificador = self._criar_verificador({"https://linktr.ee/barbearia_imperial": RespostaHttp(200, "https://linktr.ee/barbearia_imperial", html_linktree)}, perfil)

        res = ResultadoPresencaDigital(url_instagram="https://instagram.com/barbearia_imperial")
        verificador. avaliar_url("https://wa.me/5561988887777", "Google Maps (Reserva)", res, {})
        verificador.analisar_instagram(res, {"nome": "Barbearia Imperial", "telefone": "61988887777", "cidade": "Taguatinga DF"})

        self.assertFalse(res.tem_site, f"Não deveria ter site, mas acusou: {res.evidencias}")
        self.assertEqual(res.status_instagram, "verificado")

    def test_lead_com_site_no_destaque_do_instagram_eh_reprovado(self):
        """Mesmo que a bio só tenha wa.me, se nos destaques houver link de site/sistema, deve reprovar."""
        perfil = PerfilInstagram(
            username="clinica_sorriso",
            acessivel=True,
            biografia="Odontologia humanizada",
            links_bio=["https://wa.me/5561977776666"],
            qtd_destaques=2,
            destaques_verificados=True,
            links_destaques=["https://wa.me/5561977776666", "https://clinicasorriso.com.br/agendamento"],
        )
        verificador = self._criar_verificador({}, perfil)
        res = ResultadoPresencaDigital(url_instagram="https://instagram.com/clinica_sorriso")
        verificador.analisar_instagram(res, {"nome": "Clínica Sorriso", "telefone": "61977776666", "cidade": "Brasília DF"})

        self.assertTrue(res.tem_site)
        self.assertIn("Instagram (destaques)", res.motivo)
        self.assertIn("clinicasorriso.com.br", res.motivo)

    def test_lead_com_site_dentro_do_linktree_eh_reprovado(self):
        html_linktree = """
        <html><body>
            <a href="https://wa.me/5561988887777">WhatsApp</a>
            <a href="https://meusalao.canva.site/catalogo">Catálogo e Preços</a>
        </body></html>
        """
        perfil = PerfilInstagram(
            username="salao_luxo",
            acessivel=True,
            links_bio=["https://linktr.ee/salao_luxo"],
            qtd_destaques=0,
            destaques_verificados=True,
        )
        verificador = self._criar_verificador({"https://linktr.ee/salao_luxo": RespostaHttp(200, "https://linktr.ee/salao_luxo", html_linktree)}, perfil)
        res = ResultadoPresencaDigital(url_instagram="https://instagram.com/salao_luxo")
        verificador.analisar_instagram(res, {"nome": "Salão Luxo", "telefone": "61988887777", "cidade": "Águas Claras DF"})

        self.assertTrue(res.tem_site)
        self.assertIn("linktr.ee", res.motivo)
        self.assertIn("canva.site", res.motivo)

    def test_dominio_inativo_ou_a_venda_nao_reprova(self):
        """Se o cliente tem um domínio que caiu (404 / à venda), ele NÃO tem site ativo -> é uma oportunidade quente!"""
        html_parked = "<html><body>This domain is for sale at SedoParking</body></html>"
        verificador = self._criar_verificador({"https://advocaciaantiga.com.br": RespostaHttp(200, "https://advocaciaantiga.com.br", html_parked)})
        res = ResultadoPresencaDigital()
        verificador.avaliar_url("https://advocaciaantiga.com.br", "Google Maps (Website)", res, {})

        self.assertFalse(res.tem_site)
        self.assertTrue(any("oportunidade quente" in o for o in res.observacoes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
