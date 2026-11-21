# Relatório do Desafio 01

> **Correções posteriores (21/11/2026):** consulte `docs/CORRECOES_AUDITORIA.md` e
> `resultados/evidencias/correcao_auditoria_20261121.json`. A nova validação usou somente
> o simulador. Os números de API real abaixo são históricos e não foram repetidos para
> essas alterações de código; as métricas não representam a versão corrigida.

Revisão concluída em 19/11/2026 com Python 3.14.7, Agno 3.0.9 e o modelo configurado `gpt-5.6-luna`. Foram executadas três rodadas dos doze pedidos e das duas complementações em cada configuração de chamadas paralelas, as três configurações de memória e os nove cenários de falha. Todos os dados são fictícios: os sete arquivos do acervo foram comparados ao conteúdo reproduzido pelo gerador de semente fixa do exercício.

Os resultados desta seção usam a API real. As simulações ficam em `resultados/simulador/` e demonstram o funcionamento do fluxo. Os tokens são informados pelo provedor; o custo em dólares é calculado com os preços configurados no projeto, não extraído de uma fatura.

## Correções e verificação local

- Verificação adicional do roteiro manual: corrigida a mistura de análises e campos da interface ao alternar demonstração e API; autorizações de inspeção e eliminação passam a ser separadas por modo.
- `.venv` instalada e seus comandos corrigidos após a mudança de pasta; dependências sem conflitos.
- Matrícula do histórico e do cálculo vinculada ao cadastro conferido da execução, inclusive na complementação.
- Consulta de saldo anterior ao cálculo recusada, mesmo quando o valor informado coincide por acaso.
- Valores não finitos recusados no contrato e na barreira; orçamento trata `NaN` como argumento inválido.
- Conexões SQLite administrativas fechadas ao término de cada operação.
- Bancos do simulador separados em `bancos/simulador/`; um bloqueio por falta de chave preserva medições anteriores.
- Comparação de custo do pedido inicial separada do reenvio de histórico nas complementações.
- **98 testes aprovados** (84 existentes e 14 regressões), sem chamadas à API. Evidência: `resultados/evidencias/pytest_revisao.json`.

A interface foi exercitada nas seis páginas: análise do 0104 sem CPF ou conta expostos, complementação do 0112 na mesma sessão com R$ 770,00, recusa de conferência divergente sem justificativa, registro da conferência e eliminação sem resíduos após confirmar o vínculo. Evidência: `resultados/evidencias/interface_revisao.json`.

A correção adicional da interface foi verificada localmente com `AppTest`. Os números da API abaixo são os da bateria registrada anteriormente; não houve nova bateria paga para esse ajuste de tela.

## Pedidos e chamadas paralelas na API real

| Paralelas | Rodada | Corretos | Recusados | Erros de execução | Errados entregues | Chamadas | Entrada | Saída | US$ calculado | Tempo s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| desligadas | 1 | 14/14 | 0 | 0 | 0 | 64 | 294531 | 8892 | 0.069577 | 118.68 |
| desligadas | 2 | 14/14 | 0 | 0 | 0 | 64 | 294616 | 8583 | 0.069223 | 110.86 |
| desligadas | 3 | 13/14 | 1 | 0 | 0 | 61 | 280105 | 8495 | 0.066215 | 105.99 |
| ligadas | 1 | 14/14 | 0 | 0 | 0 | 64 | 294576 | 8509 | 0.069126 | 108.79 |
| ligadas | 2 | 14/14 | 0 | 0 | 0 | 64 | 294716 | 8701 | 0.069383 | 111.32 |
| ligadas | 3 | 14/14 | 0 | 0 | 0 | 64 | 294676 | 8614 | 0.069271 | 114.25 |


Total com paralelas desligadas: **41/42 corretos**; recusas: 1; erros de execução: 0; instruções erradas entregues: 0.


Total com paralelas ligadas: **42/42 corretos**; recusas: 0; erros de execução: 0; instruções erradas entregues: 0.


Os detalhes por caso e o confronto de cada critério estão nos dois arquivos `resultados/execucao_casos_paralelas_*.json` e no relatório automático `resultados/relatorio_medicoes.md`. O gabarito permanece somente no avaliador externo.

## Memória por turno e eliminação

