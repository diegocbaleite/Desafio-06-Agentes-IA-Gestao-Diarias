"""Gera resultados/relatorio_medicoes.md a partir dos JSON gravados pelos scripts de avaliação.

Nada é digitado à mão: cada número vem de um arquivo de resultados. Execuções bloqueadas
aparecem como "não executado", com o motivo. Uso: python -m avaliacao.gerar_relatorio [--simulador]
"""

from __future__ import annotations

import json
import sys

from avaliacao.execucao import argumentos, pasta_saida


def _ler(pasta, nome):
    arq = pasta / nome
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else None


def _bloqueio(d, nome) -> str | None:
    if d is None:
        return f"_{nome}: arquivo não gerado._\n"
    if d.get("situacao") == "nao_executado":
        return f"_{nome}: **não executado** — {d['motivo']}_\n"
    return None


def main() -> int:
    args = argumentos(__doc__)
    pasta = pasta_saida(args.simulador)
    out = ["# Relatório de medições (gerado automaticamente)\n"]
    if args.simulador:
        out.append("> **Simulador local — NÃO são medições do modelo.** Tokens, tempo e custo abaixo são do "
                   "simulador; servem apenas para demonstrar o pipeline.\n")
    for rot in ("paralelas_desligadas", "paralelas_ligadas"):
        nome = f"execucao_casos_{rot}.json"
        d = _ler(pasta, nome)
        out.append(f"\n## Casos contra o gabarito — {rot.replace('_', ' ')}\n")
        b = _bloqueio(d, nome)
        if b:
            out.append(b)
            continue
        out.append("| Rodada | Corretos | Recusados | Erros | Errados entregues | Chamadas modelo | Ferram. | "
                   "Entrada | Saída | US$ total | US$ médio (mín–máx) | Tempo total s (mín–máx) |\n"
                   "|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in d["rodadas"]:
            s = r["resumo"]
            out.append(f"| {r['rodada']} | {s['corretos']}/{s['casos']} | {s['recusados_pela_barreira']} | "
                       f"{s['erros_de_execucao']} | {s['instruidos_errados_entregues']} | {s['chamadas_modelo']} | "
                       f"{s['chamadas_ferramenta']} | {s['tokens_entrada']} | {s['tokens_saida']} | "
                       f"{s['custo_total_usd']} | {s['custo_medio_usd']} ({s['custo_min_usd']}–{s['custo_max_usd']}) | "
                       f"{s['tempo_total_s']} ({s['tempo_min_s']}–{s['tempo_max_s']}) |\n")
        out.append("\nAcertos por critério (rodada 1): " +
                   ", ".join(f"{k} {v}/14" for k, v in d["rodadas"][0]["resumo"]["acertos_por_criterio"].items()) + "\n")
        out.append("\n| Caso | Esperado | Obtido (r1) | r1 | r2 | r3 |\n|---|---|---|---|---|---|\n")
        for i, c in enumerate(d["rodadas"][0]["casos"]):
            marcas = []
            for r in d["rodadas"]:
                x = r["casos"][i]
                marcas.append("✅" if x["comparacao"]["correto"] else ("⛔ recusado" if x["situacao"] != "aprovada" else "❌"))
            marcas += [""] * (3 - len(marcas))
            out.append(f"| {c['caso']} | {c['esperado']} | {c['obtido']} | " + " | ".join(marcas[:3]) + " |\n")
    d = _ler(pasta, "medicao_memoria.json")
    out.append("\n## Memória por turno\n")
    b = _bloqueio(d, "medicao_memoria.json")
    if b:
        out.append(b)
    else:
        out.append("| Configuração | Pedido | Entrada T1 | Entrada T2 | US$ T1+T2 | Tempo T1+T2 s | Aplicada ao pedido certo |\n"
                   "|---|---|---|---|---|---|---|\n")
        for l in d["linhas"]:
            t1, t2 = l["turno1"], l["turno2"]
            out.append(f"| {l['configuracao']} | {l['pedido']} | {t1.get('tokens_entrada')} | {t2.get('tokens_entrada')} | "
                       f"{round((t1.get('custo_usd') or 0) + (t2.get('custo_usd') or 0), 6)} | "
                       f"{round((t1.get('segundos') or 0) + (t2.get('segundos') or 0), 2)} | "
                       f"{'sim' if l['complementacao_aplicada_ao_pedido_certo'] else 'não'} |\n")
        for n in ("DIA-2026-0111", "DIA-2026-0112"):
            e = d["eliminacao"].get(n)
            if e:
                out.append(f"\n- Eliminação {n}: sem confirmação → nada restou = **{e['sem_confirmacao']['nada_restou']}** "
                           f"(não apagadas: {len(e['sem_confirmacao']['nao_apagadas'])}); com vínculo verificado e "
                           f"confirmação → nada restou = **{e['com_confirmacao']['nada_restou']}**; resíduo depois: "
                           f"`{e['com_confirmacao']['depois']['ocorrencias']}`\n")
    d = _ler(pasta, "falhas_provocadas.json")
    out.append("\n## Falhas provocadas\n")
    b = _bloqueio(d, "falhas_provocadas.json")
    if b:
        out.append(b)
    else:
        out.append("| Id | Falha | Situação | Entregue ao conferente | Detectada ou inofensiva | Motivo principal |\n"
                   "|---|---|---|---|---|---|\n")
        for f in d["falhas"]:
            motivo = (f["motivos_recusa"] or ["—"])[0].replace("|", "/")
            out.append(f"| {f['id']} | {f['falha']} | {f['situacao']} | {f['recomendacao_entregue']} | "
                       f"{'sim' if f['detectada_ou_inofensiva'] else '**NÃO**'} | {motivo[:110]} |\n")
    d = _ler(pasta, "comparacao_desempenho.json")
    if d and d.get("estimativa_etapa1"):
        e = d["estimativa_etapa1"]
        out.append(f"\n## Etapa 1 × medido\n\nEstimativa de referência: {e['entrada_estimada_min']}–"
                   f"{e['entrada_estimada_max']} tokens de entrada por pedido regular; medido (média): "
                   f"{e['entrada_medida_media']}; diferença (medido − ponto médio da referência) / medido: "
                   f"{e.get('erro_relativo_ao_medido', e.get('erro_relativo_ao_ponto_medio'))}.\n")
    destino = pasta / "relatorio_medicoes.md"
    destino.write_text("".join(out), encoding="utf-8")
    print(f"Gravado em {destino}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
