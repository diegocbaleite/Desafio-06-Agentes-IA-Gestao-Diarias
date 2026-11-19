"""Etapa 2: ferramentas testadas sem agente e sem chave, com os casos dos próprios pedidos."""

from __future__ import annotations

import inspect
import json

import pytest

from conftest import ESPERADO
from ferramentas import (FERRAMENTAS, acervo, calcular_diarias, consultar_historico_diarias,
                         consultar_saldo_diarias, consultar_servidor)


def j(texto: str) -> dict:
    return json.loads(texto)


# ------------------------------------------------------------------ casos obrigatórios


def test_0112_matricula_de_outro_servidor():
    r = j(consultar_servidor("207481", "Carla Regina Souza"))
    assert r["situacao"] == "localizado"
    assert r["conferencia_nome"] == "diverge"
    assert r["criterio_cadastro"] == "nao_atende"
    # Minimização: o nome do verdadeiro titular da matrícula não é devolvido ao modelo.
    assert "Rafael" not in json.dumps(r, ensure_ascii=False)
    assert "grupo_diaria" not in r and "unidade" not in r


def test_0112_matricula_corrigida():
    r = j(consultar_servidor("207418", "Carla Regina Souza"))
    assert (r["criterio_cadastro"], r["grupo_diaria"], r["unidade"]) == ("atende", "C", "CUC")


def test_0108_prestacao_vencida():
    r = j(consultar_historico_diarias("203648", "2026-11-03"))
    assert r["criterio_prestacao_contas"] == "nao_atende"
    vencida = r["prestacoes_pendentes"][0]
    assert (vencida["pedido"], vencida["prazo_final"], vencida["situacao"]) == \
        ("DIA-2026-0023", "2026-09-25", "vencida")


def test_0102_pendente_no_prazo_nao_impede():
    r = j(consultar_historico_diarias("205882", "2026-11-09"))
    assert r["prestacoes_pendentes"][0]["situacao"] == "no_prazo"
    assert r["prestacoes_pendentes"][0]["prazo_final"] == "2026-10-13"
    assert r["criterio_prestacao_contas"] == "atende"


def test_0103_meia_diaria():
    r = j(calcular_diarias("203156", "MT", "2026-10-07", "2026-11-05", "2026-11-05"))
    assert (r["pernoites"], r["quantidade_diarias"], r["valor_total"]) == (0, 0.5, 140.0)


def test_0110_saldo_insuficiente():
    calc = j(calcular_diarias("205507", "RO", "2026-10-02", "2026-11-10", "2026-11-14"))
    assert (calc["classe_destino"], calc["valor_total"]) == ("outra_uf", 1800.0)
    r = j(consultar_saldo_diarias("CRH", calc["valor_total"]))
    assert (r["saldo_disponivel"], r["criterio_saldo_orcamentario"]) == (640.0, "nao_atende")


# ------------------------------------------------------------------ todos os pedidos


@pytest.mark.parametrize("numero", [n for n, e in ESPERADO.items() if e[1] is not None])
def test_calculo_de_todos_os_pedidos(pedidos, numero):
    p = pedidos[numero]
    r = j(calcular_diarias(p["matricula"], p["destino_uf"], p["data_pedido"], p["data_partida"],
                           p["data_retorno"]))
    assert (r["quantidade_diarias"], r["valor_total"]) == ESPERADO[numero][1:3]


def test_antecedencia_0105_0106_0107(pedidos):
    for numero, dias in (("DIA-2026-0105", 5), ("DIA-2026-0106", 1), ("DIA-2026-0107", 5)):
        p = pedidos[numero]
        r = j(calcular_diarias(p["matricula"], p["destino_uf"], p["data_pedido"], p["data_partida"],
                               p["data_retorno"]))
        assert r["antecedencia_dias"] == dias and r["antecedencia_minima_atendida"] is False


def test_0109_limite_mensal():
    r = j(calcular_diarias("208114", "MT", "2026-10-06", "2026-11-23", "2026-11-26"))
    assert (r["diarias_ja_concedidas_no_mes"], r["total_no_mes_com_pedido"]) == (8.0, 11.5)
    assert r["criterio_limite_mensal"] == "nao_atende"


