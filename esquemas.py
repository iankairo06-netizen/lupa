"""Formato dos dados que entram e saem da API.

O FastAPI usa estes modelos para validar o que chega (e responder 422 se
estiver errado) e para montar a documentação do Swagger.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from cascata import Analise
from diagnostico import Categoria, Gravidade
from pipeline import Resultado
from relatorio import ordenar

Nivel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

EXEMPLO_LOG = (
    "2026-11-10 07:00:33,754 INFO     [api] GET /api/faturas/334053 200 em 111ms\n"
    "2026-11-10 07:14:26,511 ERROR    [faturamento] Erro ao calcular consumo médio "
    "do cliente CPF 030.564.139-53 (matrícula 787277)\n"
    "Traceback (most recent call last):\n"
    '  File "/app/faturamento/consumo.py", line 47, in calcular_media\n'
    "ZeroDivisionError: division by zero\n"
    "2026-11-10 07:31:02,118 ERROR    [core.db] Falha ao obter conexão com o banco de dados\n"
)


class PedidoAnalise(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"conteudo": EXEMPLO_LOG, "nivel_minimo": "WARNING", "usar_ia": False}]
        }
    )

    conteudo: str = Field(min_length=1, description="Texto do log.")
    nivel_minimo: Nivel = Field(
        default="WARNING", description="Nível mínimo dos eventos analisados."
    )
    usar_ia: bool = Field(
        default=True, description="Tenta o LLM; se não estiver disponível, usa as regras."
    )


class Problema(BaseModel):
    gravidade: Gravidade
    categoria: Categoria
    modulo: str
    nivel_no_log: str
    ocorrencias: int
    primeira_ocorrencia: datetime
    ultima_ocorrencia: datetime
    exemplo: str
    causa_provavel: str
    acao_sugerida: str
    diagnostico_por: str


class ResumoAnalise(BaseModel):
    id: int
    criada_em: datetime
    nome_arquivo: str | None
    eventos_lidos: int
    total_problemas: int
    diagnostico_por: dict[str, int]


class AnaliseCompleta(ResumoAnalise):
    dados_mascarados: dict[str, int]
    problemas: list[Problema]


class Erro(BaseModel):
    detail: str


@dataclass
class Registro:
    """Uma análise guardada pela API."""

    id: int
    criada_em: datetime
    nome_arquivo: str | None
    resultado: Resultado


def para_problema(analise: Analise) -> Problema:
    grupo, diagnostico = analise.grupo, analise.diagnostico
    return Problema(
        gravidade=diagnostico.gravidade,
        categoria=diagnostico.categoria,
        modulo=grupo.modulo,
        nivel_no_log=grupo.nivel,
        ocorrencias=grupo.quantidade,
        primeira_ocorrencia=grupo.primeiro,
        ultima_ocorrencia=grupo.ultimo,
        exemplo=grupo.exemplos[0],
        causa_provavel=diagnostico.causa_provavel,
        acao_sugerida=diagnostico.acao_sugerida,
        diagnostico_por=analise.origem,
    )


def para_resumo(registro: Registro) -> ResumoAnalise:
    resultado = registro.resultado
    return ResumoAnalise(
        id=registro.id,
        criada_em=registro.criada_em,
        nome_arquivo=registro.nome_arquivo,
        eventos_lidos=resultado.eventos_lidos,
        total_problemas=len(resultado.analises),
        diagnostico_por=dict(Counter(analise.origem for analise in resultado.analises)),
    )


def para_analise_completa(registro: Registro) -> AnaliseCompleta:
    return AnaliseCompleta(
        **para_resumo(registro).model_dump(),
        dados_mascarados=dict(registro.resultado.mascarados),
        problemas=[para_problema(analise) for analise in ordenar(registro.resultado.analises)],
    )
