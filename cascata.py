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
) -> list[Analise]:
    analises: list[Analise] = []

    for grupo in grupos:
        if principal is not None:
            try:
                diagnostico = principal.diagnosticar(grupo)
                analises.append(Analise(grupo, diagnostico, principal.nome))
                continue
            except Exception as erro:  # qualquer falha da IA cai na reserva
                logger.warning(
                    "%s falhou no grupo [%s]: %s. Usando %s.",
                    principal.nome,
                    grupo.modulo,
                    erro,
                    reserva.nome,
                )

        diagnostico = reserva.diagnosticar(grupo)
        analises.append(Analise(grupo, diagnostico, reserva.nome))

    return analises