def test_0104_distrito_federal_grupo_a():
    r = j(calcular_diarias("200941", "DF", "2026-10-06", "2026-11-16", "2026-11-18"))
    assert (r["classe_destino"], r["valor_unitario"], r["valor_total"]) == ("distrito_federal", 600.0, 1500.0)


# ------------------------------------------------------------------ não encontrado x impedimento x erro


def test_nao_localizado_difere_de_impedimento():
    r = j(consultar_servidor("999999", "Fulano"))
    assert r["situacao"] == "nao_localizado" and r["criterio_cadastro"] == "nao_atende"
    h = j(consultar_historico_diarias("209999", "2026-11-01"))
    assert h["situacao"] == "consultado" and h["prestacoes_pendentes"] == []  # sem registros não é erro


@pytest.mark.parametrize("args", [("20431", "Ana"), ("2043170", "Ana"), ("", "Ana"), ("abc123", "Ana")])
def test_matricula_invalida(args):
    assert j(consultar_servidor(*args))["situacao"] == "argumento_invalido"


def test_datas_invalidas_e_ausentes():
    assert j(calcular_diarias("204317", "MT", "2026-10-08", "2026-11-09", ""))["situacao"] == "dados_incompletos"
    assert j(calcular_diarias("204317", "MT", "08/10/2026", "2026-11-09", "2026-11-12"))["situacao"] == "dados_incompletos"
    assert j(calcular_diarias("204317", "MT", "2026-10-08", "2026-11-12", "2026-11-09"))["situacao"] == "argumento_invalido"
    assert j(calcular_diarias("204317", "M", "2026-10-08", "2026-11-09", "2026-11-12"))["situacao"] == "argumento_invalido"


def test_saldo_unidade_inexistente_e_valor_invalido():
    assert j(consultar_saldo_diarias("XYZ", 100.0))["situacao"] == "nao_localizado"
    assert j(consultar_saldo_diarias("CFF", -5))["situacao"] == "argumento_invalido"
    assert j(consultar_saldo_diarias("cff ", 980.0))["criterio_saldo_orcamentario"] == "atende"


def test_saldo_limite_exato_em_decimal():
    # 640,00 contra 640,00: suficiente (saldo >= valor), sem erro de ponto flutuante.
    assert j(consultar_saldo_diarias("CRH", 640.00))["criterio_saldo_orcamentario"] == "atende"
    assert j(consultar_saldo_diarias("CRH", 640.01))["criterio_saldo_orcamentario"] == "nao_atende"


# ------------------------------------------------------------------ minimização e documentação


def test_nenhuma_ferramenta_devolve_cpf_ou_email():
    for s in acervo.servidores().values():
        saida = consultar_servidor(s["matricula"], s["nome"])
        assert s["cpf"] not in saida and s["email"] not in saida and "@" not in saida
        saida_h = consultar_historico_diarias(s["matricula"], "2026-11-01")
        assert s["cpf"] not in saida_h


@pytest.mark.parametrize("funcao", FERRAMENTAS, ids=lambda f: f.__name__)
def test_docstring_e_tipos(funcao):
    doc = inspect.getdoc(funcao)
    for trecho in ("Quando usar", "Devolve", "Erros"):
        assert trecho in doc, f"docstring de {funcao.__name__} sem '{trecho}'"
    assert "Argumentos" in doc or "`unidade`" in doc
    assinatura = inspect.signature(funcao)
    assert all(p.annotation is not inspect.Parameter.empty for p in assinatura.parameters.values())


def test_rastreabilidade_fonte_e_argumentos():
    for saida in (consultar_servidor("204317", "Ana Paula Figueiredo"),
                  consultar_historico_diarias("204317", "2026-11-09"),
                  calcular_diarias("204317", "MT", "2026-10-08", "2026-11-09", "2026-11-12"),
                  consultar_saldo_diarias("CFF", 980.0)):
        r = j(saida)
        assert r["fonte"] and r["regra"] and r["argumentos"]
