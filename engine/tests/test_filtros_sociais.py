import unittest

from engine.scraper import corresponde_filtros_sociais
from engine.verifier import parse_web_profile_info


class FiltrosSociaisTest(unittest.TestCase):
    def test_seguidores_ausentes_diferem_de_zero(self):
        user = {"username": "loja"}
        lead = {"status_instagram": "verificado"}
        for contagem, passa in [(None, False), (0, True), (12, True)]:
            user["edge_followed_by"] = {"count": contagem}
            lead["instagram"] = parse_web_profile_info({"data": {"user": user}}).to_dict()
            self.assertEqual(corresponde_filtros_sociais(lead, {"seguidoresMinimos": 0}), passa)
            self.assertEqual(lead["sinais_sociais"]["seguidores"], contagem)
        lead["status_instagram"] = "inacessivel"
        self.assertFalse(corresponde_filtros_sociais(lead, {"instagramVerificado": True}))
        self.assertIsNone(lead["sinais_sociais"]["instagramVerificado"])

    def test_whatsapp_exige_link_publicado_com_destino_valido(self):
        lead = {"whatsapp_confirmado": True, "link_whatsapp": "https://wa.me/5511998765432"}
        for url, passa in [("https://outro.test/?q=wa.me/5511998765432", False),
                           ("https://wa.me/mensagem5511998765432", False),
                           ("https://wa.me/5511998765432", True),
                           ("https://api.whatsapp.com/send?phone=5511998765432", True)]:
            lead["links_brutos_maps"] = [url]
            self.assertEqual(corresponde_filtros_sociais(lead, {"whatsappLinkPublicado": True}), passa)
            self.assertIs(lead["sinais_sociais"]["whatsappLinkPublicado"], True if passa else None)

    def test_lote_aplica_filtro_antes_de_contar_e_gravar_no_historico(self):
        from unittest.mock import patch
        from engine.prospeccao import coletar_lotes

        base = dict(telefone="", nota=5, qtd_avaliacoes=30, qtd_avaliacoes_escritas=12, score_potencial=80)
        sem_link = dict(base, nome="Sem evidência")
        com_link = dict(base, nome="Oficina", links_brutos_maps=["https://wa.me/5511998765432"])
        historico = {}
        with patch("engine.scraper.coletar_leads_brutos_regiao", return_value=[sem_link, com_link]), \
             patch("engine.scraper.executar_funil_sequencial") as funil:
            funil.return_value.leads_aprovados = [sem_link, com_link]
            lotes = list(coletar_lotes(None, {"Oficinas": {}}, ["Campinas"], 1, historico, object(),
                                       {"whatsappLinkPublicado": True}))
        self.assertEqual(lotes, [[com_link]])
        self.assertEqual(list(historico["nomes_cidade"].values()), [{"nome": "Oficina"}])
