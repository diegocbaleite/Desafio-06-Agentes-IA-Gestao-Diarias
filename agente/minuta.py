"""Redação factual da minuta a partir dos campos já conferidos pela barreira."""

from decimal import Decimal

from agente.modelos import CRITERIOS, Instrucao

RECOMENDACOES = {"apto_para_autorizacao": "apto para autorização",
                 "diligencia": "diligência", "nao_recomendado": "não recomendado"}
SITUACOES = {"atende": "atende", "nao_atende": "não atende", "nao_verificado": "não verificado"}


def redigir_minuta(instrucao: Instrucao) -> str:
    """Gera a proposta; não reutiliza afirmações livres da minuta sugerida pelo modelo."""
    linhas = [f"Despacho de instrução — pedido {instrucao.numero_pedido}.",
              f"Matrícula conferida: {instrucao.matricula}."]
    verificacoes = {v.criterio: v.situacao for v in instrucao.verificacoes}
    linhas.append("Verificações: " + "; ".join(
        f"{c}: {SITUACOES[verificacoes[c]]}" for c in CRITERIOS) + ".")
    if instrucao.recomendacao == "diligencia":
        linhas.append("Sem cálculo de diárias: pedido devolvido em diligência (art. 9º).")
        if verificacoes["cadastro"] != "atende":
            linhas.append("Pendência: corrigir a identificação conforme o cadastro funcional.")
        if verificacoes["dados_completos"] == "nao_atende":
            linhas.append("Pendência: completar os dados obrigatórios do pedido.")
    else:
        quantidade = format(Decimal(str(instrucao.quantidade_diarias)), "f").replace(".", ",")
        valor = f"{instrucao.valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        linhas.append(f"Quantidade: {quantidade} diária(s). Valor total: R$ {valor}.")
    linhas.append(f"Recomendação: {RECOMENDACOES[instrucao.recomendacao]}.")
    if instrucao.exige_autorizacao_superior:
        linhas.append("Urgência condicionada à autorização expressa e escrita do Secretário Adjunto, "
                      "registrada no processo (art. 5º, § 2º).")
    linhas.append("À consideração do ordenador de despesa.")
    return "\n".join(linhas)
