from datetime import datetime
from pathlib import Path

from esquemas import Registro, para_analise_completa
from leitura import ler_eventos
from pipeline import analisar


def test_analisa_o_log_de_exemplo_sem_ia():
    resultado = analisar(ler_eventos(Path("logs_exemplo/app.log")), usar_ia=False)

    assert resultado.eventos_lidos == 231
    assert len(resultado.analises) == 8
    assert {analise.origem for analise in resultado.analises} == {"regras"}
    assert resultado.mascarados["email"] == 61


def test_resposta_da_api_vem_ordenada_e_sem_dados_sensiveis():
    resultado = analisar(ler_eventos(Path("logs_exemplo/app.log")), usar_ia=False)
    registro = Registro(id=1, criada_em=datetime(2026, 11, 25, 9, 0), nome_arquivo="app.log", resultado=resultado)

    resposta = para_analise_completa(registro)

    assert resposta.total_problemas == 8
    assert resposta.problemas[0].gravidade == "critica"
    assert "@" not in resposta.model_dump_json()
