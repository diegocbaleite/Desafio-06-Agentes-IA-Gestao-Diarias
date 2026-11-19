"""Etapa 1: ESTIMATIVA (não medição) dos tokens de entrada por chamada, antes da API.

Captura, pelo simulador local, o corpo EXATO de cada requisição que o Agno monta (instrução,
esquemas das ferramentas, esquema de saída, pedido, resultados das ferramentas) e conta os
tokens com o tokenizador o200k_base (tiktoken), o da família GPT-4o/GPT-5. O tokenizador do
gpt-5.6-luna não é público: a contagem é aproximação, a ser confrontada com a medição real.

Uso: python -m avaliacao.estimar_tokens      (requer: pip install tiktoken)
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import config
from agente.agente_diarias import construir_agente, instruir
from ferramentas import acervo
from simulador.servidor_openai_simulado import SimuladorOpenAI


def main() -> int:
    try:
        import tiktoken
    except ImportError:
        print("Instale tiktoken: pip install tiktoken")
        return 2
    enc = tiktoken.get_encoding("o200k_base")

    def n(texto: str) -> int:
        return len(enc.encode(texto))

    def tokens(corpo: str) -> int:
        b = json.loads(corpo)
        total = 0
        for m in b["messages"]:
            c = m.get("content") or ""
            if isinstance(c, list):
                c = " ".join(x.get("text", "") for x in c)
            total += n(c) + 4  # ~4 tokens de moldura por mensagem
            for tc in m.get("tool_calls") or []:
                total += n(json.dumps(tc["function"], ensure_ascii=False))
        total += n(json.dumps(b.get("tools", []), ensure_ascii=False))
        if b.get("response_format"):
            total += n(json.dumps(b["response_format"], ensure_ascii=False))
        return total

    pedidos = {p["numero"]: p for p in acervo.pedidos()}
    compls = {c["numero"]: c for c in acervo.complementacoes()}
    casos = {}
    with SimuladorOpenAI() as sim, tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as pasta:
        ag = construir_agente(db_file=Path(pasta) / "estimativa.db", base_url=sim.url, api_key="simulador")
        for numero in pedidos:
            i = len(sim.requisicoes)
            instruir(ag, pedidos[numero])
            casos[numero] = [tokens(c) for c in sim.requisicoes[i:]]
        for numero in compls:
            i = len(sim.requisicoes)
            instruir(ag, pedidos[numero], compls[numero])
            casos[numero + " (complementação, com histórico)"] = [tokens(c) for c in sim.requisicoes[i:]]
        primeira = json.loads(sim.requisicoes[0])
        corpo_ok = {k: primeira.get(k) for k in ("model", "parallel_tool_calls", "reasoning_effort")}
    componentes = {
        "instrucao_de_sistema_com_norma": n(primeira["messages"][0]["content"]),
        "norma_sozinha": n(acervo.norma()),
        "esquemas_das_4_ferramentas": n(json.dumps(primeira["tools"], ensure_ascii=False)),
        "esquema_de_saida_Instrucao": n(json.dumps(primeira["response_format"], ensure_ascii=False)),
        "mensagem_do_pedido_0101": n(primeira["messages"][-1]["content"]),
    }
    regulares = [v for k, v in casos.items() if len(v) == 5 and "compl" not in k]
    incrementos = [b - a for v in regulares for a, b in zip(v, v[1:])]
    resumo = {
        "primeira_chamada_media": round(sum(v[0] for v in regulares) / len(regulares)),
        "incremento_medio": round(sum(incrementos) / len(incrementos)),
        "incremento_min": min(incrementos), "incremento_max": max(incrementos),
        "entrada_total_media_pedido_regular": round(sum(sum(v) for v in regulares) / len(regulares)),
    }
    dados = {"natureza": "ESTIMATIVA com tokenizador o200k_base sobre as requisições reais montadas pelo Agno; "
                         "não é medição do gpt-5.6-luna.",
             "parametros_enviados_na_requisicao": corpo_ok, "componentes_primeira_chamada": componentes,
             "resumo_pedidos_regulares_5_chamadas": resumo, "entrada_por_chamada": casos}
    config.EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    destino = config.EVIDENCIAS / "estimativa_tokens_o200k.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"componentes": componentes, "resumo": resumo, "parametros": corpo_ok},
                     ensure_ascii=False, indent=2))
    print(f"Gravado em {destino}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
