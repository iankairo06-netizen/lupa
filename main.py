"""Lupa pela linha de comando: do arquivo de log ao relatório.

    python main.py logs_exemplo/app.log
    python main.py logs_exemplo/app.log --sem-ia
    python main.py logs_exemplo/app.log --mostrar-prompt
"""

import argparse
import logging
from pathlib import Path

from agrupamento import NIVEIS, Grupo, agrupar
from leitura import ler_eventos
from pipeline import analisar
from relatorio import gerar_relatorio

logger = logging.getLogger("lupa")


def ler_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lê um log, agrupa os problemas e gera um relatório com diagnóstico."
    )
    parser.add_argument("arquivo", type=Path, help="arquivo de log a analisar")
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path("relatorio.md"),
        help="onde salvar o relatório (padrão: relatorio.md)",
    )
    parser.add_argument(
        "--nivel",
        default="WARNING",
        choices=list(NIVEIS),
        help="nível mínimo dos eventos analisados (padrão: WARNING)",
    )
    parser.add_argument(
        "--sem-ia",
        action="store_true",
        help="usa só as regras, sem chamar o LLM",
    )
    parser.add_argument(
        "--mostrar-prompt",
        action="store_true",
        help="mostra o prompt do problema mais grave, sem chamar o LLM",
    )
    return parser.parse_args(argv)


def mostrar_prompt(grupo: Grupo) -> None:
    from ia import montar_mensagens

    for papel, texto in montar_mensagens(grupo):
        print(f"===== {papel} =====")
        print(texto)
        print()


def main(argv: list[str] | None = None) -> int:
    argumentos = ler_argumentos(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    if not argumentos.arquivo.exists():
        logger.error("Arquivo não encontrado: %s", argumentos.arquivo)
        return 1

    eventos = ler_eventos(argumentos.arquivo)

    if argumentos.mostrar_prompt:
        grupos = agrupar(eventos, nivel_minimo=argumentos.nivel)
        if grupos:
            mostrar_prompt(grupos[0])
        return 0

    resultado = analisar(eventos, argumentos.nivel, usar_ia=not argumentos.sem_ia)
    logger.info(
        "%d eventos lidos, %d problemas encontrados",
        resultado.eventos_lidos,
        len(resultado.analises),
    )

    texto = gerar_relatorio(
        resultado.analises,
        arquivo_log=str(argumentos.arquivo),
        total_eventos=resultado.eventos_lidos,
        mascarados=resultado.mascarados,
    )
    argumentos.saida.write_text(texto, encoding="utf-8")
    logger.info("Relatório salvo em %s", argumentos.saida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
