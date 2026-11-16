# Relatório da Lupa

- **Arquivo:** `logs_exemplo/app.log`
- **Gerado em:** 16/11/2026 09:03
- **Eventos lidos:** 231
- **Eventos analisados:** 84, agrupados em 8 problemas
- **Diagnóstico por:** regras (8)
- **Dados sensíveis mascarados:** 61 e-mails, 61 IPs, 13 CPFs, 13 matrículas, 10 telefones, 4 chaves/senhas

## Problemas

| # | Gravidade | Categoria | Módulo | Ocorrências | Período | Diagnóstico por |
|---|---|---|---|---|---|---|
| 1 | Crítica | Outro | ordens_servico | 1 | às 07:53 | regras |
| 2 | Alta | Bug | faturamento | 13 | 07:14 a 11:54 | regras |
| 3 | Alta | Banco de dados | core.db | 7 | 07:31 a 11:56 | regras |
| 4 | Média | Segurança | auth | 16 | 07:03 a 11:31 | regras |
| 5 | Média | Dados inválidos | leituras | 12 | 07:16 a 10:53 | regras |
| 6 | Média | Integração externa | notificacoes | 10 | 07:04 a 11:18 | regras |
| 7 | Média | Integração externa | pagamentos | 4 | 07:27 a 10:07 | regras |
| 8 | Baixa | Desempenho | api | 21 | 07:01 a 11:28 | regras |

## Detalhes

### 1. Fila de ordens de serviço parada com 375 itens pendentes

- **Gravidade:** Crítica (Outro)
- **Módulo:** ordens_servico | **Nível no log:** CRITICAL
- **Ocorrências:** 1 (às 07:53)
- **Causa provável:** Nenhuma regra conhecida para este problema.
- **Ação sugerida:** Analisar o grupo manualmente.
- **Diagnóstico por:** regras

### 2. Erro ao calcular consumo médio do cliente CPF <CPF> (matrícula <MATRICULA>)

- **Gravidade:** Alta (Bug)
- **Módulo:** faturamento | **Nível no log:** ERROR
- **Ocorrências:** 13 (07:14 a 11:54)
- **Causa provável:** Um cálculo divide por um valor que pode ser zero.
- **Ação sugerida:** Validar o divisor antes do cálculo e tratar o caso de zero.
- **Diagnóstico por:** regras

```
Erro ao calcular consumo médio do cliente CPF <CPF> (matrícula <MATRICULA>)
...
  File "/app/faturamento/consumo.py", line 47, in calcular_media
    return total_m3 / dias_lidos
ZeroDivisionError: division by zero
```

### 3. Falha ao obter conexão com o banco de dados

- **Gravidade:** Alta (Banco de dados)
- **Módulo:** core.db | **Nível no log:** ERROR
- **Ocorrências:** 7 (07:31 a 11:56)
- **Causa provável:** O banco não respondeu a tempo ou o pool de conexões esgotou.
- **Ação sugerida:** Verificar a saúde do banco e o tamanho do pool de conexões.
- **Diagnóstico por:** regras

```
Falha ao obter conexão com o banco de dados
...
  File "/app/core/pool.py", line 201, in get
    raise TimeoutError("sem conexão disponível após 30s")
TimeoutError: sem conexão disponível após 30s
```

### 4. Falha de login para <EMAIL> a partir de <IP> (senha incorreta)

- **Gravidade:** Média (Segurança)
- **Módulo:** auth | **Nível no log:** WARNING
- **Ocorrências:** 16 (07:03 a 11:31)
- **Causa provável:** Tentativas de login com senha errada: erro do usuário ou tentativa de acesso indevido.
- **Ação sugerida:** Verificar se as falhas se concentram em poucos IPs ou usuários.
- **Diagnóstico por:** regras

### 5. Registro inválido no lote do arquivo leituras_20261110.csv

- **Gravidade:** Média (Dados inválidos)
- **Módulo:** leituras | **Nível no log:** ERROR
- **Ocorrências:** 12 (07:16 a 10:53)
- **Causa provável:** Um registro chegou sem um campo obrigatório.
- **Ação sugerida:** Validar os registros na entrada e rejeitar os incompletos com uma mensagem clara.
- **Diagnóstico por:** regras

```
Registro inválido no lote do arquivo leituras_20261110.csv
...
  File "/app/leituras/importador.py", line 31, in normalizar
    matricula = item["matricula"]
KeyError: 'matricula'
```

### 6. Gateway de SMS retornou 503 ao notificar <TELEFONE>

- **Gravidade:** Média (Integração externa)
- **Módulo:** notificacoes | **Nível no log:** ERROR
- **Ocorrências:** 10 (07:04 a 11:18)
- **Causa provável:** Um serviço externo está fora do ar ou instável.
- **Ação sugerida:** Verificar o status do serviço externo e se há novas tentativas automáticas.
- **Diagnóstico por:** regras

### 7. Falha ao chamar API de pagamentos (api_key=<SEGREDO>): HTTP 502 Bad Gateway

- **Gravidade:** Média (Integração externa)
- **Módulo:** pagamentos | **Nível no log:** ERROR
- **Ocorrências:** 4 (07:27 a 10:07)
- **Causa provável:** Um serviço externo está fora do ar ou instável.
- **Ação sugerida:** Verificar o status do serviço externo e se há novas tentativas automáticas.
- **Diagnóstico por:** regras

### 8. Resposta lenta em /api/faturas: 6467ms

- **Gravidade:** Baixa (Desempenho)
- **Módulo:** api | **Nível no log:** WARNING
- **Ocorrências:** 21 (07:01 a 11:28)
- **Causa provável:** Requisições demorando mais que o esperado.
- **Ação sugerida:** Medir quais consultas ou chamadas estão lentas nos horários afetados.
- **Diagnóstico por:** regras

```
Resposta lenta em /api/faturas: 6467ms
Resposta lenta em /api/faturas: 6392ms
Resposta lenta em /api/faturas: 2375ms
```
