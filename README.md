# 🌿 Sistema de Gestão e Instrução de Pedidos de Diárias

Sistema desenvolvido em Python para instruir pedidos de diárias com um agente de IA,
consultas a dados estruturados, verificações no código e conferência humana em uma
aplicação Streamlit.

O projeto recebe o pedido, consulta cadastro funcional, histórico de diárias e prestações
de contas, calcula quantidades e valores, verifica o orçamento e apresenta uma recomendação
com a minuta do despacho. Quando o pedido retorna de uma diligência, a complementação é
tratada na mesma sessão, usando o histórico persistido.

**O agente instrui e recomenda; o servidor confere; o ordenador de despesa decide.**

Todos os servidores, matrículas, valores, pedidos e a IN SEMA nº 07/2026 utilizados no
exercício são **fictícios**.

---

## 👨‍💻 Identificação

**Aluno:**

- Diego Assunção Leite

**Curso:** FIC_DEV — Programador de Sistemas com IA.

**Módulo:** Inteligência Artificial Generativa — Aulas 01 a 17.

**Instituição:** SECITECI / Escola Técnica Estadual de Cuiabá.

**Atividade:** Desafio Prático 01 — Instrução de Pedidos de Diárias — versão 1.0 (2026).

**Repositório:** [Desafio-06-Agentes-IA-Gestao-Diarias](https://github.com/diegocbaleite/Desafio-06-Agentes-IA-Gestao-Diarias).

**Modalidade:** Individual.

---

## 🎯 Objetivo

Desenvolver uma aplicação modular capaz de:

- Consultar o cadastro funcional e identificar divergências entre nome e matrícula;
- Verificar prestações de contas vencidas e diárias já concedidas no mês;
- Calcular antecedência, quantidade e valor das diárias no código Python;
- Comparar o valor solicitado com o saldo da unidade de lotação;
- Produzir uma resposta estruturada, validada com Pydantic;
- Mascarar CPF, conta, agência bancária e e-mail antes do envio ao modelo;
- Recusar instruções com argumentos ou valores inconsistentes;
- Manter histórico por pedido para receber complementações;
- Eliminar dados do banco de trabalho e conferir se restaram ocorrências;
- Permitir a edição da minuta e o registro da decisão do conferente;
- Medir acertos, recusas, chamadas ao modelo, tokens, tempo e custo calculado;
- Verificar o comportamento diante de manipulação de texto, dados incompletos e falhas da API.

---

## 📌 Mapeamento da Implementação dos Requisitos

O mapeamento abaixo segue as etapas do desafio. A matriz completa está em
[requisitos_rastreabilidade.md](requisitos_rastreabilidade.md).

### 🔹 Desenho do processo e quadro PEAS

- **Requisito:** descrever o processo, o quadro PEAS, a confiabilidade composta, o custo
  por passos e o ponto de conferência humana.
- **Implementação:** [desenho.md](desenho.md) registra o fluxo e as estimativas anteriores
  às medições. O confronto com os resultados está em [relatorio.md](relatorio.md).

### 🔹 Ferramentas sobre os dados

- **Requisito:** implementar funções comuns em Python, com docstrings, minimização de
  dados e contas fora do modelo.
- **Implementação:** o pacote `ferramentas/` disponibiliza quatro consultas:

| Ferramenta | Responsabilidade |
|---|---|
| `consultar_servidor()` | Conferir cadastro, nome, matrícula, grupo de diária e unidade |
| `consultar_historico_diarias()` | Consultar prestações de contas e diárias do mês |
| `calcular_diarias()` | Calcular quantidade, valor, antecedência e limite mensal |
| `consultar_saldo_diarias()` | Consultar o saldo da unidade e compará-lo com o valor calculado |

As contas monetárias utilizam `Decimal`. As ferramentas devolvem resultados em JSON
com os argumentos utilizados e a identificação da fonte e da regra aplicada.

### 🔹 Agente com saída estruturada e barreiras

- **Requisito:** integrar ferramentas, contrato de saída, limites, filtro de dados pessoais
  e verificação do resultado da execução.
- **Implementação:** `agente/agente_diarias.py` constrói o agente Agno e executa a instrução.
  As classes `Verificacao` e `Instrucao`, em `agente/modelos.py`, definem o contrato Pydantic.
  A resposta só segue à tela após a conferência do status e de `verificar_instrucao()`,
  em `seguranca/barreiras.py`.

A configuração padrão utiliza `tool_call_limit=6`, `num_history_runs=3`,
`parallel_tool_calls=False`, `reasoning_effort="none"` e `telemetry=False`.

### 🔹 Memória, complementação e eliminação

- **Requisito:** manter a sessão do pedido, medir três configurações de memória e comprovar
  a eliminação dos dados do titular.
- **Implementação:** o agente usa `SqliteDb`, com `session_id` igual ao número do pedido
  e `user_id` igual à matrícula utilizada na sessão. A complementação recupera o histórico
  do pedido. `memoria/eliminacao.py` localiza e elimina registros, enquanto
  `memoria/verificacao.py` procura matrícula e nome nas tabelas.

No caso de matrícula corrigida, a eliminação também procura referências gravadas sob
outro `user_id` e exige a verificação e a confirmação do vínculo antes de apagar a sessão.

### 🔹 Formulário de conferência humana

- **Requisito:** mostrar verificações, fontes, recomendação, pendências, alertas e uma
  minuta editável, registrando o encaminhamento escolhido pelo servidor.
- **Implementação:** `app.py` organiza o formulário em seis páginas:

| Página | Finalidade |
|---|---|
| Painel | Apresentar os pedidos e o resumo do acompanhamento |
| Análise de pedidos | Executar as consultas e mostrar a instrução verificada |
| Conferência humana | Editar a minuta e registrar a decisão, com justificativa na divergência |
| Diligências | Receber complementações e reanalisar na mesma sessão |
| Memória e LGPD | Inspecionar registros, eliminar dados e verificar resíduos |
| Resultados e auditoria | Consultar medições, falhas, análises e evidências |

### 🔹 Avaliação e modos de falha

- **Requisito:** executar os doze pedidos e as duas complementações em três rodadas,
  comparar paralelismo, medir memória e provocar falhas.
- **Implementação:** os módulos de `avaliacao/` comparam as respostas com o gabarito
  externo e gravam os resultados. O gabarito fica em `avaliacao/externo/` e não é
  fornecido ao agente.

---

## ⚠️ Decisões para Dados Inválidos e Falhas

1. **Sem cálculo com informação ausente:** uma data de retorno não informada exige
   diligência; o modelo não deve substituí-la por uma data provável.
2. **Matrícula consistente entre consultas:** histórico e cálculo precisam usar a
   matrícula conferida no cadastro, inclusive após uma complementação.
3. **Valores conferidos no código:** quantidades e valores devem coincidir com os
   resultados das ferramentas. Números não finitos são recusados.
4. **Saldo após o cálculo:** a consulta de orçamento deve usar a unidade do cadastro e
   o total calculado, respeitando a ordem registrada das consultas.
5. **Texto do solicitante tratado como dado:** ordens embutidas na justificativa não
   alteram as regras da análise e devem gerar alerta.
6. **Falha visível:** erro de execução ou recusa da barreira apresenta a mensagem padrão
   e encaminha o pedido à análise manual, sem exibir a instrução recusada.
7. **Conferência registrada:** uma decisão divergente exige justificativa. A minuta final
   e o encaminhamento ficam no registro administrativo.
8. **Evidências preservadas:** bancos do simulador ficam separados dos bancos reais;
   a falta de chave não apaga uma medição anterior já concluída.

---

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Uso no projeto |
|---|---|
| Python 3.14.7 | Ambiente de referência validado |
| Agno 3.0.9 | Agente, ferramentas, histórico e persistência |
| SDK OpenAI | Comunicação com o modelo de linguagem |
| Pydantic | Contrato e validação da resposta estruturada |
| Streamlit | Formulário interativo de análise e conferência |
| SQLAlchemy com `asyncio` e `greenlet` | Dependências da persistência usada pelo Agno |
| SQLite | Bancos locais do agente e do registro administrativo |
| python-dotenv | Leitura da configuração no `.env` |
| Pandas | Tabelas da interface |
| Pytest | Testes automatizados |
| tiktoken | Estimativa de tokens |
| Decimal e Regex | Contas monetárias, validações e reconhecimento de padrões |
| GitHub | Publicação e histórico do código |

As dependências principais estão em `requirements.txt`. O arquivo
`requirements.lock.txt` registra as 73 dependências instaladas na revisão.

---

## 📁 Estrutura do Projeto

```text
Desafio-06-Agentes-IA-Gestao-Diarias/
├── agente/                      # Agente, instruções e contrato Pydantic
├── ferramentas/                 # Cadastro, histórico, cálculos e orçamento
├── seguranca/                    # Filtro de dados pessoais e barreiras
├── memoria/                      # Persistência, eliminação e verificação
├── avaliacao/                    # Execução dos casos e medições
│   └── externo/gabarito.json      # Respostas esperadas, separadas do agente
├── simulador/                    # API local para demonstração e testes
├── dados/                        # Acervo fictício utilizado pela aplicação
├── exemplos/                     # Gerador e dados de referência do exercício
├── testes/                       # Testes unitários, de integração e regressão
├── resultados/
│   ├── evidencias/               # Evidências dos testes e da interface
│   ├── historico/                # Resultados anteriores preservados
│   └── simulador/                # Saídas identificadas como simulação
├── docs/roteiro_apresentacao.md
├── app.py
├── config.py
├── desenho.md
├── relatorio.md
├── requisitos_rastreabilidade.md
├── LEIA-ME.md
├── requirements.txt
├── requirements.lock.txt
├── .env.example
├── .gitignore
└── README.md
```

A `.venv`, o `.env` e a pasta `bancos/` são locais e ficam fora do versionamento.

---

## ⚙️ Configuração

O módulo `config.py` lê as variáveis do `.env`. A estrutura de configuração está
documentada em [.env.example](.env.example):

```dotenv
OPENAI_API_KEY=
MODELO_DIARIAS=gpt-5.6-luna
TOOL_CALL_LIMIT=6
NUM_HISTORY_RUNS=3
PARALLEL_TOOL_CALLS=false
USD_ENTRADA_POR_MILHAO=0.20
USD_SAIDA_POR_MILHAO=1.20
AGNO_TELEMETRY=false
```

`gpt-5.6-luna` é o modelo de referência usado nas medições registradas. Os preços
configurados servem para calcular uma estimativa de custo a partir dos tokens informados
pelo provedor; esse cálculo não é uma fatura da API.

Para usar a API real, preencha a chave somente no `.env`. Para demonstrar o fluxo sem
chave, ative o **Modo demonstração** na barra lateral. O simulador não mede o comportamento
do modelo real. Chamadas reais consomem créditos da API.

---

## 🐍 Ambiente Virtual e Instalação

### 1. Clonar o repositório

```powershell
git clone https://github.com/diegocbaleite/Desafio-06-Agentes-IA-Gestao-Diarias.git
cd Desafio-06-Agentes-IA-Gestao-Diarias
```

### 2. Criar a `.venv`

No Windows PowerShell:

```powershell
python -m venv .venv
```

No Linux/macOS:

```bash
python3 -m venv .venv
```

### 3. Instalar as dependências

No Windows, os comandos podem usar diretamente o Python do ambiente, sem ativá-lo:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

No Linux/macOS:

```bash
.venv/bin/python -m pip install -r requirements.lock.txt
test -f .env || cp .env.example .env
```

O ambiente validado é Windows com Python 3.14.7. Após mover ou copiar o projeto para
outro local, recrie a `.venv`, pois seus comandos podem conter caminhos absolutos.

---

## ▶️ Execução da Aplicação

No Windows:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

No Linux/macOS:

```bash
.venv/bin/python -m streamlit run app.py
```

O Streamlit informa no terminal o endereço para abrir a aplicação. Sem chave, utilize
o modo demonstração. Com a chave configurada, desligue esse modo para usar a API real.

Para verificar somente as ferramentas, sem chamar o modelo:

```powershell
.\.venv\Scripts\python.exe -m ferramentas
```

---

## 🧪 Testes Automatizados

Os testes cobrem ferramentas, regras de cálculo, filtro de dados pessoais, barreiras,
histórico, eliminação, conferência humana, isolamento do gabarito e regressões.

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Resultado registrado na revisão de **19/11/2026**:

```text
97 passed in 18.30s
```

São 84 testes existentes e 13 regressões acrescentadas na revisão. Esses testes não
fazem chamadas à API real. A conferência das seis páginas e do fluxo da interface
também foi realizada com `AppTest`.

Evidências: [testes](resultados/evidencias/pytest_revisao.txt) e
[interface](resultados/evidencias/interface_revisao.json).

---

## 📊 Medições com a API Real

A bateria executou os doze pedidos e as duas complementações em três rodadas para
cada configuração de chamadas paralelas.

| Configuração | Acertos | Recusas da barreira | Instruções erradas entregues |
|---|---:|---:|---:|
| Paralelas desligadas | 41/42 | 1 | 0 |
| Paralelas ligadas | 42/42 | 0 | 0 |
| **Total** | **83/84** | **1** | **0** |

A recusa ocorreu porque o modelo deixou de realizar consultas obrigatórias no pedido
com tentativa de manipulação. A barreira impediu a exibição da instrução sem essas fontes.

Também foram medidas as três configurações de memória:

| Configuração | Complementações aplicadas ao pedido certo |
|---|---:|
| Sem memória | 0/2 |
| Histórico da sessão | 2/2 |
| Histórico e memórias do usuário | 2/2 |

Nas duas rotinas de eliminação, a verificação terminou sem resíduos após a confirmação
dos vínculos. Foram executados ainda nove cenários de falha, incluindo manipulação de
texto, dados incompletos, limite insuficiente de ferramentas, erro de API e configuração
incorreta dos identificadores de sessão.

As 84 execuções repetem os quatorze casos fictícios do exercício. Os resultados e as
limitações estão detalhados em [relatorio.md](relatorio.md) e no
[relatório automático](resultados/relatorio_medicoes.md).

---

## 📈 Reprodução das Medições

Com a chave configurada, execute na pasta do projeto:

```powershell
.\.venv\Scripts\python.exe -m avaliacao.executar_casos
.\.venv\Scripts\python.exe -m avaliacao.executar_casos --paralelas
.\.venv\Scripts\python.exe -m avaliacao.medir_memoria
.\.venv\Scripts\python.exe -m avaliacao.provocar_falhas
.\.venv\Scripts\python.exe -m avaliacao.medir_desempenho
.\.venv\Scripts\python.exe -m avaliacao.gerar_relatorio
```

Para exercitar o fluxo sem chamar a API real, acrescente `--simulador` aos comandos
de avaliação. Os resultados de simulação ficam em `resultados/simulador/`, separados
das medições reais.

---

## 🔀 Controle de Versão

O código, a documentação e as evidências estão publicados na branch **`main`**.
O `.gitignore` exclui a chave da API, ambientes virtuais, configurações locais e bancos.

[Repositório no GitHub](https://github.com/diegocbaleite/Desafio-06-Agentes-IA-Gestao-Diarias)

---

## 🤖 Uso de Ferramentas de IA

O desenvolvimento e a revisão contaram com apoio do **ChatGPT/Codex**.

### Finalidades do apoio

- Analisar os requisitos do desafio e a organização do projeto;
- Apoiar a implementação e a revisão do código;
- Configurar e verificar o ambiente virtual e as dependências;
- Identificar falhas e acrescentar testes de regressão;
- Exercitar o formulário e analisar as medições;
- Revisar a documentação e preparar a publicação no GitHub.

As solicitações durante o trabalho incluíram verificar a prontidão do projeto, instalar
a `.venv`, revisar e completar a implementação, executar as medições autorizadas e
publicar o código no repositório.

**Autor responsável pela entrega:** Diego Assunção Leite.

---

## 📚 Documentação Complementar

- [Instruções detalhadas e decisões técnicas](LEIA-ME.md)
- [Desenho do processo, PEAS e estimativas](desenho.md)
- [Relatório da revisão e limitações](relatorio.md)
- [Relatório de medições gerado a partir dos resultados](resultados/relatorio_medicoes.md)
- [Rastreabilidade dos requisitos](requisitos_rastreabilidade.md)
- [Roteiro de apresentação](docs/roteiro_apresentacao.md)

Entre as limitações registradas estão o expurgo automático por prazo ainda não
implementado, o julgamento textual de urgência e a possível mistura de pedidos quando
se provocam identificadores de sessão incorretos. A conferência humana permanece no fluxo.

---

## 👨‍💻 Autores

- **Diego Assunção Leite**

**FIC_DEV — Programador de Sistemas com IA — SECITECI / Escola Técnica Estadual de Cuiabá — 2026.**
