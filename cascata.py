"""Diagnóstico em cascata: classificador principal (IA) com reserva (regras)."""

import logging
from dataclasses import dataclass

from agrupamento import Grupo
from diagnostico import Classificador, Diagnostico

logger = logging.getLogger(__name__)


@dataclass
class Analise:
    grupo: Grupo
    diagnostico: Diagnostico
    origem: str


def diagnosticar_em_cascata(
    grupos: list[Grupo],
    principal: Classificador | None,
    reserva: Classificador,
    max_falhas_seguidas: int = 2,
) -> list[Analise]:
    """Depois de max_falhas_seguidas, o principal deixa de ser chamado.

    Se o servidor da IA estiver fora do ar, cada chamada esperaria o timeout;
    assim o atraso fica limitado a poucas tentativas, e não a todos os grupos.
    """
    analises: list[Analise] = []
    falhas_seguidas = 0

    for grupo in grupos:
        if principal is not None and falhas_seguidas < max_falhas_seguidas:
            try:
                diagnostico = principal.diagnosticar(grupo)
                analises.append(Analise(grupo, diagnostico, principal.nome))
                falhas_seguidas = 0
                continue
            except Exception as erro:  # qualquer falha da IA cai na reserva
                falhas_seguidas += 1
                logger.warning(
                    "%s falhou no grupo [%s]: %s. Usando %s.",
                    principal.nome,
                    grupo.modulo,
                    erro,
                    reserva.nome,
                )
                if falhas_seguidas == max_falhas_seguidas:
                    logger.warning(
                        "%s falhou %d vezes seguidas; o restante vai só por %s.",
                        principal.nome,
                        falhas_seguidas,
                        reserva.nome,
                    )

        diagnostico = reserva.diagnosticar(grupo)
        analises.append(Analise(grupo, diagnostico, reserva.nome))

    return analises
