"""Ponto de entrada da Lupa: do arquivo de log ao relatório.

Uso:
    python main.py logs_exemplo/app.log
    python main.py logs_exemplo/app.log --sem-ia
    python main.py logs_exemplo/app.log --saida meu_relatorio.md --nivel ERROR

Sem a IA configurada (ou com --sem-ia), o diagnóstico é feito só pelas regras.
"""

import argparse
import logging
from collections import Counter
from pathlib import Path

from agrupamento import NIVEIS, agrupar
from cascata import diagnosticar_em_cascata
from diagnostico import ClassificadorRegras
from leitura import ler_eventos
from mascara import mascarar_com_contagem
from relatorio import gerar_relatorio

logger = logging.getLogger("lupa")


def ler_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    """Lê as opções da linha de comando.

    argv=None faz o argparse ler o que foi digitado no terminal. Os testes
    passam uma lista, como se tivessem digitado.
    """
    parser = argparse.ArgumentParser(
        description="Lupa: lê um log, agrupa os problemas e gera um relatório com diagnóstico."
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
    return parser.parse_args(argv)


def criar_classificador_ia():
    """Tenta criar o ClassificadorIA. Devolve None se a IA não estiver disponível."""
    try:
        from dotenv import load_dotenv

        from ia import ClassificadorIA

        load_dotenv()  # lê o .env, se existir
        return ClassificadorIA()
    except Exception as erro:
        # Sem .env, sem LangChain ou sem o pacote do provedor: segue só com regras.
        logger.warning("IA indisponível, usando só as regras. Motivo: %s", erro)
        return None


def contar_mascarados(eventos) -> Counter[str]:
    """Conta os dados sensíveis do log inteiro, para o resumo do relatório."""
    total: Counter[str] = Counter()
    for evento in eventos:
        for texto in [evento.mensagem, *evento.detalhes]:
            _, contagem = mascarar_com_contagem(texto)
            total += contagem
    return total


def main(argv: list[str] | None = None) -> int:
    argumentos = ler_argumentos(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    if not argumentos.arquivo.exists():
        logger.error("Arquivo não encontrado: %s", argumentos.arquivo)
        return 1  # código de saída diferente de 0 indica erro

    eventos = ler_eventos(argumentos.arquivo)
    grupos = agrupar(eventos, nivel_minimo=argumentos.nivel)
    logger.info("%d eventos lidos, %d problemas encontrados", len(eventos), len(grupos))

    principal = None if argumentos.sem_ia else criar_classificador_ia()
    analises = diagnosticar_em_cascata(grupos, principal, reserva=ClassificadorRegras())

    texto = gerar_relatorio(
        analises,
        arquivo_log=str(argumentos.arquivo),
        total_eventos=len(eventos),
        mascarados=contar_mascarados(eventos),
    )
    argumentos.saida.write_text(texto, encoding="utf-8")
    logger.info("Relatório salvo em %s", argumentos.saida)
    return 0


if __name__ == "__main__":
    # raise SystemExit(...) encerra o programa com o código devolvido por main.
    raise SystemExit(main())
