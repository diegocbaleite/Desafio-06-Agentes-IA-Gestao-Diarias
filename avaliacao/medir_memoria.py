"""Etapa 4: custo da memória por turno e eliminação verificável (DIA-2026-0111 e DIA-2026-0112).

Três configurações, cada uma com banco novo:
    A · sem memória
    B · histórico da sessão (add_history_to_context, num_history_runs)
    C · histórico + memórias do usuário (update_memory_on_run)
Para cada complementação registra: entrada do 1º turno, entrada do turno da complementação,
tempo, custo e se a complementação foi aplicada ao pedido certo (contra o gabarito externo).
Em seguida, no banco da configuração C, executa a rotina de eliminação para as duas
titulares e grava a evidência tabela por tabela.

Uso: python -m avaliacao.medir_memoria [--simulador]
"""

from __future__ import annotations

import sys

import config
from agente.agente_diarias import construir_agente, instruir
from avaliacao import comparar_gabarito as cg
from avaliacao.execucao import ambiente, argumentos, banco_avaliacao, bloqueio_sem_chave, gravar
from ferramentas import acervo
from memoria import eliminacao, verificacao

CONFIGURACOES = [("A · sem memória", "sem_memoria"), ("B · histórico da sessão", "historico"),
                 ("C · histórico + memórias do usuário", "historico_usuario")]
TITULARES = {"DIA-2026-0111": ("206689", "Beatriz Moraes Cunha"),
             "DIA-2026-0112": ("207418", "Carla Regina Souza")}


def main() -> int:
    args = argumentos(__doc__)
    arquivo = "medicao_memoria.json"
    if bloqueio_sem_chave(args.simulador, arquivo, "Etapa 4 — custo da memória e eliminação"):
        return 2
    gabarito = cg.carregar_gabarito()
    pedidos = {p["numero"]: p for p in acervo.pedidos()}
    compls = {c["numero"]: c for c in acervo.complementacoes()}
    linhas, eliminacoes = [], {}
    with ambiente(args.simulador) as (base_url, api_key):
        for rotulo, memoria in CONFIGURACOES:
            db = banco_avaliacao(f"memoria_{memoria}.db", args.simulador)
            db.unlink(missing_ok=True)
            agente = construir_agente(memoria=memoria, db_file=db, base_url=base_url, api_key=api_key)
            for numero in TITULARES:
                t1 = instruir(agente, pedidos[numero])
                t2 = instruir(agente, pedidos[numero], compls[numero])
                comp = cg.comparar(t2.to_dict(), gabarito["complementacoes"][numero])
                linha = {"configuracao": rotulo, "pedido": numero,
                         "turno1": {"situacao": t1.situacao, **t1.metricas},
                         "turno2": {"situacao": t2.situacao, **t2.metricas},
                         "complementacao_aplicada_ao_pedido_certo": comp["correto"],
                         "session_id": t2.session_id, "user_id": t2.user_id,
                         "motivos_recusa_turno2": t2.motivos_recusa}
                linhas.append(linha)
                print(f"{rotulo:38} {numero}  T1 entrada={t1.metricas.get('tokens_entrada')}"
                      f"  T2 entrada={t2.metricas.get('tokens_entrada')}  aplicada={comp['correto']}")
            if memoria == "historico_usuario":
                registros = verificacao.contar_registros(db)
                memorias_por_user = {}
                for s in acervo.pedidos():
                    loc = eliminacao.localizar(db, s["matricula"], s["nome"])
                    if loc.memorias_do_titular:
                        memorias_por_user[s["matricula"]] = len(loc.memorias_do_titular)
                eliminacoes["registros_antes"] = registros
                eliminacoes["memorias_por_user_id"] = memorias_por_user
                for numero, (mat, nome) in TITULARES.items():
                    loc = eliminacao.localizar(db, mat, nome)
                    vinculadas = [s["session_id"] for s in loc.sessoes_sob_outro_user_id if s["vinculo_verificado"]]
                    # 1ª passagem sem confirmação: mostra o que a busca por user_id deixa para trás.
                    sem_conf = eliminacao.eliminar(db, mat, nome, executado_por="medir_memoria (sem confirmação)")
                    com_conf = eliminacao.eliminar(
                        db, mat, nome, sessoes_confirmadas=vinculadas,
                        memorias_confirmadas=[m["memory_id"] for m in loc.memorias_sob_outro_user_id],
                        executado_por="medir_memoria (vínculo verificado pelo pedido)")
                    eliminacoes[numero] = {"sem_confirmacao": sem_conf, "com_confirmacao": com_conf}
                    print(f"eliminação {numero}: sem confirmação nada_restou={sem_conf['nada_restou']} · "
                          f"com confirmação nada_restou={com_conf['nada_restou']}")
    gravar({"configuracoes": [c[0] for c in CONFIGURACOES], "num_history_runs": config.NUM_HISTORY_RUNS,
            "linhas": linhas, "eliminacao": eliminacoes}, arquivo, args.simulador)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
