# Desenho do processo — Instrução de Pedidos de Diárias (SEMA-MT)

Desafio 01 do Módulo de Agentes Autônomos (Aulas 01 a 07). Todos os dados, servidores e a
IN SEMA nº 07/2026 são hipotéticos.

> **Situação das medições.** Este documento foi escrito antes das execuções contra o modelo,
> como pede a Etapa 1. As contas de custo usam (a) a referência do enunciado e (b) uma
> estimativa por contagem de tokens das requisições que o Agno de fato monta
> (`avaliacao/estimar_tokens.py`). A confrontação com o **medido** fica no `relatorio.md`,
> preenchida somente com execuções reais.

---

## 1. Como o servidor instrui hoje (processo manual)

1. Recebe o pedido protocolado (formulário com número, data, matrícula, nome, destino, datas,
   transporte e justificativa).
2. Confere se o pedido está completo (todas as datas, destino, identificação).
3. Consulta o **cadastro funcional** pela matrícula e confere se o nome corresponde; anota o
   cargo, o grupo da diária (A, B ou C) e a unidade de lotação.
4. Se o pedido está incompleto ou diverge do cadastro, devolve **em diligência** (art. 9º),
   sem analisar o mérito.
5. Calcula a **antecedência** (dias corridos entre o protocolo e a partida) e, se for menor
   que 10 dias, verifica se a justificativa descreve **urgência** do art. 5º, § 1º, e se há
   autorização escrita do Secretário Adjunto (§ 2º).
6. Consulta o **histórico de diárias**: prestações de contas pendentes e se o prazo de 5 dias
   úteis após o retorno já venceu (art. 7º); diárias já concedidas no mês da partida.
7. Calcula a **quantidade** (uma por pernoite + meia no retorno; sem pernoite, meia — art. 4º)
   e o **valor** pelo Anexo I (grupo × classe do destino).
8. Soma as diárias do mês com as pedidas e compara com o **limite de 10** (art. 6º).
9. Consulta o **saldo da dotação** da unidade de lotação e compara com o valor (art. 8º).
10. Redige a **minuta do despacho** com a síntese e a recomendação.
11. Encaminha ao **ordenador de despesa**, que defere ou indefere (art. 10).
12. Quando o pedido volta da diligência, **reconstitui o caso** desde o passo 1.

Onde o processo falha hoje: contagem de dias úteis e de diárias no mês (aritmética), pendência
"no prazo" confundida com "vencida", urgência aceita sem autorização escrita, e a
reconstituição do caso na volta da diligência. Os erros aparecem meses depois, na auditoria.

## 2. Como o agente instrui

Um **único agente Agno** (`agente/agente_diarias.py`), com quatro ferramentas, saída em
contrato Pydantic e uma barreira no código entre o agente e a tela.

```text
Pedido protocolado ──► [aplicação] mascara CPF/agência/conta ──► Agent.run(session_id=nº, user_id=matrícula)
                                                                   │  pre_hook: PIIDetectionGuardrail
                                                                   │  1 consultar_servidor
                                                                   │  2 consultar_historico_diarias
                                                                   │  3 calcular_diarias
                                                                   │  4 consultar_saldo_diarias
                                                                   ▼  output_schema = Instrucao
                                   resposta.status == COMPLETED? ── não ──► mensagem padrão / análise manual
                                                                   │ sim
                                                   barreira (seguranca/barreiras.py) ── recusa ──► mensagem padrão
                                                                   │ aprova
                                Formulário: recomendação · verificações · consultas · minuta editável
                                                                   ▼
                              Conferente registra o encaminhamento (e a justificativa, se divergir)
                                                                   ▼
                                              Ordenador de despesa decide (fora do sistema)
```

