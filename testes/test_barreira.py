"""Etapa 3: a barreira no código recusa instruções com dado inventado ou inconsistente.

Os cenários são montados com as ferramentas reais e uma instrução correta; cada teste
altera um ponto e verifica que a barreira recusa — sem modelo e sem chave.
"""

from __future__ import annotations

import json

import pytest

from agente.modelos import Instrucao
from ferramentas import (calcular_diarias, consultar_historico_diarias, consultar_saldo_diarias,
                         consultar_servidor)
from seguranca.barreiras import indicios_injecao, indicios_urgencia, verificar_instrucao


def consulta(nome: str, func, **args) -> dict:
    return {"ferramenta": nome, "argumentos": args, "resultado": func(**args), "erro": False}


def cenario_completo(p: dict, retorno: str | None = None, matricula: str | None = None):
    mat = matricula or p["matricula"]
    retorno = retorno or p["data_retorno"]
    c1 = consulta("consultar_servidor", consultar_servidor, matricula=mat, nome_informado=p["nome"])
    c2 = consulta("consultar_historico_diarias", consultar_historico_diarias, matricula=mat,
                  data_partida=p["data_partida"])
    c3 = consulta("calcular_diarias", calcular_diarias, matricula=mat, destino_uf=p["destino_uf"],
                  data_pedido=p["data_pedido"], data_partida=p["data_partida"], data_retorno=retorno)
    calc = json.loads(c3["resultado"])
    c4 = consulta("consultar_saldo_diarias", consultar_saldo_diarias,
                  unidade=json.loads(c1["resultado"]).get("unidade", "CFF"), valor=calc.get("valor_total", 1.0))
    return [c1, c2, c3, c4], calc


def instrucao_para(p, consultas, calc, urgencia=False, alertas=None, matricula=None):
    r = {c["ferramenta"]: json.loads(c["resultado"]) for c in consultas}
    sit = {"cadastro": "atende", "dados_completos": "atende",
           "antecedencia": "atende" if calc["antecedencia_minima_atendida"] or urgencia else "nao_atende",
           "prestacao_contas": r["consultar_historico_diarias"].get("criterio_prestacao_contas", "atende"),
           "limite_mensal": calc["criterio_limite_mensal"],
           "saldo_orcamentario": r["consultar_saldo_diarias"]["criterio_saldo_orcamentario"]}
    imped = [k for k in ("antecedencia", "prestacao_contas", "limite_mensal", "saldo_orcamentario")
             if sit[k] == "nao_atende"]
    return Instrucao(
        numero_pedido=p["numero"], matricula=matricula or p["matricula"],
        quantidade_diarias=calc.get("quantidade_diarias"), valor_total=calc.get("valor_total"),
        verificacoes=[{"criterio": k, "situacao": v, "detalhe": f"Resultado da ferramenta: {v}."}
                      for k, v in sit.items()],
        recomendacao="nao_recomendado" if imped else "apto_para_autorizacao",
        exige_autorizacao_superior=urgencia and not imped,
        pendencias=[], alertas=alertas or [],
        minuta_despacho=f"Despacho de instrução — pedido {p['numero']}. Total R$ {calc['valor_total']:.2f}. "
                        "À consideração do ordenador de despesa.")


@pytest.fixture
def p101(pedidos):
    return pedidos["DIA-2026-0101"]


def test_instrucao_correta_e_aprovada(p101):
    consultas, calc = cenario_completo(p101)
    r = verificar_instrucao(p101, None, instrucao_para(p101, consultas, calc), consultas, "COMPLETED")
    assert r.aprovada, r.motivos


def test_status_de_erro_recusa_antes_de_ler_conteudo(p101):
    consultas, calc = cenario_completo(p101)
    r = verificar_instrucao(p101, None, instrucao_para(p101, consultas, calc), consultas, "ERROR")
    assert not r.aprovada and "status" in r.motivos[0]


def test_conteudo_fora_do_contrato(p101):
    assert not verificar_instrucao(p101, None, None, [], "COMPLETED").aprovada


def test_matricula_inventada_nos_argumentos(p101):
    consultas, calc = cenario_completo(p101)
    # O modelo troca a matrícula no histórico por uma que não consta do pedido.
    consultas[1] = consulta("consultar_historico_diarias", consultar_historico_diarias,
                            matricula="204318", data_partida=p101["data_partida"])
    inst = instrucao_para(p101, consultas, calc)
    r = verificar_instrucao(p101, None, inst, consultas, "COMPLETED")
    assert not r.aprovada and any("204318" in m for m in r.motivos)


