"""Cascata de diagnóstico: IA primeiro, regras como plano B.

Para cada grupo, tenta o classificador principal (a IA). Se ele falhar por
qualquer motivo, usa o classificador reserva (as regras). O relatório
registra quem diagnosticou cada grupo.

Os dois classificadores seguem o mesmo contrato (Protocol Classificador),
então esta função não sabe nem precisa saber qual é a IA e qual são as
regras. Isso é polimorfismo.
"""

import logging
from dataclasses import dataclass

from agrupamento import Grupo
from diagnostico import Classificador, Diagnostico

# Um logger por módulo, com o nome do módulo. É o padrão em projetos Python.
logger = logging.getLogger(__name__)


@dataclass
class Analise:
    """Um grupo, o diagnóstico dele e quem diagnosticou."""

    grupo: Grupo
    diagnostico: Diagnostico
    origem: str  # o nome do classificador: "ia" ou "regras"


def diagnosticar_em_cascata(
    grupos: list[Grupo],
    principal: Classificador | None,
    reserva: Classificador,
) -> list[Analise]:
    """Diagnostica cada grupo com o principal e, se ele falhar, com a reserva."""
    analises: list[Analise] = []

    for grupo in grupos:
        if principal is not None:
            try:
                diagnostico = principal.diagnosticar(grupo)
                analises.append(Analise(grupo, diagnostico, principal.nome))
                continue  # deu certo: vai para o próximo grupo
            except Exception as erro:
                # Em geral, capturar Exception (qualquer erro) é má prática,
                # porque esconde bugs. Aqui é a intenção: qualquer falha da IA
                # (rede, chave, tempo esgotado, resposta fora do formato) leva
                # ao plano B. E o erro não some: fica registrado no log.
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
