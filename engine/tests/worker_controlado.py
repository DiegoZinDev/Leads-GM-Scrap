"""Processo de teste usado pela suíte de integração Java."""
import sys
from unittest.mock import patch
from engine.worker import main


def fonte(**params):
    if params["nicho_nome"] == "Sem resultados":
        return []
    return [{"nome": "Clínica"} for _ in range(params["limite_leads"])]


if __name__ == "__main__":
    with patch("engine.prospeccao.buscar_leads_google_maps", side_effect=fonte):
        resultado = main()
    sys.exit(1 if "--falhar" in sys.argv else resultado)
