"""Testes do agrupamento de eventos."""

from datetime import datetime
from pathlib import Path

from agrupamento import agrupar
from leitura import Evento, ler_eventos


def criar_evento(nivel, mensagem, detalhes=None, minuto=0, modulo="api"):
    """Cria um Evento de teste sem precisar de um arquivo de log."""
    return Evento(
        momento=datetime(2026, 11, 10, 8, minuto),
        nivel=nivel,
        modulo=modulo,
        mensagem=mensagem,
        detalhes=detalhes or [],
    )


def test_numeros_diferentes_viram_o_mesmo_grupo():
    eventos = [
        criar_evento("WARNING", "Resposta lenta em /api/faturas: 6467ms", minuto=1),
        criar_evento("WARNING", "Resposta lenta em /api/faturas: 2375ms", minuto=5),
    ]

    grupos = agrupar(eventos)

    assert len(grupos) == 1
    assert grupos[0].quantidade == 2
    assert grupos[0].primeiro.minute == 1
    assert grupos[0].ultimo.minute == 5


def test_erros_diferentes_na_mesma_mensagem_viram_grupos_separados():
    eventos = [
        criar_evento("ERROR", "Falha no lote", detalhes=["KeyError: 'matricula'"]),
        criar_evento("ERROR", "Falha no lote", detalhes=["ValueError: data inválida"]),
    ]

    assert len(agrupar(eventos)) == 2


def test_ignora_eventos_abaixo_do_nivel_minimo():
    eventos = [
        criar_evento("INFO", "Tudo certo"),
        criar_evento("ERROR", "Deu ruim"),
    ]

    grupos = agrupar(eventos)

    assert [grupo.nivel for grupo in grupos] == ["ERROR"]


def test_ordena_por_gravidade_e_depois_por_quantidade():
    eventos = [
        criar_evento("ERROR", "Erro raro"),
        criar_evento("ERROR", "Erro comum"),
        criar_evento("ERROR", "Erro comum"),
        criar_evento("CRITICAL", "Sistema parado"),
    ]

    grupos = agrupar(eventos)

    assert [grupo.exemplos[0] for grupo in grupos] == [
        "Sistema parado",
        "Erro comum",
        "Erro raro",
    ]


def test_exemplos_e_traceback_saem_mascarados():
    eventos = [
        criar_evento(
            "ERROR",
            "Falha para ana@email.com",
            detalhes=["ValueError: CPF 030.564.139-53 inválido"],
        ),
    ]

    grupo = agrupar(eventos)[0]

    assert grupo.exemplos == ["Falha para <EMAIL>"]
    assert grupo.trecho_traceback == ["ValueError: CPF <CPF> inválido"]


def test_log_de_exemplo():
    grupos = agrupar(ler_eventos(Path("logs_exemplo/app.log")))

    assert len(grupos) == 8
    assert grupos[0].nivel == "CRITICAL"
    assert sum(grupo.quantidade for grupo in grupos) == 84  # 37 WARNING + 46 ERROR + 1 CRITICAL
