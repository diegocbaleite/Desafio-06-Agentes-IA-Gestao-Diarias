"""Avaliador EXTERNO ao agente: compara instruções com o gabarito.json.

O gabarito fica em avaliacao/externo/ e só é lido por este módulo. Nenhum módulo do
agente o importa (testes/test_isolamento.py verifica).
"""

from __future__ import annotations

import json
from pathlib import Path

from agente.modelos import CRITERIOS

GABARITO = Path(__file__).resolve().parent / "externo" / "gabarito.json"
TOL = 0.005


def carregar_gabarito(caminho: Path = GABARITO) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _igual(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= TOL


def comparar(resultado: dict, esperado: dict) -> dict:
    """Compara um ResultadoInstrucao (dict) com a entrada do gabarito, critério a critério."""
    inst = resultado.get("instrucao")
    if resultado.get("situacao") != "aprovada" or not inst:
        return {"instruido": False, "recusado": resultado.get("situacao") == "recusada",
                "erro": resultado.get("situacao") == "erro_execucao", "correto": False,
                "acertos": {}}
    nao_atendidos = sorted(v["criterio"] for v in inst["verificacoes"] if v["situacao"] == "nao_atende")
    acertos = {
        "recomendacao": inst["recomendacao"] == esperado["recomendacao"],
        "quantidade_diarias": _igual(inst["quantidade_diarias"], esperado["quantidade_diarias"]),
        "valor_total": _igual(inst["valor_total"], esperado["valor_total"]),
        "exige_autorizacao_superior": inst["exige_autorizacao_superior"] == esperado["exige_autorizacao_superior"],
        "criterios_nao_atendidos": nao_atendidos == sorted(esperado["criterios_nao_atendidos"]),
    }
    return {"instruido": True, "recusado": False, "erro": False, "correto": all(acertos.values()),
            "acertos": acertos, "nao_atendidos_agente": nao_atendidos}


def resumir(linhas: list[dict]) -> dict:
    """Totais de uma rodada: linhas = [{"caso", "comparacao", "metricas"}]."""
    n = len(linhas)
    campos = ("recomendacao", "quantidade_diarias", "valor_total", "exige_autorizacao_superior",
              "criterios_nao_atendidos")
    metr = [l["metricas"] for l in linhas if l["metricas"].get("tokens_entrada") is not None]
    custos = [m.get("custo_usd", 0.0) for m in metr]
    tempos = [m.get("segundos", 0.0) for m in metr]
    return {
        "casos": n,
        "corretos": sum(l["comparacao"]["correto"] for l in linhas),
        "recusados_pela_barreira": sum(l["comparacao"]["recusado"] for l in linhas),
        "erros_de_execucao": sum(l["comparacao"]["erro"] for l in linhas),
        "instruidos_errados_entregues": sum(l["comparacao"]["instruido"] and not l["comparacao"]["correto"]
                                            for l in linhas),
        "acertos_por_criterio": {c: sum(l["comparacao"]["acertos"].get(c, False) for l in linhas) for c in campos},
        "tokens_entrada": sum(m.get("tokens_entrada", 0) for m in metr),
        "tokens_saida": sum(m.get("tokens_saida", 0) for m in metr),
        "chamadas_modelo": sum(m.get("chamadas_modelo", 0) for m in metr),
        "chamadas_ferramenta": sum(m.get("chamadas_ferramenta", 0) for m in metr),
        "max_ferramentas_simultaneas": max((m.get("max_ferramentas_simultaneas", 0) for m in metr), default=0),
        "custo_total_usd": round(sum(custos), 6),
        "custo_medio_usd": round(sum(custos) / len(custos), 6) if custos else None,
        "custo_min_usd": min(custos, default=None), "custo_max_usd": max(custos, default=None),
        "tempo_total_s": round(sum(tempos), 2),
        "tempo_medio_s": round(sum(tempos) / len(tempos), 2) if tempos else None,
        "tempo_min_s": min(tempos, default=None), "tempo_max_s": max(tempos, default=None),
        "criterios_verificados": list(CRITERIOS),
    }
