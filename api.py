"""Lupa pela HTTP: API com FastAPI.

Rodar:
    uvicorn api:app --reload --port 8080

Documentação interativa (Swagger): http://127.0.0.1:8080/docs
"""

from datetime import datetime
from itertools import count
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import PlainTextResponse

from esquemas import (
    AnaliseCompleta,
    Erro,
    Nivel,
    PedidoAnalise,
    Registro,
    ResumoAnalise,
    para_analise_completa,
    para_resumo,
)
from leitura import ler_linhas
from pipeline import analisar
from relatorio import gerar_relatorio

TAMANHO_MAXIMO = 5 * 1024 * 1024  # 5 MB

# Guardadas em memória: somem quando a API reinicia. Em produção, seria um banco.
ANALISES: dict[int, Registro] = {}
_ids = count(1)

app = FastAPI(
    title="Lupa",
    description=(
        "Analisador de logs com IA. Recebe um log, agrupa os eventos que são o mesmo "
        "problema, mascara dados sensíveis e diagnostica cada problema com o LLM "
        "(ou com regras, se o LLM não estiver disponível)."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "análises", "description": "Enviar logs e consultar os resultados."},
        {"name": "sistema", "description": "Estado da API."},
    ],
)

RESPOSTA_400 = {400: {"model": Erro, "description": "O conteúdo não tem nenhum evento de log reconhecível"}}
RESPOSTA_404 = {404: {"model": Erro, "description": "Análise não encontrada"}}


def processar(conteudo: str, nivel_minimo: str, usar_ia: bool, nome_arquivo: str | None) -> Registro:
    eventos = ler_linhas(conteudo.splitlines())
    if not eventos:
        raise HTTPException(
            status_code=400,
            detail=(
                "Nenhum evento de log reconhecido. Formato esperado: "
                "'AAAA-MM-DD HH:MM:SS,mmm NÍVEL [módulo] mensagem'."
            ),
        )

    registro = Registro(
        id=next(_ids),
        criada_em=datetime.now(),
        nome_arquivo=nome_arquivo,
        resultado=analisar(eventos, nivel_minimo, usar_ia),
    )
    ANALISES[registro.id] = registro
    return registro


def buscar(id_analise: int) -> Registro:
    registro = ANALISES.get(id_analise)
    if registro is None:
        raise HTTPException(status_code=404, detail=f"Análise {id_analise} não encontrada.")
    return registro


@app.get("/saude", tags=["sistema"], summary="Verifica se a API está no ar")
def saude() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/analises",
    status_code=201,
    tags=["análises"],
    summary="Analisa um log enviado como texto (JSON)",
    responses=RESPOSTA_400,
)
def criar_analise(pedido: PedidoAnalise, response: Response) -> AnaliseCompleta:
    registro = processar(pedido.conteudo, pedido.nivel_minimo, pedido.usar_ia, nome_arquivo=None)
    response.headers["Location"] = f"/analises/{registro.id}"
    return para_analise_completa(registro)


@app.post(
    "/analises/arquivo",
    status_code=201,
    tags=["análises"],
    summary="Analisa um arquivo de log (upload)",
    responses={
        **RESPOSTA_400,
        413: {"model": Erro, "description": "Arquivo maior que 5 MB"},
    },
)
def enviar_arquivo(
    response: Response,
    arquivo: Annotated[UploadFile, File(description="Arquivo de log em texto (UTF-8).")],
    nivel_minimo: Annotated[Nivel, Query(description="Nível mínimo dos eventos analisados.")] = "WARNING",
    usar_ia: Annotated[bool, Query(description="Tenta o LLM; se não estiver disponível, usa as regras.")] = True,
) -> AnaliseCompleta:
    dados = arquivo.file.read(TAMANHO_MAXIMO + 1)
    if len(dados) > TAMANHO_MAXIMO:
        raise HTTPException(status_code=413, detail="O arquivo passa de 5 MB.")

    try:
        conteudo = dados.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="O arquivo não é um texto em UTF-8.") from None

    registro = processar(conteudo, nivel_minimo, usar_ia, nome_arquivo=arquivo.filename)
    response.headers["Location"] = f"/analises/{registro.id}"
    return para_analise_completa(registro)


@app.get("/analises", tags=["análises"], summary="Lista as análises feitas")
def listar_analises() -> list[ResumoAnalise]:
    return [para_resumo(registro) for registro in ANALISES.values()]


@app.get(
    "/analises/{id_analise}",
    tags=["análises"],
    summary="Mostra uma análise com todos os problemas",
    responses=RESPOSTA_404,
)
def obter_analise(id_analise: int) -> AnaliseCompleta:
    return para_analise_completa(buscar(id_analise))


@app.get(
    "/analises/{id_analise}/relatorio",
    tags=["análises"],
    summary="Baixa o relatório da análise em Markdown",
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/markdown": {}}}, **RESPOSTA_404},
)
def obter_relatorio(id_analise: int) -> PlainTextResponse:
    registro = buscar(id_analise)
    texto = gerar_relatorio(
        registro.resultado.analises,
        arquivo_log=registro.nome_arquivo or "texto enviado pela API",
        total_eventos=registro.resultado.eventos_lidos,
        mascarados=registro.resultado.mascarados,
        gerado_em=registro.criada_em,
    )
    return PlainTextResponse(texto, media_type="text/markdown; charset=utf-8")


@app.delete(
    "/analises/{id_analise}",
    status_code=204,
    tags=["análises"],
    summary="Apaga uma análise",
    responses=RESPOSTA_404,
)
def apagar_analise(id_analise: int) -> Response:
    buscar(id_analise)
    del ANALISES[id_analise]
    return Response(status_code=204)
