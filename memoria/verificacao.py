"""Inspeção direta do banco SQLite do agente, tabela por tabela, sem passar pelo Agno.

É a prova da eliminação: a rotina não confia no retorno dos métodos de exclusão e
procura, em todas as tabelas, a matrícula e o nome do titular.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path


def _variantes(termo: str) -> set[str]:
    """O termo como está e como o JSON o grava com escape de acentos (\\u00e9)."""
    return {termo, json.dumps(termo)[1:-1]}


def contar_registros(db_file: Path | str) -> dict[str, int]:
    """Quantidade de linhas em cada tabela do banco."""
    if not Path(db_file).exists():
        return {}
    with closing(sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)) as con:
        tabelas = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tabelas}


def ocorrencias(db_file: Path | str, termos: list[str]) -> dict[str, dict[str, int]]:
    """Para cada tabela, quantas linhas contêm cada termo (busca em todas as colunas)."""
    if not Path(db_file).exists():
        return {}
    resultado: dict[str, dict[str, int]] = {}
    with closing(sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)) as con:
        tabelas = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for t in tabelas:
            linhas = [" ".join(str(c) for c in linha) for linha in con.execute(f'SELECT * FROM "{t}"')]
            for termo in termos:
                n = sum(1 for linha in linhas if any(v in linha for v in _variantes(termo)))
                if n:
                    resultado.setdefault(t, {})[termo] = n
    return resultado


def sessoes(db_file: Path | str) -> list[dict]:
    """Sessões gravadas, com user_id, para inspeção autorizada na tela."""
    if not Path(db_file).exists():
        return []
    with closing(sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)) as con:
        try:
            linhas = con.execute("SELECT session_id, user_id, created_at, updated_at FROM agno_sessions").fetchall()
        except sqlite3.OperationalError:
            return []
    return [{"session_id": s, "user_id": u, "criada_em": c, "atualizada_em": a} for s, u, c, a in linhas]


def sessoes_que_citam(db_file: Path | str, termos: list[str]) -> list[dict]:
    """Sessões cujo registro ou execuções contêm algum dos termos, com o user_id gravado."""
    if not Path(db_file).exists():
        return []
    achadas: dict[str, dict] = {}
    with closing(sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)) as con:
        tabelas = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        consultas = []
        if "agno_sessions" in tabelas:
            consultas.append(("agno_sessions", "SELECT session_id, user_id, * FROM agno_sessions"))
        if "agno_runs" in tabelas:
            consultas.append(("agno_runs", "SELECT session_id, user_id, * FROM agno_runs"))
        for tabela, sql in consultas:
            for linha in con.execute(sql):
                texto = " ".join(str(c) for c in linha)
                citados = [t for t in termos if any(v in texto for v in _variantes(t))]
                if citados:
                    item = achadas.setdefault(linha[0], {"session_id": linha[0], "user_ids": set(),
                                                         "tabelas": set(), "termos": set()})
                    if linha[1]:
                        item["user_ids"].add(linha[1])
                    item["tabelas"].add(tabela)
                    item["termos"].update(citados)
    return [{**v, "user_ids": sorted(v["user_ids"]), "tabelas": sorted(v["tabelas"]),
             "termos": sorted(v["termos"])} for v in achadas.values()]
