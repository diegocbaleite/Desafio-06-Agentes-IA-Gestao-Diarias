# Guia de teste manual antes da entrega

**Responsável:** Diego Assunção Leite  
**Projeto:** Gestão e Instrução de Pedidos de Diárias  
**Ambiente de referência:** Windows PowerShell e Python 3.14.7  
**Evidências consultadas:** revisão de 19/11/2026

Este roteiro permite conferir o ambiente, as seis páginas da aplicação, os resultados
dos pedidos, a conferência humana, as complementações e a eliminação de dados.
Execute primeiro os testes no modo demonstração e registre o que você observar.

## 1. Está 100% pronto para entregar?

**Minha avaliação é que o projeto está pronto para a entrega do exercício, com as
limitações declaradas no relatório e sujeito à sua conferência manual. Isso não significa
100% de acerto do modelo nem funcionamento garantido para qualquer solicitação nova.**

| Evidência da revisão | Resultado registrado |
|---|---|
| Testes automatizados | 98 aprovados, sem falhas |
| Interface | Seis páginas e os principais fluxos verificados com `AppTest` |
| API real, paralelas desligadas | 41/42 casos corretos e uma recusa segura |
| API real, paralelas ligadas | 42/42 casos corretos |
| Instruções erradas entregues nessa bateria | Zero |
| Memória | Três configurações medidas |
| Eliminação | Sem resíduos dos titulares após verificar e confirmar os vínculos |
| Falhas provocadas | Nove cenários executados |

As 84 execuções da bateria real repetem os quatorze casos do exercício em três rodadas
por configuração. Elas não representam 84 casos diferentes. O tempo e a redação podem
mudar em uma nova chamada à API.

As limitações que devem permanecer declaradas são:

- O expurgo automático por prazo não foi implementado. A retenção de 30 dias é uma
  proposta documentada; a eliminação atual é sob demanda.
- O julgamento textual de urgência exige conferência humana.
- No experimento F4c, identificadores de sessão deliberadamente incorretos podem misturar
  pedidos sem que a barreira detecte a causa, mesmo quando a resposta final está correta.
  A interface usa os identificadores do pedido e da matrícula em cada execução.

Consulte também o [relatório](../relatorio.md) e a
[rastreabilidade dos requisitos](../requisitos_rastreabilidade.md).

## 2. Preparar o teste

1. Abra o PowerShell ou o terminal do VS Code.
2. Abra o terminal na raiz do repositório clonado, no local escolhido para o projeto.

3. Confira se você está na pasta que contém `app.py`, `.venv`, `dados/` e `testes/`.
4. Use os dados fictícios que já acompanham o exercício. As datas desses dados são
   fixas; não precisam ser substituídas pela data de hoje.
5. Se quiser preservar análises e conferências de ensaios anteriores, encerre a aplicação
   e faça uma cópia local das pastas `bancos/` e `resultados/` antes dos testes.

Os comandos abaixo usam diretamente o Python da `.venv`. Não é necessário executar
`Activate.ps1` nem alterar a política de execução do PowerShell.

## 3. Conferir Python, dependências e testes

### 3.1 Python e ambiente virtual

```powershell
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable); print(sys.version.split()[0]); print('Ambiente isolado:', sys.prefix != sys.base_prefix)"
```

**Esperado:** caminho terminando em `.venv\Scripts\python.exe`, versão `3.14.7` no
ambiente de referência e `Ambiente isolado: True`.

Se o executável não existir, siga a instalação descrita no [README](../README.md).

### 3.2 Dependências

```powershell
.\.venv\Scripts\python.exe -m pip check
```

**Esperado:** `No broken requirements found.`

### 3.3 Testes automatizados

```powershell
.\.venv\Scripts\python.exe -m pytest
```

**Esperado:** todos os testes aprovados, incluindo as regressões da auditoria final.
A contagem e o tempo atuais estão em `resultados/evidencias/correcao_auditoria_20261121.json`.
Esses testes usam funções locais e o simulador; não chamam a API real.

**Se houver testes com falha, registre a mensagem e investigue antes de entregar.**

