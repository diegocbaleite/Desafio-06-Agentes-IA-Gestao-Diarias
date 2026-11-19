"""Ferramenta 4 — saldo da dotação de diárias da unidade (substitui a consulta ao sistema financeiro)."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from ferramentas import acervo


def consultar_saldo_diarias(unidade: str, valor: float) -> str:
    """Consulta o saldo da dotação de diárias de uma unidade e o compara com o valor pedido.

    Finalidade: verificar o critério "saldo_orcamentario" (art. 8º).

    Quando usar: por último, DEPOIS de calcular_diarias. `unidade` é a sigla da unidade de
    lotação devolvida por consultar_servidor (como CFF ou GAB), nunca a do destino;
    `valor` é exatamente o valor_total devolvido por calcular_diarias, em reais, com ponto
    decimal, como 980.0.

    Devolve: texto JSON com unidade, nome_unidade, saldo_disponivel, valor_pedido,
    criterio_saldo_orcamentario ("atende" se saldo >= valor, senão "nao_atende"), fonte,
    regra e argumentos. A comparação é feita em Decimal, com centavos.

    Erros: sigla inexistente devolve situacao "nao_localizado" com as siglas válidas;
    valor não numérico ou não positivo devolve "argumento_invalido".
    """
    argumentos = {"unidade": unidade, "valor": valor}
    base = {"ferramenta": "consultar_saldo_diarias", "fonte": "unidades.json",
            "regra": "art. 8º (saldo suficiente na dotação da unidade de lotação)",
            "argumentos": argumentos}
    sigla = (unidade or "").strip().upper()
    unidades = acervo.unidades()
    if sigla not in unidades:
        return json.dumps({**base, "situacao": "nao_localizado",
                           "mensagem": f"Unidade '{unidade}' não localizada. Siglas válidas: "
                                       f"{', '.join(unidades)}."}, ensure_ascii=False)
    try:
        pedido = Decimal(str(valor)).quantize(acervo.CENTAVO)
    except (InvalidOperation, ValueError, TypeError):
        pedido = None
    if pedido is None or not pedido.is_finite() or pedido <= 0:
        return json.dumps({**base, "situacao": "argumento_invalido",
                           "mensagem": "Valor deve ser o total calculado, positivo, como 980.0."},
                          ensure_ascii=False)
    saldo = Decimal(str(unidades[sigla]["saldo_diarias"])).quantize(acervo.CENTAVO)
    return json.dumps({**base, "situacao": "consultado", "unidade": sigla,
                       "nome_unidade": unidades[sigla]["nome"],
                       "saldo_disponivel": acervo.dinheiro(saldo),
                       "valor_pedido": acervo.dinheiro(pedido),
                       "criterio_saldo_orcamentario": "atende" if saldo >= pedido else "nao_atende"},
                      ensure_ascii=False)
