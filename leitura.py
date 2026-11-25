"""Leitura do log (arquivo ou texto) em eventos."""

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# 2026-11-10 07:14:26,511 ERROR    [faturamento] Erro ao calcular consumo...
PADRAO_EVENTO = re.compile(
    r"^(?P<data>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3}\s+"
    r"(?P<nivel>[A-Z]+)\s+"
    r"\[(?P<modulo>[^\]]+)\]\s+"
    r"(?P<mensagem>.*)$"
)

FORMATO_DATA = "%Y-%m-%d %H:%M:%S"


@dataclass
class Evento:
    momento: datetime
    nivel: str
    modulo: str
    mensagem: str
    detalhes: list[str] = field(default_factory=list)

    @property
    def fim_traceback(self) -> str | None:
        """Última linha do traceback, que identifica o erro."""
        return self.detalhes[-1] if self.detalhes else None


def ler_eventos(caminho: Path) -> list[Evento]:
    with caminho.open(encoding="utf-8") as arquivo:
        return ler_linhas(arquivo)


def ler_linhas(linhas: Iterable[str]) -> list[Evento]:
    """Junta cada linha de continuação (traceback) ao evento anterior."""
    eventos: list[Evento] = []

    for linha in linhas:
        linha = linha.rstrip("\n")
        if not linha.strip():
            continue

        inicio = PADRAO_EVENTO.match(linha)
        if inicio:
            eventos.append(
                Evento(
                    momento=datetime.strptime(inicio["data"], FORMATO_DATA),
                    nivel=inicio["nivel"],
                    modulo=inicio["modulo"],
                    mensagem=inicio["mensagem"],
                )
            )
        elif eventos:
            eventos[-1].detalhes.append(linha)
        # Continuação antes do primeiro evento não tem a quem pertencer: é descartada.

    return eventos
