"""
Testes automatizados das Implementações 4 e 5 (e critérios do Item 6):
- Triagem minuciosa de cada lead, validação de >= 10 avaliações escritas, regra de nota 4.0
  com exceção para > 10 avaliações, verificação obrigatória de WhatsApp (Maps + fallback Instagram)
  e priorização de autônomos e micro-empreendedores em ascensão.
- Algoritmo de Funil Eliminatório Sequencial em Lote (Pandas + NumPy) sobre todos os leads
  coletados de uma região, eliminando critério por critério na sequência exata.
"""

import unittest

from qualifier import (
    avaliar_reputacao_e_avaliacoes,
    classificar_perfil_empreendedor,
    eh_grande_rede_ou_orgao_publico,
    executar_funil_sequencial,
    realizar_triagem_minuciosa,
    verificar_e_obter_whatsapp,
)
from verifier import Evidencia, PerfilInstagram, ResultadoPresencaDigital


class TestTriagemMinuciosa(unittest.TestCase):
    def test_minimo_10_avaliacoes_escritas(self):
        # Menos de 10 avaliações escritas -> reprova
        ok, _, motivo = avaliar_reputacao_e_avaliacoes(nota=4.9, qtd_avaliacoes=15, qtd_avaliacoes_escritas=8)
        self.assertFalse(ok)
        self.assertIn("8 avaliações escritas", motivo)

        # Pelo menos 10 avaliações escritas e nota >= 4.0 -> aprova
        ok2, excecao2, _ = avaliar_reputacao_e_avaliacoes(nota=4.5, qtd_avaliacoes=12, qtd_avaliacoes_escritas=10)
        self.assertTrue(ok2)
        self.assertFalse(excecao2)

    def test_regra_estrelas_menor_que_4_com_mais_de_10_avaliacoes(self):
        # Nota < 4.0 com exatamente 10 avaliações (não possui MAIS de 10) -> reprova
        ok, _, _ = avaliar_reputacao_e_avaliacoes(nota=3.8, qtd_avaliacoes=10, qtd_avaliacoes_escritas=10)
        self.assertFalse(ok)

        # Nota < 4.0 mas com MAIS de 10 avaliações (ex: 18 avaliações, 12 escritas) -> aprova pela exceção
        ok2, excecao2, msg2 = avaliar_reputacao_e_avaliacoes(nota=3.8, qtd_avaliacoes=18, qtd_avaliacoes_escritas=12)
        self.assertTrue(ok2)
        self.assertTrue(excecao2)
        self.assertIn("18 avaliações", msg2)

    def test_whatsapp_obrigatorio_maps_e_fallback_instagram(self):
        # Caso 1: Telefone fixo no Maps sem wa.me e sem Instagram -> reprova
        res1 = verificar_e_obter_whatsapp(telefone_maps="(61) 3562-8226")
        self.assertFalse(res1.possui_whatsapp)

        # Caso 2: Telefone fixo no Maps, mas perfil do Instagram tem wa.me na bio ou destaque -> aprova pelo Instagram!
        perfil_ig = PerfilInstagram(
            username="estudio_mariana",
            acessivel=True,
            biografia="Alongamento em Gel em Taguatinga",
            links_bio=[],
            links_destaques=["https://wa.me/5561984556677"],
        )
        res2 = verificar_e_obter_whatsapp(telefone_maps="(61) 3562-8226", perfil_instagram=perfil_ig)
        self.assertTrue(res2.possui_whatsapp)
        self.assertEqual(res2.numero_e164, "5561984556677")
        self.assertEqual(res2.numero_formatado, "(61) 98455-6677")
        self.assertIn("Instagram", res2.origem)

        # Caso 3: Sem telefone no Maps, mas número de celular escrito no texto da bio do Instagram -> aprova!
        perfil_bio_tel = PerfilInstagram(
            username="dr_henrique_adv",
            acessivel=True,
            biografia="Advogado Civil e Trabalhista | Agendamentos: (61) 99123-4567",
        )
        res3 = verificar_e_obter_whatsapp(telefone_maps="", perfil_instagram=perfil_bio_tel)
        self.assertTrue(res3.possui_whatsapp)
        self.assertEqual(res3.numero_e164, "5561991234567")
        self.assertIn("Instagram", res3.origem)

    def test_descarte_grandes_redes_e_fechados(self):
        eh_rede, _ = eh_grande_rede_ou_orgao_publico("Academia Smart Fit - Taguatinga")
        self.assertTrue(eh_rede)
        eh_rede2, _ = eh_grande_rede_ou_orgao_publico("Oral Unic Implantes")
        self.assertTrue(eh_rede2)
        eh_rede3, _ = eh_grande_rede_ou_orgao_publico("Estúdio Bela Unhas Mariana")
        self.assertFalse(eh_rede3)

        lead_fechado = {
            "nome": "Clínica Antiga",
            "nicho": "Odontologia",
            "cidade": "Brasília DF",
            "nota": 4.8,
            "qtd_avaliacoes": 30,
            "qtd_avaliacoes_escritas": 20,
            "fechado_permanentemente": True,
            "telefone": "(61) 99988-7766",
        }
        triagem = realizar_triagem_minuciosa(lead_fechado, ResultadoPresencaDigital())
        self.assertFalse(triagem.aprovado)
        self.assertEqual(triagem.etapa_reprovacao, "status_operacional")

    def test_prioridade_autonomos_e_micro_em_ascensao(self):
        lead_autonomo = {
            "nome": "Dra. Camila Ribeiro Odontologia",
            "nicho": "Odontologia",
            "cidade": "Águas Claras DF",
            "nota": 4.9,
            "qtd_avaliacoes": 34,
            "qtd_avaliacoes_escritas": 18,
            "telefone": "",  # Sem telefone no Maps, vai recuperar do Instagram
            "tem_fotos": True,
            "dono_gerente": "Dra. Camila Ribeiro",
        }
        perfil_ig = PerfilInstagram(
            username="dracamilaribeiro",
            acessivel=True,
            biografia="Odontologia estética e implantes em Águas Claras",
            links_bio=["https://wa.me/5561999112233"],
        )
        presenca = ResultadoPresencaDigital(
            url_instagram="https://www.instagram.com/dracamilaribeiro/",
            perfil_instagram=perfil_ig,
            status_instagram="verificado",
        )
        triagem = realizar_triagem_minuciosa(lead_autonomo, presenca)
        self.assertTrue(triagem.aprovado)
        self.assertTrue(triagem.perfil.prioridade_maxima)
        self.assertEqual(triagem.perfil.segmento, "autonomo_ascensao")
        self.assertEqual(lead_autonomo["telefone"], "(61) 99911-2233")
        self.assertGreaterEqual(lead_autonomo["score_potencial"], 90)

        # Compara score com empresa consolidada grande (> 250 avaliações)
        lead_consolidada = {
            "nome": "Centro Médico Hospitalar Integrado Ltda",
            "nicho": "Fisioterapia",
            "cidade": "Brasília DF",
            "nota": 4.1,
            "qtd_avaliacoes": 320,
            "qtd_avaliacoes_escritas": 110,
            "telefone": "(61) 98888-7777",
            "tem_fotos": False,
        }
        triagem_cons = realizar_triagem_minuciosa(lead_consolidada, ResultadoPresencaDigital())
        self.assertTrue(triagem_cons.aprovado)
        self.assertEqual(triagem_cons.perfil.segmento, "consolidada")
        self.assertGreater(lead_autonomo["score_potencial"], lead_consolidada["score_potencial"])

    def test_reprova_se_tiver_site_ou_sistema(self):
        lead = {
            "nome": "Barbearia Estilo",
            "nicho": "Hair Designer",
            "cidade": "Taguatinga DF",
            "nota": 4.9,
            "qtd_avaliacoes": 45,
            "qtd_avaliacoes_escritas": 20,
            "telefone": "(61) 99988-7766",
        }
        presenca = ResultadoPresencaDigital(
            evidencias=[Evidencia("Instagram (bio)", "https://appbarber.com.br/estilo", "sistema", "Sistema AppBarber", True)]
        )
        triagem = realizar_triagem_minuciosa(lead, presenca)
        self.assertFalse(triagem.aprovado)
        self.assertEqual(triagem.etapa_reprovacao, "possui_site_ou_sistema")


