"""Testes do diagnóstico por regras."""

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from agrupamento import Grupo, agrupar
from diagnostico import ClassificadorRegras, Diagnostico, RegraDiagnostico
from leitura import ler_eventos


def criar_grupo(nivel="ERROR", exemplos=None, trecho_traceback=None, modulo="api"):
    """Cria um Grupo de teste sem precisar de um arquivo de log."""
    exemplos = exemplos or ["Mensagem de teste"]
    return Grupo(
        assinatura=f"{nivel} [{modulo}] {exemplos[0]}",
        nivel=nivel,
        modulo=modulo,
        quantidade=1,
        primeiro=datetime(2026, 11, 10, 8, 0),
        ultimo=datetime(2026, 11, 10, 8, 0),
        exemplos=exemplos,
        trecho_traceback=trecho_traceback or [],
    )


def test_reconhece_divisao_por_zero():
    grupo = criar_grupo(trecho_traceback=["ZeroDivisionError: division by zero"])

    diagnostico = ClassificadorRegras().diagnosticar(grupo)

    assert diagnostico.categoria == "bug"
    assert diagnostico.gravidade == "alta"


def test_reconhece_falha_no_banco():
    grupo = criar_grupo(exemplos=["Falha ao obter conexão com o banco de dados"])

    assert ClassificadorRegras().diagnosticar(grupo).categoria == "banco_de_dados"


def test_numero_parecido_com_codigo_de_erro_nao_confunde():
    # 5034ms contém "503", mas é uma resposta lenta, não um erro 503.
    grupo = criar_grupo(nivel="WARNING", exemplos=["Resposta lenta em /api/faturas: 5034ms"])

    assert ClassificadorRegras().diagnosticar(grupo).categoria == "desempenho"


def test_sem_regra_usa_a_gravidade_do_nivel():
    grupo = criar_grupo(nivel="CRITICAL", exemplos=["Algo inédito aconteceu"])

    diagnostico = ClassificadorRegras().diagnosticar(grupo)

    assert diagnostico.categoria == "outro"
    assert diagnostico.gravidade == "critica"


def test_aceita_regras_personalizadas():
    regra = RegraDiagnostico(
        palavras=("disco cheio",),
        diagnostico=Diagnostico(
            gravidade="critica",
            categoria="outro",
            causa_provavel="Sem espaço em disco.",
            acao_sugerida="Liberar espaço.",
        ),
    )
    grupo = criar_grupo(exemplos=["Falha ao gravar: disco cheio"])

    diagnostico = ClassificadorRegras(regras=[regra]).diagnosticar(grupo)

    assert diagnostico.causa_provavel == "Sem espaço em disco."


def test_diagnostico_recusa_gravidade_fora_da_lista():
    with pytest.raises(ValidationError):
        Diagnostico(
            gravidade="altíssima",
            categoria="bug",
            causa_provavel="x",
            acao_sugerida="y",
        )


def test_diagnostico_recusa_texto_vazio():
    with pytest.raises(ValidationError):
        Diagnostico(
            gravidade="alta",
            categoria="bug",
            causa_provavel="",
            acao_sugerida="y",
        )


def test_log_de_exemplo():
    grupos = agrupar(ler_eventos(Path("logs_exemplo/app.log")))
    classificador = ClassificadorRegras()

    categorias = {grupo.modulo: classificador.diagnosticar(grupo).categoria for grupo in grupos}

    assert categorias == {
        "ordens_servico": "outro",
        "faturamento": "bug",
        "leituras": "dados_invalidos",
        "notificacoes": "integracao_externa",
        "core.db": "banco_de_dados",
        "pagamentos": "integracao_externa",
        "api": "desempenho",
        "auth": "seguranca",
    }
