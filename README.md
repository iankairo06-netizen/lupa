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

O núcleo (`pipeline.py`) tem duas portas de entrada: a linha de comando (`main.py`) e a API HTTP (`api.py`). Um exemplo de relatório está em [`exemplos/relatorio_regras.md`](exemplos/relatorio_regras.md).

| Arquivo | O que faz |
|---|---|
| `leitura.py` | Lê o log e junta as linhas de continuação (tracebacks) ao evento anterior |
| `mascara.py` | Troca e-mail, CPF, IP, telefone, matrícula e chaves de API por marcadores (`<EMAIL>`, `<CPF>`...) |
| `agrupamento.py` | Agrupa eventos pela assinatura (mensagem normalizada + erro do traceback) |
| `diagnostico.py` | Modelo `Diagnostico` (Pydantic), contrato `Classificador` e `ClassificadorRegras` |
| `ia.py` | `ClassificadorIA`: LangChain com exemplos no prompt (few-shot) e saída estruturada |
| `cascata.py` | Tenta o classificador principal (IA) e, se ele falhar, usa o reserva (regras) |
| `relatorio.py` | Gera o relatório em Markdown: resumo, tabela de problemas e detalhes |
| `pipeline.py` | Núcleo: de eventos a problemas diagnosticados, usado pela linha de comando e pela API |
| `main.py` | Linha de comando: do arquivo de log ao relatório |
| `esquemas.py` | Modelos Pydantic do que entra e sai da API |
| `api.py` | API HTTP com FastAPI, documentada no Swagger |

## Decisões

- **Máscara antes da IA.** O agrupamento já entrega exemplos e tracebacks mascarados, então o dado sensível nem chega ao código da IA. Mesmo com o modelo rodando localmente, o prompt pode ficar em logs do servidor ou ir para outro provedor no futuro.
- **Agrupar antes de diagnosticar.** A IA recebe 8 problemas resumidos, e não 423 linhas: menos custo, resposta mais rápida e menos ruído.
- **Saída tipada.** O `Diagnostico` usa `Literal` para gravidade e categoria. Resposta fora do formato vira erro na hora, em vez de chegar quebrada ao relatório.
- **Regras e IA com o mesmo contrato.** `ClassificadorRegras` e `ClassificadorIA` seguem o `Protocol Classificador` (`nome` e `diagnosticar(grupo)`), então um pode substituir o outro.
- **Cascata com plano B.** Se a IA falhar num grupo (rede, tempo esgotado, resposta fora do formato), aquele grupo é diagnosticado pelas regras e o erro fica registrado no log. Depois de 2 falhas seguidas, a IA deixa de ser chamada, para um servidor fora do ar não atrasar a execução inteira. Sem IA configurada, tudo vai pelas regras. O relatório mostra quem diagnosticou cada problema.
- **Ordem pela gravidade do diagnóstico.** O relatório ordena pelo impacto avaliado no diagnóstico, e não pelo nível do log, que é só o que o programador escolheu ao escrever a mensagem.
- **LLM local via vLLM.** O vLLM expõe uma API compatível com a da OpenAI, então o `ClassificadorIA` usa o provedor `openai` do LangChain apontando para `LUPA_BASE_URL`. A saída estruturada usa `method="json_schema"`: o servidor restringe a geração ao formato do `Diagnostico`. Trocar de modelo ou de provedor é só mudar o `.env`.
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
python main.py logs_exemplo/app.log                    # usa a IA, se configurada; senão, as regras
python main.py logs_exemplo/app.log --sem-ia           # só as regras
python main.py logs_exemplo/app.log --mostrar-prompt   # mostra o prompt enviado ao LLM, sem chamar a API
python main.py --help                                  # todas as opções
```

Para usar o LLM de verdade:

1. Confira o servidor e o nome do modelo: `wget -qO- http://ENDERECO:8000/v1/models` (o nome é o campo `"id"`).
2. `cp .env.example .env` e preencha `LUPA_MODELO` e `LUPA_BASE_URL`.
3. `python main.py logs_exemplo/app.log`

## API (FastAPI)

```
uvicorn api:app --reload --port 8080
```

A documentação interativa (Swagger) fica em http://127.0.0.1:8080/docs: dá para testar cada rota pelo navegador, em **Try it out**. A porta 8080 evita conflito com o vLLM, que costuma usar a 8000.

| Método | Rota | O que faz | Respostas |
|---|---|---|---|
| GET | `/saude` | Verifica se a API está no ar | 200 |
| POST | `/analises` | Analisa um log enviado como texto (JSON) | 201, 400, 422 |
| POST | `/analises/arquivo` | Analisa um arquivo de log (upload) | 201, 400, 413, 422 |
| GET | `/analises` | Lista as análises feitas | 200 |
| GET | `/analises/{id}` | Mostra uma análise com todos os problemas | 200, 404, 422 |
| GET | `/analises/{id}/relatorio` | Relatório em Markdown | 200, 404, 422 |
| DELETE | `/analises/{id}` | Apaga uma análise | 204, 404, 422 |

- **200 OK:** deu certo e a resposta traz dados.
- **201 Created:** um recurso novo foi criado; o cabeçalho `Location` diz onde ele está.
- **204 No Content:** deu certo e não há nada para devolver.
- **400 Bad Request:** o pedido chegou no formato certo, mas não dá para processar (texto sem nenhum evento de log, arquivo que não é UTF-8).
- **404 Not Found:** o recurso pedido não existe.
- **413 Content Too Large:** arquivo maior que 5 MB.
- **422 Unprocessable Content:** o pedido não passou na validação (campo faltando, tipo errado, valor fora da lista). O FastAPI responde sozinho, a partir dos modelos do `esquemas.py`.
- **500 Internal Server Error:** erro inesperado no servidor. A API não devolve 500 de propósito; se a IA falhar, as regras assumem.

As análises ficam em memória e somem quando a API reinicia. Em produção, seriam guardadas num banco de dados.

## Situação

- [x] Leitura, máscara, agrupamento e diagnóstico por regras, com testes
- [x] Diagnóstico com LLM (código e testes com modelo falso)
- [x] Relatório em Markdown e `main.py` com a cascata IA → regras
- [x] API HTTP com FastAPI e Swagger
- [ ] Testar a chamada real ao vLLM (aguardando acesso à workstation)

## Limitações conhecidas

- A máscara reconhece só os formatos das regras. Um CPF sem pontuação ou o nome de uma pessoa passam direto.
- A leitura espera o formato `data hora,ms NÍVEL [módulo] mensagem`. Logs em JSON ainda não são lidos.
- As regras de diagnóstico cobrem só os problemas previstos. Os outros caem em "outro", com a gravidade do nível do log.