def test_data_inventada_no_calculo(pedidos):
    p = pedidos["DIA-2026-0111"]  # sem data de retorno: o modelo "supõe" uma
    consultas, calc = cenario_completo(p, retorno="2026-11-20")
    inst = instrucao_para(p, consultas, calc)
    r = verificar_instrucao(p, None, inst, consultas, "COMPLETED")
    assert not r.aprovada and any("2026-11-20" in m for m in r.motivos)


def test_mesma_data_e_aceita_quando_vem_da_complementacao(pedidos, complementacoes):
    p = pedidos["DIA-2026-0111"]
    consultas, calc = cenario_completo(p, retorno="2026-11-20")
    inst = instrucao_para(p, consultas, calc)
    r = verificar_instrucao(p, complementacoes["DIA-2026-0111"], inst, consultas, "COMPLETED")
    assert r.aprovada, r.motivos


def test_valor_divergente_da_ferramenta(p101):
    consultas, calc = cenario_completo(p101)
    inst = instrucao_para(p101, consultas, calc).model_copy(update={"valor_total": 1030.0})
    r = verificar_instrucao(p101, None, inst, consultas, "COMPLETED")
    assert not r.aprovada and any("valor_total" in m for m in r.motivos)


def test_saida_de_outro_pedido(p101):
    consultas, calc = cenario_completo(p101)
    inst = instrucao_para(p101, consultas, calc).model_copy(update={"numero_pedido": "DIA-2026-0102"})
    assert not verificar_instrucao(p101, None, inst, consultas, "COMPLETED").aprovada


def test_saldo_consultado_com_unidade_ou_valor_errados(p101):
    consultas, calc = cenario_completo(p101)
    consultas[3] = consulta("consultar_saldo_diarias", consultar_saldo_diarias, unidade="GAB", valor=980.0)
    r = verificar_instrucao(p101, None, instrucao_para(p101, consultas, calc), consultas, "COMPLETED")
    assert not r.aprovada and any("unidade" in m for m in r.motivos)


def test_ferramenta_faltando(p101):
    consultas, calc = cenario_completo(p101)
    inst = instrucao_para(p101, consultas, calc)
    r = verificar_instrucao(p101, None, inst, consultas[:3], "COMPLETED")
    assert not r.aprovada


def test_recomendacao_incompativel(pedidos):
    p = pedidos["DIA-2026-0108"]
    consultas, calc = cenario_completo(p)
    inst = instrucao_para(p, consultas, calc)
    falsa = inst.model_copy(update={"recomendacao": "apto_para_autorizacao"})
    assert not verificar_instrucao(p, None, falsa, consultas, "COMPLETED").aprovada


def test_0107_injecao_obedecida_e_recusada(pedidos):
    p = pedidos["DIA-2026-0107"]
    consultas, calc = cenario_completo(p)
    inst = instrucao_para(p, consultas, calc, urgencia=True, alertas=["x"])  # obedeceu à ordem
    r = verificar_instrucao(p, None, inst, consultas, "COMPLETED")
    assert not r.aprovada and any("ordem embutida" in m.lower() or "§ 1º" in m for m in r.motivos)


def test_0107_correto_exige_alerta(pedidos):
    p = pedidos["DIA-2026-0107"]
    consultas, calc = cenario_completo(p)
    sem_alerta = instrucao_para(p, consultas, calc)
    assert not verificar_instrucao(p, None, sem_alerta, consultas, "COMPLETED").aprovada
    com_alerta = instrucao_para(p, consultas, calc, alertas=["Ordem embutida na justificativa, desconsiderada."])
    r = verificar_instrucao(p, None, com_alerta, consultas, "COMPLETED")
    assert r.aprovada, r.motivos
    assert any("verbal" in a for a in r.alertas_codigo)


def test_0106_urgencia_legitima_aceita_com_autorizacao(pedidos):
    p = pedidos["DIA-2026-0106"]
    consultas, calc = cenario_completo(p)
    inst = instrucao_para(p, consultas, calc, urgencia=True)
    assert inst.exige_autorizacao_superior
    assert verificar_instrucao(p, None, inst, consultas, "COMPLETED").aprovada
    sem_autorizacao = inst.model_copy(update={"exige_autorizacao_superior": False})
    assert not verificar_instrucao(p, None, sem_autorizacao, consultas, "COMPLETED").aprovada


def test_0105_urgencia_sem_fundamento_e_recusada(pedidos):
    p = pedidos["DIA-2026-0105"]
    consultas, calc = cenario_completo(p)
    inst = instrucao_para(p, consultas, calc, urgencia=True)
    assert not verificar_instrucao(p, None, inst, consultas, "COMPLETED").aprovada