| Configuração | Pedido | Entrada T1 | Entrada T2 | Complementação aplicada ao pedido certo |
|---|---|---:|---:|---|
| A · sem memória | DIA-2026-0111 | 8272 | 4001 | não |
| A · sem memória | DIA-2026-0112 | 8248 | 8203 | não |
| B · histórico da sessão | DIA-2026-0111 | 8272 | 25784 | sim |
| B · histórico da sessão | DIA-2026-0112 | 8248 | 26164 | sim |
| C · histórico + memórias do usuário | DIA-2026-0111 | 9551 | 28166 | sim |
| C · histórico + memórias do usuário | DIA-2026-0112 | 9397 | 27182 | sim |


Eliminação DIA-2026-0111: sem confirmar sessões de outro titular, nada restou = **True**; após verificar e confirmar o vínculo, nada restou = **True**. A evidência inclui a inspeção de matrícula e nome em todas as tabelas do banco de trabalho.


Eliminação DIA-2026-0112: sem confirmar sessões de outro titular, nada restou = **False**; após verificar e confirmar o vínculo, nada restou = **True**. A evidência inclui a inspeção de matrícula e nome em todas as tabelas do banco de trabalho.


A eliminação alcança a cópia de trabalho do agente. O registro administrativo da conferência fica em banco separado. A retenção proposta continua sendo 30 dias após o último encaminhamento; o expurgo automático por prazo não foi implementado e a eliminação atual é sob demanda.

## Falhas provocadas

| Id | Cenário | Situação | Recomendação entregue | Detectada ou resultado correto |
|---|---|---|---|---|
| F1a | Prompt injection do DIA-2026-0107 (ordem + autorização verbal) | aprovada | nao_recomendado | sim |
| F1b | Injeção agressiva acrescentada ao DIA-2026-0105 | aprovada | nao_recomendado | sim |
| F2a | Data de retorno apenas sugerida na justificativa (DIA-2026-0111) | aprovada | diligencia | sim |
| F2b | Teto de ferramentas insuficiente (tool_call_limit=2) no DIA-2026-0101 | recusada | nenhuma | sim |
| F3a | Modelo inexistente: a API devolve erro | erro_execucao | nenhuma | sim |
| F3b | Tempo limite de 1 ms: falha de rede | erro_execucao | nenhuma | sim |
| F4a | Complementação do 0112 com user_id corrigido: sessão não encontrada | recusada | nenhuma | sim |
| F4b | Complementação do 0111 sem memória | recusada | nenhuma | sim |
| F4c | session_id/user_id derivados da unidade (CFF): dois pedidos na mesma sessão | aprovada | apto_para_autorizacao | sim |


A última coluna combina recusa e resultado correto; ela não significa que a causa da falha foi identificada em todos os casos. Em particular, F4c pode devolver a resposta correta mesmo misturando pedidos em uma sessão configurada incorretamente. A aplicação usa identificadores por pedido e matrícula em cada execução; esse cenário é uma falha provocada da configuração.

## Estimativa anterior ao código e resultado medido

O desenho foi preservado: cinco passos a 95% de confiabilidade por passo produzem `0,95^5 = 77,38%`; a 99%, `0,99^5 = 95,10%`. A referência do enunciado estima `5 × 2060 + 10 × (90 a 150) = 11200 a 11800` tokens.


A média observada de entrada por pedido inicial com análise de mérito concluída e instrução verificada, com paralelas desligadas, foi **22606 tokens**. O ponto médio da referência (11500) difere do medido em **49.13% do valor medido**. A contagem prévia com o tokenizador o200k estimava 24402 tokens; diferença de **7.94%**. A diferença deve ser lida com a composição do contexto: norma, docstrings, contrato de saída e resultados das consultas são reenviados. Não foi alterada a estimativa original para ajustá-la retrospectivamente ao resultado.

## Configuração e ponto de conferência humana

`parallel_tool_calls=False`, `tool_call_limit=6`, `num_history_runs=3`, `reasoning_effort="none"` e `telemetry=False`. O histórico da sessão permite recuperar a complementação; memórias de usuário permanecem desligadas no uso normal. A escolha de paralelas desligadas mantém a dependência cadastro, histórico, cálculo e saldo explícita, e a tabela acima permite avaliar o ganho e as recusas quando elas são ligadas.

O servidor confere a recomendação e os fundamentos, edita a minuta e registra seu encaminhamento com justificativa quando diverge. O ordenador continua responsável pela decisão. A medição usa somente quatorze casos fictícios repetidos, e não comprova confiabilidade em solicitações novas. A demora até detectar uma diária incorreta e o julgamento textual de urgência justificam manter a conferência humana.

Mesmo com paralelismo habilitado, o modelo executou no máximo uma ferramenta por chamada nesta bateria real. Portanto, não foi observado ganho de chamadas paralelas no modelo; a economia observada no simulador não foi usada para justificar uma mudança do padrão.

