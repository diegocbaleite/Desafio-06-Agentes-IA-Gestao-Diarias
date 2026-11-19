# Agente de IA para instrução de pedidos de diárias

Implementação do exercício **Instrução de Pedidos de Diárias**, com Agno, Python e Streamlit.
O agente consulta cadastro, histórico, cálculos e orçamento, aplica uma barreira de verificação
e apresenta a instrução para conferência humana. A decisão final permanece com o ordenador.

Todos os dados e a norma usados no exercício são **fictícios**.

## Executar no Windows

Ambiente validado: **Python 3.14.7**. Na pasta do repositório, execute no PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Sem chave da API, use o **modo demonstração** da barra lateral. Para usar a OpenAI,
preencha `OPENAI_API_KEY` no `.env` e desligue o modo demonstração. Chamadas reais
consomem créditos da API. O modelo de referência do exercício é configurável no `.env`.

O ambiente virtual e os bancos são criados localmente. O arquivo `.env.example` documenta
a configuração; a chave da API fica somente no `.env`, fora do versionamento.

## Verificar

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ferramentas
```

- **97 testes aprovados**, incluindo validação de argumentos, filtro de dados pessoais,
  memória, eliminação, isolamento do gabarito e regressões da revisão.
- Seis páginas do formulário verificadas com `AppTest`.
- Bateria com a API real: **41/42 acertos com paralelas desligadas e 42/42 com elas ligadas**,
  uma recusa segura e nenhuma instrução errada entregue nos 84 casos executados.
- Três configurações de memória e nove cenários de falha medidos.

As rodadas repetem os quatorze casos do exercício. Os resultados não substituem a
conferência humana. As saídas do simulador ficam separadas das medições reais.

## Documentação e evidências

- [Como executar e decisões técnicas](LEIA-ME.md)
- [Desenho do processo e quadro PEAS](desenho.md)
- [Relatório da revisão e limitações](relatorio.md)
- [Relatório automático de medições](resultados/relatorio_medicoes.md)
- [Rastreabilidade dos requisitos](requisitos_rastreabilidade.md)
- [Roteiro de apresentação](docs/roteiro_apresentacao.md)
- [Evidências dos testes e da interface](resultados/evidencias/)

O gabarito fica separado do agente, em `avaliacao/externo/`. A eliminação alcança o
banco de trabalho do agente; o registro administrativo da conferência é mantido em
banco separado. A retenção por prazo está documentada, e o expurgo automático é uma
limitação registrada no relatório.
