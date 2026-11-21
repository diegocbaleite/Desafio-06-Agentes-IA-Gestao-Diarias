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

O enunciado original não foi encontrado no workspace; a aderência integral à rubrica
permanece não comprovada. A tabela abaixo descreve as evidências da revisão histórica.

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
| Ambiente e dependências | .venv, requirements.txt | pip check, 98 testes e interface | instalado e verificado |
| Documentação e conferência humana | LEIA-ME.md, desenho.md, relatorio.md | resultados reais e formulário | atualizado |

Limites: o expurgo automático por prazo não foi implementado; urgência continua exigindo julgamento e conferência humana; os casos são fictícios e não cobrem toda a variedade de solicitações novas.
