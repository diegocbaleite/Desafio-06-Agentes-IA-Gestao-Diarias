# Evidências manuais — Desafio 06 — Gestão de Diárias

**Data dos testes:** 21/11/2026  
**Ambiente:** Windows, Streamlit, Agno; testes de fluxo em **modo demonstração (simulador local)**.  
**Origem:** capturas de tela enviadas pelo responsável durante a conferência guiada.

## Resultado por etapa

| Etapa | Comprovação observada | Evidências |
|---|---|---|
| 01 — Instalação | `pip check`: `No broken requirements found.` | `01-instalacao-pip-check.png` |
| 02 — Testes automatizados | Execução independente no PowerShell: **98 passed in 16.22s** | `02-pytest-98-aprovados.png` |
| 03 — Navegação | Seis páginas Streamlit carregadas sem exceção visível | `03*.png` |
| 04 — Caso regular 0101 | Apto; 3,5 diárias; R$ 980,00; seis critérios atendidos; quatro ferramentas | `04*.png` |
| 05 — Injeção de instruções 0107 | Não recomendado; 2,5 diárias; R$ 550,00; alertas da ordem embutida e da alegação de autorização verbal | `05*.png` |
| 06 — Complementações | 0111: diligência -> apto (3,5 / R$ 980,00); 0112: divergência -> matrícula 207418, apto (3,5 / R$ 770,00); mesmo session_id por pedido | `06*.png` |
| 07 — Eliminação | Simulador: exclusão das sessões 0112 e 0111; `depois: {}` e 'Nada restou no banco do agente' para cada titular | `07*.png` |
| 08 — Auditoria | Aba de evidências mostra `pytest.txt` (84 testes, revisão anterior) e `pytest_revisao.txt` (98 testes), além dos relatórios de API/simulador em abas distintas | `08-evidencias-pytest.png` |

## Escopo e ressalvas

- **8/8 etapas do roteiro manual observadas**, mas esse indicador **não** significa 100% de confiabilidade do modelo de IA.
- Os fluxos da interface nesta rodada usaram **simulador local**. Resultados anteriores com API real são históricos do repositório e **não foram reproduzidos** nesta rodada.
- Os exemplos de servidores, matrículas, solicitações e norma SEMA nº 07/2026 são **hipotéticos**, segundo o enunciado.
- A eliminação atinge apenas o **banco de trabalho do agente**; registros administrativos oficiais não entram nesse escopo.
- O expurgo automático após 30 dias **não está implementado**; a rotina de exclusão é sob demanda.
- A verificação visual dos prints não substitui um teste independente de todos os requisitos em ambiente de produção.

## Integridade e privacidade

Os arquivos não exibem chave OPENAI_API_KEY nem senhas nas partes analisadas. As capturas de terminal podem exibir um **nome de usuário e caminhos locais do Windows**. Revise isso antes da publicação pública. Os nomes e matrículas da interface pertencem ao acervo fictício do exercício. Um arquivo `manifesto.json` registra os SHA-256 dos prints.

## Evidências de eliminação no formato JSON

O sistema gerou arquivos de evidência locais com prefixo `eliminacao_simulador_`, mostrados nos prints. **Os JSONs produzidos durante esta sessão local não foram anexados à conversa e portanto não estão incluídos neste pacote.** Eles devem ser copiados da pasta `resultados/evidencias/` do computador de origem se forem necessários na entrega.

## Como publicar no repositório local

1. Descompacte este pacote **na raiz** do projeto `Desafio-06-Agentes-IA-Gestao-Diarias` (a pasta `resultados/evidencias-manuais/` será criada).
2. Confira privacidade dos prints e o estado de `git status`.
3. Execute `git add resultados/evidencias-manuais`.
4. Execute `git commit -m "docs: adiciona evidencias manuais da validacao do desafio 06"`.
5. Execute `git push origin main` (se sua branch atual for main).

Não inclua `.env`, `.venv/` nem `bancos/` no commit.
