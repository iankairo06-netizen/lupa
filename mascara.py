"""Máscara de dados sensíveis.

Troca dados pessoais e segredos por marcadores, como <EMAIL> e <CPF>, antes
que qualquer texto do log saia da máquina (por exemplo, para a API de IA).

Atenção: a máscara reconhece só os formatos descritos nas regras abaixo.
Um CPF sem pontuação ou o nome de uma pessoa, por exemplo, passam direto.
Ela é uma rede de segurança, não uma garantia.

Para ver funcionando:
    python mascara.py
"""

import re
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class Regra:
    """Um tipo de dado sensível e como escondê-lo."""

    nome: str
    padrao: re.Pattern[str]
    substituto: str


# A ordem importa: as regras são aplicadas de cima para baixo.
# Os segredos vêm primeiro porque uma senha pode conter "@" e ser confundida
# com um e-mail.
REGRAS = [
    Regra(
        nome="segredo",
        # api_key=..., token=..., senha=... até um espaço, vírgula, ";" ou ")".
        # (?i) faz a regra ignorar maiúsculas e minúsculas.
        # \1 no substituto repete o que foi capturado no primeiro parêntese
        # (o nome do campo), para o resultado ficar "api_key=<SEGREDO>".
        padrao=re.compile(r"(?i)\b(api_key|token|senha|password|secret)=[^\s,;)]+"),
        substituto=r"\1=<SEGREDO>",
    ),
    Regra(
        nome="email",
        # algo@dominio.com, algo@dominio.com.br...
        padrao=re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
        substituto="<EMAIL>",
    ),
    Regra(
        nome="cpf",
        # 000.000.000-00
        padrao=re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
        substituto="<CPF>",
    ),
    Regra(
        nome="telefone",
        # (85) 96514-2674 ou (85) 3101-1234
        padrao=re.compile(r"\(\d{2}\)\s?9?\d{4}-\d{4}"),
        substituto="<TELEFONE>",
    ),
    Regra(
        nome="ip",
        # 189.51.194.72
        padrao=re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        substituto="<IP>",
    ),
    Regra(
        nome="matricula",
        # "matrícula 787277" (identifica o cliente)
        padrao=re.compile(r"(?i)\b(matr[íi]cula\s+)\d+"),
        substituto=r"\1<MATRICULA>",
    ),
]


def mascarar_com_contagem(texto: str) -> tuple[str, Counter[str]]:
    """Mascara o texto e conta quantos dados de cada tipo foram escondidos."""
    contagem: Counter[str] = Counter()
    for regra in REGRAS:
        # subn substitui e devolve duas coisas: o texto novo e quantas trocas fez.
        texto, quantidade = regra.padrao.subn(regra.substituto, texto)
        if quantidade:
            contagem[regra.nome] += quantidade
    return texto, contagem


def mascarar(texto: str) -> str:
    """Devolve o texto com os dados sensíveis trocados por marcadores."""
    texto_mascarado, _ = mascarar_com_contagem(texto)
    return texto_mascarado


if __name__ == "__main__":
    # Os imports ficam aqui dentro porque só esta demonstração usa a leitura.
    # Assim, a máscara continua independente: funciona com qualquer texto.
    from pathlib import Path

    from leitura import ler_eventos

    eventos = ler_eventos(Path("logs_exemplo/app.log"))

    total: Counter[str] = Counter()
    tipos_ja_mostrados: set[str] = set()

    print("Um exemplo de cada tipo de dado (antes → depois):\n")
    for evento in eventos:
        for texto in [evento.mensagem, *evento.detalhes]:
            mascarado, contagem = mascarar_com_contagem(texto)
            total += contagem

            tipos_novos = set(contagem) - tipos_ja_mostrados
            if tipos_novos:
                print(f"  {texto}")
                print(f"  → {mascarado}\n")
                tipos_ja_mostrados |= tipos_novos

    print("Dados mascarados no log inteiro:")
    for nome, quantidade in total.most_common():
        print(f"  {nome}: {quantidade}")