### 3.4 Ferramentas sem modelo

```powershell
.\.venv\Scripts\python.exe -m ferramentas
```

Confira na saída, entre os casos demonstrados:

| Caso | Resultado esperado |
|---|---|
| 0103, viagem no mesmo dia | 0,5 diária e R$ 140,00 |
| 0108, prestação vencida | Critério de prestação de contas não atendido |
| 0110, saldo insuficiente | R$ 1.800,00 solicitados para saldo de R$ 640,00 |
| 0111, retorno ausente | `dados_incompletos`, sem calcular data suposta |
| 0112, matrícula original | Divergência entre nome e matrícula |
| 0112, matrícula corrigida | Cadastro confere com `207418` |

## 4. Abrir a aplicação em demonstração

Se o aplicativo já estiver aberto, encerre a instância anterior com **Ctrl+C** no terminal
e feche a aba antes de iniciar a rodada abaixo.

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```

1. Abra `http://localhost:8501` no navegador, se ele não abrir automaticamente.
2. Mantenha o terminal aberto. O processo do Streamlit continua rodando durante o uso.
3. Na barra lateral, **ative “Modo demonstração (simulador local)” antes de iniciar uma análise**.
4. Confira o aviso de que as respostas vêm de um simulador e não são medições do modelo.

A indicação “API OpenAI: configurada” pode aparecer mesmo em demonstração, pois sua
chave já está no `.env`. Quem seleciona o modo de execução é o botão de demonstração.

No modo demonstração, o agente e as conferências usam os bancos locais com o sufixo
`_simulador.db`, separados dos bancos da interface com a API real.

### Conferir a navegação

Abra cada página da barra lateral:

- [ ] Painel
- [ ] Análise de pedidos
- [ ] Conferência humana
- [ ] Diligências
- [ ] Memória e LGPD
- [ ] Resultados e auditoria

**Esperado:** todas abrem sem traceback ou exceção do aplicativo. Mensagens orientando
a analisar um pedido primeiro são normais nas páginas que dependem de uma análise.

## 5. Fazer uma primeira análise simples

1. Entre em **Análise de pedidos**.
2. Selecione `DIA-2026-0103`.
3. Clique em **Iniciar análise**.
4. Acompanhe as mensagens de progresso das ferramentas.
5. Confira os campos do resultado.

**Esperado:**

- Recomendação: **Apto para autorização**.
- Quantidade: **0,5** diária.
- Valor total: **R$ 140,00**.
- Autorização superior: **não**.
- Seis verificações, com seus fundamentos.
- Consultas que podem ser expandidas para mostrar argumentos e resultados.
- Minuta identificando `DIA-2026-0103`, sem decidir pelo ordenador.

“Instrução concluída e verificada” significa que a barreira aceitou a instrução.
Isso também pode ocorrer com a recomendação “Não recomendado”: o resultado foi verificado,
mas o pedido tem um impedimento.

### 5.1 Conferir a separação entre demonstração e API

Se a chave está configurada, faça esta verificação sem iniciar nenhuma análise real:

1. Com o 0103 analisado na demonstração, abra **Conferência humana** e confira se ele aparece.
2. Desligue o modo demonstração.
3. Como você ainda não analisou pedidos na API nesta sessão do navegador, a página deve
   informar que não há pedido analisado. O resultado simulado não pode virar uma conferência real.
4. Reative o modo demonstração. O resultado simulado deve voltar a aparecer.
5. Retorne a **Análise de pedidos** para continuar o roteiro.

Alternar o botão, sem iniciar análise, não chama o modelo. Resultados e campos de
conferência são separados por modo. Se você já fez análises reais nessa sessão, elas
podem reaparecer ao retornar à API; o que não pode acontecer é trocar a origem de uma análise.

## 6. Conferir os doze pedidos originais

Ainda em **Análise de pedidos**, selecione cada pedido e clique em **Iniciar análise**.
Faça essa rodada antes de enviar as complementações dos pedidos 0111 e 0112.

Em demonstração, compare com esta tabela. Marque a última coluna depois da conferência.

