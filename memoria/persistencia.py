"""Persistência do agente (SqliteDb do Agno) e registro administrativo das análises e conferências.

Dois bancos, com finalidades e regras de retenção diferentes:

- `bancos/agente_diarias.db` — banco de TRABALHO do agente (SqliteDb): sessões, execuções e
  memórias. session_id = número do pedido; user_id = matrícula do solicitante. Pode e deve
  ser eliminado a pedido do titular (memoria/eliminacao.py).
- `bancos/registro_conferencias.db` — registro ADMINISTRATIVO: o que o agente recomendou,
  as consultas feitas, o que o servidor decidiu e por quê. Integra o processo de despesa
  pública e segue a guarda da prestação de contas; não é alcançado pela eliminação.
  Não guarda a justificativa nem texto livre do solicitante, apenas o resultado da análise.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

import config
from seguranca.filtro_pii import mascarar_estrutura, mascarar_texto

ESQUEMA = """
CREATE TABLE IF NOT EXISTS analises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL, turno TEXT NOT NULL, situacao TEXT NOT NULL,
    recomendacao TEXT, quantidade_diarias REAL, valor_total REAL,
    motivos_recusa TEXT, alertas TEXT, consultas TEXT, metricas TEXT,
    modelo TEXT, registrado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conferencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL, analise_id INTEGER,
    recomendacao_agente TEXT, encaminhamento_servidor TEXT NOT NULL,
    divergiu INTEGER NOT NULL, justificativa TEXT,
    minuta_final TEXT, minuta_editada INTEGER NOT NULL,
    conferente TEXT NOT NULL, registrado_em TEXT NOT NULL
);
"""


@contextmanager
def _conectar(db_file: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    arquivo = Path(db_file or config.DB_CONFERENCIAS)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(arquivo)
    try:
        con.executescript(ESQUEMA)
        with con:
            yield con
    finally:
        con.close()


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def registrar_analise(resultado, db_file: Path | str | None = None) -> int:
    """Grava o resultado de `instruir` (aprovado ou recusado). Devolve o id da análise."""
    dados = mascarar_estrutura(resultado.to_dict())
    inst = dados["instrucao"] or {}
    consultas = [{"ferramenta": c["ferramenta"], "argumentos": c["argumentos"]} for c in dados["consultas"]]
    with _conectar(db_file) as con:
        cur = con.execute(
            "INSERT INTO analises (numero, turno, situacao, recomendacao, quantidade_diarias, valor_total,"
            " motivos_recusa, alertas, consultas, metricas, modelo, registrado_em)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (dados["numero"], dados["turno"], dados["situacao"], inst.get("recomendacao"),
             inst.get("quantidade_diarias"), inst.get("valor_total"),
             json.dumps(dados["motivos_recusa"], ensure_ascii=False),
             json.dumps(inst.get("alertas", []) + dados["alertas_aplicacao"], ensure_ascii=False),
             json.dumps(consultas, ensure_ascii=False), json.dumps(dados["metricas"]),
             dados["modelo"], _agora()))
        return int(cur.lastrowid)


def registrar_conferencia(numero: str, analise_id: int | None, recomendacao_agente: str | None,
                          encaminhamento: str, justificativa: str, minuta_final: str,
                          minuta_original: str, conferente: str,
                          db_file: Path | str | None = None) -> int:
    """Grava a decisão do servidor ao lado da recomendação do agente.

    A divergência exige justificativa; a função recusa o registro sem ela.
    """
    divergiu = recomendacao_agente is not None and encaminhamento != recomendacao_agente
    if (divergiu or recomendacao_agente is None) and not justificativa.strip():
        raise ValueError("Justificativa obrigatória quando o encaminhamento diverge do agente "
                         "ou quando não houve instrução verificada.")
    if not conferente.strip():
        raise ValueError("Identifique o servidor conferente.")
    justificativa, minuta_final, minuta_original, conferente = (
        mascarar_texto(v)[0] for v in (justificativa, minuta_final, minuta_original or "", conferente))
    with _conectar(db_file) as con:
        cur = con.execute(
            "INSERT INTO conferencias (numero, analise_id, recomendacao_agente, encaminhamento_servidor,"
            " divergiu, justificativa, minuta_final, minuta_editada, conferente, registrado_em)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (numero, analise_id, recomendacao_agente, encaminhamento, int(divergiu), justificativa.strip(),
             minuta_final, int(minuta_final.strip() != (minuta_original or "").strip()),
             conferente.strip(), _agora()))
        return int(cur.lastrowid)


def listar(tabela: str, db_file: Path | str | None = None, numero: str | None = None) -> list[dict]:
    assert tabela in ("analises", "conferencias")
    with _conectar(db_file) as con:
        con.row_factory = sqlite3.Row
        sql = f"SELECT * FROM {tabela}" + (" WHERE numero = ?" if numero else "") + " ORDER BY id DESC"
        return [dict(r) for r in con.execute(sql, (numero,) if numero else ())]


def taxa_divergencia(db_file: Path | str | None = None) -> dict:
    """Com que frequência o servidor discorda do agente (medida que o uso vai produzir)."""
    linhas = listar("conferencias", db_file)
    total = len(linhas)
    divergentes = sum(1 for l in linhas if l["divergiu"])
    return {"conferencias": total, "divergencias": divergentes,
            "taxa": round(divergentes / total, 3) if total else None}
