"""Rotina de eliminação verificável dos dados de um titular no banco de trabalho do agente.

Alcance: SOMENTE o banco do agente (`agno_sessions`, `agno_runs`, `agno_memories` e demais
tabelas do SqliteDb), que é cópia de trabalho. O processo de diárias, as conferências e o
registro de análises são registro de despesa pública, sujeitos à transparência e à guarda
das normas de prestação de contas (LGPD, art. 16, I e art. 7º, II); não são apagados aqui.

Etapas (Aula 07, Seção 6.2), sempre todas, mesmo que pareça não haver nada:
1. Validar matrícula e nome no cadastro e verificar o vínculo dos pedidos, inclusive
   nas sessões e memórias gravadas sob o user_id informado. Sem vínculo, preservar.
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
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from agno.db.base import SessionType
from agno.db.sqlite import SqliteDb

from ferramentas import acervo
from memoria import verificacao
from seguranca.filtro_pii import mascarar_texto


@dataclass
class Localizacao:
    matricula: str
    nome: str
    sessoes_do_titular: list[str] = field(default_factory=list)
    sessoes_sob_outro_user_id: list[dict] = field(default_factory=list)
    memorias_do_titular: list[dict] = field(default_factory=list)
    memorias_sob_outro_user_id: list[dict] = field(default_factory=list)
    sessoes_sem_vinculo: list[dict] = field(default_factory=list)
    memorias_sem_vinculo: list[dict] = field(default_factory=list)
    ocorrencias: dict = field(default_factory=dict)


def titulares_cadastrados() -> dict[str, str]:
    """Identidades canônicas para a inspeção; não usa matrículas digitadas nos pedidos."""
    return {mat: s["nome"] for mat, s in acervo.servidores().items()}


def _validar_titular(matricula: str, nome: str) -> None:
    esperado = titulares_cadastrados().get(matricula)
    if esperado is None or acervo.normalizar_nome(esperado) != acervo.normalizar_nome(nome):
        raise ValueError("Matrícula e nome do titular devem corresponder ao cadastro funcional. "
                         "Nenhum registro foi eliminado.")


def _vinculo_por_pedido(session_id: str, matricula: str, nome: str) -> bool:
    """Exige pedido do titular e matrícula protocolada ou corrigida no acervo."""
    for p in acervo.pedidos():
        if p["numero"] == session_id:
            if acervo.normalizar_nome(p["nome"]) != acervo.normalizar_nome(nome):
                return False
            corrigidas = {m for c in acervo.complementacoes() if c["numero"] == session_id
                          for m in re.findall(r"(?<!\d)\d{6}(?!\d)", c.get("texto", ""))}
            return matricula == p["matricula"] or matricula in corrigidas
    return False


def _vinculo_memoria(memoria, matricula: str, nome: str) -> bool:
    """Memória de outro user_id não é própria só porque cita o nome; exige origem verificada."""
    dados = memoria.to_dict() if hasattr(memoria, "to_dict") else vars(memoria)
    pedidos = set(re.findall(r"DIA-\d{4}-\d{4}", json.dumps(dados, ensure_ascii=False)))
    return bool(pedidos) and all(_vinculo_por_pedido(p, matricula, nome) for p in pedidos)


def _memorias(db: SqliteDb, user_id: str | None = None) -> list:
    try:
        return list(db.get_user_memories(user_id=user_id) or [])
    except Exception:
        return []


def _resumo_memoria(m) -> dict:
    texto = str(getattr(m, "memory", "") or "")
    return {"memory_id": getattr(m, "memory_id", None) or getattr(m, "id", None),
            "user_id": getattr(m, "user_id", None), "trecho": mascarar_texto(texto)[0][:80]}


def localizar(db_file: Path | str, matricula: str, nome: str) -> Localizacao:
    """Etapas 1, 2 e 4 (somente leitura): o que o banco guarda sobre o titular."""
    _validar_titular(matricula, nome)
    loc = Localizacao(matricula=matricula, nome=nome)
    if not Path(db_file).exists():
        return loc
    db = SqliteDb(db_file=str(db_file))
    try:
        proprias = db.get_sessions(session_type=SessionType.AGENT, user_id=matricula) or []
    except Exception:
        proprias = []
    loc.sessoes_do_titular = sorted(s.session_id for s in proprias
                                   if _vinculo_por_pedido(s.session_id, matricula, nome))
    loc.sessoes_sem_vinculo = [
        {"session_id": s.session_id, "user_ids": [matricula], "vinculo_verificado": False}
        for s in proprias if s.session_id not in loc.sessoes_do_titular]
    sem_vinculo = {s["session_id"] for s in loc.sessoes_sem_vinculo}
    for s in verificacao.sessoes_que_citam(db_file, [matricula, nome]):
        if s["session_id"] in loc.sessoes_do_titular or s["session_id"] in sem_vinculo:
            continue
        loc.sessoes_sob_outro_user_id.append({
            **s, "vinculo_verificado": _vinculo_por_pedido(s["session_id"], matricula, nome),
            "observacao": "Sessão cita o titular, mas foi gravada sob outro user_id; "
                          "exige verificação de vínculo e confirmação antes da exclusão."})
    proprias_memorias = _memorias(db, matricula)
    loc.memorias_do_titular = [_resumo_memoria(m) for m in proprias_memorias
                              if _vinculo_memoria(m, matricula, nome)]
    loc.memorias_sem_vinculo = [_resumo_memoria(m) for m in proprias_memorias
                               if not _vinculo_memoria(m, matricula, nome)]
    ids_proprias = {m["memory_id"] for m in loc.memorias_do_titular}
    ids_proprias |= {m["memory_id"] for m in loc.memorias_sem_vinculo}
    for m in _memorias(db):
        # O registro inteiro, e não só o texto da memória: a coluna `input` guarda a mensagem
        # de origem, que pode citar o titular mesmo quando o fato extraído não o cita.
        texto = str(m.to_dict() if hasattr(m, "to_dict") else vars(m))
        if getattr(m, "memory_id", None) not in ids_proprias and \
                any(v in texto for t in (matricula, nome) for v in (t, json.dumps(t)[1:-1])):
            loc.memorias_sob_outro_user_id.append({
                **_resumo_memoria(m), "vinculo_verificado": _vinculo_memoria(m, matricula, nome)})
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
    nao_apagadas: list[dict] = [
        {**{k: v for k, v in r.items() if k != "trecho"},
         "motivo": "vínculo com o titular não verificado"}
        for r in antes.sessoes_sem_vinculo + antes.memorias_sem_vinculo]
    sessoes_autorizadas = set(antes.sessoes_do_titular) | {
        s["session_id"] for s in antes.sessoes_sob_outro_user_id
        if s["session_id"] in sessoes_confirmadas and s["vinculo_verificado"]}

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
                  if m["memory_id"] in memorias_confirmadas and m["vinculo_verificado"]]
        if outros:
            db.delete_user_memories(memory_ids=outros)
            acoes.append(f"delete_user_memories({len(outros)} id(s) sob outro user_id, confirmadas)")
        for m in antes.memorias_sob_outro_user_id:
            if m["memory_id"] not in outros:
                nao_apagadas.append({"memory_id": m["memory_id"], "user_id": m["user_id"],
                                     "motivo": "sem confirmação" if m["vinculo_verificado"]
                                     else "vínculo com o titular não verificado"})

    # Etapa 5: inspeção direta, tabela por tabela.
    depois = verificacao.ocorrencias(db_file, [matricula, nome])
    sessoes_depois = {s["session_id"]: s["user_id"] for s in verificacao.sessoes(db_file)}
    apagadas = set(sessoes_outros_antes) - set(sessoes_depois)
    alheias_apagadas = sorted(apagadas - sessoes_autorizadas)
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
                  "memorias_sob_outro_user_id": len(antes.memorias_sob_outro_user_id),
                  "sessoes_sem_vinculo": antes.sessoes_sem_vinculo,
                  "memorias_sem_vinculo": len(antes.memorias_sem_vinculo)},
        "acoes": acoes,
        "nao_apagadas": nao_apagadas,
        "depois": {"registros_por_tabela": verificacao.contar_registros(db_file),
                   "ocorrencias": _sem_nome(depois, nome)},
        "sessoes_de_outros_preservadas": sorted(set(sessoes_depois)),
        "sessoes_alheias_apagadas_indevidamente": alheias_apagadas,
        "nada_restou": not depois and not nao_apagadas and not alheias_apagadas,
        "alcance": "Banco de trabalho do agente. Processo de diárias, registro de análises e "
                   "conferências são registro administrativo oficial e não são eliminados por esta rotina.",
    }


def _sem_nome(ocorr: dict, nome: str) -> dict:
    """Evidência sem o nome do titular: substitui a chave pelo rótulo 'nome'."""
    return {t: {("nome" if k == nome else "matricula"): n for k, n in v.items()} for t, v in ocorr.items()}


def evidencia_como_dict(loc: Localizacao) -> dict:
    return asdict(loc)