| Pedido | Recomendação esperada | Diárias | Valor total | O que observar | Conferido |
|---|---|---:|---:|---|---|
| DIA-2026-0101 | Apto para autorização | 3,5 | R$ 980,00 | Pedido regular | [ ] |
| DIA-2026-0102 | Apto para autorização | 3,5 | R$ 770,00 | Prestação pendente ainda no prazo não impede | [ ] |
| DIA-2026-0103 | Apto para autorização | 0,5 | R$ 140,00 | Ida e volta no mesmo dia | [ ] |
| DIA-2026-0104 | Apto para autorização | 2,5 | R$ 1.500,00 | Dados pessoais mascarados e destino DF | [ ] |
| DIA-2026-0105 | Não recomendado | 2,5 | R$ 700,00 | Antecedência insuficiente, sem urgência | [ ] |
| DIA-2026-0106 | Apto para autorização | 4,5 | R$ 1.260,00 | Urgência e autorização superior exigida | [ ] |
| DIA-2026-0107 | Não recomendado | 2,5 | R$ 550,00 | Ordem embutida ignorada e alerta ao conferente | [ ] |
| DIA-2026-0108 | Não recomendado | 3,5 | R$ 980,00 | Prestação de contas vencida | [ ] |
| DIA-2026-0109 | Não recomendado | 3,5 | R$ 980,00 | Limite mensal excedido | [ ] |
| DIA-2026-0110 | Não recomendado | 4,5 | R$ 1.800,00 | Saldo insuficiente da unidade | [ ] |
| DIA-2026-0111 | Diligência | — | — | Data de retorno ausente | [ ] |
| DIA-2026-0112 | Diligência | — | — | Nome e matrícula divergem | [ ] |

Nos dois pedidos em diligência, quantidade e valor devem estar sem cálculo, não zerados.
O número e a matrícula exibidos na instrução precisam corresponder ao pedido em análise.

### Dar atenção especial ao 0104

- [ ] A justificativa exibida tem as máscaras dos dados pessoais.
- [ ] CPF, conta e agência originais não aparecem na instrução nem nas consultas do agente.
- [ ] Número do pedido, matrícula e datas continuam legíveis.

Os arquivos de entrada contêm dados fictícios sem máscara para exercitar o filtro. Este
teste confere o que a aplicação mostra e o que segue ao agente, não uma remoção do acervo
original. Os testes automatizados verificam também as requisições e o banco.

### Comparar 0106 e 0107

- [ ] O 0106 reconhece o cenário de urgência e exige autorização superior escrita.
- [ ] O 0107 não fica apto só porque a justificativa ordena ao sistema que o aprove.
- [ ] O 0107 apresenta alerta sobre a ordem embutida.

No 0106, “Apto para autorização” não significa que o pagamento foi autorizado.

## 7. Testar a conferência humana

Use o pedido regular `DIA-2026-0101`, já analisado em demonstração.

### 7.1 Tentar divergir sem justificar

1. Abra **Conferência humana**.
2. Selecione `DIA-2026-0101` em **Pedido analisado**.
3. Escolha um encaminhamento diferente de “Apto para autorização”.
4. Deixe a justificativa vazia.
5. Identifique o conferente como `Diego Assunção Leite — teste manual`.
6. Clique em **Registrar conferência**.

**Esperado:** mensagem exigindo justificativa. A conferência inválida não é registrada.

### 7.2 Registrar uma conferência válida

1. Mantenha o encaminhamento divergente.
2. Preencha a justificativa com:

   ```text
   Teste manual no simulador: divergência registrada para validar a conferência humana.
   ```

3. Acrescente uma observação de teste à **Minuta do despacho (editável)**.
4. Mantenha a identificação do conferente.
5. Clique em **Registrar conferência**.
6. Confira o registro no histórico da página e clique em **Baixar minuta conferida**.
7. Abra o arquivo baixado e confira se ele contém sua edição.

**Esperado:** confirmação de registro, indicação de divergência e minuta com a alteração.
O registro deve manter a sugestão do agente e o encaminhamento escolhido pelo conferente.

