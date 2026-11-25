from pathlib import Path

from leitura import ler_eventos, ler_linhas


def test_junta_traceback_no_evento_anterior(tmp_path):
    arquivo = tmp_path / "teste.log"
    arquivo.write_text(
        "2026-11-10 07:00:00,000 INFO     [api] Tudo certo\n"
        "2026-11-10 07:00:01,000 ERROR    [faturamento] Falha no cálculo\n"
        "Traceback (most recent call last):\n"
        '  File "/app/consumo.py", line 47, in calcular_media\n'
        "ZeroDivisionError: division by zero\n",
        encoding="utf-8",
    )

    eventos = ler_eventos(arquivo)

    assert len(eventos) == 2
    assert eventos[0].detalhes == []
    assert eventos[1].nivel == "ERROR"
    assert eventos[1].modulo == "faturamento"
    assert len(eventos[1].detalhes) == 3
    assert eventos[1].fim_traceback == "ZeroDivisionError: division by zero"


def test_ignora_linhas_em_branco(tmp_path):
    arquivo = tmp_path / "teste.log"
    arquivo.write_text(
        "2026-11-10 07:00:00,000 INFO     [api] Primeira\n"
        "\n"
        "2026-11-10 07:00:01,000 INFO     [api] Segunda\n",
        encoding="utf-8",
    )

    eventos = ler_eventos(arquivo)

    assert len(eventos) == 2
    assert eventos[0].detalhes == []


def test_log_de_exemplo():
    eventos = ler_eventos(Path("logs_exemplo/app.log"))

    assert len(eventos) == 231
    linhas_lidas = sum(1 + len(evento.detalhes) for evento in eventos)
    assert linhas_lidas == 423  # nenhuma linha se perdeu


def test_le_eventos_de_texto():
    texto = (
        "2026-11-10 07:00:01,000 ERROR    [faturamento] Falha no cálculo\n"
        "ZeroDivisionError: division by zero\n"
    )

    eventos = ler_linhas(texto.splitlines())

    assert len(eventos) == 1
    assert eventos[0].fim_traceback == "ZeroDivisionError: division by zero"