| Passo do servidor | No agente | Quem executa |
|---|---|---|
| 2 dados completos | instrução + barreira (`PedidoEfetivo.dados_completos`) | código decide; modelo reporta |
| 3 cadastro | `consultar_servidor(matricula, nome_informado)` | código |
| 4 diligência | regra na instrução, verificada pela barreira | código decide; modelo redige |
| 5 antecedência | `calcular_diarias` (dias) | código |
| 5 urgência | julgamento sobre o texto da justificativa | **modelo** (com verificação de indícios na barreira) |
| 6 histórico | `consultar_historico_diarias` | código |
| 7–8 quantidade, valor, limite | `calcular_diarias` (Decimal) | código |
| 9 saldo | `consultar_saldo_diarias` | código |
| 10 minuta | campo `minuta_despacho` | **modelo** (barreira proíbe verbos decisórios, dado pessoal, matrícula/data estranhas) |
| 11 encaminhamento | formulário de conferência | **servidor** |
| 12 complementação | mesma sessão (`session_id` = nº do pedido), histórico recuperado | Agno + barreira |

## 3. Informações necessárias

- **Do pedido:** número, data do protocolo, matrícula, nome, município e UF de destino, datas
  de partida e retorno, justificativa (texto **não confiável**).
- **Do cadastro:** grupo da diária e unidade de lotação (CPF e e-mail **não** saem da ferramenta).
- **Do histórico:** prestações pendentes, data de retorno de cada uma, diárias do mês.
- **Da tabela/norma:** valores do Anexo I, antecedência mínima, limite mensal, prazo de
  prestação, data da análise (2026-10-09).
- **Da unidade:** saldo da dotação de diárias.
- **Da complementação:** o dado corrigido (data de retorno, matrícula).

## 4. Ferramentas

| Ferramenta | Substitui | Argumentos | Devolve (JSON em texto) |
|---|---|---|---|
| `consultar_servidor` | consulta ao RH | `matricula`, `nome_informado` | localizado/não localizado; confere/diverge; grupo, unidade |
| `consultar_historico_diarias` | planilha de controle | `matricula`, `data_partida` | pendências com prazo e situação vencida/no prazo; diárias do mês |
| `calcular_diarias` | calculadora | `matricula`, `destino_uf`, `data_pedido`, `data_partida`, `data_retorno` | quantidade, valor unitário e total, antecedência, limite mensal |
| `consultar_saldo_diarias` | sistema financeiro | `unidade`, `valor` | saldo, suficiente/insuficiente |

Decisões: o grupo é lido pela matrícula dentro da ferramenta (o modelo não o informa); toda
aritmética monetária em `Decimal`; "não localizado" é distinto de "impedimento" e de
"argumento inválido"; cada resultado traz `fonte`, `regra` e `argumentos`.

## 5. Etapas determinísticas × dependentes do modelo × validação humana

| Determinísticas (código) | Dependentes do modelo | Exigem validação humana |
|---|---|---|
| Máscara de dados pessoais | Ordem e argumentos das chamadas (verificados pela barreira) | Encaminhamento final (formulário) |
| Conferência do cadastro | Julgamento de urgência (art. 5º, § 1º) | Urgência aceita: autorização **escrita** do Secretário Adjunto |
| Quantidade, valor, antecedência, limite, prazo, saldo | Redação da minuta, pendências e alertas | Minuta (campo editável) |
| Barreira: argumentos ancorados, números iguais aos da ferramenta, coerência da recomendação | Reconhecer ordens embutidas e registrar alerta | Toda recusa da barreira (análise manual) |
| Status da execução, eliminação e verificação no banco | Recuperar o pedido do histórico na complementação | Eliminação de sessão gravada sob outro user_id (vínculo + confirmação) |

## 6. Quadro PEAS

| Elemento | Especificação |
|---|---|
| **Performance** (medida de desempenho) | Por caso, contra `gabarito.json` (avaliador externo): recomendação igual; quantidade e valor iguais (±R$ 0,005); `exige_autorizacao_superior` igual; conjunto de critérios "não atende" igual. **Meta:** 14/14 casos corretos ou recusados com mensagem padrão; **zero** instrução errada entregue ao conferente. Secundárias: tokens, tempo e custo por pedido; chamadas ao modelo; recusas da barreira; eliminação com zero ocorrência residual. |
| **Environment** (ambiente) | Cadastro funcional (`servidores.csv`), histórico (`historico_diarias.csv`), tabela e regras (`tabela_diarias.json`), unidades e saldos (`unidades.json`), IN SEMA 07/2026 (`normas.md`), pedidos e complementações; banco de trabalho do agente (SQLite); o servidor conferente e o ordenador. Ambiente parcialmente observável (só o que as ferramentas devolvem), determinístico nas regras e estocástico no modelo; texto do solicitante não confiável. |
| **Actuators** (atuadores) | Chamadas às 4 ferramentas (somente leitura); emissão do objeto `Instrucao` (recomendação, verificações, pendências, alertas, minuta). Não altera cadastro, não autoriza pagamento, não envia nada ao solicitante. |
| **Sensors** (sensores) | Campos do pedido; justificativa e complementação (mascaradas e delimitadas como dado); resultados das ferramentas; histórico da sessão (Agno/SQLite). |

