# Rastreabilidade da revisão do Desafio 01
Atualizada em 19/11/2026 com os resultados reais e as verificações locais.

Atualização de 21/11/2026: os registros reais abaixo são históricos. A correção da
auditoria final foi validada sem API paga e está em `docs/CORRECOES_AUDITORIA.md`, com
evidência em `resultados/evidencias/correcao_auditoria_20261121.json`.

| Achado | Correção | Regressão |
|---|---|---|
| F1 — titular e exclusão indevida | Cadastro canônico e vínculo verificado de sessões e memórias | testes/test_auditoria_final.py |
| F2 — minuta contraditória | Minuta factual gerada no código após a barreira | testes/test_auditoria_final.py |
| F3 — pontuação bancária | Padrões compartilhados entre máscara e guardrail | testes/test_auditoria_final.py |
| F4 — dados em recusas | Sanitização na escrita SQLite, diagnósticos, registro administrativo e logs Agno | testes/test_auditoria_final.py |
| F5 — UF inexistente | Validação contra as 27 UFs | testes/test_auditoria_final.py |
| F6–F8 — documentação | Instalação, caminhos, JSONs de eliminação e descrição de paralelismo corrigidos | revisão documental |

Na auditoria de 19/11, o enunciado original não estava no workspace. Na revisão de entrega,
**o avaliador teve acesso ao documento oficial de 8 páginas, _Desafio 01 — Instrução de Pedidos de Diárias_**
(Aulas 01–07), fornecido separadamente. **Desafio 06** é o nome do repositório.
A matriz abaixo preserva as evidências históricas; o complemento final distingue a validação
local corrigida e a revisão manual posterior.

| Requisito | Implementação | Evidência | Situação |
|---|---|---|---|
| Processo, PEAS, confiabilidade, custo e autonomia | desenho.md | confronto no relatorio.md | documentado e confrontado |
| Quatro ferramentas, contas no código e docstrings | ferramentas/ | testes/test_ferramentas.py | verificado |
| Contrato, limites, filtro de dados e status | agente/, seguranca/ | testes e execuções reais | verificado |
| Matrículas, datas e valores ancorados | seguranca/barreiras.py | testes/test_barreira.py e testes/test_revisao.py | verificado, incluindo correção de matrícula |
| Memória nas três configurações | avaliacao/medir_memoria.py | resultados/medicao_memoria.json | medido na API real |
| Eliminação dos dois titulares e busca por conteúdo | memoria/ | medicao_memoria.json, testes e interface_revisao.json | conferido tabela por tabela |
| Formulário, progresso, minuta e conferência | app.py | interface_revisao.json | seis páginas verificadas |
| Complementação na mesma sessão | agente/ e app.py | testes, interface e medição de memória | verificado |
| Três rodadas dos doze pedidos e duas complementações | avaliacao/executar_casos.py | execucao_casos_paralelas_desligadas.json e ..._ligadas.json | medido na API real; acertos e erros no relatório |
| Comparação de paralelas | avaliacao/medir_desempenho.py | comparacao_desempenho.json | medido na API real |
| Quatro famílias de falha, nove cenários | avaliacao/provocar_falhas.py | falhas_provocadas.json | provocado e relatado, inclusive limites de detecção |
| Gabarito separado do agente e chave fora do código | avaliacao/externo/, .env e .gitignore | testes/test_isolamento.py | verificado |
| Isolamento entre demonstração e API | estado, formulários e confirmações em app.py | testes/test_interface_modos.py | verificado com AppTest |
| Ambiente e dependências | .venv, requirements.txt | pip check, 131 testes locais em 21/11 | verificado no ambiente de referência |
| Documentação e conferência humana | LEIA-ME.md, desenho.md, relatorio.md | resultados reais e formulário | atualizado |

Limites: o expurgo automático por prazo não foi implementado; urgência continua exigindo julgamento e conferência humana; os casos são fictícios e não cobrem toda a variedade de solicitações novas.

## Matriz final de entregáveis e critérios do enunciado

| Critério do enunciado oficial | Arquivo/função real | Evidência | Situação e limite |
|---|---|---|---|
| Etapa 1 — processo, PEAS, confiabilidade, custo e autonomia | [desenho.md](desenho.md) | Estimativa anterior e confronto em [relatorio.md](relatorio.md) | **Atendido** documentalmente |
| Etapa 2 — quatro ferramentas e docstrings; cálculo no código | `ferramentas/{cadastro,historico,calculos,orcamento}.py` | `testes/test_ferramentas.py`; registro [ferramentas_sem_agente.txt](resultados/evidencias/ferramentas_sem_agente.txt) | **Atendido** nos cenários testados |
| Etapa 3 — Pydantic, limites, filtro e status | `agente/agente_diarias.py`, `agente/modelos.py`, `seguranca/filtro_pii.py` | `testes/test_barreira.py`, `testes/test_filtro_pii.py` | **Atendido** nos formatos testados |
| Etapa 3 — barreira de argumentos e cálculo ancorado | `seguranca/barreiras.py:verificar_instrucao` | `testes/test_auditoria_final.py` e histórico de recusas | **Atendido** nos cenários testados |
| Etapa 4 — sessão por pedido, histórico, três configurações de memória | `agente/agente_diarias.py`, `avaliacao/medir_memoria.py` | [medição histórica](resultados/medicao_memoria.json); capturas 0111/0112 no [índice](resultados/INDICE_EVIDENCIAS_API_REAL.md) | **Atendido** no exercício |
| Etapa 4 — eliminação de duas titulares e verificação tabela a tabela | `memoria/eliminacao.py`, `memoria/verificacao.py` | JSONs históricos, [JSON posterior 0112](resultados/evidencias/eliminacao_api_207418_20261121155444.json) | **Atendido no banco de trabalho**; backups fora do escopo |
| Etapa 5 — formulário, minuta editável, revisão e mensagens de erro | `app.py`, `memoria/persistencia.py` | `testes/test_interface_modos.py` e [prints](resultados/INDICE_EVIDENCIAS_API_REAL.md) | **Atendido** nos fluxos avaliados |
| Medições — três rodadas, doze pedidos + duas complementações e paralelismo | `avaliacao/executar_casos.py` e `avaliacao/medir_desempenho.py` | [paralelas desligadas](resultados/execucao_casos_paralelas_desligadas.json) e [ligadas](resultados/execucao_casos_paralelas_ligadas.json) | **Atendido historicamente** em 19/11 (83/84 corretos, 1 recusa) |
| Falhas provocadas | `avaliacao/provocar_falhas.py` | [falhas_provocadas.json](resultados/falhas_provocadas.json) | **Atendido** com limites de detecção documentados |
| Entregáveis — desenho, fonte, resultados, relatório, LEIA-ME e exemplo sem chave | Arquivos existentes na raiz e pastas citadas | [inventário](docs/ESTRUTURA_PROJETO.md), [.env.example](.env.example), [.gitignore](.gitignore) | **Atendido** na publicação |
| Validação da versão corrigida | `testes/` | [131 aprovações locais](resultados/evidencias/pytest_correcao_20261121.txt) | **Verificado por log**, não equivale a nova bateria paga |

**Itens não exigidos expressamente pelo enunciado:** política de expurgo automático de 30 dias, autenticação corporativa/controle de papéis e implantação em produção. São aprimoramentos de engenharia e conformidade, não justificativa para reclassificar artificialmente um requisito do exercício como ausente.

**Importante:** testes registrados e capturas publicadas foram examinados como evidências; esta atualização documental não realizou novas chamadas à API ou ao banco.
