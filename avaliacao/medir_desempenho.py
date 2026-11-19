"""Etapa 7: comparação de chamadas paralelas ligadas x desligadas, a partir das execuções gravadas.

Lê resultados/execucao_casos_paralelas_desligadas.json e ..._ligadas.json (gerados por
`python -m avaliacao.executar_casos [--paralelas]`) e produz a tabela comparativa:
acertos, recusas, chamadas ao modelo, ferramentas simultâneas, tokens, tempo e custo.
Também confronta a estimativa de custo da Etapa 1 (desenho.md) com o medido.

Uso: python -m avaliacao.medir_desempenho [--simulador]
"""

from __future__ import annotations

import json
import sys

import config
from avaliacao.execucao import argumentos, gravar, pasta_saida

# Estimativa da Etapa 1 (desenho.md): 1ª chamada ~2.060 tokens; +90 a +150 por passo; 5 passos.
PRIMEIRA = 2060
PASSOS = 5


def estimativa(acrescimo: int) -> int:
    return sum(PRIMEIRA + acrescimo * i for i in range(PASSOS))


def resumo_config(dados: dict) -> dict:
    rodadas = dados["rodadas"]
    pedidos_regulares = [c for r in rodadas for c in r["casos"]
                         if c["situacao"] == "aprovada" and c["obtido"] != "diligencia"
                         and "(complementação)" not in c["caso"]]
    entrada_por_chamada = [c["metricas"].get("entrada_por_chamada", []) for c in pedidos_regulares]
    primeira = [e[0] for e in entrada_por_chamada if e]
    incrementos = [b - a for e in entrada_por_chamada for a, b in zip(e, e[1:])]
    return {
        "rodadas": len(rodadas),
        "corretos_por_rodada": [r["resumo"]["corretos"] for r in rodadas],
        "recusados_por_rodada": [r["resumo"]["recusados_pela_barreira"] for r in rodadas],
        "erros_por_rodada": [r["resumo"]["erros_de_execucao"] for r in rodadas],
        "errados_entregues_por_rodada": [r["resumo"]["instruidos_errados_entregues"] for r in rodadas],
        "chamadas_modelo_por_rodada": [r["resumo"]["chamadas_modelo"] for r in rodadas],
        "max_ferramentas_simultaneas": max(r["resumo"]["max_ferramentas_simultaneas"] for r in rodadas),
        "custo_por_rodada_usd": [r["resumo"]["custo_total_usd"] for r in rodadas],
        "tempo_por_rodada_s": [r["resumo"]["tempo_total_s"] for r in rodadas],
        "primeira_chamada_media_tokens": round(sum(primeira) / len(primeira)) if primeira else None,
        "incremento_medio_por_passo_tokens": round(sum(incrementos) / len(incrementos)) if incrementos else None,
        "entrada_media_pedido_regular_tokens": round(sum(sum(e) for e in entrada_por_chamada) /
                                                     len(entrada_por_chamada)) if entrada_por_chamada else None,
    }


def main() -> int:
    args = argumentos(__doc__)
    pasta = pasta_saida(args.simulador)
    comparacao = {}
    for rotulo in ("paralelas_desligadas", "paralelas_ligadas"):
        arquivo = pasta / f"execucao_casos_{rotulo}.json"
        if not arquivo.exists():
            comparacao[rotulo] = {"situacao": "nao_executado", "motivo": f"{arquivo.name} ausente"}
            continue
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        if dados.get("situacao") == "nao_executado":
            comparacao[rotulo] = dados
            continue
        comparacao[rotulo] = resumo_config(dados)
    medido = (comparacao.get("paralelas_desligadas") or {}).get("entrada_media_pedido_regular_tokens")
    est = {"premissa": f"1ª chamada {PRIMEIRA} tokens, +90 a +150 por passo, {PASSOS} passos",
           "entrada_estimada_min": estimativa(90), "entrada_estimada_max": estimativa(150),
           "entrada_medida_media": medido,
           "erro_relativo_ao_medido": round((medido - estimativa(120)) / medido, 4) if medido else None}
    for rotulo, r in comparacao.items():
        print(rotulo, json.dumps(r, ensure_ascii=False)[:400])
    print("estimativa x medido:", est)
    gravar({"comparacao_paralelas": comparacao, "estimativa_etapa1": est,
            "custo_por_milhao": {"entrada": config.USD_ENTRADA_POR_MILHAO, "saida": config.USD_SAIDA_POR_MILHAO}},
           "comparacao_desempenho.json", args.simulador)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