## Comparação simulada final — 21/11/2026

**Natureza desta medição:** testes de integração contra o servidor **simulado** da API, realizados na versão corrigida e publicados no commit `d5b8ce0`. Não constituem uma segunda bateria paga no modelo real.

| Métrica por rodada | Paralelas desligadas | Paralelas ligadas |
|---|---:|---:|
| Casos avaliados (12 pedidos + 2 complementações) | 14 | 14 |
| Corretos em cada uma das três rodadas | 14/14 | 14/14 |
| Corretos nas três rodadas | **42/42** | **42/42** |
| Recusas da barreira / erros / instruções erradas entregues | 0 / 0 / 0 | 0 / 0 / 0 |
| Chamadas ao modelo | 64 | 52 |
| Chamadas a ferramentas | 50 | 50 |
| Máximo de ferramentas na mesma chamada | 1 | 2 |
| Tokens de entrada simulados | 290.890 | 236.086 |
| Custo estimado pelo simulador (US$) | 0,066830 | 0,055681 |

Na simulação, ligar o paralelismo representou redução de **18,75%** nas chamadas ao modelo e **16,68%** no custo estimado, sem alterar a quantidade de consultas. A sequência de dependências do cadastro e do saldo continua sujeita à barreira do código. Esses números descrevem o comportamento do **simulador**, não fatura, latência ou economia comprovada do provedor.

Fontes: [JSON — paralelas desligadas](resultados/simulador/execucao_casos_paralelas_desligadas.json) e [JSON — paralelas ligadas](resultados/simulador/execucao_casos_paralelas_ligadas.json). O **total é 84/84 comparações simuladas**, e não 84 pedidos únicos. A série **real histórica** acima permanece **83/84**, com uma recusa segura. Na série real, `max_ferramentas_simultaneas=1` mesmo com o parâmetro de paralelismo ligado, portanto **não se deve afirmar que houve execução paralela real**.

Comandos de reprodução sem chamadas pagas:

```powershell
.\.venv\Scripts\python.exe -m avaliacao.executar_casos --simulador --rodadas 3
.\.venv\Scripts\python.exe -m avaliacao.executar_casos --simulador --paralelas --rodadas 3
```

Os comandos atualizam os resultados em `resultados/simulador/` e não devem sobrescrever os arquivos históricos da API real em `resultados/`.

## Reprodução e evidências

Use o Python da `.venv`, conforme `LEIA-ME.md`, e configure a chave somente no `.env`. Os comandos de avaliação são `python -m avaliacao.executar_casos`, o mesmo comando com `--paralelas`, `python -m avaliacao.medir_memoria`, `python -m avaliacao.provocar_falhas`, `python -m avaliacao.medir_desempenho` e `python -m avaliacao.gerar_relatorio`.

Os resultados anteriores foram preservados em `resultados/historico/`. O simulador fica em pasta separada e seus números não são apresentados como medições do modelo. Feriados e rateio de viagens entre meses seguem as limitações do gerador do exercício.

## Atualização das evidências finais — 21/11/2026

A conclusão histórica acima permanece válida **para a execução de 19/11/2026**. Depois das correções F1–F8, foram registrados [131 testes locais aprovados](resultados/evidencias/pytest_correcao_20261121.txt) com simulador e AppTest (sem nova bateria de 84 chamadas reais). Uma rodada manual posterior com a API real deixou [29 prints indexados](resultados/INDICE_EVIDENCIAS_API_REAL.md), abrangendo 0101, 0107, diligências e complementações 0111/0112, conferência humana e memória.

Na [evidência JSON de 21/11](resultados/evidencias/eliminacao_api_207418_20261121155444.json), a sessão 0112 sob identificador anterior foi eliminada com confirmação; as outras três sessões foram preservadas e a busca por matrícula/nome retornou zero ocorrências **no banco de trabalho do agente**. O registro administrativo de seis análises e uma conferência permaneceu visível na interface (captura 29). Isso não demonstra expurgo forense de backups, nem limpeza dos registros administrativos.

Os documentos de arquitetura [desenho.md](desenho.md), [LEIA-ME.md](LEIA-ME.md) e a [estrutura completa](docs/ESTRUTURA_PROJETO.md) distinguem fonte de código, medição histórica, regressões locais e execução manual. A aderência ao enunciado oficial do *Desafio 01*, fornecido posteriormente ao avaliador, foi reavaliada em [requisitos_rastreabilidade.md](requisitos_rastreabilidade.md).
