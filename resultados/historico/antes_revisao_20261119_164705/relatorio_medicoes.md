# Relatório de medições (gerado automaticamente)

## Casos contra o gabarito — paralelas desligadas
| Rodada | Corretos | Recusados | Erros | Errados entregues | Chamadas modelo | Ferram. | Entrada | Saída | US$ total | US$ médio (mín–máx) | Tempo total s (mín–máx) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 13/14 | 1 | 0 | 0 | 64 | 50 | 291934 | 8592 | 0.068697 | 0.004907 (0.002122–0.005898) | 122.26 (4.75–11.67) |
| 2 | 13/14 | 1 | 0 | 0 | 64 | 50 | 292039 | 8465 | 0.068565 | 0.004897 (0.002131–0.00589) | 118.05 (4.87–9.42) |
| 3 | 12/14 | 1 | 0 | 1 | 64 | 50 | 291944 | 8678 | 0.068802 | 0.004914 (0.002117–0.005887) | 121.64 (4.61–10.42) |

Acertos por critério (rodada 1): recomendacao 13/14, quantidade_diarias 13/14, valor_total 13/14, exige_autorizacao_superior 13/14, criterios_nao_atendidos 13/14

| Caso | Esperado | Obtido (r1) | r1 | r2 | r3 |
|---|---|---|---|---|---|
| DIA-2026-0101 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0102 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0103 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0104 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0105 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0106 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ❌ |
| DIA-2026-0107 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0108 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0109 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0110 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0111 | diligencia | diligencia | ✅ | ✅ | ✅ |
| DIA-2026-0112 | diligencia | None | ⛔ recusado | ⛔ recusado | ⛔ recusado |
| DIA-2026-0111 (complementação) | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0112 (complementação) | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |

## Casos contra o gabarito — paralelas ligadas
_execucao_casos_paralelas_ligadas.json: **não executado** — OPENAI_API_KEY ausente no ambiente e no .env; a execução contra o modelo gpt-5.6-luna não foi realizada. Nenhuma medição foi produzida._

## Memória por turno
_medicao_memoria.json: **não executado** — OPENAI_API_KEY ausente no ambiente e no .env; a execução contra o modelo gpt-5.6-luna não foi realizada. Nenhuma medição foi produzida._

## Falhas provocadas
_falhas_provocadas.json: **não executado** — OPENAI_API_KEY ausente no ambiente e no .env; a execução contra o modelo gpt-5.6-luna não foi realizada. Nenhuma medição foi produzida._

## Etapa 1 × medido

Estimativa de referência: 11200–11800 tokens de entrada por pedido regular; medido (média): 22967; diferença relativa ao ponto médio: 0.4993.
