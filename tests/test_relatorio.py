import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from agrupamento import Grupo, agrupar
from cascata import Analise, diagnosticar_em_cascata
from diagnostico import ClassificadorRegras, Diagnostico
from leitura import ler_eventos
from main import main
from relatorio import gerar_relatorio, ordenar


def criar_grupo(modulo):
    return Grupo(
        assinatura=modulo,
        nivel="ERROR",
        modulo=modulo,
        quantidade=1,
        primeiro=datetime(2026, 11, 10, 8, 0),
        ultimo=datetime(2026, 11, 10, 8, 0),
        exemplos=["Teste"],
    )


def criar_diagnostico(gravidade):
    return Diagnostico(
        gravidade=gravidade, categoria="outro", causa_provavel="x", acao_sugerida="y"
    )


def analises_do_log_de_exemplo():
    eventos = ler_eventos(Path("logs_exemplo/app.log"))
    grupos = agrupar(eventos)
    return eventos, diagnosticar_em_cascata(grupos, None, ClassificadorRegras())


def test_ordena_pela_gravidade_do_diagnostico():
    # Mesmo nível no log: quem decide a ordem é o diagnóstico.
    media = Analise(criar_grupo("auth"), criar_diagnostico("media"), "regras")
    alta = Analise(criar_grupo("api"), criar_diagnostico("alta"), "ia")

    assert ordenar([media, alta]) == [alta, media]


def test_relatorio_tem_resumo_tabela_e_detalhes():
    eventos, analises = analises_do_log_de_exemplo()

    texto = gerar_relatorio(
        analises,
        arquivo_log="logs_exemplo/app.log",
        total_eventos=len(eventos),
        mascarados=Counter({"email": 61, "cpf": 13}),
        gerado_em=datetime(2026, 11, 16, 9, 0),
    )

    assert texto.startswith("# Relatório da Lupa")
    assert "**Eventos lidos:** 231" in texto
    assert "agrupados em 8 problemas" in texto
    assert "61 e-mails, 13 CPFs" in texto
    assert "16/11/2026 09:00" in texto
    linhas_da_tabela = [linha for linha in texto.splitlines() if re.match(r"\| \d+ \|", linha)]
    assert len(linhas_da_tabela) == 8


def test_relatorio_nao_tem_dados_sensiveis():
    eventos, analises = analises_do_log_de_exemplo()

    texto = gerar_relatorio(analises, "app.log", len(eventos), Counter())

    assert "@" not in texto
    assert not re.search(r"\d{3}\.\d{3}\.\d{3}-\d{2}", texto)
    assert not re.search(r"\b189\.\d+\.\d+\.\d+\b", texto)


def test_main_gera_o_arquivo(tmp_path):
    saida = tmp_path / "relatorio.md"

    codigo = main(["logs_exemplo/app.log", "--sem-ia", "--saida", str(saida)])

    assert codigo == 0
    assert saida.read_text(encoding="utf-8").startswith("# Relatório da Lupa")


def test_main_avisa_se_o_arquivo_nao_existe(tmp_path):
    codigo = main([str(tmp_path / "nao_existe.log"), "--sem-ia"])

    assert codigo == 1


def test_main_mostra_o_prompt_sem_gerar_relatorio(tmp_path, capsys):
    saida = tmp_path / "relatorio.md"

    codigo = main(["logs_exemplo/app.log", "--mostrar-prompt", "--saida", str(saida)])

    assert codigo == 0
    assert "===== system =====" in capsys.readouterr().out
    assert not saida.exists()
