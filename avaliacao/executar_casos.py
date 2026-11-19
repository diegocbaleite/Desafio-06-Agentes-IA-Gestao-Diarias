"""Etapa 6/7: os 12 pedidos e as 2 complementações, em N rodadas, contra o gabarito externo.

Uso:
    python -m avaliacao.executar_casos                    # API real, 3 rodadas, paralelas desligadas
    python -m avaliacao.executar_casos --paralelas        # mesma coisa com paralelas ligadas
    python -m avaliacao.executar_casos --simulador        # pipeline contra o simulador local

Cada rodada usa um banco novo, para que nenhuma herde memória da anterior.
"""

from __future__ import annotations

import sys

import config
from agente.agente_diarias import construir_agente, instruir
from avaliacao import comparar_gabarito as cg
from avaliacao.execucao import ambiente, argumentos, banco_avaliacao, bloqueio_sem_chave, gravar
from ferramentas import acervo


def executar_rodada(agente, gabarito: dict, ao_terminar=None) -> list[dict]:
    pedidos = {p["numero"]: p for p in acervo.pedidos()}
    linhas = []
    casos = [(n, None) for n in pedidos] + [(c["numero"], c) for c in acervo.complementacoes()]
    for numero, compl in casos:
        r = instruir(agente, pedidos[numero], compl).to_dict()
        esperado = (gabarito["complementacoes"] if compl else gabarito["pedidos"])[numero]
        linha = {"caso": numero + (" (complementação)" if compl else ""), "cenario": esperado["caso"],
                 "situacao": r["situacao"], "esperado": esperado["recomendacao"],
                 "obtido": (r["instrucao"] or {}).get("recomendacao"),
                 "comparacao": cg.comparar(r, esperado), "metricas": r["metricas"],
                 "motivos_recusa": r["motivos_recusa"],
                 "consultas": [{"ferramenta": c["ferramenta"], "argumentos": c["argumentos"]} for c in r["consultas"]],
                 "session_id": r["session_id"], "user_id": r["user_id"]}
        linhas.append(linha)
        if ao_terminar:
            ao_terminar(linha)
    return linhas


def main() -> int:
    args = argumentos(__doc__, lambda p: (p.add_argument("--rodadas", type=int, default=3),
                                          p.add_argument("--paralelas", action="store_true")))
    rotulo = "paralelas_ligadas" if args.paralelas else "paralelas_desligadas"
    arquivo = f"execucao_casos_{rotulo}.json"
    if bloqueio_sem_chave(args.simulador, arquivo, f"Etapa 6 — 12 pedidos + 2 complementações ({rotulo})"):
        return 2
    gabarito = cg.carregar_gabarito()
    rodadas = []
    with ambiente(args.simulador) as (base_url, api_key):
        for i in range(1, args.rodadas + 1):
            db = banco_avaliacao(f"avaliacao_{rotulo}_r{i}.db", args.simulador)
            db.unlink(missing_ok=True)
            agente = construir_agente(memoria="historico", paralelas=args.paralelas, db_file=db,
                                      base_url=base_url, api_key=api_key)
            print(f"\nRodada {i} — {rotulo}")
            linhas = executar_rodada(agente, gabarito, lambda l: print(
                f"  {l['caso']:34} {l['situacao']:14} esperado={l['esperado']:22} obtido={l['obtido']}"
                f"  {'OK' if l['comparacao']['correto'] else '--'}"))
            resumo = cg.resumir(linhas)
            print(f"  corretos {resumo['corretos']}/{resumo['casos']} · recusados {resumo['recusados_pela_barreira']}"
                  f" · custo US$ {resumo['custo_total_usd']}")
            rodadas.append({"rodada": i, "resumo": resumo, "casos": linhas})
    gravar({"configuracao": {"paralelas": args.paralelas, "tool_call_limit": config.TOOL_CALL_LIMIT,
                             "num_history_runs": config.NUM_HISTORY_RUNS, "memoria": "historico"},
            "rodadas": rodadas}, arquivo, args.simulador)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
