"""Diagnóstico por regras.

Define três coisas:
- Diagnostico: o formato de um diagnóstico, validado pelo Pydantic;
- Classificador: o contrato que todo classificador segue;
- ClassificadorRegras: um classificador que usa palavras-chave.

As regras têm dois papéis no projeto:
- linha de base: um diagnóstico que funciona sem IA, sem custo e sem rede;
- plano B: quando a IA falhar, o programa usa as regras no lugar dela.

Para ver funcionando:
    python diagnostico.py
"""

from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from agrupamento import Grupo

# Literal diz quais valores são aceitos. Qualquer outro valor é recusado.
# Os valores não têm acento nem espaço porque são valores de código, não texto
# para pessoas: assim não há erro de digitação nem de codificação.
Gravidade = Literal["baixa", "media", "alta", "critica"]
Categoria = Literal[
    "banco_de_dados",
    "integracao_externa",
    "dados_invalidos",
    "bug",
    "desempenho",
    "seguranca",
    "outro",
]


class Diagnostico(BaseModel):
    """O que se sabe sobre um problema e o que fazer com ele.

    Herda de BaseModel, do Pydantic: ao criar um Diagnostico, o Pydantic
    confere cada campo e recusa o que estiver fora do formato. As descrições
    dos campos também são enviadas à IA na Parte 5, para ela saber o que
    preencher em cada um.
    """

    # frozen=True: depois de criado, o diagnóstico não pode ser alterado.
    model_config = ConfigDict(frozen=True)

    gravidade: Gravidade = Field(
        description="Impacto do problema: baixa, media, alta ou critica."
    )
    categoria: Categoria = Field(description="Tipo de problema.")
    causa_provavel: str = Field(
        min_length=1,
        description="Causa mais provável, em uma ou duas frases.",
    )
    acao_sugerida: str = Field(
        min_length=1,
        description="Próximo passo concreto para investigar ou resolver.",
    )


class Classificador(Protocol):
    """Contrato: qualquer classe com estes membros serve como classificador.

    Não é preciso herdar desta classe. Basta ter um atributo "nome" e um
    método "diagnosticar" com esta assinatura. As regras (aqui) e a IA
    (Parte 5) cumprem o mesmo contrato, e por isso uma substitui a outra.
    """

    nome: str

    def diagnosticar(self, grupo: Grupo) -> Diagnostico: ...


@dataclass(frozen=True)
class RegraDiagnostico:
    """Se alguma das palavras aparecer no grupo, este é o diagnóstico."""

    palavras: tuple[str, ...]
    diagnostico: Diagnostico


# A ordem importa: vale a primeira regra que combinar.
REGRAS = [
    RegraDiagnostico(
        palavras=("TimeoutError", "conexão com o banco"),
        diagnostico=Diagnostico(
            gravidade="alta",
            categoria="banco_de_dados",
            causa_provavel="O banco não respondeu a tempo ou o pool de conexões esgotou.",
            acao_sugerida="Verificar a saúde do banco e o tamanho do pool de conexões.",
        ),
    ),
    RegraDiagnostico(
        palavras=("ZeroDivisionError",),
        diagnostico=Diagnostico(
            gravidade="alta",
            categoria="bug",
            causa_provavel="Um cálculo divide por um valor que pode ser zero.",
            acao_sugerida="Validar o divisor antes do cálculo e tratar o caso de zero.",
        ),
    ),
    RegraDiagnostico(
        palavras=("KeyError",),
        diagnostico=Diagnostico(
            gravidade="media",
            categoria="dados_invalidos",
            causa_provavel="Um registro chegou sem um campo obrigatório.",
            acao_sugerida="Validar os registros na entrada e rejeitar os incompletos com uma mensagem clara.",
        ),
    ),
    RegraDiagnostico(
        # Sem números soltos como "503": uma resposta de 5034ms seria
        # confundida com um erro 503.
        palavras=("Bad Gateway", "retornou 503", "HTTP 502", "HTTP 503"),
        diagnostico=Diagnostico(
            gravidade="media",
            categoria="integracao_externa",
            causa_provavel="Um serviço externo está fora do ar ou instável.",
            acao_sugerida="Verificar o status do serviço externo e se há novas tentativas automáticas.",
        ),
    ),
    RegraDiagnostico(
        palavras=("senha incorreta", "falha de login"),
        diagnostico=Diagnostico(
            gravidade="media",
            categoria="seguranca",
            causa_provavel="Tentativas de login com senha errada: erro do usuário ou tentativa de acesso indevido.",
            acao_sugerida="Verificar se as falhas se concentram em poucos IPs ou usuários.",
        ),
    ),
    RegraDiagnostico(
        palavras=("resposta lenta", "lento"),
        diagnostico=Diagnostico(
            gravidade="baixa",
            categoria="desempenho",
            causa_provavel="Requisições demorando mais que o esperado.",
            acao_sugerida="Medir quais consultas ou chamadas estão lentas nos horários afetados.",
        ),
    ),
]

# Quando nenhuma regra combina, a gravidade vem do nível do log.
GRAVIDADE_POR_NIVEL: dict[str, Gravidade] = {
    "CRITICAL": "critica",
    "ERROR": "media",
    "WARNING": "baixa",
}


class ClassificadorRegras:
    """Diagnostica um grupo procurando palavras-chave."""

    nome = "regras"

    def __init__(self, regras: list[RegraDiagnostico] | None = None) -> None:
        # Recebe as regras de fora (ou usa as padrão). Assim, os testes e
        # outros projetos podem usar regras próprias sem mexer nesta classe.
        self.regras = regras if regras is not None else REGRAS

    def diagnosticar(self, grupo: Grupo) -> Diagnostico:
        texto = " ".join([grupo.assinatura, *grupo.exemplos, *grupo.trecho_traceback])
        texto = texto.lower()

        for regra in self.regras:
            # any() é True se pelo menos uma palavra aparecer no texto.
            if any(palavra.lower() in texto for palavra in regra.palavras):
                return regra.diagnostico

        return Diagnostico(
            gravidade=GRAVIDADE_POR_NIVEL.get(grupo.nivel, "baixa"),
            categoria="outro",
            causa_provavel="Nenhuma regra conhecida para este problema.",
            acao_sugerida="Analisar o grupo manualmente.",
        )


if __name__ == "__main__":
    from pathlib import Path

    from pydantic import ValidationError

    from agrupamento import agrupar
    from leitura import ler_eventos

    grupos = agrupar(ler_eventos(Path("logs_exemplo/app.log")))
    classificador = ClassificadorRegras()

    for grupo in grupos:
        diagnostico = classificador.diagnosticar(grupo)
        print(
            f"{grupo.quantidade:>3}x  [{grupo.modulo}]  →  "
            f"{diagnostico.gravidade} / {diagnostico.categoria}"
        )
        print(f"       causa: {diagnostico.causa_provavel}")

    print("\nUm diagnóstico em JSON (o formato que a IA vai devolver na Parte 5):")
    print(classificador.diagnosticar(grupos[1]).model_dump_json(indent=2))

    print("\nO Pydantic recusa o que estiver fora do formato:")
    try:
        Diagnostico(
            gravidade="altíssima",
            categoria="banco_de_dados",
            causa_provavel="Banco fora do ar.",
            acao_sugerida="Reiniciar.",
        )
    except ValidationError as erro:
        print(f"  ValidationError: {erro.errors()[0]['msg']}")
