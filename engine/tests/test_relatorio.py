import unittest
from engine.relatorio import documento


class RelatorioTest(unittest.TestCase):
    def test_conteudo_do_lote_e_textos_literais(self):
        pedido = dict(titulo="Saúde & TI", id=1, execucao=2, nicho="TI", regiao="Campinas - SP",
                      inicio="15/11/2026 10:00", geracao="15/11/2026 10:05", meta=5, leads=[])
        self.assertIn("Leads coletados: 0 de 5", documento(pedido))
        pedido["leads"] = [{"nome": "Clínica <A>"}, {"nome": "Empresa B"}]
        pagina = documento(pedido)
        for texto in ("Saúde &amp; TI", "Clínica &lt;A&gt;", "Empresa B", "Leads coletados: 2 de 5",
                      "15/11/2026 10:00", "15/11/2026 10:05"):
            self.assertIn(texto, pagina)
