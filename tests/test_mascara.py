"""Testes da máscara de dados sensíveis."""

import pytest

from mascara import mascarar, mascarar_com_contagem


# parametrize roda o mesmo teste uma vez para cada par (original, esperado).
@pytest.mark.parametrize(
    ("original", "esperado"),
    [
        (
            "Usuário ana.souza@email.com autenticado",
            "Usuário <EMAIL> autenticado",
        ),
        (
            "cliente CPF 030.564.139-53 (matrícula 787277)",
            "cliente CPF <CPF> (matrícula <MATRICULA>)",
        ),
        (
            "a partir de 189.51.194.72",
            "a partir de <IP>",
        ),
        (
            "ao notificar (85) 96514-2674",
            "ao notificar <TELEFONE>",
        ),
        (
            "pagamentos (api_key=3f9a0c1b77): HTTP 502",
            "pagamentos (api_key=<SEGREDO>): HTTP 502",
        ),
    ],
)
def test_mascara_cada_tipo(original, esperado):
    assert mascarar(original) == esperado


def test_nao_altera_texto_sem_dados_sensiveis():
    texto = "GET /api/faturas/334053 200 em 111ms"
    assert mascarar(texto) == texto


def test_conta_o_que_foi_mascarado():
    _, contagem = mascarar_com_contagem("ana@email.com e bruno@email.com de 10.0.0.1")
    assert contagem == {"email": 2, "ip": 1}
