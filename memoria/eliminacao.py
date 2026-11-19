"""Rotina de eliminação verificável dos dados de um titular no banco de trabalho do agente.

Alcance: SOMENTE o banco do agente (`agno_sessions`, `agno_runs`, `agno_memories` e demais
tabelas do SqliteDb), que é cópia de trabalho. O processo de diárias, as conferências e o
registro de análises são registro de despesa pública, sujeitos à transparência e à guarda
das normas de prestação de contas (LGPD, art. 16, I e art. 7º, II); não são apagados aqui.

Etapas (Aula 07, Seção 6.2), sempre todas, mesmo que pareça não haver nada:
1. Localizar as sessões gravadas sob o user_id do titular.
2. Localizar, por conteúdo, sessões que citam a matrícula ou o nome do titular mas foram
   gravadas sob OUTRO user_id (caso DIA-2026-0112: matrícula digitada de outro servidor).
   Essas só são apagadas com vínculo verificado (o pedido da sessão foi protocolado em nome
   do titular) E confirmação expressa de quem executa a rotina.
3. Apagar as sessões (o SqliteDb remove junto as execuções).
4. Listar as memórias do titular e apagá-las com delete_user_memories(memory_ids=...).
   Memórias sob outro user_id que citem o titular também exigem confirmação.
5. Inspecionar todas as tabelas, procurando matrícula e nome; registrar a evidência.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from agno.db.base import SessionType
from agno.db.sqlite import SqliteDb

from ferramentas import acervo
from memoria import verificacao


@dataclass
class Localizacao:
    matricula: str
    nome: str
    sessoes_do_titular: list[str] = field(default_factory=list)
    sessoes_sob_outro_user_id: list[dict] = field(default_factory=list)
    memorias_do_titular: list[dict] = field(default_factory=list)
    memorias_sob_outro_user_id: list[dict] = field(default_factory=list)
    ocorrencias: dict = field(default_factory=dict)


def _vinculo_por_pedido(session_id: str, nome: str) -> bool:
    """A sessão tem session_id = número de um pedido protocolado em nome do titular?"""
    for p in acervo.pedidos():
        if p["numero"] == session_id:
            return acervo.normalizar_nome(p["nome"]) == acervo.normalizar_nome(nome)
    return False


def _memorias(db: SqliteDb, user_id: str | None = None) -> list:
    try:
        return list(db.get_user_memories(user_id=user_id) or [])
    except Exception:
        return []


def _resumo_memoria(m) -> dict:
    texto = str(getattr(m, "memory", "") or "")
    return {"memory_id": getattr(m, "memory_id", None) or getattr(m, "id", None),
            "user_id": getattr(m, "user_id", None), "trecho": texto[:80]}


def localizar(db_file: Path | str, matricula: str, nome: str) -> Localizacao:
    """Etapas 1, 2 e 4 (somente leitura): o que o banco guarda sobre o titular."""
    loc = Localizacao(matricula=matricula, nome=nome)
    if not Path(db_file).exists():
        return loc
    db = SqliteDb(db_file=str(db_file))
    try:
        proprias = db.get_sessions(session_type=SessionType.AGENT, user_id=matricula) or []
    except Exception:
        proprias = []
    loc.sessoes_do_titular = sorted(s.session_id for s in proprias)
    for s in verificacao.sessoes_que_citam(db_file, [matricula, nome]):
        if s["session_id"] in loc.sessoes_do_titular:
            continue
        loc.sessoes_sob_outro_user_id.append({
            **s, "vinculo_verificado": _vinculo_por_pedido(s["session_id"], nome),
            "observacao": "Sessão cita o titular, mas foi gravada sob outro user_id; "
                          "exige verificação de vínculo e confirmação antes da exclusão."})
    loc.memorias_do_titular = [_resumo_memoria(m) for m in _memorias(db, matricula)]
    ids_proprias = {m["memory_id"] for m in loc.memorias_do_titular}
    for m in _memorias(db):
        # O registro inteiro, e não só o texto da memória: a coluna `input` guarda a mensagem
        # de origem, que pode citar o titular mesmo quando o fato extraído não o cita.
        texto = str(m.to_dict() if hasattr(m, "to_dict") else vars(m))
        if getattr(m, "memory_id", None) not in ids_proprias and \
                any(v in texto for t in (matricula, nome) for v in (t, json.dumps(t)[1:-1])):
            loc.memorias_sob_outro_user_id.append(_resumo_memoria(m))
    loc.ocorrencias = verificacao.ocorrencias(db_file, [matricula, nome])
    return loc


def eliminar(db_file: Path | str, matricula: str, nome: str,
             sessoes_confirmadas: list[str] | None = None,
             memorias_confirmadas: list[str] | None = None,
             executado_por: str = "rotina") -> dict:
    """Executa a eliminação e devolve a evidência (antes, ações, depois, conclusão).

    sessoes_confirmadas / memorias_confirmadas: identificadores sob OUTRO user_id que quem
    executa a rotina confirmou pertencerem ao titular. Uma sessão sem vínculo verificado
    NÃO é apagada, mesmo confirmada: protege dados de outro titular.
    """
    sessoes_confirmadas = set(sessoes_confirmadas or [])
    memorias_confirmadas = set(memorias_confirmadas or [])
    antes = localizar(db_file, matricula, nome)
    registros_antes = verificacao.contar_registros(db_file)
    sessoes_outros_antes = {s["session_id"]: s["user_id"] for s in verificacao.sessoes(db_file)}
    acoes: list[str] = []
    nao_apagadas: list[dict] = []

    if Path(db_file).exists():
        db = SqliteDb(db_file=str(db_file))
        # Etapa 3a: sessões do próprio titular (as execuções vão junto).
        if antes.sessoes_do_titular:
            db.delete_sessions(session_ids=antes.sessoes_do_titular, user_id=matricula)
            acoes.append(f"delete_sessions({antes.sessoes_do_titular}, user_id={matricula})")
        # Etapa 3b: sessões sob outro user_id, só com vínculo verificado e confirmação.
        for s in antes.sessoes_sob_outro_user_id:
            sid = s["session_id"]
            if sid in sessoes_confirmadas and s["vinculo_verificado"]:
                db.delete_sessions(session_ids=[sid])
                acoes.append(f"delete_sessions([{sid}]) — gravada sob user_id {s['user_ids']}, "
                             f"vínculo verificado pelo pedido e confirmado por {executado_por}")
            else:
                motivo = ("sem confirmação" if sid not in sessoes_confirmadas
                          else "vínculo com o titular não verificado")
                nao_apagadas.append({"session_id": sid, "user_ids": s["user_ids"], "motivo": motivo})
        # Etapa 4: memórias do titular, listadas e apagadas por identificador.
        ids = [m["memory_id"] for m in antes.memorias_do_titular if m["memory_id"]]
        if ids:
            db.delete_user_memories(memory_ids=ids, user_id=matricula)
            acoes.append(f"delete_user_memories({len(ids)} id(s), user_id={matricula})")
        outros = [m["memory_id"] for m in antes.memorias_sob_outro_user_id
                  if m["memory_id"] in memorias_confirmadas]
        if outros:
            db.delete_user_memories(memory_ids=outros)
            acoes.append(f"delete_user_memories({len(outros)} id(s) sob outro user_id, confirmadas)")
        for m in antes.memorias_sob_outro_user_id:
            if m["memory_id"] not in memorias_confirmadas:
                nao_apagadas.append({"memory_id": m["memory_id"], "user_id": m["user_id"],
                                     "motivo": "sem confirmação"})

    # Etapa 5: inspeção direta, tabela por tabela.
    depois = verificacao.ocorrencias(db_file, [matricula, nome])
    sessoes_depois = {s["session_id"]: s["user_id"] for s in verificacao.sessoes(db_file)}
    apagadas = set(sessoes_outros_antes) - set(sessoes_depois)
    alheias_apagadas = [sid for sid in apagadas
                        if sid not in antes.sessoes_do_titular and sid not in sessoes_confirmadas]
    return {
        "titular": {"matricula": matricula},  # o nome não é repetido na evidência
        "executado_por": executado_por,
        "executado_em": datetime.now().isoformat(timespec="seconds"),
        "banco": Path(db_file).name,
        "antes": {"registros_por_tabela": registros_antes, "ocorrencias": _sem_nome(antes.ocorrencias, nome),
                  "sessoes_do_titular": antes.sessoes_do_titular,
                  "sessoes_sob_outro_user_id": [{k: v for k, v in s.items() if k != "termos"}
                                                for s in antes.sessoes_sob_outro_user_id],
                  "memorias_do_titular": len(antes.memorias_do_titular),
                  "memorias_sob_outro_user_id": len(antes.memorias_sob_outro_user_id)},
        "acoes": acoes,
        "nao_apagadas": nao_apagadas,
        "depois": {"registros_por_tabela": verificacao.contar_registros(db_file),
                   "ocorrencias": _sem_nome(depois, nome)},
        "sessoes_de_outros_preservadas": sorted(set(sessoes_depois)),
        "sessoes_alheias_apagadas_indevidamente": alheias_apagadas,
        "nada_restou": not depois,
        "alcance": "Banco de trabalho do agente. Processo de diárias, registro de análises e "
                   "conferências são registro administrativo oficial e não são eliminados por esta rotina.",
    }


def _sem_nome(ocorr: dict, nome: str) -> dict:
    """Evidência sem o nome do titular: substitui a chave pelo rótulo 'nome'."""
    return {t: {("nome" if k == nome else "matricula"): n for k, n in v.items()} for t, v in ocorr.items()}


def evidencia_como_dict(loc: Localizacao) -> dict:
    return asdict(loc)
