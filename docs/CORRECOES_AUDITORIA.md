# Correções da auditoria final — 21/11/2026

Exercício acadêmico: **Desafio 01 — Instrução de Pedidos de Diárias**.
Repositório: **Desafio 06 — Agentes de IA para Gestão de Diárias**.

As correções foram autorizadas após a entrega da auditoria independente. A validação
desta versão utilizou somente ferramentas locais, simulador e AppTest. Nenhuma nova
chamada à API real foi realizada; as medições de 19/11/2026 continuam históricas.

## Alterações realizadas

| Achado | Comportamento corrigido | Arquivos principais |
|---|---|---|
| F1 — eliminação de terceiro | O seletor usa as identidades do cadastro. A rotina recusa nome/matrícula divergentes antes de qualquer exclusão. Sessões e memórias exigem vínculo com os pedidos do titular, inclusive quando estão sob seu user_id. Registros sem vínculo são preservados e relacionados na evidência. | app.py; memoria/eliminacao.py |
| F2 — minuta contraditória | A minuta entregue é redigida no Python a partir dos campos aprovados pela barreira. Quantidade, valor, recomendação e exigência de autorização não são copiados da redação livre do modelo. A edição humana continua disponível e registrada. | agente/minuta.py; agente/agente_diarias.py |
| F3 — pontuação bancária | Agência, ag., ag, conta corrente/poupança e c/c aceitam separadores usuais, como dois-pontos, sinal de igualdade e indicação de número. Máscara da aplicação e guardrail usam os mesmos padrões. | seguranca/filtro_pii.py |
| F4 — persistência e diagnósticos | O adaptador SQLite sanitiza cópias de sessões, execuções, memórias e resultados de ferramentas antes da escrita, inclusive em caminhos de erro. A resposta original continua disponível à barreira para ser recusada. Motivos, registros administrativos, argumentos mostrados no progresso e logs Agno são sanitizados. | memoria/banco_protegido.py; memoria/persistencia.py; seguranca/barreiras.py; seguranca/filtro_pii.py |
| F5 — UF inexistente | A ferramenta calcula somente para as 27 UFs brasileiras; siglas inexistentes retornam argumento inválido. | ferramentas/acervo.py; ferramentas/calculos.py |
| F6 — instalação | Os guias usam a raiz do clone e o ambiente de referência Python 3.14.7. A indicação incorreta de compatibilidade com Python 3.10 foi removida. O lock exige no mínimo 3.12, mas outras versões não foram validadas. | LEIA-ME.md; docs/GUIA_TESTE_MANUAL.md |
| F7 — evidências manuais | O relatório identifica os dois JSONs de eliminação já incluídos. Capturas, hashes e JSONs históricos foram preservados. | resultados/evidencias-manuais/RELATORIO_VALIDACAO_MANUAL.md |
| F8 — paralelismo | A documentação distingue o limite de uma ferramenta por resposta da ordem verificada pela barreira. A hipótese compatível de paralelismo exige quatro chamadas; na bateria real histórica foram observadas cinco nos pedidos regulares. | desenho.md; docs/roteiro_apresentacao.md |

Os parâmetros da API permanecem os do projeto. O contrato mínimo da resposta do modelo
foi mantido; seu campo de minuta é tratado como rascunho. As estimativas e os números
anteriores de tokens/custo não foram recalculados como se pertencessem ao código corrigido.

## Verificação executada

- **131 testes aprovados em 38,20 s**: os 98 anteriores e 33 regressões da auditoria.
- **Zero falhas, erros ou testes ignorados.**
- Doze pedidos e duas complementações conferidos com o avaliador externo nas duas
  configurações de paralelismo; o agente foi reconstruído antes das complementações
  para exigir recuperação efetiva do SQLite. O gabarito não foi enviado ao simulador.
- Entradas bancárias com pontuação não chegaram ao endpoint nem ao banco; respostas
  com e-mail sintético foram recusadas sem vazar por motivos ou registros administrativos.
- Erro de API local com dado pessoal sintético foi sanitizado no log e no SQLite.
- Tentativas de eliminação com identidade incorreta foram bloqueadas; sessões de
  terceiros sob o mesmo user_id e memórias sem vínculo foram preservadas.
- AppTest carregou as seis páginas e verificou as duas complementações, a minuta
  gerada, a recusa de divergência sem justificativa, a preservação de uma edição humana
  e as duas eliminações com manutenção dos registros administrativos.
- `pip check`: `No broken requirements found.`
- `git diff --check` com reconhecimento de CRLF: sem problemas de whitespace.

A evidência resumida está em
[`resultados/evidencias/correcao_auditoria_20261121.json`](../resultados/evidencias/correcao_auditoria_20261121.json).
O log da suíte está em
[`resultados/evidencias/pytest_correcao_20261121.txt`](../resultados/evidencias/pytest_correcao_20261121.txt).

Para reproduzir sem chamadas pagas, use o Python da `.venv`. Se o diretório temporário
padrão do Pytest tiver permissões incompatíveis, escolha um diretório novo:

```powershell
$testeBase = Join-Path $env:TEMP ('regressao-diarias-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe -m pytest -v -p no:cacheprovider --basetemp $testeBase
```

## Limites que permanecem

- O enunciado original e sua rubrica não estão no workspace; não é possível comprovar
  aderência integral aos requisitos acadêmicos a partir dos documentos disponíveis.
- A retenção de 30 dias continua proposta, sem expurgo automático. Não foi criada uma
  política de exclusão por prazo sem o enunciado ou a definição de retenção aplicável.
- A confirmação de resíduos é uma busca lógica por matrícula/nome nas tabelas; não
  constitui uma verificação forense do disco, de cópias de segurança ou de outros sistemas.
- As proteções de escrita alcançam novas gravações. Não foi feita limpeza retroativa
  dos bancos originais, nem alteração das medições históricas ou da chave no `.env`.
- AppTest verifica comportamento e elementos produzidos; não houve nova inspeção visual
  interativa em navegador. A instalação limpa em outro computador não foi executada.
- O julgamento de urgência e a conferência humana permanecem necessários. O cenário F4c
  ainda documenta a mistura provocada ao fornecer identificadores de sessão incorretos;
  a aplicação usa os identificadores do pedido e da matrícula em cada execução.
- Os filtros cobrem os formatos testados; não se trata de certificação de conformidade
  jurídica ou de garantia universal contra prompt injection e dados pessoais em texto livre.

**Parecer sobre as correções:** os achados F1–F8 foram tratados e as regressões locais
passaram. A prontidão acadêmica integral depende da conferência do enunciado e das
ressalvas acima; este registro não declara 100% de conformidade.