class TestFunilSequencialEmLote(unittest.TestCase):
    def test_funil_eliminatorio_sequencial_em_lote_pandas_numpy(self):
        """
        Simula 7 escritórios/clínicas coletados de uma região e verifica que o funil
        elimina sequencialmente em cada um dos 6 critérios:
          1. Franquia nacional (Oral Unic) -> eliminada no Critério 1 (restam 6)
          2. Poucas avaliações escritas (< 10) -> eliminada no Critério 2 (restam 5)
          3. Nota < 4.0 com apenas 10 avaliações (sem >10) -> eliminada no Critério 3 (restam 4)
          4. Possui site/sistema na bio do Instagram -> eliminada no Critério 4 (restam 3)
          5. Apenas telefone fixo sem WhatsApp nem no Maps nem no Instagram -> eliminada no Critério 5 (restam 2)
          6. Os 2 sobreviventes (1 empresa consolidada c/ nota 3.8 mas >10 avaliações + 1 autônoma em ascensão
             c/ WhatsApp na bio do Instagram) passam pelo Critério 6 e são ordenados com a autônoma em 1º lugar!
        """
        leads_regiao = [
            # 1) Eliminado no Critério 1 (Franquia Nacional)
            {
                "nome": "Oral Unic Implantes Taguatinga",
                "nicho": "Odontologia",
                "cidade": "Taguatinga DF",
                "nota": 4.9,
                "qtd_avaliacoes": 120,
                "qtd_avaliacoes_escritas": 45,
                "telefone": "(61) 99999-0001",
            },
            # 2) Eliminado no Critério 2 (Apenas 6 avaliações escritas < 10)
            {
                "nome": "Consultório Novo Horizonte",
                "nicho": "Odontologia",
                "cidade": "Taguatinga DF",
                "nota": 5.0,
                "qtd_avaliacoes": 8,
                "qtd_avaliacoes_escritas": 6,
                "telefone": "(61) 99999-0002",
            },
            # 3) Eliminado no Critério 3 (Nota 3.7 com exatas 10 avaliações — não tem MAIS de 10)
            {
                "nome": "Clínica Dental Popular",
                "nicho": "Odontologia",
                "cidade": "Taguatinga DF",
                "nota": 3.7,
                "qtd_avaliacoes": 10,
                "qtd_avaliacoes_escritas": 10,
                "telefone": "(61) 99999-0003",
            },
            # 4) Eliminado no Critério 4 (Possui site próprio na bio do Instagram)
            {
                "nome": "Studio Dental Prime",
                "nicho": "Odontologia",
                "cidade": "Taguatinga DF",
                "nota": 4.8,
                "qtd_avaliacoes": 28,
                "qtd_avaliacoes_escritas": 15,
                "telefone": "(61) 99999-0004",
            },
            # 5) Eliminado no Critério 5 (Telefone fixo sem WhatsApp nem no Maps nem no Instagram)
            {
                "nome": "Clínica Tradicional Fixo",
                "nicho": "Odontologia",
                "cidade": "Taguatinga DF",
                "nota": 4.6,
                "qtd_avaliacoes": 40,
                "qtd_avaliacoes_escritas": 19,
                "telefone": "(61) 3351-2200",
            },
            # 6) APROVADO (Empresa consolidada com nota 3.8 mas > 10 avaliações [290 avaliações] e celular WhatsApp)
            {
                "nome": "Centro Odontológico Integrado Brasília Ltda",
                "nicho": "Odontologia",
                "cidade": "Taguatinga DF",
                "nota": 3.8,
                "qtd_avaliacoes": 290,
                "qtd_avaliacoes_escritas": 85,
                "telefone": "(61) 98877-6655",
                "tem_fotos": False,
            },
            # 7) APROVADO COM PRIORIDADE MÁXIMA (Autônoma em ascensão, sem tel no Maps mas com wa.me no Instagram)
            {
                "nome": "Dra. Beatriz Mendes Odontologia Estética",
                "nicho": "Odontologia",
                "cidade": "Taguatinga DF",
                "nota": 4.9,
                "qtd_avaliacoes": 32,
                "qtd_avaliacoes_escritas": 18,
                "telefone": "",
                "tem_fotos": True,
                "dono_gerente": "Dra. Beatriz Mendes",
            },
        ]

        def mock_investigacao(lead: dict) -> ResultadoPresencaDigital:
            nome = lead["nome"]
            if "Studio Dental Prime" in nome:
                return ResultadoPresencaDigital(
                    evidencias=[Evidencia("Instagram (bio)", "https://studiodentalprime.com.br", "site_proprio", "Site próprio", True)]
                )
            if "Dra. Beatriz Mendes" in nome:
                perfil_bia = PerfilInstagram(
                    username="drabeatrizmendes",
                    acessivel=True,
                    biografia="Facetas e Lentes em Taguatinga",
                    links_bio=["https://wa.me/5561992223344"],
                )
                return ResultadoPresencaDigital(
                    url_instagram="https://www.instagram.com/drabeatrizmendes/",
                    perfil_instagram=perfil_bia,
                    status_instagram="verificado",
                )
            return ResultadoPresencaDigital(status_instagram="verificado")

        relatorio = executar_funil_sequencial(
            leads_brutos=leads_regiao,
            regiao="Taguatinga DF",
            nicho="Odontologia",
            config_filtros={"min_avaliacoes_escritas": 10, "nota_minima": 4.0, "exigir_sem_site": True},
            config_verificacao={"exigir_instagram_verificado": False, "rejeitar_inconclusivos": True},
            callback_investigacao=mock_investigacao,
            silencioso=True,
        )

        # Verifica contagens exatas de entrada/sobreviventes em cada uma das 6 etapas do funil
        self.assertEqual(relatorio.total_bruto_coletado, 7)
        self.assertEqual(len(relatorio.etapas), 6)

        # Etapa 1: 7 -> 6 (elimina Oral Unic)
        self.assertEqual((relatorio.etapas[0].entrada, relatorio.etapas[0].sobreviventes), (7, 6))
        # Etapa 2: 6 -> 5 (elimina Consultório Novo Horizonte c/ 6 escritas)
        self.assertEqual((relatorio.etapas[1].entrada, relatorio.etapas[1].sobreviventes), (6, 5))
        # Etapa 3: 5 -> 4 (elimina Clínica Dental Popular c/ 3.7 e apenas 10 av.)
        self.assertEqual((relatorio.etapas[2].entrada, relatorio.etapas[2].sobreviventes), (5, 4))
        # Etapa 4: 4 -> 3 (elimina Studio Dental Prime c/ site na bio)
        self.assertEqual((relatorio.etapas[3].entrada, relatorio.etapas[3].sobreviventes), (4, 3))
        # Etapa 5: 3 -> 2 (elimina Clínica Tradicional Fixo sem WhatsApp)
        self.assertEqual((relatorio.etapas[4].entrada, relatorio.etapas[4].sobreviventes), (3, 2))
        # Etapa 6: 2 -> 2 (classifica e ordena por prioridade de ascensão)
        self.assertEqual((relatorio.etapas[5].entrada, relatorio.etapas[5].sobreviventes), (2, 2))

        self.assertEqual(relatorio.total_qualificados, 2)
        # Garante que a autônoma em ascensão (Dra. Beatriz) ficou em 1º lugar na fila e com WhatsApp do Instagram
        primeiro = relatorio.leads_aprovados[0]
        segundo = relatorio.leads_aprovados[1]
        self.assertIn("Dra. Beatriz Mendes", primeiro["nome"])
        self.assertTrue(primeiro["prioridade_maxima"])
        self.assertEqual(primeiro["telefone"], "(61) 99222-3344")
        self.assertIn("Instagram", primeiro["origem_whatsapp"])

        self.assertIn("Centro Odontológico Integrado", segundo["nome"])
        self.assertFalse(segundo["prioridade_maxima"])

        # Verifica DataFrame Pandas e estatísticas NumPy
        self.assertIsNotNone(relatorio.dataframe_final)
        self.assertEqual(len(relatorio.dataframe_final), 2)
        self.assertIn("score_medio", relatorio.estatisticas_numpy)
        self.assertEqual(relatorio.estatisticas_numpy["total_em_ascensao"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
