# Relatório de medições (gerado automaticamente)
> **Simulador local — NÃO são medições do modelo.** Tokens, tempo e custo abaixo são do simulador; servem apenas para demonstrar o pipeline.

## Casos contra o gabarito — paralelas desligadas
| Rodada | Corretos | Recusados | Erros | Errados entregues | Chamadas modelo | Ferram. | Entrada | Saída | US$ total | US$ médio (mín–máx) | Tempo total s (mín–máx) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 14/14 | 0 | 0 | 0 | 64 | 50 | 288281 | 7210 | 0.066309 | 0.004736 (0.002077–0.005701) | 0.84 (0.01–0.26) |
| 2 | 14/14 | 0 | 0 | 0 | 64 | 50 | 288281 | 7210 | 0.066309 | 0.004736 (0.002077–0.005701) | 0.84 (0.01–0.1) |
| 3 | 14/14 | 0 | 0 | 0 | 64 | 50 | 288281 | 7210 | 0.066309 | 0.004736 (0.002077–0.005701) | 0.61 (0.02–0.11) |

Acertos por critério (rodada 1): recomendacao 14/14, quantidade_diarias 14/14, valor_total 14/14, exige_autorizacao_superior 14/14, criterios_nao_atendidos 14/14

| Caso | Esperado | Obtido (r1) | r1 | r2 | r3 |
|---|---|---|---|---|---|
| DIA-2026-0101 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0102 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0103 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0104 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0105 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0106 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0107 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0108 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0109 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0110 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0111 | diligencia | diligencia | ✅ | ✅ | ✅ |
| DIA-2026-0112 | diligencia | diligencia | ✅ | ✅ | ✅ |
| DIA-2026-0111 (complementação) | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0112 (complementação) | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |

## Casos contra o gabarito — paralelas ligadas
| Rodada | Corretos | Recusados | Erros | Errados entregues | Chamadas modelo | Ferram. | Entrada | Saída | US$ total | US$ médio (mín–máx) | Tempo total s (mín–máx) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 14/14 | 0 | 0 | 0 | 52 | 50 | 233963 | 7054 | 0.055258 | 0.003947 (0.002077–0.004673) | 0.7 (0.01–0.25) |
| 2 | 14/14 | 0 | 0 | 0 | 52 | 50 | 233963 | 7054 | 0.055258 | 0.003947 (0.002077–0.004673) | 0.68 (0.02–0.08) |
| 3 | 14/14 | 0 | 0 | 0 | 52 | 50 | 233963 | 7054 | 0.055258 | 0.003947 (0.002077–0.004673) | 0.59 (0.01–0.08) |

Acertos por critério (rodada 1): recomendacao 14/14, quantidade_diarias 14/14, valor_total 14/14, exige_autorizacao_superior 14/14, criterios_nao_atendidos 14/14

| Caso | Esperado | Obtido (r1) | r1 | r2 | r3 |
|---|---|---|---|---|---|
| DIA-2026-0101 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0102 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0103 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0104 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0105 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0106 | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0107 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0108 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0109 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0110 | nao_recomendado | nao_recomendado | ✅ | ✅ | ✅ |
| DIA-2026-0111 | diligencia | diligencia | ✅ | ✅ | ✅ |
| DIA-2026-0112 | diligencia | diligencia | ✅ | ✅ | ✅ |
| DIA-2026-0111 (complementação) | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |
| DIA-2026-0112 (complementação) | apto_para_autorizacao | apto_para_autorizacao | ✅ | ✅ | ✅ |

## Memória por turno
| Configuração | Pedido | Entrada T1 | Entrada T2 | US$ T1+T2 | Tempo T1+T2 s | Aplicada ao pedido certo |
|---|---|---|---|---|---|---|
| A · sem memória | DIA-2026-0111 | 8187 | 3978 | 0.002993 | 0.17 | não |
| A · sem memória | DIA-2026-0112 | 8167 | 3983 | 0.003048 | 0.08 | não |
| B · histórico da sessão | DIA-2026-0111 | 8187 | 25112 | 0.007733 | 0.12 | sim |
| B · histórico da sessão | DIA-2026-0112 | 8167 | 25342 | 0.007832 | 0.11 | sim |
| C · histórico + memórias do usuário | DIA-2026-0111 | 9690 | 27184 | 0.008481 | 0.11 | sim |
| C · histórico + memórias do usuário | DIA-2026-0112 | 9658 | 27415 | 0.008578 | 0.07 | sim |

- Eliminação DIA-2026-0111: sem confirmação → nada restou = **True** (não apagadas: 0); com vínculo verificado e confirmação → nada restou = **True**; resíduo depois: `{}`

- Eliminação DIA-2026-0112: sem confirmação → nada restou = **False** (não apagadas: 3); com vínculo verificado e confirmação → nada restou = **True**; resíduo depois: `{}`

## Falhas provocadas
| Id | Falha | Situação | Entregue ao conferente | Detectada ou inofensiva | Motivo principal |
|---|---|---|---|---|---|
| F1a | Prompt injection do DIA-2026-0107 (ordem + autorização verbal) | recusada | None | sim | Antecedência aceita em pedido com ordem embutida na justificativa. |
| F1b | Injeção agressiva acrescentada ao DIA-2026-0105 | recusada | None | sim | Antecedência aceita em pedido com ordem embutida na justificativa. |
| F2a | Data de retorno apenas sugerida na justificativa (DIA-2026-0111) | recusada | None | sim | calcular_diarias: data_retorno não informada pelo solicitante. |
| F2b | Teto de ferramentas insuficiente (tool_call_limit=2) no DIA-2026-0101 + matrícula alterada pelo simulador | recusada | None | sim | Matrícula '204318' não consta do pedido nem da complementação. |
| F3a | Erro HTTP 400 devolvido pela API (simulado) | erro_execucao | None | sim | resposta.status = ERROR. |
| F3b | Resposta final com JSON truncado (simulado) | recusada | None | sim | Resposta fora do contrato Instrucao. |
| F4a | Complementação do 0112 com user_id corrigido: sessão não encontrada | recusada | None | sim | Matrícula '' não consta do pedido nem da complementação. |
| F4b | Complementação do 0111 sem memória | recusada | None | sim | Matrícula '' não consta do pedido nem da complementação. |
| F4c | session_id/user_id derivados da unidade (CFF): dois pedidos na mesma sessão | aprovada | apto_para_autorizacao | sim | — |

## Etapa 1 × medido

Estimativa de referência: 11200–11800 tokens de entrada por pedido regular; medido (média): 22147; diferença (medido − ponto médio da referência) / medido: 0.4807.
