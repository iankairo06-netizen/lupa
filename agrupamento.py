"""Agrupamento de eventos.

Junta os eventos que representam o mesmo problema em um grupo só, com a
contagem, a primeira e a última ocorrência e alguns exemplos. É isso que
reduz centenas de eventos a poucos problemas, e são só os grupos que vão
para a IA.

Para ver funcionando:
    python agrupamento.py
"""

import re
from dataclasses import dataclass, field
from datetime import datetime

from leitura import Evento
from mascara import mascarar

# Ordem de gravidade dos níveis do log: quanto maior o número, mais grave.
NIVEIS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

# Quantas linhas do fim do traceback guardar. As últimas linhas dizem onde
# o erro aconteceu e qual foi o erro; o começo costuma ser repetitivo.
LINHAS_DO_TRACEBACK = 3

NUMERO = re.compile(r"\d+")


@dataclass
class Grupo:
    """Um problema do log: eventos com a mesma assinatura."""

    assinatura: str
    nivel: str
    modulo: str
    quantidade: int
    primeiro: datetime
    ultimo: datetime
    exemplos: list[str] = field(default_factory=list)  # mensagens já mascaradas
    trecho_traceback: list[str] = field(default_factory=list)  # já mascarado


def normalizar(texto: str) -> str:
    """Mascara dados sensíveis e troca qualquer número por <N>."""
    return NUMERO.sub("<N>", mascarar(texto))


def assinatura(evento: Evento) -> str:
    """Texto que é igual para todos os eventos do mesmo problema.

    Os números variam de um evento para outro ("6467ms", "2375ms") e não
    mudam o problema, então viram <N>. O erro do traceback entra na
    assinatura porque a mesma mensagem pode esconder erros diferentes.
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
    """Agrupa os eventos a partir de nivel_minimo, do problema mais grave ao menos grave."""
    limite = NIVEIS[nivel_minimo]

    # Dicionário: para cada assinatura, o grupo correspondente.
    # Buscar uma chave num dicionário é instantâneo, mesmo com milhares de grupos.
    grupos: dict[str, Grupo] = {}

    for evento in eventos:
        if NIVEIS.get(evento.nivel, 0) < limite:
            continue

        chave = assinatura(evento)
        grupo = grupos.get(chave)  # None se a assinatura ainda não apareceu

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
        # min e max, em vez de supor que o log está em ordem de horário.
        grupo.primeiro = min(grupo.primeiro, evento.momento)
        grupo.ultimo = max(grupo.ultimo, evento.momento)

        exemplo = mascarar(evento.mensagem)
        if len(grupo.exemplos) < max_exemplos and exemplo not in grupo.exemplos:
            grupo.exemplos.append(exemplo)

    # Ordena pelo nível e, dentro do mesmo nível, pela quantidade.
    # reverse=True coloca o mais grave e o mais frequente primeiro.
    return sorted(
        grupos.values(),
        key=lambda grupo: (NIVEIS[grupo.nivel], grupo.quantidade),
        reverse=True,
    )


if __name__ == "__main__":
    from pathlib import Path

    from leitura import ler_eventos

    eventos = ler_eventos(Path("logs_exemplo/app.log"))
    grupos = agrupar(eventos)

    total_agrupado = sum(grupo.quantidade for grupo in grupos)
    print(f"{len(eventos)} eventos → {total_agrupado} de WARNING para cima → {len(grupos)} grupos\n")

    for grupo in grupos:
        print(f"{grupo.quantidade:>4}x  {grupo.nivel:<8}  [{grupo.modulo}]  {grupo.exemplos[0]}")

    # O primeiro grupo da lista (o mais grave) que tem traceback.
    exemplo = next(grupo for grupo in grupos if grupo.trecho_traceback)
    print("\nDetalhe do grupo mais grave com traceback:")
    print(f"  assinatura: {exemplo.assinatura}")
    print(f"  quantidade: {exemplo.quantidade}")
    print(f"  período:    {exemplo.primeiro:%H:%M} até {exemplo.ultimo:%H:%M}")
    print("  exemplos:")
    for mensagem in exemplo.exemplos:
        print(f"    {mensagem}")
    print("  fim do traceback:")
    for linha in exemplo.trecho_traceback:
        print(f"    {linha}")
