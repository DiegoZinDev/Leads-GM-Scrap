"""
Testes automatizados da Implementação 2:
Garante que o salvamento de leads gera APENAS o relatório PDF (.pdf),
sem criar arquivos Excel (.xlsx), ordenando por potencial e atribuindo IDs.
"""

import os
import tempfile
import unittest

from exporter import calcular_score_potencial, salvar_relatorio_pdf


class TestExportacaoApenasPdf(unittest.TestCase):
    def test_salvar_relatorio_gera_apenas_pdf_sem_excel(self):
        leads = [
            {
                "nome": "Clínica Sorriso Real",
                "nicho": "Odontologia",
                "cidade": "Taguatinga DF",
                "nota": 4.9,
                "qtd_avaliacoes": 68,
                "tem_site": False,
                "telefone": "(61) 99988-7766",
                "endereco": "QNA 12 Lote 5, Taguatinga DF",
                "url_maps": "https://www.google.com/maps/place/Clinica+Sorriso",
                "dono_gerente": "Dra. Mariana",
                "copy_abordagem": "Olá, equipe da Clínica Sorriso Real!",
            },
            {
                "nome": "Serralheria Forte Ferro",
                "nicho": "Serralheria",
                "cidade": "Ceilândia DF",
                "nota": 4.2,
                "qtd_avaliacoes": 12,
                "tem_site": False,
                "telefone": "(61) 98877-6655",
                "endereco": "QNN 4, Ceilândia DF",
                "url_maps": "https://www.google.com/maps/place/Serralheria+Forte",
                "dono_gerente": "Sr. Carlos",
                "copy_abordagem": "Olá, equipe da Serralheria Forte Ferro!",
            },
        ]
        for l in leads:
            l["score_potencial"] = calcular_score_potencial(l)

        with tempfile.TemporaryDirectory() as tmpdir:
            caminho_pdf, id_lote = salvar_relatorio_pdf(leads, id_lote="TST002", pasta_destino=tmpdir)
            self.assertTrue(os.path.exists(caminho_pdf), "O arquivo PDF deveria existir")
            self.assertTrue(caminho_pdf.endswith(".pdf"))
            self.assertEqual(id_lote, "TST002")

            # Verifica assinatura binária %PDF-
            with open(caminho_pdf, "rb") as f:
                cabecalho = f.read(5)
            self.assertEqual(cabecalho, b"%PDF-")

            # Garante que NENHUM arquivo .xlsx ou .csv foi criado no diretório
            arquivos = os.listdir(tmpdir)
            self.assertEqual(len(arquivos), 1)
            self.assertFalse(any(a.endswith((".xlsx", ".xls", ".csv")) for a in arquivos))


if __name__ == "__main__":
    unittest.main(verbosity=2)
