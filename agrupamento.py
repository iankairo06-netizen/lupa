"""Agrupamento de eventos que representam o mesmo problema.

Exemplos e tracebacks saem daqui já mascarados: nada sensível chega à IA.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime

from leitura import Evento
from mascara import mascarar

NIVEIS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

# O fim do traceback diz onde e qual foi o erro; o começo costuma se repetir.
LINHAS_DO_TRACEBACK = 3

NUMERO = re.compile(r"\d+")


@dataclass
class Grupo:
    assinatura: str
    nivel: str
    modulo: str
    quantidade: int
    primeiro: datetime
    ultimo: datetime
    exemplos: list[str] = field(default_factory=list)
    trecho_traceback: list[str] = field(default_factory=list)


def normalizar(texto: str) -> str:
    return NUMERO.sub("<N>", mascarar(texto))


def assinatura(evento: Evento) -> str:
    """Igual para todos os eventos do mesmo problema.

    Números viram <N> ("6467ms" e "2375ms" são o mesmo problema). O erro do
    traceback entra porque a mesma mensagem pode esconder erros diferentes.
    """
    partes = [evento.nivel, f"[{evento.modulo}]", normalizar(evento.mensagem)]
    if evento.fim_traceback:
        partes.append("| " + normalizar(evento.fim_traceback))
    return " ".join(partes)


def agrupar(
    eventos: list[Evento],
    nivel_minimo: str = "WARNING",
    max_exemplos: int = 3,
) -> list[Grupo]:
    """Agrupa os eventos a partir de nivel_minimo, do mais grave ao menos grave."""
    limite = NIVEIS[nivel_minimo]
    grupos: dict[str, Grupo] = {}

    for evento in eventos:
        if NIVEIS.get(evento.nivel, 0) < limite:
            continue

        chave = assinatura(evento)
        grupo = grupos.get(chave)
        if grupo is None:
            grupo = Grupo(
                assinatura=chave,
                nivel=evento.nivel,
                modulo=evento.modulo,
                quantidade=0,
                primeiro=evento.momento,
                ultimo=evento.momento,
                trecho_traceback=[
                    mascarar(linha) for linha in evento.detalhes[-LINHAS_DO_TRACEBACK:]
                ],
            )
            grupos[chave] = grupo

        grupo.quantidade += 1
        # min/max porque logs de vários servidores podem vir fora de ordem.
        grupo.primeiro = min(grupo.primeiro, evento.momento)
        grupo.ultimo = max(grupo.ultimo, evento.momento)

        exemplo = mascarar(evento.mensagem)
        if len(grupo.exemplos) < max_exemplos and exemplo not in grupo.exemplos:
            grupo.exemplos.append(exemplo)

    return sorted(
        grupos.values(),
        key=lambda grupo: (NIVEIS[grupo.nivel], grupo.quantidade),
        reverse=True,
    )
