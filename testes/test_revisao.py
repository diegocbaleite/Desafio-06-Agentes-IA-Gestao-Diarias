"""Regressões encontradas na revisão do fluxo e da instalação local."""

import json
import sqlite3

import pytest

from ferramentas import calcular_diarias, consultar_historico_diarias, consultar_saldo_diarias
from avaliacao import execucao
from avaliacao.medir_desempenho import resumo_config
from memoria import persistencia
from seguranca.barreiras import verificar_instrucao
from test_barreira import cenario_completo, consulta, instrucao_para


@pytest.mark.parametrize("campo", ["quantidade_diarias", "valor_total"])
def test_barreira_recusa_nan_mesmo_sem_validacao_pydantic(pedidos, campo):
    pedido = pedidos["DIA-2026-0101"]
    consultas, calculo = cenario_completo(pedido)
    instrucao = instrucao_para(pedido, consultas, calculo).model_copy(update={campo: float("nan")})
    assert not verificar_instrucao(pedido, None, instrucao, consultas, "COMPLETED").aprovada


@pytest.mark.parametrize("ferramenta", ["historico", "calculo"])
def test_complementacao_nao_mistura_consultas_de_duas_matriculas(pedidos, complementacoes, ferramenta):
    pedido = pedidos["DIA-2026-0112"]
    consultas, calculo = cenario_completo(pedido, matricula="207418")
    if ferramenta == "historico":
        consultas[1] = consulta("consultar_historico_diarias", consultar_historico_diarias,
                                matricula=pedido["matricula"], data_partida=pedido["data_partida"])
    else:
        consultas[2] = consulta("calcular_diarias", calcular_diarias, matricula=pedido["matricula"],
                                destino_uf=pedido["destino_uf"], data_pedido=pedido["data_pedido"],
                                data_partida=pedido["data_partida"], data_retorno=pedido["data_retorno"])
        calculo = json.loads(consultas[2]["resultado"])
        consultas[3] = consulta("consultar_saldo_diarias", consultar_saldo_diarias,
                                unidade="CUC", valor=calculo["valor_total"])
    instrucao = instrucao_para(pedido, consultas, calculo, matricula="207418")
    resultado = verificar_instrucao(pedido, complementacoes[pedido["numero"]], instrucao,
                                    consultas, "COMPLETED")
    assert not resultado.aprovada


def test_saldo_antes_do_calculo_nao_e_aceito_so_porque_valor_coincide(pedidos):
    pedido = pedidos["DIA-2026-0101"]
    consultas, calculo = cenario_completo(pedido)
    instrucao = instrucao_para(pedido, consultas, calculo)
    consultas = [consultas[0], consultas[1], consultas[3], consultas[2]]
    assert not verificar_instrucao(pedido, None, instrucao, consultas, "COMPLETED").aprovada


@pytest.mark.parametrize("valor", [float("nan"), float("inf"), float("-inf"), "NaN"])
def test_orcamento_recusa_valor_nao_finito_sem_excecao(valor):
    assert json.loads(consultar_saldo_diarias("CFF", valor))["situacao"] == "argumento_invalido"


def test_consulta_administrativa_fecha_a_conexao_sqlite(tmp_path, monkeypatch):
    conectar = sqlite3.connect
    conexoes = []

    def rastrear(*args, **kwargs):
        conexao = conectar(*args, **kwargs)
        conexoes.append(conexao)
        return conexao

    monkeypatch.setattr(persistencia.sqlite3, "connect", rastrear)
    assert persistencia.listar("analises", tmp_path / "administrativo.db") == []
    try:
        with pytest.raises(sqlite3.ProgrammingError):
            conexoes[0].execute("SELECT 1")
    finally:
        for conexao in conexoes:
            conexao.close()


def test_simulacao_nao_reutiliza_banco_da_medicao_real(tmp_path, monkeypatch):
    monkeypatch.setattr(execucao.config, "BANCOS", tmp_path)
    real = execucao.banco_avaliacao("casos.db", False)
    simulado = execucao.banco_avaliacao("casos.db", True)
    real.write_bytes(b"evidencia da medicao real")
    simulado.write_bytes(b"somente simulacao")
    assert real.read_bytes() == b"evidencia da medicao real"
    assert simulado.parent == tmp_path / "simulador"


def test_bloqueio_sem_chave_preserva_medicao_anterior(tmp_path, monkeypatch):
    monkeypatch.setattr(execucao.config, "RESULTADOS", tmp_path)
    monkeypatch.setattr(execucao.config, "chave_configurada", lambda: False)
    medicao = tmp_path / "casos.json"
    anterior = '{"modo": "api_real", "rodadas": [{"rodada": 1}]}'
    medicao.write_text(anterior, encoding="utf-8")
    assert execucao.bloqueio_sem_chave(False, "casos.json", "Revisão")
    assert medicao.read_text(encoding="utf-8") == anterior
    bloqueio = json.loads((tmp_path / "bloqueios" / "casos.json").read_text(encoding="utf-8"))
    assert bloqueio["situacao"] == "nao_executado"


def test_custo_do_pedido_inicial_nao_inclui_reenvio_da_complementacao():
    resumo = {"corretos": 2, "recusados_pela_barreira": 0, "erros_de_execucao": 0,
              "instruidos_errados_entregues": 0, "chamadas_modelo": 4,
              "max_ferramentas_simultaneas": 1, "custo_total_usd": 0.01, "tempo_total_s": 1}
    casos = [{"caso": "DIA-2026-0101", "situacao": "aprovada", "obtido": "apto_para_autorizacao",
              "metricas": {"entrada_por_chamada": [100, 110]}},
             {"caso": "DIA-2026-0111 (complementação)", "situacao": "aprovada",
              "obtido": "apto_para_autorizacao", "metricas": {"entrada_por_chamada": [2000, 2100]}}]
    resultado = resumo_config({"rodadas": [{"resumo": resumo, "casos": casos}]})
    assert resultado["entrada_media_pedido_regular_tokens"] == 210
    assert resultado["primeira_chamada_media_tokens"] == 100
    assert resultado["incremento_medio_por_passo_tokens"] == 10
