"""Ferramenta 2 — histórico de diárias e prestações de contas (substitui a planilha de controle)."""

from __future__ import annotations

import json

from ferramentas import acervo


def consultar_historico_diarias(matricula: str, data_partida: str) -> str:
    """Consulta as diárias já concedidas a um servidor e a situação das prestações de contas.

    Finalidade: verificar o critério "prestacao_contas" (art. 7º) e informar as diárias já
    concedidas no mês civil da partida, usadas no limite mensal (art. 6º).

    Quando usar: depois de consultar_servidor, apenas se o cadastro "atende". Use a mesma
    matrícula conferida no cadastro e a data de partida do pedido.

    Argumentos:
        matricula: seis algarismos, como "203648".
        data_partida: data de partida do pedido no formato AAAA-MM-DD, como "2026-11-03".

    Devolve: texto JSON com
        prestacoes_pendentes: lista com pedido, data_retorno, prazo_final (5 dias úteis após o
            retorno, sem feriados) e situacao "vencida" ou "no_prazo", na data da análise;
        criterio_prestacao_contas: "nao_atende" se houver prestação vencida, senão "atende"
            (pendência ainda no prazo NÃO impede a concessão);
        mes_da_partida e diarias_ja_concedidas_no_mes (número, com meias diárias);
        data_da_analise, fonte, regra e argumentos.

    Erros: matrícula ou data fora do formato devolve situacao "argumento_invalido".
    Servidor sem registros devolve listas vazias, o que NÃO é erro.
    """
    argumentos = {"matricula": matricula, "data_partida": data_partida}
    base = {"ferramenta": "consultar_historico_diarias", "fonte": "historico_diarias.csv",
            "regra": "art. 7º (prestação vencida impede) e art. 6º (limite mensal)",
            "argumentos": argumentos}
    mat = (matricula or "").strip()
    partida = acervo.ler_data(data_partida)
    if not acervo.matricula_valida(mat) or partida is None:
        return json.dumps({**base, "situacao": "argumento_invalido",
                           "criterio_prestacao_contas": "nao_verificado",
                           "mensagem": "Informe matrícula de seis algarismos e data AAAA-MM-DD "
                                       "constantes do pedido."}, ensure_ascii=False)
    hoje = acervo.data_da_analise()
    prazo_dias = int(acervo.tabela()["prazo_prestacao_dias_uteis"])
    registros = [h for h in acervo.historico() if h["matricula"] == mat]

    pendentes = []
    for h in registros:
        if h["prestacao_contas"] != "pendente":
            continue
        prazo = acervo.somar_dias_uteis(acervo.ler_data(h["data_retorno"]), prazo_dias)
        pendentes.append({"pedido": h["pedido"], "data_retorno": h["data_retorno"],
                          "prazo_final": prazo.isoformat(),
                          "situacao": "vencida" if prazo < hoje else "no_prazo"})
    vencidas = [p for p in pendentes if p["situacao"] == "vencida"]

    mes = partida.isoformat()[:7]
    no_mes = [h for h in registros if h["data_partida"][:7] == mes]
    usadas = sum((acervo.Decimal(h["quantidade"]) for h in no_mes), acervo.Decimal("0"))

    return json.dumps({**base, "situacao": "consultado", "data_da_analise": hoje.isoformat(),
                       "prestacoes_pendentes": pendentes,
                       "criterio_prestacao_contas": "nao_atende" if vencidas else "atende",
                       "mes_da_partida": mes,
                       "diarias_ja_concedidas_no_mes": float(usadas),
                       "pedidos_no_mes": [h["pedido"] for h in no_mes]}, ensure_ascii=False)