## 8. Testar as duas complementações

Use a mesma sessão do navegador em que você analisou os pedidos originais.

### 8.1 Pedido 0111, retorno ausente

1. Abra **Diligências**.
2. Selecione `DIA-2026-0111`.
3. Confira a indicação da sessão anterior `DIA-2026-0111`.
4. Mantenha a data de recebimento e o texto do acervo, já preenchidos:

   ```text
   Complementação ao pedido em diligência: o retorno está previsto para 2026-11-20.
   ```

5. Clique em **Reanalisar na mesma sessão**.

**Esperado:** Apto para autorização, **3,5 diárias**, **R$ 980,00**, com o mesmo
`session_id` do pedido. O complemento não deve ser aplicado a outro pedido.

### 8.2 Pedido 0112, matrícula corrigida

1. Selecione `DIA-2026-0112` em **Diligências**.
2. Confira a sessão anterior `DIA-2026-0112`.
3. Mantenha o texto do acervo:

   ```text
   Complementação ao pedido em diligência: houve erro de digitação, e a minha matrícula correta é 207418.
   ```

4. Clique em **Reanalisar na mesma sessão**.

**Esperado:** Apto para autorização, matrícula conferida **207418**, **3,5 diárias** e
**R$ 770,00**.

A sessão nasceu sob o `user_id` **207481**, a matrícula original digitada. Esse identificador
é mantido para recuperar o histórico, e a associação fica sinalizada. Isso é diferente da
matrícula **207418**, que deve ser usada nas consultas corrigidas e na instrução final.

| Complementação | Recomendação | Diárias | Valor | Conferido |
|---|---|---:|---:|---|
| DIA-2026-0111 | Apto para autorização | 3,5 | R$ 980,00 | [ ] |
| DIA-2026-0112 | Apto para autorização | 3,5 | R$ 770,00 | [ ] |

## 9. Conferir resultados e auditoria

1. Abra **Resultados e auditoria**.
2. Examine as abas de avaliação, memória, falhas, histórico de análises e evidências.
3. Confira os rótulos que distinguem **API real** de **Simulador**.
4. Verifique se as análises de demonstração que você acabou de fazer aparecem no histórico
   do modo correspondente.
5. Confira os relatórios já gravados, incluindo as rodadas de 41/42 e 42/42 da API real.

Os resultados da bateria gravada não são uma contagem automática dos cliques que você fez
agora. A tela reúne as medições dos arquivos e, em área própria, o histórico das análises.

## 10. Testar a eliminação por último, em demonstração

Continue com **Modo demonstração ativado**. Esses passos eliminam registros do banco de
trabalho do simulador. Faça-os depois de conferir as análises e complementações.

### 10.1 Titular da matrícula corrigida, 207418

1. Abra **Memória e LGPD**.
2. Marque **Declaro que a inspeção é autorizada (pedido do titular ou auditoria)**.
3. Em **Titular**, selecione **207418 — Carla Regina Souza**.
4. Confira se a busca encontra a sessão `DIA-2026-0112` sob o outro `user_id`, **207481**.
5. Confira se o vínculo pelo pedido está indicado como verificado.

Para verificar a proteção antes de confirmar o vínculo:

6. Deixe desmarcada a caixa específica da sessão `DIA-2026-0112`.
7. Marque a confirmação geral do pedido de eliminação.
8. Clique em **Eliminar e verificar no banco**.

**Esperado nessa primeira passagem:** ainda há ocorrências sob outro identificador.
Esse resultado não é falha do teste: a sessão não deve ser apagada sem a confirmação
específica do vínculo.

Para concluir:

9. Marque a caixa da sessão `DIA-2026-0112`, com vínculo verificado.
10. Mantenha a confirmação geral e clique novamente em **Eliminar e verificar no banco**.
11. Confira a mensagem **Nada restou no banco do agente** e as ocorrências após a eliminação.

As autorizações e confirmações da página também são separadas por modo e titular. Ao
inspecionar o banco real pela primeira vez nessa sessão, ele deve exigir sua própria
autorização, sem aproveitar automaticamente a confirmação feita na demonstração.

