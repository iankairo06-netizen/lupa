"""Diagnóstico de grupos: modelo, contrato dos classificadores e regras.

As regras funcionam sem IA e servem de plano B quando ela falha.
"""

from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from agrupamento import Grupo

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
    """As descrições dos campos também vão para a IA, como instrução."""

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
    nome: str

    def diagnosticar(self, grupo: Grupo) -> Diagnostico: ...


@dataclass(frozen=True)
class RegraDiagnostico:
    palavras: tuple[str, ...]
    diagnostico: Diagnostico


# Vale a primeira regra que combinar.
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
        # Sem códigos soltos como "503": "5034ms" seria confundido com o erro 503.
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

GRAVIDADE_POR_NIVEL: dict[str, Gravidade] = {
    "CRITICAL": "critica",
    "ERROR": "media",
    "WARNING": "baixa",
}


class ClassificadorRegras:
    nome = "regras"

    def __init__(self, regras: list[RegraDiagnostico] | None = None) -> None:
        self.regras = regras if regras is not None else REGRAS

    def diagnosticar(self, grupo: Grupo) -> Diagnostico:
        texto = " ".join([grupo.assinatura, *grupo.exemplos, *grupo.trecho_traceback]).lower()

        for regra in self.regras:
            if any(palavra.lower() in texto for palavra in regra.palavras):
                return regra.diagnostico

        return Diagnostico(
            gravidade=GRAVIDADE_POR_NIVEL.get(grupo.nivel, "baixa"),
            categoria="outro",
            causa_provavel="Nenhuma regra conhecida para este problema.",
            acao_sugerida="Analisar o grupo manualmente.",
        )
