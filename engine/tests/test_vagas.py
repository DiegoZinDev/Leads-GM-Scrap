import io
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from engine.curriculo import sugerir
from engine.vagas import buscar, qualificar
from engine.worker import executar


def anuncio(i, **dados):
    return dict({"id": f"00000000-0000-0000-0000-{i:012}", "text": "Senior Java Developer",
                 "country": "GB", "workplaceType": "remote", "categories": {"location": "London"},
                 "descriptionPlain": "Python e SQL", "createdAt": 1700000000000}, **dados)


class VagasTest(unittest.TestCase):
    def test_criterios_ranking_salario_parcial_e_meta(self):
        filtros = {"pais": "GB", "modalidade": "REMOTO", "nivel": "SENIOR", "cargo": "Java",
                   "moeda": "GBP", "periodo": "ANO", "salarioMin": 100, "habilidades": ["SQL"]}
        pedido = dict(nicho="", regiao="", vagas=filtros, meta=4)
        faixa = {"currency": "GBP", "interval": "per-year", "min": 100}
        itens = [anuncio(1), anuncio(2, salaryRange=faixa), anuncio(3, country="BR"), anuncio(4, createdAt=None)]
        with patch("engine.vagas.consultar", return_value=itens):
            resultados = list(buscar(pedido))
        self.assertEqual([v["idFonte"][-1] for v in resultados], ["2","1","4"])
        self.assertEqual(resultados[0]["salario"], dict(min=100,max=None,moeda="GBP",periodo="ANO"))
        self.assertIsNone(resultados[1]["salario"])
        self.assertIsNone(resultados[2]["publicadaEm"])
        self.assertIsNone(qualificar(itens[0], dict(pedido, vagas={"exterior":False})))
        self.assertIsNone(qualificar(itens[0], dict(pedido, vagas={"vinculo":"CLT"})))

    def test_curriculo_docx_e_pdf_sugerem_sem_expor_texto(self):
        import json
        from playwright.sync_api import sync_playwright
        docx=io.BytesIO()
        with ZipFile(docx,"w") as z:
            z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:t>Email teste@example.com Python, SQL</w:t></w:document>')
        with sync_playwright() as pw:
            browser=pw.chromium.launch()
            pagina=browser.new_page()
            pagina.set_content("<p>Nome privado. Python e SQL</p>")
            pdf=pagina.pdf()
            browser.close()
        for tipo,dados in [("pdf",pdf),("docx",docx.getvalue())]:
            sugestoes=sugerir(dados,tipo)
            self.assertEqual(sugestoes,{"habilidades":["Python","SQL"]})
            eventos=[]
            with patch("engine.vagas.consultar", return_value=[anuncio(1),anuncio(2,descriptionPlain="")]):
                executar(dict(nicho="",regiao="",meta=1,vagas=sugestoes),eventos.append)
            self.assertEqual(eventos[1]["vaga"]["habilidadesEncontradas"],["Python","SQL"])
            self.assertNotIn("teste@example",json.dumps(eventos))

    def test_paginacao_deduplica_id_entre_paginas(self):
        import json
        from engine.vagas import consultar
        def pagina(itens): return io.BytesIO(json.dumps(itens).encode())
        with patch("engine.vagas.urlopen", side_effect=[pagina([anuncio(i) for i in range(100)]),pagina([anuncio(99),anuncio(100)])]):
            self.assertEqual(len(list(consultar())),101)

    def test_resultados_sem_anexo_sao_eventos_de_vaga(self):
        eventos=[]
        with patch("engine.vagas.consultar", return_value=[anuncio(1)]):
            executar(dict(nicho="",regiao="",meta=2,vagas={}),eventos.append)
        self.assertEqual([e["tipo"] for e in eventos],["inicio","vaga","fim"])
        self.assertEqual(eventos[-1]["total"],1)


    def test_pagina_interrompida_preserva_vaga_ja_obtida(self):
        def parcial():
            yield anuncio(1)
            raise OSError("Fonte indisponível")
        eventos = []
        with patch("engine.vagas.consultar", side_effect=parcial), self.assertRaises(OSError):
            executar(dict(nicho="",regiao="",meta=4,vagas={}),eventos.append)
        self.assertEqual([e["tipo"] for e in eventos], ["inicio", "vaga"])
