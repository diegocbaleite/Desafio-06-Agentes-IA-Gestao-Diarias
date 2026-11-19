"""Ferramenta 1 — consulta ao cadastro funcional (substitui a consulta manual ao sistema de RH)."""

from __future__ import annotations

import json

from ferramentas import acervo


def consultar_servidor(matricula: str, nome_informado: str) -> str:
    """Consulta o cadastro funcional de um servidor e confere o nome informado no pedido.

    Finalidade: verificar o critério "cadastro" (art. 9º da IN SEMA nº 07/2026) e obter o
    grupo da diária e a sigla da unidade de lotação, necessários às demais consultas.

    Quando usar: SEMPRE como primeira consulta de cada pedido ou complementação. Use a
    matrícula exatamente como consta do pedido ou, se a complementação a corrigir, a
    matrícula corrigida. Nunca deduza, complete ou invente uma matrícula.

    Argumentos:
        matricula: seis algarismos, sem pontos ou espaços, como "204317".
        nome_informado: nome do solicitante exatamente como escrito no pedido.

    Devolve: texto JSON com os campos
        situacao: "localizado", "nao_localizado" (dado não encontrado, NÃO é impedimento)
                  ou "argumento_invalido";
        conferencia_nome: "confere" ou "diverge" (apenas quando localizado);
        criterio_cadastro: "atende" ou "nao_atende" (diverge ou não localizado => diligência);
        cargo, grupo_diaria (A, B ou C), unidade (sigla, como CFF), municipio_sede —
                  devolvidos somente quando o nome confere;
        fonte, regra e argumentos recebidos, para rastreabilidade.
    Por minimização (LGPD, art. 6º, III), CPF e e-mail nunca são devolvidos, e o nome do
    titular de uma matrícula que não corresponde ao solicitante também não.

    Erros: matrícula fora do formato devolve situacao "argumento_invalido" e a orientação de
    não prosseguir; nenhuma exceção é lançada ao agente.
    """
    argumentos = {"matricula": matricula, "nome_informado": nome_informado}
    base = {"ferramenta": "consultar_servidor", "fonte": "servidores.csv",
            "regra": "art. 9º (dados divergentes do cadastro => diligência)",
            "argumentos": argumentos}
    mat = (matricula or "").strip()
    if not acervo.matricula_valida(mat):
        return json.dumps({**base, "situacao": "argumento_invalido",
                           "criterio_cadastro": "nao_verificado",
                           "mensagem": "Matrícula deve ter seis algarismos, como consta do pedido. "
                                       "Não prossiga com matrícula suposta."}, ensure_ascii=False)
    servidor = acervo.servidores().get(mat)
    if servidor is None:
        return json.dumps({**base, "situacao": "nao_localizado", "criterio_cadastro": "nao_atende",
                           "mensagem": f"Matrícula {mat} não consta do cadastro funcional. "
                                       "Pedido em diligência para correção."}, ensure_ascii=False)
    if acervo.normalizar_nome(servidor["nome"]) != acervo.normalizar_nome(nome_informado):
        return json.dumps({**base, "situacao": "localizado", "conferencia_nome": "diverge",
                           "criterio_cadastro": "nao_atende",
                           "mensagem": f"A matrícula {mat} pertence a outro servidor: o nome informado "
                                       "não corresponde ao titular da matrícula. Pedido em diligência; "
                                       "não calcule diárias com esta matrícula."}, ensure_ascii=False)
    return json.dumps({**base, "situacao": "localizado", "conferencia_nome": "confere",
                       "criterio_cadastro": "atende", "matricula": mat, "nome": servidor["nome"],
                       "cargo": servidor["cargo"], "grupo_diaria": servidor["grupo_diaria"],
                       "unidade": servidor["unidade"], "municipio_sede": servidor["municipio_sede"]},
                      ensure_ascii=False)
