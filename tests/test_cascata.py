import logging
from datetime import datetime

from agrupamento import Grupo
from cascata import diagnosticar_em_cascata
from diagnostico import Diagnostico

DIAGNOSTICO_IA = Diagnostico(
    gravidade="alta", categoria="bug", causa_provavel="Pela IA.", acao_sugerida="x"
)
DIAGNOSTICO_REGRAS = Diagnostico(
    gravidade="media", categoria="outro", causa_provavel="Pelas regras.", acao_sugerida="y"
)


class ClassificadorFalso:
    def __init__(self, nome, resposta, falhar_no_modulo=None):
        self.nome = nome
        self.resposta = resposta
        self.falhar_no_modulo = falhar_no_modulo
        self.chamadas = 0

    def diagnosticar(self, grupo):
        self.chamadas += 1
        if self.falhar_no_modulo in (grupo.modulo, "todos"):
            raise TimeoutError("a API demorou demais")
        return self.resposta


def criar_grupo(modulo="api"):
    return Grupo(
        assinatura=modulo,
        nivel="ERROR",
        modulo=modulo,
        quantidade=1,
        primeiro=datetime(2026, 11, 10, 8, 0),
        ultimo=datetime(2026, 11, 10, 8, 0),
        exemplos=["Teste"],
    )


REGRAS = ClassificadorFalso("regras", DIAGNOSTICO_REGRAS)


def test_usa_a_ia_quando_ela_funciona():
    ia = ClassificadorFalso("ia", DIAGNOSTICO_IA)

    analises = diagnosticar_em_cascata([criar_grupo()], ia, REGRAS)

    assert analises[0].origem == "ia"
    assert analises[0].diagnostico == DIAGNOSTICO_IA


def test_usa_as_regras_quando_a_ia_falha(caplog):
    ia = ClassificadorFalso("ia", DIAGNOSTICO_IA, falhar_no_modulo="todos")

    with caplog.at_level(logging.WARNING):
        analises = diagnosticar_em_cascata([criar_grupo()], ia, REGRAS)

    assert analises[0].origem == "regras"
    assert analises[0].diagnostico == DIAGNOSTICO_REGRAS
    assert "a API demorou demais" in caplog.text


def test_sem_ia_usa_so_as_regras():
    analises = diagnosticar_em_cascata([criar_grupo(), criar_grupo("auth")], None, REGRAS)

    assert [analise.origem for analise in analises] == ["regras", "regras"]


def test_falha_num_grupo_nao_afeta_os_outros():
    ia = ClassificadorFalso("ia", DIAGNOSTICO_IA, falhar_no_modulo="auth")
    grupos = [criar_grupo("api"), criar_grupo("auth"), criar_grupo("leituras")]

    analises = diagnosticar_em_cascata(grupos, ia, REGRAS)

    assert [analise.origem for analise in analises] == ["ia", "regras", "ia"]


def test_para_de_chamar_a_ia_depois_de_falhas_seguidas(caplog):
    ia = ClassificadorFalso("ia", DIAGNOSTICO_IA, falhar_no_modulo="todos")
    grupos = [criar_grupo(f"modulo{numero}") for numero in range(5)]

    with caplog.at_level(logging.WARNING):
        analises = diagnosticar_em_cascata(grupos, ia, REGRAS, max_falhas_seguidas=2)

    assert ia.chamadas == 2
    assert [analise.origem for analise in analises] == ["regras"] * 5
    assert "falhou 2 vezes seguidas" in caplog.text
