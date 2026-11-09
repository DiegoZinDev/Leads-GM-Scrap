"""
Testes automatizados da Implementação 4 (e critérios do Item 6):
Triagem minuciosa de cada lead, validação de >= 10 avaliações escritas, regra de nota 4.0
com exceção para > 10 avaliações, verificação obrigatória de WhatsApp (Maps + fallback Instagram)
e priorização de autônomos e micro-empreendedores em ascensão.
"""

import unittest

from instagram import PerfilInstagram
from qualifier import (
    avaliar_reputacao_e_avaliacoes,
    classificar_perfil_empreendedor,
    eh_grande_rede_ou_orgao_publico,
    realizar_triagem_minuciosa,
    verificar_e_obter_whatsapp,
)
from verifier import Evidencia, ResultadoPresencaDigital


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