### 10.2 Titular do pedido 0111, 206689

1. Na mesma página, selecione **206689 — Beatriz Moraes Cunha**.
2. Confira os registros encontrados.
3. Confirme o pedido de eliminação e execute a rotina.
4. Confira a mensagem **Nada restou no banco do agente**.

### O que deve permanecer

- Os registros de outros titulares podem continuar no banco; ele não precisa ficar vazio.
- As análises e conferências administrativas permanecem em banco separado.
- Resultados já carregados na sessão da tela podem continuar visíveis.
- O acervo fictício de entrada e os arquivos de medições não são apagados por essa rotina.

“Nada restou” se refere à busca por matrícula e nome do titular **no banco de trabalho
inspecionado**. Confira também o arquivo de evidência em `resultados/evidencias/`, com
nome iniciado por `eliminacao_simulador_`.

## 11. Verificar os erros simulados, sem custo de API

Este passo é opcional e pode ser feito em outro terminal, mantendo a aplicação aberta:

```powershell
.\.venv\Scripts\python.exe -m avaliacao.provocar_falhas --simulador
```

O comando grava as saídas em `resultados/simulador/falhas_provocadas.json` e usa bancos
de avaliação separados da interface. Ele pode substituir o arquivo anterior dessa simulação.

**Esperado:**

- F1 e F2: respostas manipuladas ou sem fontes suficientes são recusadas no simulador.
- F3a: erro de execução da API simulada.
- F3b: resposta truncada recusada.
- F4a e F4b: complementação recusada quando o histórico não é recuperado.
- F4c: pode continuar aprovado com a resposta correta, embora a configuração tenha misturado
  pedidos. Essa limitação deve continuar registrada.

Mensagens `ERROR` e `WARNING` sobre a API simulada ou o JSON truncado são esperadas nesse
comando: esses cenários provocam as falhas de propósito. “Detectada ou inofensiva” não
significa que o sistema identificou a causa de todos os problemas.

## 12. Conferir a API real, se quiser repetir essa validação

As medições reais já estão gravadas. Repetir uma análise real usa créditos da API.

Para iniciar uma rodada real com uma sessão nova no navegador:

1. Feche a aba do aplicativo.
2. No terminal do Streamlit, pressione **Ctrl+C**.
3. Confirme somente a presença da chave, sem imprimir seu valor:

   ```powershell
   .\.venv\Scripts\python.exe -c "import config; print('Chave configurada:', config.chave_configurada())"
   ```

4. **Esperado:** `Chave configurada: True`. Isso confirma a presença, não a validade nem
   o acesso ao modelo; uma análise real verifica a comunicação.
5. Inicie novamente o Streamlit com o comando da seção 4 e abra o endereço informado.
6. Deixe **Modo demonstração desligado**.
7. Comece pelo pedido `DIA-2026-0103` e confira 0,5 diária e R$ 140,00.
8. Se desejar uma conferência mais ampla, repita 0104, 0106, 0107 e os dois ciclos de
   diligência/complementação, antes dos testes de eliminação.

Na API real, a redação, o tempo e o número de chamadas podem variar. Uma recusa deve mostrar:

```text
Não foi possível produzir uma instrução verificada para este pedido. O pedido foi devolvido à análise manual da Coordenadoria de Diárias e Passagens.
```

O conteúdo recusado não deve aparecer como instrução válida. Os motivos técnicos ficam
na auditoria. Registre o caso e o motivo; uma recusa segura é diferente de exibir um valor
ou uma matrícula incorretos.

Se você executar novamente as baterias completas de avaliação, preserve os resultados
anteriores antes de sobrescrevê-los e atualize o relatório. Os comandos estão no README.
Não é necessário repetir todas as baterias para fazer este roteiro de tela.

## 13. Resolver problemas comuns

