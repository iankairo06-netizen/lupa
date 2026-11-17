"""Máscara de dados sensíveis antes de qualquer texto sair para a IA.

Reconhece só os formatos das regras abaixo: um CPF sem pontuação ou o nome
de uma pessoa, por exemplo, não são mascarados.
"""

import re
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class Regra:
    nome: str
    padrao: re.Pattern[str]
    substituto: str


# A ordem importa: segredos primeiro, porque uma senha pode conter "@".
REGRAS = [
    Regra(
        nome="segredo",
        padrao=re.compile(r"(?i)\b(api_key|token|senha|password|secret)=[^\s,;)]+"),
        substituto=r"\1=<SEGREDO>",
    ),
    Regra(
        nome="email",
        padrao=re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
        substituto="<EMAIL>",
    ),
    Regra(
        nome="cpf",
        padrao=re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
        substituto="<CPF>",
    ),
    Regra(
        nome="telefone",
        padrao=re.compile(r"\(\d{2}\)\s?9?\d{4}-\d{4}"),
        substituto="<TELEFONE>",
    ),
    Regra(
        nome="ip",
        padrao=re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        substituto="<IP>",
    ),
    Regra(
        nome="matricula",
        padrao=re.compile(r"(?i)\b(matr[íi]cula\s+)\d+"),
        substituto=r"\1<MATRICULA>",
    ),
]


def mascarar_com_contagem(texto: str) -> tuple[str, Counter[str]]:
    contagem: Counter[str] = Counter()
    for regra in REGRAS:
        texto, quantidade = regra.padrao.subn(regra.substituto, texto)
        if quantidade:
            contagem[regra.nome] += quantidade
    return texto, contagem


def mascarar(texto: str) -> str:
    texto_mascarado, _ = mascarar_com_contagem(texto)
    return texto_mascarado
