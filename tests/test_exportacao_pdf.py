"""
Testes automatizados das Implementações 2 e 3:
- Salvamento exclusivo em PDF (.pdf), sem criar arquivos Excel (.xlsx)
- Layout editorial suave (A4 Paisagem, Visão Geral em Tabela + Fichas Detalhadas de Abordagem)
"""

import os
import tempfile
import unittest

from exporter import (
    calcular_score_potencial,
    formatar_telefone_exibicao,
    montar_html_relatorio,
    salvar_relatorio_pdf,
)


class TestExportacaoEEstiloPdf(unittest.TestCase):
    def _leads_exemplo(self) -> list[dict]:
        leads = [
            {
                "nome": "Clínica Sorriso Real",
                "nicho": "Odontologia",
                "cidade": "Taguatinga DF",
                "nota": 4.9,
                "qtd_avaliacoes": 68,
                "tem_site": False,
                "telefone": "061999887766",
                "endereco": "QNA 12 Lote 5, Taguatinga Norte, Brasília - DF",
                "url_maps": "https://www.google.com/maps/place/Clinica+Sorriso",
                "url_instagram": "https://www.instagram.com/clinicasorrisoreal/",
                "dono_gerente": "Dra. Mariana Alves",
                "observacoes": ["Instagram verificado sem site na bio ou destaques"],
                "copy_abordagem": "Olá, equipe da Clínica Sorriso Real! Vi que a nota de vocês é ótima no Google...",
            },
            {
                "nome": "Serralheria Forte Ferro",
                "nicho": "Serralheria",
                "cidade": "Ceilândia DF",
                "nota": 4.3,
                "qtd_avaliacoes": 19,
                "tem_site": False,
                "telefone": "556133334444",
                "endereco": "QNN 4 Conjunto B, Ceilândia - DF",
                "url_maps": "https://www.google.com/maps/place/Serralheria+Forte",
                "dono_gerente": "Sr. Carlos Eduardo",
                "copy_abordagem": "Olá! Vi o trabalho e as excelentes avaliações da Serralheria Forte Ferro no Google Maps.",
            },
        ]
        for idx, l in enumerate(leads, 1):
            l["score_potencial"] = calcular_score_potencial(l)
            l["id_lead"] = f"LEAD-TST003-{idx:03d}"
        return leads

    def test_formatar_telefone_exibicao(self):
        self.assertEqual(formatar_telefone_exibicao("061999887766"), "(61) 99988-7766")
        self.assertEqual(formatar_telefone_exibicao("556133334444"), "(61) 3333-4444")
        self.assertEqual(formatar_telefone_exibicao(""), "Não informado")

    def test_html_relatorio_suave_com_dupla_visualizacao(self):
        leads = self._leads_exemplo()
        html_out = montar_html_relatorio(leads, "TST003")

        # Verifica presença da Tabela Resumo e das Fichas Detalhadas
        self.assertIn("1. Visão Geral para Prospecção Rápida", html_out)
        self.assertIn("2. Fichas Detalhadas & Mensagens de Abordagem", html_out)
        self.assertIn("(61) 99988-7766", html_out)
        self.assertIn("@clinicasorrisoreal", html_out)
        self.assertIn("size: A4 landscape", html_out)
        # Garante que o antigo vermelho agressivo (#dc2626) e canvas 520mm foram removidos
        self.assertNotIn("#dc2626", html_out)
        self.assertNotIn("520mm", html_out)

    def test_salvar_relatorio_gera_apenas_pdf_sem_excel(self):
        leads = self._leads_exemplo()
        with tempfile.TemporaryDirectory() as tmpdir:
            caminho_pdf, id_lote = salvar_relatorio_pdf(leads, id_lote="TST003", pasta_destino=tmpdir)
            self.assertTrue(os.path.exists(caminho_pdf), "O arquivo PDF deveria existir")
            self.assertTrue(caminho_pdf.endswith(".pdf"))
            self.assertEqual(id_lote, "TST003")

            with open(caminho_pdf, "rb") as f:
                cabecalho = f.read(5)
            self.assertEqual(cabecalho, b"%PDF-")

            arquivos = os.listdir(tmpdir)
            self.assertEqual(len(arquivos), 1)
            self.assertFalse(any(a.endswith((".xlsx", ".xls", ".csv")) for a in arquivos))


if __name__ == "__main__":
    unittest.main(verbosity=2)
