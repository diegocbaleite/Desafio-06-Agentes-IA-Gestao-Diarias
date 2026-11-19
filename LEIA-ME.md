# LEIA-ME — Instrução de Pedidos de Diárias (Desafio 01)

Agente Agno que instrui pedidos de diárias da SEMA-MT segundo a IN SEMA nº 07/2026
(hipotética) e entrega a instrução a um formulário de conferência humana. O agente
**recomenda** (`apto_para_autorizacao`, `diligencia`, `nao_recomendado`); quem decide é o
ordenador de despesa.

## 1. Instalação

Neste computador, use a `.venv` já instalada na pasta do projeto. No PowerShell:

```powershell
cd "C:\Users\Diego\Downloads\desafio-01-diarias"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Os comandos usam diretamente o Python da `.venv`; não dependem do atalho `python` do
Windows nem da ativação do PowerShell. Para recriar o ambiente neste computador:

```powershell
& "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe" -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Em outro computador, crie a `.venv` com o Python 3.10+ disponível. Crie um ambiente novo
após mover o projeto: ambientes virtuais contêm comandos que usam caminhos absolutos.

Python 3.10 ou superior (verificado em 3.14.7). O extra `sqlalchemy[asyncio]` é obrigatório:
sem ele o `SqliteDb` falha por falta do `greenlet`.

`requirements.lock.txt` registra as 73 dependências instaladas e verificadas nesta revisão.
Para reproduzir essas versões, use `-r requirements.lock.txt` na instalação com o Python
da `.venv`; o ambiente de referência é Windows com Python 3.14.7.