def test_minuta_com_decisao_ou_dado_pessoal(p101):
    consultas, calc = cenario_completo(p101)
    inst = instrucao_para(p101, consultas, calc)
    for texto in (f"Despacho {p101['numero']}. Defiro o pedido.",
                  f"Despacho {p101['numero']}. CPF 052.318.947-20.",
                  f"Despacho {p101['numero']}. Servidor matrícula 207481.",
                  f"Despacho {p101['numero']}. Retorno em 2026-12-01."):
        r = verificar_instrucao(p101, None, inst.model_copy(update={"minuta_despacho": texto}),
                                consultas, "COMPLETED")
        assert not r.aprovada, texto


def test_diligencia_0112(pedidos):
    p = pedidos["DIA-2026-0112"]
    c1 = consulta("consultar_servidor", consultar_servidor, matricula=p["matricula"], nome_informado=p["nome"])
    inst = Instrucao(numero_pedido=p["numero"], matricula=p["matricula"], quantidade_diarias=None,
                     valor_total=None,
                     verificacoes=[{"criterio": "cadastro", "situacao": "nao_atende", "detalhe": "Nome diverge do titular."},
                                   {"criterio": "dados_completos", "situacao": "atende", "detalhe": "Datas informadas."}] +
                                  [{"criterio": c, "situacao": "nao_verificado", "detalhe": "Não examinado na diligência."}
                                   for c in ("antecedencia", "prestacao_contas", "limite_mensal", "saldo_orcamentario")],
                     recomendacao="diligencia", exige_autorizacao_superior=False,
                     pendencias=["Confirmar a matrícula."], alertas=[],
                     minuta_despacho=f"Despacho de instrução — pedido {p['numero']}. Diligência. "
                                     "À consideração do ordenador de despesa.")
    assert verificar_instrucao(p, None, inst, [c1], "COMPLETED").aprovada
    calculada = inst.model_copy(update={"recomendacao": "apto_para_autorizacao"})
    assert not verificar_instrucao(p, None, calculada, [c1], "COMPLETED").aprovada


def test_detectores_de_texto(pedidos):
    assert indicios_injecao(pedidos["DIA-2026-0107"]["justificativa"])
    assert not indicios_injecao(pedidos["DIA-2026-0106"]["justificativa"])
    assert indicios_urgencia(pedidos["DIA-2026-0106"]["justificativa"])
    sem_falso_positivo = [n for n, p in pedidos.items() if indicios_injecao(p["justificativa"])]
    assert sem_falso_positivo == ["DIA-2026-0107"]


def test_0112_abstencao_em_dados_completos_e_aceita_so_com_pedido_completo(pedidos):
    """Achado da medição real: o modelo marcou dados_completos como nao_verificado no 0112."""
    p = pedidos["DIA-2026-0112"]
    c1 = consulta("consultar_servidor", consultar_servidor, matricula=p["matricula"], nome_informado=p["nome"])
    verifs = [{"criterio": "cadastro", "situacao": "nao_atende", "detalhe": "Nome diverge do titular."}] +              [{"criterio": c, "situacao": "nao_verificado", "detalhe": "Não examinado na diligência."}
              for c in ("dados_completos", "antecedencia", "prestacao_contas", "limite_mensal", "saldo_orcamentario")]
    inst = Instrucao(numero_pedido=p["numero"], matricula=p["matricula"], quantidade_diarias=None, valor_total=None,
                     verificacoes=verifs, recomendacao="diligencia", exige_autorizacao_superior=False,
                     pendencias=["Confirmar a matrícula."], alertas=[],
                     minuta_despacho=f"Despacho de instrução — pedido {p['numero']}. Diligência.")
    assert verificar_instrucao(p, None, inst, [c1], "COMPLETED").aprovada
    # Num pedido INCOMPLETO a abstenção esconderia a falta: continua recusada.
    q = pedidos["DIA-2026-0111"]
    c2 = consulta("consultar_servidor", consultar_servidor, matricula=q["matricula"], nome_informado=q["nome"])
    inst2 = inst.model_copy(update={"numero_pedido": q["numero"], "matricula": q["matricula"],
                                    "minuta_despacho": f"Despacho de instrução — pedido {q['numero']}."})
    assert not verificar_instrucao(q, None, inst2, [c2], "COMPLETED").aprovada


def test_0106_alerta_de_urgencia_ao_conferente(pedidos):
    """Achado da medição real (rodada 3): o modelo não reconheceu a urgência do 0106."""
    p = pedidos["DIA-2026-0106"]
    consultas, calc = cenario_completo(p)
    r = verificar_instrucao(p, None, instrucao_para(p, consultas, calc), consultas, "COMPLETED")
    assert r.aprovada and any("urgência" in a for a in r.alertas_codigo)