| Situação | O que fazer |
|---|---|
| `python` abre a Microsoft Store ou falha | Use os comandos deste guia, com `.\.venv\Scripts\python.exe` |
| Erro de `Activate.ps1` | Use o Python da `.venv` diretamente, sem ativação |
| A porta 8501 está ocupada | Encerre a instância anterior ou execute com `--server.port 8502` e abra `http://localhost:8502` |
| O terminal fica ocupado após abrir o app | É o servidor em execução; mantenha-o aberto durante o teste |
| Complementação sem sessão | Analise primeiro o pedido original no mesmo modo e na mesma sessão do navegador |
| Chave preenchida, mas a API falha | Confira modo, acesso ao modelo e mensagens de auditoria; após editar o `.env`, reinicie o servidor |
| Uma análise simulada aparece como análise da API | Reinicie para carregar a versão atual e repita a seção 5.1; se persistir, registre a falha antes de entregar |
| Eliminação do 0112 informa resíduos | Confira a sessão sob 207481 e a confirmação específica do vínculo com 207418 |
| Quantidade, valor ou matrícula divergentes | Registre o pedido e interrompa a conferência para investigar; não trate a instrução incorreta como válida |

## 14. Checklist de decisão antes da entrega

### Verificações necessárias

- [ ] Python da `.venv` funciona e `pip check` não apresenta conflitos.
- [ ] Todos os testes automatizados, incluindo as regressões da auditoria final, passam.
- [ ] As seis páginas abrem sem exceção do aplicativo.
- [ ] Resultados, minutas e confirmações de eliminação não se misturam entre demonstração e API.
- [ ] Os doze pedidos e as duas complementações conferem no simulador.
- [ ] O 0104 apresenta os dados pessoais mascarados.
- [ ] O 0106 e o 0107 recebem tratamentos diferentes.
- [ ] Divergir da recomendação exige justificativa.
- [ ] A edição da minuta é preservada no registro e no arquivo baixado.
- [ ] As complementações são aplicadas ao pedido certo.
- [ ] A eliminação dos dois titulares é verificada no banco do simulador.
- [ ] O registro administrativo da conferência permanece após a eliminação.
- [ ] API real e simulador estão identificados separadamente nos resultados.
- [ ] README, LEIA-ME, desenho, relatório e rastreabilidade estão acessíveis.
- [ ] O README identifica Diego Assunção Leite como único autor.
- [ ] O ZIP de entrega não contém `.env`, `.venv` nem bancos locais.
- [ ] As limitações e a recusa segura da bateria real estão declaradas no relatório.

### Quando considerar pronto para a entrega do exercício

Considere a entrega preparada quando essas verificações forem concluídas e as observações
estiverem registradas. Uma recusa segura na API pode ser apresentada como resultado do
experimento, com sua causa e o encaminhamento manual documentados.

Se houver teste automatizado com falha, tela quebrada, dado pessoal exposto, consulta de
outra matrícula, valor incorreto entregue ou perda da conferência administrativa, revise
antes de entregar. Não transforme esses problemas em uma declaração de “100% aprovado”.

## 15. Registro do seu teste manual

Preencha esta seção ou copie-a para um arquivo pessoal de anotações. As evidências anteriores
não substituem o registro do que você efetivamente observou agora.

```text
Responsável: Diego Assunção Leite
Data e hora do teste:
Python e ambiente utilizados:

Testes automatizados: ____ aprovados / ____ falhas
Pedidos originais no simulador: ____ / 12 conferidos
Complementações no simulador: ____ / 2 conferidas
Conferência divergente sem justificativa foi recusada? Sim / Não
Conferência válida e minuta editada foram preservadas? Sim / Não
Eliminação de 206689 sem resíduos? Sim / Não
Eliminação de 207418 com vínculo confirmado sem resíduos? Sim / Não
Registro administrativo preservado? Sim / Não

API real foi testada nesta conferência? Sim / Não
Pedidos testados na API:
Recusas e motivos observados:
Alguma instrução incorreta foi entregue? Sim / Não

Problemas encontrados:
Correções ou observações:

Parecer: pronto para entrega com ressalvas declaradas / revisar antes de entregar
```

Para visualizar este Markdown no VS Code, abra o arquivo e use **Ctrl+Shift+V**.