## 2. Configuração

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Abra .env e preencha OPENAI_API_KEY, preservando uma chave que já esteja configurada.
```

A chave é lida pelo SDK a partir do ambiente (`load_dotenv` em `config.py`). Ela não aparece
no código, nos registros, nos resultados nem na tela (a tela mostra só "configurada" ou
"indisponível"). `.env` e os bancos estão no `.gitignore`. Demais variáveis: `MODELO_DIARIAS`
ou `MODELO_LLM` (ex.: `openai/gpt-5.6-luna`; padrão `gpt-5.6-luna`), `TOOL_CALL_LIMIT`, `NUM_HISTORY_RUNS`, `PARALLEL_TOOL_CALLS`, preços.

## 3. Execução

| Objetivo | Comando | Precisa de chave |
|---|---|---|
| Ferramentas sem agente (evidência da Etapa 2) | `python -m ferramentas` | não |
| Testes automatizados (97) | `python -m pytest` | não |
| Formulário de conferência | `streamlit run app.py` | sim (ou modo demonstração) |
| 12 pedidos + 2 complementações, 3 rodadas | `python -m avaliacao.executar_casos` | sim |
| O mesmo com paralelas ligadas | `python -m avaliacao.executar_casos --paralelas` | sim |
| Custo da memória e eliminação | `python -m avaliacao.medir_memoria` | sim |
| Falhas provocadas | `python -m avaliacao.provocar_falhas` | sim |
| Comparação de paralelas e Etapa 1 × medido | `python -m avaliacao.medir_desempenho` | não (lê os JSON) |
| Relatório de medições em Markdown | `python -m avaliacao.gerar_relatorio` | não (lê os JSON) |
| Estimativa de tokens (o200k) | `python -m avaliacao.estimar_tokens` | não |

Sem chave, os scripts que medem o modelo preservam medições anteriores e gravam `"situacao": "nao_executado"` e saem com
código 2. Todos aceitam `--simulador`, que roda o pipeline real do Agno contra um servidor
local que imita a API e grava em `resultados/simulador/` com aviso explícito de que **não é
medição**. Na tela, o mesmo simulador é o "modo demonstração" da barra lateral.

## 4. Funcionamento

1. A aplicação mascara CPF, agência, conta e e-mail do texto livre (`seguranca/filtro_pii.py`).
2. Chama `agente.run(mensagem, session_id=<nº do pedido>, user_id=<matrícula>)`. O
   `PIIDetectionGuardrail` repete a máscara no `pre_hook`.
3. O agente consulta, em ordem: `consultar_servidor` → `consultar_historico_diarias` →
   `calcular_diarias` → `consultar_saldo_diarias`; toda conta é feita nessas funções.
4. A resposta vem no contrato `Instrucao` (`agente/modelos.py`).
5. A aplicação confere `resposta.status` e passa a instrução pela barreira
   (`seguranca/barreiras.py`). Se algo falhar, a tela mostra a mensagem padrão e o pedido
   volta à análise manual; nada do conteúdo recusado é exibido.
6. O servidor edita a minuta, escolhe o encaminhamento e, se divergir, justifica. O registro
   vai para `bancos/registro_conferencias.db`.
7. Na diligência, a complementação é enviada **na mesma sessão**; o histórico traz o pedido.
8. Em "Memória e LGPD", a rotina de eliminação localiza, apaga e verifica tabela por tabela.

## 5. Estrutura

```text
desafio-01-diarias/
├── app.py                      formulário Streamlit (6 páginas)
├── config.py                   .env, modelo, limites, preços, mensagem padrão
├── agente/
│   ├── agente_diarias.py       construir_agente() e instruir() — fronteira com a tela
│   ├── instrucoes.py           instrução de sistema (com a norma) e mensagens dos turnos
│   └── modelos.py              Verificacao e Instrucao (Pydantic)
├── ferramentas/                cadastro, histórico, cálculos, orçamento + acervo (dados e regras)
├── seguranca/                  filtro_pii.py (máscara + guardrail) e barreiras.py
├── memoria/                    persistencia.py, eliminacao.py, verificacao.py
├── avaliacao/                  executar_casos, medir_memoria, provocar_falhas, medir_desempenho,
│   │                           estimar_tokens, gerar_relatorio, comparar_gabarito, execucao
│   └── externo/gabarito.json   lido SOMENTE por comparar_gabarito.py
├── simulador/                  servidor local que imita /v1/chat/completions (só testes/demonstração)
├── testes/                     97 testes Pytest, nenhum usa chave
├── dados/                      acervo de exemplos/dados (cópia) + gerador original
├── resultados/                 medições (API real), simulador/ e evidencias/
├── docs/roteiro_apresentacao.md
├── desenho.md · relatorio.md · requisitos_rastreabilidade.md
└── requirements.txt · .env.example · .gitignore
```

## 6. Decisões de engenharia

- **Ferramentas recebem a matrícula, não o grupo.** O grupo e a unidade são lidos do cadastro
  dentro da função; o modelo não tem como informar um grupo errado.
- **Ferramentas devolvem JSON em texto** com `fonte`, `regra` e `argumentos`, para o modelo
  ler e para a barreira conferir.
- **Decimal** em toda conta monetária; comparação de saldo no centavo (640,00 × 640,01 testado).
- **Três estados distintos:** dado não encontrado (`nao_localizado`), impedimento
  (`criterio_* = nao_atende`) e argumento inválido.
- **Barreira no código**, não no prompt: lê `RunOutput.tools` e confere argumentos e números.
- **Dois bancos:** o do agente (eliminável) e o administrativo (guarda legal).
- **Bancos de avaliação separados:** `bancos/simulador/` não sobrescreve bancos de medições
  reais; executar uma avaliação sem chave preserva resultados anteriores e registra o
  bloqueio em `resultados/bloqueios/` quando necessário.
- **Consistência da matrícula:** histórico e cálculo precisam usar a matrícula conferida
  no cadastro da execução, inclusive depois de uma correção por complementação.
- **Validação numérica:** números não finitos são recusados no contrato e na barreira;
  a consulta de orçamento devolve erro de argumento em vez de lançar exceção com `NaN`.
- **Agente único em cache** no Streamlit: seguro porque os identificadores vão em cada `run`.
- **Complementação mantém o user_id com que a sessão nasceu**; a divergência vira alerta e a
  rotina de eliminação a trata (ver pergunta 3).

## 7. Respostas às perguntas do enunciado

### 7.1 Que configuração de chamadas paralelas, teto de chamadas e memória foi escolhida, e com base em que número?
- **Paralelas desligadas.** Na revisão real, 41/42 casos corretos e 0 instruções erradas entregues; com paralelas ligadas, 42/42 corretos e 0 erradas. As rodadas e contagens de chamadas estão no relatório. O padrão mantém explícita a dependência entre cadastro, cálculo e saldo.
- **Teto de seis ferramentas.** Quatro consultas necessárias e duas de margem. O experimento F2b mede o comportamento com teto dois; a barreira exige as fontes antes de liberar a instrução.
- **Histórico da sessão com teto de três execuções.** O ciclo do desafio usa dois turnos. A tabela abaixo mostra o resultado real das três configurações; memórias de usuário não são necessárias para o fluxo e ficam desligadas no uso normal.

| Configuração | Complementações aplicadas ao pedido certo |
|---|---:|
| A · sem memória | 0/2 |
| B · histórico da sessão | 2/2 |
| C · histórico + memórias do usuário | 2/2 |

### 7.2 Como o sistema impede que uma instrução fundamentada em dado inventado chegue ao conferente?

Em quatro camadas, todas em código:

1. **Ferramentas não aceitam suposição:** sem data de retorno, `calcular_diarias` devolve
   `dados_incompletos`; matrícula fora do formato devolve `argumento_invalido`.
2. **`resposta.status`** é conferido antes de qualquer leitura; erro de API vira mensagem padrão.
3. **Barreira** (`seguranca/barreiras.py`), sobre os argumentos e resultados reais de
   `RunOutput.tools`:
   - toda matrícula consultada e toda data usada constam do pedido ou da complementação;
   - nome, UF, data do pedido e data de partida dos argumentos são os do pedido;
   - o saldo foi consultado com a unidade do cadastro e o valor calculado;
   - número do pedido e matrícula da saída correspondem ao pedido em análise;
   - quantidade e valor iguais aos da ferramenta (±R$ 0,005);
   - cada situação de critério igual à da ferramenta; recomendação coerente com elas;
   - antecedência insuficiente só é aceita com `exige_autorizacao_superior`, indício de
     urgência do § 1º e nenhuma ordem embutida;
   - minuta sem verbo decisório, dado pessoal, matrícula ou data estranha.
4. **Tela:** se recusada, mostra só a mensagem padrão; os motivos ficam no registro de auditoria.

### 7.3 Que dados do servidor o agente guarda, por quanto tempo, e como o titular os elimina?

- **O que:** no banco de trabalho do agente (`bancos/agente_diarias.db`): a sessão (id = nº do
  pedido, user_id = matrícula), as execuções (mensagens com matrícula, nome, destino, datas,
  justificativa **já mascarada** e resultados das ferramentas, que não contêm CPF nem e-mail).
  Memórias de usuário só existem se `update_memory_on_run` for ligado (não é, em produção).
- **Por quanto tempo:** pela duração da instrução; proposta de retenção de **30 dias após o
  último encaminhamento** do pedido (o banco é cópia de trabalho; o processo oficial já
  contém a instrução conferida). O expurgo automático por prazo **não foi implementado** —
  é o próximo passo, e hoje a eliminação é sob demanda.
- **Como elimina:** página "Memória e LGPD" ou `memoria/eliminacao.eliminar()`:
  1. localiza sessões pelo user_id do titular;
  2. localiza, por conteúdo, sessões que citam o titular sob **outro** user_id (o 0112);
  3. apaga as sessões (as execuções vão junto); as de outro user_id só com vínculo verificado
     pelo pedido e confirmação;
  4. lista e apaga as memórias com `delete_user_memories(memory_ids=…)`;
  5. inspeciona todas as tabelas por matrícula e nome e grava a evidência em
     `resultados/evidencias/`.
- **O que não é eliminado:** o processo de diárias, o registro de análises e as conferências
  (`bancos/registro_conferencias.db`) são registro de despesa pública, sujeitos à transparência
  e à guarda da prestação de contas (LGPD, art. 7º, II e art. 16, I).

### 7.4 Fundamentação das recomendações

Cada verificação traz no `detalhe` o dado da ferramenta; a tela lista as consultas com
argumentos e resultados. Uma recomendação só é exibida se cada critério coincidir com o
resultado da ferramenta correspondente.

## 8. Evidências da revisão

97 testes locais aprovados, fluxo da interface verificado e medições reais nas duas configurações de paralelismo, nas três configurações de memória e nos cenários de falha. Consulte `relatorio.md` e `resultados/relatorio_medicoes.md`.
