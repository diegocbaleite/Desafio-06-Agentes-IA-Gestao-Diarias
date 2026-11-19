"""Pipeline real do Agno (ferramentas, output_schema, pre_hooks, SqliteDb, barreira) contra o
simulador local da API. Não mede o modelo: verifica que o encaixe funciona e que as falhas
provocadas são recusadas. Nenhuma chave é usada.
"""

from __future__ import annotations

import pytest

from agente.agente_diarias import construir_agente, instruir
from conftest import ESPERADO, ESPERADO_COMPLEMENTACAO
from memoria import verificacao
from simulador.servidor_openai_simulado import SimuladorOpenAI

CPF_0104 = "052.318.947-20"


def agente(sim, tmp_path, **kw):
    return construir_agente(base_url=sim.url, api_key="simulador",
                            db_file=kw.pop("db_file", tmp_path / "agente.db"), **kw)


def conferir(resultado, esperado):
    rec, qtd, valor, autorizacao = esperado
    inst = resultado.instrucao
    assert resultado.aprovada, resultado.motivos_recusa
    assert (inst["recomendacao"], inst["quantidade_diarias"], inst["valor_total"],
            inst["exige_autorizacao_superior"]) == (rec, qtd, valor, autorizacao)


def test_doze_pedidos_e_duas_complementacoes(tmp_path, pedidos, complementacoes):
    with SimuladorOpenAI() as sim:
        ag = agente(sim, tmp_path)
        for numero, esperado in ESPERADO.items():
            r = instruir(ag, pedidos[numero])
            conferir(r, esperado)
            assert (r.session_id, r.user_id) == (numero, pedidos[numero]["matricula"])
        for numero, esperado in ESPERADO_COMPLEMENTACAO.items():
            r = instruir(ag, pedidos[numero], complementacoes[numero])
            conferir(r, esperado)
            assert r.session_id == numero
            # Só as chamadas desta execução: o histórico reenviado não conta como passo.
            assert r.metricas["chamadas_modelo"] == 5
            # A complementação continua na sessão original, sob o user_id com que ela nasceu.
            assert r.user_id == pedidos[numero]["matricula"]
    ids = {s["session_id"]: s["user_id"] for s in verificacao.sessoes(tmp_path / "agente.db")}
    assert ids["DIA-2026-0112"] == "207481" and ids["DIA-2026-0101"] == "204317"
    assert len(ids) == 12  # uma sessão por pedido, complementações incluídas na mesma


def test_progresso_anunciado_e_ordem_das_consultas(tmp_path, pedidos):
    anunciadas = []
    with SimuladorOpenAI() as sim:
        r = instruir(agente(sim, tmp_path), pedidos["DIA-2026-0101"],
                     ao_chamar_ferramenta=lambda nome, args: anunciadas.append(nome))
    assert anunciadas == ["consultar_servidor", "consultar_historico_diarias", "calcular_diarias",
                          "consultar_saldo_diarias"]
    assert [c["ferramenta"] for c in r.consultas] == anunciadas
    assert r.metricas["max_ferramentas_simultaneas"] == 1  # paralelas desligadas


def test_0104_cpf_nao_chega_ao_modelo_nem_ao_banco(tmp_path, pedidos):
    with SimuladorOpenAI() as sim:
        r = instruir(agente(sim, tmp_path), pedidos["DIA-2026-0104"])
        assert r.aprovada
        enviados = "\n".join(sim.requisicoes)
    for dado in (CPF_0104, "98765-4", "1234-5"):
        assert dado not in enviados
    assert not verificacao.ocorrencias(tmp_path / "agente.db", [CPF_0104, "98765-4", "agência 1234-5"])
    # Identificadores administrativos seguem legíveis no que foi enviado e gravado.
    assert "DIA-2026-0104" in enviados and "200941" in enviados and "2026-11-16" in enviados
    assert any("mascarado" in a.lower() for a in r.alertas_aplicacao)


def test_guardrail_sozinho_protege_modelo_e_banco(tmp_path, pedidos):
    """Defesa em profundidade: chamando o agente direto, sem a máscara da aplicação."""
    p = pedidos["DIA-2026-0104"]
    with SimuladorOpenAI() as sim:
        ag = agente(sim, tmp_path)
        ag.run(f"numero: {p['numero']}\nmatricula: {p['matricula']}\n{p['justificativa']}",
               session_id=p["numero"], user_id=p["matricula"])
        enviados = "\n".join(sim.requisicoes)
    assert CPF_0104 not in enviados and "98765-4" not in enviados
    assert not verificacao.ocorrencias(tmp_path / "agente.db", [CPF_0104, "98765-4"])
    assert p["matricula"] in enviados


@pytest.mark.parametrize("modo,numero", [
    ("matricula_inventada", "DIA-2026-0101"),
    ("valor_divergente", "DIA-2026-0103"),
    ("injecao_obedecida", "DIA-2026-0107"),
    ("data_inventada", "DIA-2026-0111"),
    ("pedido_trocado", "DIA-2026-0105"),
])
def test_falhas_do_modelo_sao_recusadas(tmp_path, pedidos, modo, numero):
    with SimuladorOpenAI(modo=modo) as sim:
        r = instruir(agente(sim, tmp_path), pedidos[numero])
    assert r.situacao == "recusada" and r.instrucao is None
    assert r.mensagem.startswith("Não foi possível")
    assert r.motivos_recusa


def test_saldo_antecipado_em_paralelo_e_recusado(tmp_path, pedidos):
    with SimuladorOpenAI(modo="saldo_antecipado") as sim:
        r = instruir(agente(sim, tmp_path, paralelas=True), pedidos["DIA-2026-0101"])
    assert r.situacao == "recusada"
    assert any("ordem das consultas" in m or "unidade" in m or "valor" in m for m in r.motivos_recusa)


@pytest.mark.parametrize("modo", ["erro_api", "json_invalido"])
def test_erro_da_api_ou_resposta_invalida(tmp_path, pedidos, modo):
    with SimuladorOpenAI(modo=modo) as sim:
        r = instruir(agente(sim, tmp_path), pedidos["DIA-2026-0101"])
    assert r.situacao in ("erro_execucao", "recusada") and r.instrucao is None
    assert "Simulated API error" not in str(r.to_dict())  # mensagem da API nunca vai à tela


def test_sem_memoria_complementacao_nao_e_aplicada(tmp_path, pedidos, complementacoes):
    with SimuladorOpenAI() as sim:
        ag = agente(sim, tmp_path, memoria="sem_memoria")
        instruir(ag, pedidos["DIA-2026-0111"])
        r = instruir(ag, pedidos["DIA-2026-0111"], complementacoes["DIA-2026-0111"])
    assert r.situacao == "recusada"  # sem o pedido, a instrução não se sustenta na barreira


def test_associacao_incorreta_de_sessao_e_detectada(tmp_path, pedidos, complementacoes):
    """Falha 4 provocada: a complementação do 0112 enviada com o user_id corrigido.

    A sessão foi gravada sob 207481; com user_id=207418 o Agno não a encontra (a busca é
    filtrada por user_id), o histórico não é recuperado e a barreira recusa a instrução.
    """
    with SimuladorOpenAI() as sim:
        ag = agente(sim, tmp_path)
        instruir(ag, pedidos["DIA-2026-0112"])
        r = instruir(ag, pedidos["DIA-2026-0112"], complementacoes["DIA-2026-0112"], user_id="207418")
    assert r.situacao == "recusada"
