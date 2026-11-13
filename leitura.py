"""Leitura do arquivo de log.

Transforma as linhas do arquivo em eventos. Um evento é uma linha que começa
com data e hora, junto com as linhas de continuação que vêm logo depois dela
(por exemplo, as linhas de um traceback).

Para ver funcionando:
    python leitura.py
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Expressão regular (regex) que reconhece a linha de início de um evento:
#
#   2026-11-10 07:14:26,511 ERROR    [faturamento] Erro ao calcular consumo...
#   └──── data e hora ────┘ └nível┘  └─ módulo ──┘ └────── mensagem ───────┘
#
# Cada (?P<nome>...) captura um pedaço da linha e dá um nome a ele, para
# depois pegarmos o pedaço pelo nome: inicio["nivel"], inicio["modulo"]...
#   \d{4}    exatamente 4 dígitos
#   \s+      um ou mais espaços
#   [A-Z]+   uma ou mais letras maiúsculas
#   [^\]]+   um ou mais caracteres que não sejam "]"
#   .*       qualquer coisa até o fim da linha
PADRAO_EVENTO = re.compile(
    r"^(?P<data>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3}\s+"
    r"(?P<nivel>[A-Z]+)\s+"
    r"\[(?P<modulo>[^\]]+)\]\s+"
    r"(?P<mensagem>.*)$"
)

# Formato da data no log, usado para transformar o texto em um datetime.
FORMATO_DATA = "%Y-%m-%d %H:%M:%S"


@dataclass
class Evento:
    """Um acontecimento registrado no log."""

    momento: datetime
    nivel: str  # INFO, WARNING, ERROR ou CRITICAL
    modulo: str  # parte do sistema que gerou o evento
    mensagem: str
    detalhes: list[str] = field(default_factory=list)  # linhas de continuação

    @property
    def fim_traceback(self) -> str | None:
        """Última linha do traceback, que diz qual foi o erro. None se não houver."""
        if self.detalhes:
            return self.detalhes[-1]
        return None


def ler_eventos(caminho: Path) -> list[Evento]:
    """Lê o arquivo de log e devolve os eventos, na ordem em que aparecem."""
    eventos: list[Evento] = []

    with caminho.open(encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.rstrip("\n")
            if not linha.strip():
                continue  # pula linhas em branco

            inicio = PADRAO_EVENTO.match(linha)
            if inicio:
                # A linha começa um evento novo.
                eventos.append(
                    Evento(
                        momento=datetime.strptime(inicio["data"], FORMATO_DATA),
                        nivel=inicio["nivel"],
                        modulo=inicio["modulo"],
                        mensagem=inicio["mensagem"],
                    )
                )
            elif eventos:
                # A linha é continuação: pertence ao último evento lido.
                eventos[-1].detalhes.append(linha)
            # Se a primeira linha do arquivo já for uma continuação, não existe
            # evento para ela pertencer, então ela é descartada.

    return eventos


# Este bloco só roda quando você executa "python leitura.py".
# Quando outro arquivo faz "from leitura import ler_eventos", ele não roda.
if __name__ == "__main__":
    eventos = ler_eventos(Path("logs_exemplo/app.log"))

    print(f"{len(eventos)} eventos lidos")

    # Counter conta quantas vezes cada valor aparece.
    por_nivel = Counter(evento.nivel for evento in eventos)
    for nivel, quantidade in por_nivel.most_common():
        print(f"  {nivel}: {quantidade}")

    # Lista só com os eventos que têm traceback (list comprehension).
    com_traceback = [evento for evento in eventos if evento.detalhes]
    print(f"{len(com_traceback)} eventos com traceback")

    print("\nExemplo de evento com traceback:")
    exemplo = com_traceback[0]
    print(f"  momento:  {exemplo.momento}")
    print(f"  nível:    {exemplo.nivel}")
    print(f"  módulo:   {exemplo.modulo}")
    print(f"  mensagem: {exemplo.mensagem}")
    print(f"  detalhes: {len(exemplo.detalhes)} linhas")
    print(f"  erro:     {exemplo.fim_traceback}")
