"""O agente Agno de instrução de pedidos de diárias e a função `instruir`, fronteira com a tela.

A aplicação não conversa com o Agno: chama `instruir(pedido, ...)` e recebe um
`ResultadoInstrucao`, que já passou pela barreira. Um único agente pode ficar em cache,
porque `session_id` (número do pedido) e `user_id` (matrícula do solicitante) são
informados em cada chamada a `run`, e não na construção (Aula 07, Seção 5.1).
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Literal, Optional

from agno.agent import Agent
from agno.db.base import SessionType
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIChat
from agno.run.base import RunStatus

import config
from agente.instrucoes import instrucao_sistema, mensagem_complementacao, mensagem_pedido
from agente.modelos import Instrucao
from ferramentas import FERRAMENTAS
from seguranca import filtro_pii
from seguranca.barreiras import ResultadoBarreira, agora_iso, verificar_instrucao

Memoria = Literal["sem_memoria", "historico", "historico_usuario"]

# Funções de progresso por sessão: permitem à tela anunciar cada ferramenta no momento em
# que ela começa, sem acoplar o agente em cache a uma tela específica.
_AO_CHAMAR: dict[str, Callable[[str, dict], None]] = {}


def _anunciar_ferramenta(function_name: str, function_call: Callable, arguments: dict, run_context=None):
    """tool_hook do Agno: avisa a tela e executa a ferramenta sem alterar argumentos."""
    sessao = getattr(run_context, "session_id", None)
    aviso = _AO_CHAMAR.get(sessao)
    if aviso:
        try:
            aviso(function_name, dict(arguments))
        except Exception:  # a tela nunca pode derrubar a instrução
            pass
    return function_call(**arguments)


def construir_agente(memoria: Memoria = "historico", paralelas: bool | None = None,
                     db_file: Path | str | None = None, modelo: str | None = None,
                     num_history_runs: int | None = None,
                     tool_call_limit: int | None = None, base_url: str | None = None,
                     api_key: str | None = None) -> Agent:
    """Monta o agente com ferramentas, contrato, limites, filtro de dados pessoais e memória.

    memoria:
        "sem_memoria"        — sem banco; cada chamada começa do zero.
        "historico"          — SqliteDb + add_history_to_context + num_history_runs (padrão).
        "historico_usuario"  — o anterior + update_memory_on_run (memórias do usuário).
    paralelas: liga as chamadas paralelas de ferramentas (padrão do config: desligadas).
    base_url/api_key: usados apenas pelos testes com o simulador local.
    """
    paralelas = config.PARALLEL_TOOL_CALLS if paralelas is None else paralelas
    modelo_llm = OpenAIChat(
        id=modelo or config.MODELO,
        reasoning_effort="none",  # exigido pela família GPT-5.6 com ferramentas (Aula 06, 4.1)
        request_params={"parallel_tool_calls": paralelas},
        base_url=base_url or config.BASE_URL,
        api_key=api_key,  # None => o SDK lê OPENAI_API_KEY do ambiente (.env)
        max_retries=1,
    )
    extras: dict = {}
    if memoria != "sem_memoria":
        arquivo = Path(db_file or config.DB_AGENTE)
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        extras = {"db": SqliteDb(db_file=str(arquivo)), "add_history_to_context": True,
                  "num_history_runs": num_history_runs or config.NUM_HISTORY_RUNS}
        if memoria == "historico_usuario":
            extras["update_memory_on_run"] = True
    return Agent(
        name="instrutor_diarias",
        model=modelo_llm,
        tools=list(FERRAMENTAS),
        tool_hooks=[_anunciar_ferramenta],
        instructions=instrucao_sistema(),
        output_schema=Instrucao,
        markdown=False,
        tool_call_limit=tool_call_limit or config.TOOL_CALL_LIMIT,
        pre_hooks=[filtro_pii.criar_guardrail()],
        telemetry=False,
        debug_mode=False,
        **extras,
    )


@dataclass
class ResultadoInstrucao:
    """O que a tela, o registro e o avaliador recebem. Só `instrucao` vem do modelo."""

    numero: str
    turno: Literal["pedido", "complementacao"]
    situacao: Literal["aprovada", "recusada", "erro_execucao"]
    session_id: str
    user_id: str
    modelo: str
    inicio: str
    instrucao: Optional[dict] = None          # preenchido SOMENTE se aprovada pela barreira
    mensagem: str = ""
    motivos_recusa: list[str] = field(default_factory=list)   # para auditoria, não para a tela
    alertas_aplicacao: list[str] = field(default_factory=list)
    consultas: list[dict] = field(default_factory=list)
    metricas: dict = field(default_factory=dict)

    @property
    def aprovada(self) -> bool:
        return self.situacao == "aprovada"

    def to_dict(self) -> dict:
        return asdict(self)


def user_id_da_sessao(agente: Agent, session_id: str, padrao: str) -> str:
    """Devolve o user_id sob o qual a sessão já foi gravada; senão, o padrão.

    No DIA-2026-0112 a sessão nasce sob a matrícula digitada (de outro servidor). A
    complementação continua sob o MESMO user_id, para que o histórico seja recuperado; a
    associação equivocada fica registrada em alerta e é tratada pela rotina de eliminação.
    """
    if getattr(agente, "db", None) is None:
        return padrao
    try:
        sessao = agente.db.get_session(session_id=session_id, session_type=SessionType.AGENT)
    except Exception:
        return padrao
    return getattr(sessao, "user_id", None) or padrao


def _consultas(resposta) -> list[dict]:
    consultas = []
    for t in (getattr(resposta, "tools", None) or []):
        consultas.append({"ferramenta": t.tool_name, "argumentos": dict(t.tool_args or {}),
                          "resultado": t.result if isinstance(t.result, str) else str(t.result),
                          "erro": bool(t.tool_call_error)})
    return consultas


def _metricas(resposta, segundos: float) -> dict:
    m = getattr(resposta, "metrics", None)
    entrada = int(getattr(m, "input_tokens", 0) or 0)
    saida = int(getattr(m, "output_tokens", 0) or 0)
    # Mensagens reenviadas do histórico (from_history) pertencem a execuções anteriores.
    chamadas = [msg for msg in (getattr(resposta, "messages", None) or [])
                if msg.role == "assistant" and getattr(msg, "metrics", None)
                and not getattr(msg, "from_history", False)]
    por_chamada = [int(msg.metrics.input_tokens or 0) for msg in chamadas]
    simultaneas = [len(msg.tool_calls or []) for msg in chamadas]
    return {"tokens_entrada": entrada, "tokens_saida": saida,
            "entrada_por_chamada": por_chamada, "chamadas_modelo": len(chamadas),
            "ferramentas_por_chamada": simultaneas,
            "max_ferramentas_simultaneas": max(simultaneas, default=0),
            "chamadas_ferramenta": len(getattr(resposta, "tools", None) or []),
            "segundos": round(segundos, 2), "custo_usd": round(config.custo_usd(entrada, saida), 6)}


def instruir(agente: Agent, pedido: dict, complementacao: dict | None = None,
             ao_chamar_ferramenta: Callable[[str, dict], None] | None = None,
             user_id: str | None = None, session_id: str | None = None) -> ResultadoInstrucao:
    """Instrui um pedido (ou sua complementação) e devolve o resultado já verificado.

    1. Mascara dados pessoais do texto livre ANTES do modelo e do banco.
    2. Executa o agente com session_id = número do pedido e user_id = matrícula do solicitante.
    3. Confere resposta.status antes de ler o conteúdo.
    4. Passa a instrução pela barreira; se recusada, nada do conteúdo segue à tela.

    user_id e session_id só são informados pelos experimentos de falha (identificador
    derivado de forma errada); a aplicação usa sempre os padrões.
    """
    numero = pedido["numero"]
    sid = session_id or numero
    if complementacao is None:
        texto, mascarados = filtro_pii.mascarar_texto(pedido.get("justificativa", ""))
        entrada = mensagem_pedido(pedido, texto, mascarados)
        turno = "pedido"
    else:
        texto, mascarados = filtro_pii.mascarar_texto(complementacao.get("texto", ""))
        entrada = mensagem_complementacao(numero, complementacao.get("data", ""), texto)
        turno = "complementacao"
    uid = user_id or user_id_da_sessao(agente, sid, pedido["matricula"])

    alertas_app = []
    if mascarados:
        alertas_app.append(f"Dado pessoal mascarado pela aplicação antes do envio ao modelo: "
                           f"{', '.join(mascarados)}.")
    if complementacao is not None and uid != pedido["matricula"]:
        alertas_app.append(f"Sessão gravada sob user_id {uid}, diferente da matrícula do pedido.")

    resultado = ResultadoInstrucao(numero=numero, turno=turno, situacao="erro_execucao",
                                   session_id=sid, user_id=uid, modelo=agente.model.id,
                                   inicio=agora_iso(), alertas_aplicacao=alertas_app)
    if ao_chamar_ferramenta:
        _AO_CHAMAR[sid] = ao_chamar_ferramenta
    inicio = time.perf_counter()
    try:
        resposta = agente.run(entrada, session_id=sid, user_id=uid)
    except Exception as erro:  # rede, configuração, validação: nunca chega como instrução
        resultado.mensagem = config.MENSAGEM_PADRAO
        resultado.motivos_recusa = [f"Exceção na execução: {type(erro).__name__}."]
        resultado.metricas = {"segundos": round(time.perf_counter() - inicio, 2)}
        return resultado
    finally:
        _AO_CHAMAR.pop(sid, None)

    resultado.metricas = _metricas(resposta, time.perf_counter() - inicio)
    resultado.consultas = _consultas(resposta)
    status = getattr(resposta, "status", None)
    if status != RunStatus.completed:
        # O conteúdo de uma execução com erro é a mensagem da API: não é lido nem exibido.
        resultado.mensagem = config.MENSAGEM_PADRAO
        resultado.motivos_recusa = [f"resposta.status = {getattr(status, 'value', status)}."]
        return resultado

    conteudo = resposta.content
    if isinstance(conteudo, dict):
        try:
            conteudo = Instrucao.model_validate(conteudo)
        except Exception:
            conteudo = None
    barreira: ResultadoBarreira = verificar_instrucao(pedido, complementacao, conteudo,
                                                      resultado.consultas, "COMPLETED")
    resultado.alertas_aplicacao += barreira.alertas_codigo
    if not barreira.aprovada:
        resultado.situacao = "recusada"
        resultado.mensagem = config.MENSAGEM_PADRAO
        resultado.motivos_recusa = barreira.motivos
        return resultado
    resultado.situacao = "aprovada"
    resultado.instrucao = conteudo.model_dump()
    return resultado
