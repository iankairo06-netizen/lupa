"""Núcleo da Lupa: de eventos a problemas diagnosticados.

A linha de comando (main.py) e a API (api.py) são duas portas de entrada
para este mesmo núcleo.
"""

import logging
from collections import Counter
from dataclasses import dataclass

from agrupamento import agrupar
from cascata import Analise, diagnosticar_em_cascata
from diagnostico import ClassificadorRegras
from leitura import Evento
from mascara import mascarar_com_contagem

logger = logging.getLogger(__name__)


@dataclass
class Resultado:
    eventos_lidos: int
    analises: list[Analise]
    mascarados: Counter[str]


def criar_classificador_ia():
    """O ClassificadorIA, ou None se a IA não estiver disponível."""
    try:
        from dotenv import load_dotenv

        from ia import ClassificadorIA

        load_dotenv()
        return ClassificadorIA()
    except Exception as erro:
        logger.warning("IA indisponível, usando só as regras. Motivo: %s", erro)
        return None


def contar_mascarados(eventos: list[Evento]) -> Counter[str]:
    total: Counter[str] = Counter()
    for evento in eventos:
        for texto in [evento.mensagem, *evento.detalhes]:
            _, contagem = mascarar_com_contagem(texto)
            total += contagem
    return total


def analisar(
    eventos: list[Evento],
    nivel_minimo: str = "WARNING",
    usar_ia: bool = True,
) -> Resultado:
    grupos = agrupar(eventos, nivel_minimo=nivel_minimo)
    principal = criar_classificador_ia() if usar_ia else None
    analises = diagnosticar_em_cascata(grupos, principal, reserva=ClassificadorRegras())
    return Resultado(
        eventos_lidos=len(eventos),
        analises=analises,
        mascarados=contar_mascarados(eventos),
    )
