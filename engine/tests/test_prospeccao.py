import unittest
from unittest.mock import patch

from engine.prospeccao import coletar_lotes


class ColetaPorLotesTest(unittest.TestCase):
    @patch("engine.prospeccao.buscar_leads_google_maps")
    def test_limita_pedido_ao_saldo(self, buscar):
        buscar.side_effect = lambda **params: list(range(params["limite_leads"]))
        for meta, pedidos in [(3, [3]), (36, [35, 1])]:
            with self.subTest(meta=meta):
                buscar.reset_mock()
                lotes = list(coletar_lotes(None, {"Teste": {}}, ["Campinas"], meta, {}, None))
                self.assertEqual(sum(map(len, lotes)), meta)
                self.assertEqual([c.kwargs["limite_leads"] for c in buscar.call_args_list], pedidos)

    @patch("engine.prospeccao.buscar_leads_google_maps")
    def test_encerra_ao_atingir_meta(self, buscar):
        lote = [{"nome": "Empresa A"}, {"nome": "Empresa B"}]
        buscar.return_value = lote
        historico = {}
        encontrados = list(coletar_lotes(None, {"Oficina": {}}, ["Cidade A", "Cidade B"], 2, historico, None))
        self.assertEqual(encontrados, [lote])
        buscar.assert_called_once()
        self.assertEqual(buscar.call_args.kwargs["cidade"], "Cidade A")
        self.assertEqual(buscar.call_args.kwargs["termo_busca"], "Oficina")
        self.assertIs(buscar.call_args.kwargs["historico"], historico)

    @patch("engine.prospeccao.buscar_leads_google_maps")
    def test_retorna_lote_parcial_quando_as_fontes_se_esgotam(self, buscar):
        lote = [{"nome": "Empresa A"}]
        buscar.side_effect = [[], lote, [], []]
        encontrados = list(coletar_lotes(None, {"Auto": {"termos": ["Oficina", "Peças"]}}, ["Cidade A"], 8, {}, None))
        self.assertEqual(encontrados, [lote])
        self.assertEqual([c.kwargs["termo_busca"] for c in buscar.call_args_list],
                         ["Oficina", "Peças", "Oficina", "Peças"])


if __name__ == "__main__":
    unittest.main()
