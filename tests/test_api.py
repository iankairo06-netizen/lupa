from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

import api  # noqa: E402

LOG_CURTO = (
    "2026-11-10 07:14:26,511 ERROR    [faturamento] Falha para ana@email.com\n"
    "ZeroDivisionError: division by zero\n"
)


@pytest.fixture
def cliente():
    api.ANALISES.clear()
    return TestClient(api.app)


def enviar_texto(cliente, **campos):
    corpo = {"conteudo": LOG_CURTO, "usar_ia": False, **campos}
    return cliente.post("/analises", json=corpo)


def test_saude(cliente):
    resposta = cliente.get("/saude")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_post_com_json_cria_a_analise(cliente):
    resposta = enviar_texto(cliente)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert resposta.headers["location"] == f"/analises/{corpo['id']}"
    assert corpo["total_problemas"] == 1
    assert corpo["problemas"][0]["categoria"] == "bug"
    assert "ana@email.com" not in resposta.text


def test_post_com_arquivo_cria_a_analise(cliente):
    conteudo = Path("logs_exemplo/app.log").read_bytes()

    resposta = cliente.post(
        "/analises/arquivo",
        params={"usar_ia": False},
        files={"arquivo": ("app.log", conteudo, "text/plain")},
    )

    assert resposta.status_code == 201
    assert resposta.json()["eventos_lidos"] == 231
    assert resposta.json()["total_problemas"] == 8


def test_lista_e_mostra_as_analises(cliente):
    id_analise = enviar_texto(cliente).json()["id"]

    lista = cliente.get("/analises")
    detalhe = cliente.get(f"/analises/{id_analise}")

    assert lista.status_code == 200
    assert [item["id"] for item in lista.json()] == [id_analise]
    assert detalhe.status_code == 200
    assert detalhe.json()["problemas"][0]["modulo"] == "faturamento"


def test_relatorio_em_markdown(cliente):
    id_analise = enviar_texto(cliente).json()["id"]

    resposta = cliente.get(f"/analises/{id_analise}/relatorio")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/markdown")
    assert resposta.text.startswith("# Relatório da Lupa")


def test_analise_inexistente_da_404(cliente):
    resposta = cliente.get("/analises/999")

    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Análise 999 não encontrada."}


def test_id_que_nao_e_numero_da_422(cliente):
    assert cliente.get("/analises/abc").status_code == 422


def test_nivel_invalido_da_422(cliente):
    assert enviar_texto(cliente, nivel_minimo="URGENTE").status_code == 422


def test_conteudo_vazio_da_422(cliente):
    assert enviar_texto(cliente, conteudo="").status_code == 422


def test_texto_sem_eventos_da_400(cliente):
    assert enviar_texto(cliente, conteudo="isso não é um log").status_code == 400


def test_arquivo_grande_da_413(cliente, monkeypatch):
    monkeypatch.setattr(api, "TAMANHO_MAXIMO", 10)

    resposta = cliente.post(
        "/analises/arquivo",
        params={"usar_ia": False},
        files={"arquivo": ("grande.log", b"x" * 50, "text/plain")},
    )

    assert resposta.status_code == 413


def test_delete_apaga_a_analise(cliente):
    id_analise = enviar_texto(cliente).json()["id"]

    primeira = cliente.delete(f"/analises/{id_analise}")
    segunda = cliente.delete(f"/analises/{id_analise}")

    assert primeira.status_code == 204
    assert primeira.content == b""
    assert segunda.status_code == 404
    assert cliente.get(f"/analises/{id_analise}").status_code == 404


def test_swagger_documenta_as_rotas(cliente):
    esquema = cliente.get("/openapi.json").json()

    assert set(esquema["paths"]) >= {"/analises", "/analises/arquivo", "/analises/{id_analise}"}
    assert cliente.get("/docs").status_code == 200