## 7. Confiabilidade composta — `P = pⁿ`

Passo = uma chamada ao modelo. Com paralelas **desligadas**, o pedido regular exige 5 chamadas
(4 ferramentas em sequência + resposta final); a diligência, 2 (cadastro + resposta); a
complementação, mais 5.

| Caso | n | p = 95% | p = 99% |
|---|---:|---:|---:|
| Diligência (cadastro diverge / dado ausente) | 2 | 90,3% | 98,0% |
| Paralelas ligadas (cadastro+histórico+cálculo juntos, saldo, final) | 3 | 85,7% | 97,0% |
| Pedido regular (paralelas desligadas) | 5 | 77,4% | 95,1% |
| Diligência + complementação (processo completo) | 7 | 69,8% | 93,2% |

Leitura: a 95% por passo, perto de 1 em 4 pedidos regulares teria algum passo errado. Por isso
o desenho **não depende** de o modelo acertar todos os passos: a barreira transforma o erro
silencioso em recusa visível (vale mais "11 certos e 3 recusados" que "13 certos e 1 calculado
para o servidor errado"). Paralelas ligadas reduzem n para 3, mas criam o risco de o saldo ser
consultado antes do valor existir (Aula 06, 4.3) — ver decisão no item 10.

## 8. Custo por passos

**(a) Referência do enunciado:** 1ª chamada ≈ 2.060 tokens; cada passo seguinte +90 a +150.
Como cada passo reenvia tudo o que veio antes, a entrada acumulada de 5 passos é
`5 × 2.060 + (0+1+2+3+4) × Δ` = **11.200 a 11.800 tokens**.

**(b) Estimativa deste desenho** (corpo real das requisições do Agno, tokenizador o200k_base,
`resultados/evidencias/estimativa_tokens_o200k.json`):

| Componente da 1ª chamada | Tokens (estim.) |
|---|---:|
| Instrução de sistema (inclui a norma, 642) | 1.702 |
| Esquemas das 4 ferramentas (docstrings completas) | 1.846 |
| Esquema de saída `Instrucao` | 714 |
| Mensagem do pedido | ~141 |
| **1ª chamada** | **≈ 4.416** |
| Acréscimo por passo (resultado da ferramenta em JSON) | 165 a 364 (média 236) |
| **Entrada acumulada de um pedido regular (5 chamadas)** | **≈ 24.400** |

A 1ª chamada estimada é o **dobro** da referência. As causas são decisões deliberadas e
documentadas: docstrings que dizem finalidade, quando usar, argumentos, retorno e erros (a
Aula 06, 5.1 mostrou que a docstring que diz o que a ferramenta devolve muda o acerto), a
norma inteira na instrução e resultados de ferramenta com `fonte/regra/argumentos` para
rastreabilidade. É um custo consciente de auditabilidade; o relatório compara com o medido.

Saída estimada: ~40 tokens por chamada de ferramenta + ~550 na instrução final ≈ **700 tokens**.

Preços do gpt-5.6-luna (Aula 06): US$ 0,20/M entrada, US$ 1,20/M saída.

| Caso | Entrada | Saída | US$ (estim.) |
|---|---:|---:|---:|
| Pedido regular — referência (a) | 11.500 | 700 | 0,0031 |
| Pedido regular — este desenho (b) | 24.400 | 700 | 0,0057 |
| Diligência (2 chamadas) | 9.000 | 450 | 0,0023 |
| Complementação com histórico (5 chamadas) | 27.600 | 700 | 0,0064 |

## 9. Volume mensal adotado e custo

Premissa: "centenas de pedidos por mês" (enunciado) → **600 pedidos/mês** (≈ 30 por dia útil,
20 dias úteis), dos quais **20% em diligência** com uma complementação cada (2 de 12 no acervo
≈ 17%; arredondado para cima por prudência).

| Parcela | Qtde | US$ unit. | US$/mês |
|---|---:|---:|---:|
| Pedidos instruídos de uma vez | 480 | 0,0057 | 2,75 |
| Diligências (1º turno) | 120 | 0,0023 | 0,28 |
| Complementações | 120 | 0,0064 | 0,77 |
| **Total estimado** | | | **≈ 3,80** |

Com a memória de usuário (`update_memory_on_run`), cada execução faz chamadas extras de
extração; a Aula 07 mediu até 5× a entrada do histórico simples. Não é adotada em produção
(item 10). O custo do modelo é irrelevante diante do custo do erro (uma diária indevida de
R$ 980, ao câmbio de R$ 5,80/US$, equivale a ~30 mil instruções); a decisão de projeto é guiada por confiabilidade, não por custo.

## 10. Configuração decidida antes da medição

| Parâmetro | Valor | Justificativa |
|---|---|---|
| `parallel_tool_calls` | **False** | O saldo depende do valor calculado e da unidade do cadastro (Aula 06, 4.3). A API garante a ordem; a instrução sozinha não. A comparação com paralelas ligadas é medida na Etapa 7. |
| `tool_call_limit` | **6** | 4 consultas necessárias + 2 de margem (uma repetição por argumento inválido). Um teto menor (2) foi provocado como falha F2b. |
| `reasoning_effort` | `"none"` | Exigido pela família GPT-5.6 com ferramentas no Chat Completions (Aula 06, 4.1). |
| `output_schema` | `Instrucao` | A tela e o avaliador leem campos, não texto. |
| Memória | `SqliteDb` + `add_history_to_context` + `num_history_runs=3` | O caso mais longo tem 2 execuções (pedido + complementação); 3 é teto com folga. Histórico simples foi o que mais lembrou e custou menos na Aula 07. |
| `update_memory_on_run` | desligado em produção; medido na Etapa 4 | Fatos em texto livre sobre o servidor não são necessários à instrução (princípio da necessidade) e encarecem cada turno. |
| `session_id` / `user_id` | nº do pedido / matrícula protocolada, **em cada `run`** | Permite um agente único em cache sem misturar pedidos (Aula 07, 5.1). |
| `PIIDetectionGuardrail` | SSN, cartão e telefone desligados; CPF, agência e conta próprios; e-mail ligado | Os padrões norte-americanos mascaravam protocolos (Aula 06, 5.2). |
| `telemetry` | False | Decisão do órgão (Aula 06, 5.4). |

## 11. Autonomia — reversibilidade × tempo de detecção (Aula 01, Seção 5)

- **Reversibilidade:** uma diária paga indevidamente é, em tese, reversível (reposição ao
  erário), mas a reversão exige processo administrativo, notificação do servidor e pode
  depender de desconto em folha; o ato de autorizar despesa é ato jurídico do ordenador.
  Na prática, **reversível com custo alto**.
- **Detecção:** o erro aparece **tarde**, na auditoria ou na prestação de contas, meses depois.

O processo cai na coluna **"erro detectado tarde"**. Mesmo lido como reversível ("agente age,
com auditoria por amostra"), o custo da reversão e a natureza decisória do ato o aproximam do
quadrante **"agente apenas aconselha"**. Decisão: **o agente prepara a instrução e a minuta; a
pessoa confere e registra; o ordenador decide.** Nenhuma ação do agente altera o mundo.

## 12. Por que a conferência humana permanece

1. **Julgamento de urgência** é interpretação de texto (0106 × 0107), exatamente onde o modelo
   é manipulável; a autorização escrita (§ 2º) só existe no processo físico.
2. A confiabilidade composta de um pedido regular fica entre 77% e 95% por execução; a barreira
   recusa o que detecta, mas não detecta erro de redação ou de julgamento que seja internamente
   coerente.
3. O erro custa caro e aparece tarde (item 11).
4. A responsabilidade legal é do ordenador (art. 10); a instrução é subsídio.
5. O registro da conferência (recomendação × decisão, com justificativa) mede, com o uso, a
   taxa de discordância — é ela que poderá, no futuro, justificar mais ou menos autonomia.
