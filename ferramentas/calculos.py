"""Ferramenta 3 — cálculo das diárias, da antecedência e do limite mensal (substitui a calculadora)."""

from __future__ import annotations

import json

from ferramentas import acervo


def calcular_diarias(matricula: str, destino_uf: str, data_pedido: str,
                     data_partida: str, data_retorno: str) -> str:
    """Calcula quantidade e valor das diárias, a antecedência e o limite mensal de um pedido.

    Finalidade: fazer no código toda a aritmética da IN SEMA nº 07/2026 — art. 4º
    (quantidade), Anexo I (valor por grupo e destino), art. 5º (antecedência mínima de
    10 dias corridos) e art. 6º (limite de 10 diárias no mês civil da partida). O grupo do
    cargo é lido do cadastro pela matrícula; não o informe.

    Quando usar: depois de consultar_servidor com cadastro "atende" e somente se o pedido
    (ou a complementação) trouxer as três datas. Se faltar a data de retorno, NÃO chame
    esta ferramenta com data suposta: o pedido vai para diligência.

    Argumentos (copie-os do pedido ou da complementação, nunca os deduza):
        matricula: seis algarismos, a mesma conferida no cadastro.
        destino_uf: sigla da UF do destino, como "MT", "DF" ou "RO".
        data_pedido: data do protocolo, AAAA-MM-DD.
        data_partida: data de partida, AAAA-MM-DD.
        data_retorno: data de retorno, AAAA-MM-DD (igual à partida quando sem pernoite).

    Devolve: texto JSON com quantidade_diarias, valor_unitario, valor_total (em reais,
    duas casas), grupo_diaria, classe_destino, antecedencia_dias,
    antecedencia_minima_atendida (bool), diarias_ja_concedidas_no_mes,
    total_no_mes_com_pedido, criterio_limite_mensal ("atende"/"nao_atende"),
    fonte, regras e argumentos. A decisão sobre urgência (art. 5º, §§ 1º e 2º) NÃO é
    feita aqui: a ferramenta apenas informa se a antecedência mínima foi cumprida.

    Erros: data ausente ou fora do formato devolve situacao "dados_incompletos"
    (diligência, art. 9º); retorno anterior à partida devolve "argumento_invalido";
    matrícula não localizada devolve "nao_localizado".
    """
    argumentos = {"matricula": matricula, "destino_uf": destino_uf, "data_pedido": data_pedido,
                  "data_partida": data_partida, "data_retorno": data_retorno}
    base = {"ferramenta": "calcular_diarias",
            "fonte": "tabela_diarias.json, servidores.csv, historico_diarias.csv",
            "regra": "art. 4º, art. 5º, art. 6º e Anexo I", "argumentos": argumentos}
    mat = (matricula or "").strip()
    if not acervo.matricula_valida(mat):
        return json.dumps({**base, "situacao": "argumento_invalido",
                           "mensagem": "Matrícula deve ter seis algarismos."}, ensure_ascii=False)
    servidor = acervo.servidores().get(mat)
    if servidor is None:
        return json.dumps({**base, "situacao": "nao_localizado",
                           "mensagem": f"Matrícula {mat} não consta do cadastro."}, ensure_ascii=False)
    datas = {n: acervo.ler_data(v) for n, v in
             (("data_pedido", data_pedido), ("data_partida", data_partida), ("data_retorno", data_retorno))}
    faltantes = [n for n, d in datas.items() if d is None]
    if faltantes:
        return json.dumps({**base, "situacao": "dados_incompletos", "campos_ausentes": faltantes,
                           "mensagem": "Dado obrigatório ausente ou fora do formato AAAA-MM-DD. "
                                       "Não calcule com data suposta: diligência (art. 9º)."},
                          ensure_ascii=False)
    pedido_em, partida, retorno = datas["data_pedido"], datas["data_partida"], datas["data_retorno"]
    if retorno < partida:
        return json.dumps({**base, "situacao": "argumento_invalido",
                           "mensagem": "Data de retorno anterior à partida."}, ensure_ascii=False)
    uf = (destino_uf or "").strip().upper()
    if len(uf) != 2 or not uf.isalpha():
        return json.dumps({**base, "situacao": "argumento_invalido",
                           "mensagem": "UF deve ter duas letras, como MT."}, ensure_ascii=False)

    grupo = servidor["grupo_diaria"]
    qtd = acervo.quantidade_diarias(partida, retorno)
    unitario = acervo.valor_unitario(grupo, uf)
    total = (qtd * unitario).quantize(acervo.CENTAVO)

    tab = acervo.tabela()
    minimo = int(tab["antecedencia_minima_dias"])
    antecedencia = acervo.antecedencia_dias(pedido_em, partida)

    limite = acervo.Decimal(str(tab["limite_mensal_diarias"]))
    mes = partida.isoformat()[:7]
    usadas = sum((acervo.Decimal(h["quantidade"]) for h in acervo.historico()
                  if h["matricula"] == mat and h["data_partida"][:7] == mes), acervo.Decimal("0"))
    total_mes = usadas + qtd

    return json.dumps({**base, "situacao": "calculado", "grupo_diaria": grupo,
                       "classe_destino": acervo.classe_destino(uf),
                       "pernoites": (retorno - partida).days,
                       "quantidade_diarias": float(qtd),
                       "valor_unitario": acervo.dinheiro(unitario),
                       "valor_total": acervo.dinheiro(total),
                       "antecedencia_dias": antecedencia, "antecedencia_minima_dias": minimo,
                       "antecedencia_minima_atendida": antecedencia >= minimo,
                       "mes_da_partida": mes, "diarias_ja_concedidas_no_mes": float(usadas),
                       "total_no_mes_com_pedido": float(total_mes),
                       "limite_mensal": float(limite),
                       "criterio_limite_mensal": "atende" if total_mes <= limite else "nao_atende"},
                      ensure_ascii=False)
