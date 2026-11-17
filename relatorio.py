"""Relatório em Markdown a partir das análises.

Os problemas são ordenados pela gravidade do diagnóstico, e não pelo nível
do log: o nível é escolha de quem escreveu a mensagem, não medida de impacto.
"""

from collections import Counter
from datetime import datetime

from cascata import Analise

ORDEM_GRAVIDADE = {"critica": 4, "alta": 3, "media": 2, "baixa": 1}

ROTULO_GRAVIDADE = {"critica": "Crítica", "alta": "Alta", "media": "Média", "baixa": "Baixa"}

ROTULO_CATEGORIA = {
    "banco_de_dados": "Banco de dados",
    "integracao_externa": "Integração externa",
    "dados_invalidos": "Dados inválidos",
    "bug": "Bug",
    "desempenho": "Desempenho",
    "seguranca": "Segurança",
    "outro": "Outro",
}

ROTULO_DADO = {
    "email": "e-mails",
    "ip": "IPs",
    "cpf": "CPFs",
    "matricula": "matrículas",
    "telefone": "telefones",
    "segredo": "chaves/senhas",
}


def ordenar(analises: list[Analise]) -> list[Analise]:
    return sorted(
        analises,
        key=lambda analise: (
            ORDEM_GRAVIDADE[analise.diagnostico.gravidade],
            analise.grupo.quantidade,
        ),
        reverse=True,
    )


def periodo(analise: Analise) -> str:
    grupo = analise.grupo
    if grupo.primeiro == grupo.ultimo:
        return f"às {grupo.primeiro:%H:%M}"
    return f"{grupo.primeiro:%H:%M} a {grupo.ultimo:%H:%M}"


def gerar_relatorio(
    analises: list[Analise],
    arquivo_log: str,
    total_eventos: int,
    mascarados: Counter[str],
    gerado_em: datetime | None = None,
) -> str:
    gerado_em = gerado_em or datetime.now()
    analises = ordenar(analises)
    origens = Counter(analise.origem for analise in analises)
    total_agrupado = sum(analise.grupo.quantidade for analise in analises)

    linhas: list[str] = [
        "# Relatório da Lupa",
        "",
        f"- **Arquivo:** `{arquivo_log}`",
        f"- **Gerado em:** {gerado_em:%d/%m/%Y %H:%M}",
        f"- **Eventos lidos:** {total_eventos}",
        f"- **Eventos analisados:** {total_agrupado}, agrupados em {len(analises)} problemas",
        "- **Diagnóstico por:** "
        + ", ".join(f"{origem} ({quantidade})" for origem, quantidade in origens.most_common()),
    ]

    if mascarados:
        resumo = ", ".join(
            f"{quantidade} {ROTULO_DADO.get(nome, nome)}"
            for nome, quantidade in mascarados.most_common()
        )
        linhas.append(f"- **Dados sensíveis mascarados:** {resumo}")

    linhas += [
        "",
        "## Problemas",
        "",
        "| # | Gravidade | Categoria | Módulo | Ocorrências | Período | Diagnóstico por |",
        "|---|---|---|---|---|---|---|",
    ]
    for numero, analise in enumerate(analises, start=1):
        diagnostico = analise.diagnostico
        linhas.append(
            f"| {numero} "
            f"| {ROTULO_GRAVIDADE[diagnostico.gravidade]} "
            f"| {ROTULO_CATEGORIA[diagnostico.categoria]} "
            f"| {analise.grupo.modulo} "
            f"| {analise.grupo.quantidade} "
            f"| {periodo(analise)} "
            f"| {analise.origem} |"
        )

    linhas += ["", "## Detalhes"]
    for numero, analise in enumerate(analises, start=1):
        grupo = analise.grupo
        diagnostico = analise.diagnostico
        linhas += [
            "",
            f"### {numero}. {grupo.exemplos[0]}",
            "",
            f"- **Gravidade:** {ROTULO_GRAVIDADE[diagnostico.gravidade]}"
            f" ({ROTULO_CATEGORIA[diagnostico.categoria]})",
            f"- **Módulo:** {grupo.modulo} | **Nível no log:** {grupo.nivel}",
            f"- **Ocorrências:** {grupo.quantidade} ({periodo(analise)})",
            f"- **Causa provável:** {diagnostico.causa_provavel}",
            f"- **Ação sugerida:** {diagnostico.acao_sugerida}",
            f"- **Diagnóstico por:** {analise.origem}",
        ]
        if len(grupo.exemplos) > 1 or grupo.trecho_traceback:
            linhas += ["", "```"]
            linhas += grupo.exemplos
            if grupo.trecho_traceback:
                linhas += ["...", *grupo.trecho_traceback]
            linhas.append("```")

    return "\n".join(linhas) + "\n"
