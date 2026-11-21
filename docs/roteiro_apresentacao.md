# Roteiro de apresentação (12–14 minutos)

Preparação: `streamlit run app.py` aberto no navegador; terminal na pasta do projeto;
`resultados/relatorio_medicoes.md` gerado. Se a chave estiver configurada, rode antes as
medições (LEIA-ME §3) e use os números de `resultados/`. Sem chave, apresente no **modo
demonstração** e diga com clareza, uma vez, que ele **não é o modelo**.

| Min | Bloco | O que mostrar | O que dizer |
|---|---|---|---|
| 0:00 | Problema | Painel | Centenas de pedidos por mês, 4 fontes, erro descoberto na auditoria; diligência obriga a reconstituir o caso. |
| 1:00 | Objetivo e arquitetura | `desenho.md` §2 (diagrama) | Um agente Agno, 4 ferramentas, contrato Pydantic, barreira no código, formulário. O agente não decide. |
| 2:00 | PEAS e aritmética | `desenho.md` §6–8 | 5 passos: 77% a 95%. Por isso a barreira: transformar erro silencioso em recusa visível. Custo estimado ≈ US$ 0,006 por pedido; 1ª chamada estimada no dobro da referência — e por quê. |
| 3:30 | Ferramentas | terminal: `python -m ferramentas` | Docstring é a especificação; contas em Decimal; 0112 diverge sem revelar o outro servidor; 0108 vencida × 0102 no prazo; 0103 meia diária; 0110 saldo. |
| 4:30 | Agno | `agente/agente_diarias.py::construir_agente` | `output_schema`, `tool_call_limit=6`, `reasoning_effort="none"`, paralelas desligadas, `pre_hooks`, `SqliteDb`; ids em cada `run`. |
| 5:30 | Pedido regular | Análise → DIA-2026-0101 | Progresso por ferramenta; verificações com fundamento; consultas com argumentos; minuta. |
| 6:30 | Proteção de dados | Análise → DIA-2026-0104 | CPF, conta e agência mascarados antes do modelo e do banco; matrícula e datas legíveis. |
| 7:15 | Impedimento | Análise → DIA-2026-0110 (ou 0108) | Não recomendado, com o saldo da ferramenta como fundamento. |
| 7:45 | Prompt injection | Análise → 0106 e 0107 lado a lado | 0106: urgência com autorização escrita exigida. 0107: ordem ignorada, alerta. Barreira: aceitar antecedência com ordem embutida é recusa. |
| 8:45 | Diligência e memória | Análise → 0112; Diligências → complementação | Sessão recuperada sob 207481; 3,5 diárias, R$ 770,00; alerta de associação. |
| 9:45 | Conferência humana | Conferência → divergir sem justificativa | O sistema exige motivo; recomendação (azul) × decisão (verde); minuta editável. |
| 10:30 | Eliminação verificável | Memória e LGPD → titular 207418 | A busca por user_id acha 0 sessões; a varredura acha a do 0112; só apaga com vínculo e confirmação; "Nada restou". |
| 11:30 | Métricas e falhas | Resultados e auditoria; relatorio.md | paralelas desligadas: 14, 14, 13 de 14; paralelas ligadas: 14, 14, 14 de 14. Mostrar as três configurações de memória e os nove cenários de falha na API real; explicar recusas e limites de detecção. |
| 12:30 | Conclusão | `relatorio.md` §8–9 | O agente instrui; a pessoa confere; o ordenador decide. Limitações e próximo passo (expurgo por prazo e novos casos de validação). |

## Perguntas prováveis e respostas

**Por que um só agente e não uma equipe?** O enunciado pede um; e a aritmética da Aula 01
mostra que mais agentes = mais passos = menos confiabilidade. Os passos aqui são consultas, não
especialidades.

**Se a barreira confere tudo, para que o modelo?** A barreira confere o que é verificável
(argumentos, números, coerência); o modelo faz o que não é regra fechada: ler a justificativa,
julgar urgência, perceber a ordem embutida, redigir pendências e encadear as consultas.
A minuta factual final é gerada no Python a partir dos campos verificados. Onde há
julgamento (urgência), a barreira só exige indícios e autorização superior.

**Por que paralelas desligadas?** O saldo depende do valor e da unidade. O parâmetro limita
cada resposta a zero ou uma ferramenta; a barreira verifica a ordem das consultas.
No simulador, agrupar histórico e cálculo após o cadastro economiza uma chamada. Na bateria
real histórica não houve ferramentas simultâneas; não afirme ganho real de paralelismo.

**Por que `tool_call_limit=6`?** São 4 consultas; 2 de margem para uma repetição. Com 2, a
instrução fica incompleta e é recusada (F2b).

**Como sabem que o gabarito não vazou?** Ele só existe em `avaliacao/externo/` e só
`comparar_gabarito.py` o lê; um teste varre os módulos do agente e da tela.

**Tokens: por que o medido (22.606) é o dobro da referência?** Docstrings completas (1.846 tokens),
norma na instrução (642) e resultados com fonte/regra/argumentos. É custo de auditabilidade;
encurtar só depois de medir o acerto.

**E se o modelo inventar uma matrícula real de outro servidor?** A barreira compara cada
matrícula de argumento com as do pedido e da complementação; qualquer outra recusa.

**O que a memória guarda e por quanto tempo?** Sessão e execuções por pedido; sem memórias de
usuário em produção. Retenção proposta de 30 dias após o encaminhamento; expurgo automático
ainda não implementado (limitação declarada).

**Por que não apagar a sessão do 0112 automaticamente?** Ela está sob a matrícula de outro
servidor. Apagar dado de terceiro sem verificar vínculo é outro incidente. A rotina exige o
vínculo (o pedido foi protocolado em nome da titular) e confirmação.

**A eliminação apaga o processo?** Não. O processo, as análises e as conferências são registro
de despesa pública com guarda legal; só o banco de trabalho do agente é eliminado.

**O que não funciona?** Sem chave, não há medição do modelo. F4c (identificador derivado da
unidade) não é detectado pela barreira quando a instrução sai coerente. Urgência descrita de
forma convincente, mas falsa, passa — por isso o humano.
