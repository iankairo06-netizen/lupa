# Lupa: analisador de logs com IA

Protótipo de estudo. A Lupa lê um arquivo de log, junta os eventos que representam o mesmo problema, mascara dados sensíveis e diagnostica cada problema com regras e com um LLM (via LangChain), com resposta tipada pelo Pydantic.

O log em `logs_exemplo/app.log` é fictício, gerado para o estudo. Não tem nenhum dado real.

## Como funciona

```
logs_exemplo/app.log          423 linhas
  → leitura.py                231 eventos (cada traceback junto do seu evento)
  → agrupamento.py            8 grupos (de WARNING para cima), já mascarados por mascara.py
  → cascata.py                para cada grupo: tenta a IA (ia.py); se falhar, usa as regras (diagnostico.py)
  → relatorio.py              relatório em Markdown, do problema mais grave ao menos grave
```

`main.py` junta tudo. Um exemplo de saída está em [`exemplos/relatorio_regras.md`](exemplos/relatorio_regras.md).

| Arquivo | O que faz |
|---|---|
| `leitura.py` | Lê o log e junta as linhas de continuação (tracebacks) ao evento anterior |
| `mascara.py` | Troca e-mail, CPF, IP, telefone, matrícula e chaves de API por marcadores (`<EMAIL>`, `<CPF>`...) |
| `agrupamento.py` | Agrupa eventos pela assinatura (mensagem normalizada + erro do traceback) |
| `diagnostico.py` | Modelo `Diagnostico` (Pydantic), contrato `Classificador` e `ClassificadorRegras` |
| `ia.py` | `ClassificadorIA`: LangChain com exemplos no prompt (few-shot) e saída estruturada |
| `cascata.py` | Tenta o classificador principal (IA) e, se ele falhar, usa o reserva (regras) |
| `relatorio.py` | Gera o relatório em Markdown: resumo, tabela de problemas e detalhes |
| `main.py` | Linha de comando: do arquivo de log ao relatório |

## Decisões

- **Máscara antes da IA.** O texto enviado à API de um LLM sai da empresa. O agrupamento já entrega exemplos e tracebacks mascarados, então o dado sensível nem chega ao código da IA.
- **Agrupar antes de diagnosticar.** A IA recebe 8 problemas resumidos, e não 423 linhas: menos custo, resposta mais rápida e menos ruído.
- **Saída tipada.** O `Diagnostico` usa `Literal` para gravidade e categoria. Resposta fora do formato vira erro na hora, em vez de chegar quebrada ao relatório.
- **Regras e IA com o mesmo contrato.** `ClassificadorRegras` e `ClassificadorIA` seguem o `Protocol Classificador` (`nome` e `diagnosticar(grupo)`), então um pode substituir o outro.
- **Cascata com plano B.** Se a IA falhar num grupo (rede, chave, tempo esgotado, resposta fora do formato), aquele grupo é diagnosticado pelas regras e o erro fica registrado no log. Sem IA configurada, tudo vai pelas regras. O relatório mostra quem diagnosticou cada problema.
- **Ordem pela gravidade do diagnóstico.** O relatório ordena pelo impacto avaliado no diagnóstico, e não pelo nível do log, que é só o que o programador escolheu ao escrever a mensagem.
- **Provedor configurável.** O modelo vem de `LUPA_MODELO` no `.env` (formato `provedor:modelo`). Trocar de provedor não exige mudar código.
- **Testes sem rede.** Os testes da IA usam um modelo falso que imita o LangChain: rodam sem chave, sem internet e sem custo.

## Como rodar

Requer Python 3.12.

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest
```

Gerar o relatório:

```
python main.py logs_exemplo/app.log              # usa a IA, se configurada; senão, as regras
python main.py logs_exemplo/app.log --sem-ia     # só as regras
python main.py --help                            # todas as opções
```

Cada etapa também pode ser vista sozinha:

```
python leitura.py
python mascara.py
python agrupamento.py
python diagnostico.py
python ia.py --mostrar-prompt    # mostra o prompt enviado ao LLM, sem chamar a API
```

Para usar o LLM de verdade:

1. `cp .env.example .env` e preencha `LUPA_MODELO` e a chave do provedor.
2. Descomente o pacote do provedor no `requirements.txt` e rode o `pip install` de novo.
3. `python ia.py` (só os 3 problemas mais graves) ou `python main.py logs_exemplo/app.log`

## Situação

- [x] Leitura, máscara, agrupamento e diagnóstico por regras, com testes
- [x] Diagnóstico com LLM (código e testes com modelo falso)
- [x] Relatório em Markdown e `main.py` com a cascata IA → regras
- [ ] Testar a chamada real ao LLM (aguardando a definição do provedor)

## Limitações conhecidas

- A máscara reconhece só os formatos das regras. Um CPF sem pontuação ou o nome de uma pessoa passam direto.
- A leitura espera o formato `data hora,ms NÍVEL [módulo] mensagem`. Logs em JSON ainda não são lidos.
- As regras de diagnóstico cobrem só os problemas previstos. Os outros caem em "outro", com a gravidade do nível do log.
