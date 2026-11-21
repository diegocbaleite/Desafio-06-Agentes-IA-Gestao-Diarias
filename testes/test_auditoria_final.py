"""Regressões dos achados F1–F5: somente dados sintéticos, bancos temporários e API local."""

import hashlib
import json
import logging
from pathlib import Path

import pytest
from agno.db.schemas.memory import UserMemory
from agno.run.agent import RunOutput
from agno.session import AgentSession
from streamlit.testing.v1 import AppTest

import config
from agente.agente_diarias import ResultadoInstrucao, construir_agente, instruir
from avaliacao import comparar_gabarito as cg
from ferramentas import acervo, calcular_diarias
from memoria import eliminacao, persistencia, verificacao
from memoria.banco_protegido import SqliteDbProtegido
from seguranca import filtro_pii
from simulador.servidor_openai_simulado import SimuladorOpenAI, _Politica

CARLA = ("207418", "Carla Regina Souza")
MARCADOR = "privacidade-auditoria@example.invalid"


def agente(sim, tmp_path, **kwargs):
    return construir_agente(db_file=tmp_path / "agente.db", base_url=sim.url,
                            api_key="simulador", **kwargs)


def test_titular_digitado_errado_nao_pode_eliminar_nenhum_registro(tmp_path, pedidos):
    with SimuladorOpenAI() as sim:
        ag = agente(sim, tmp_path)
        assert instruir(ag, pedidos["DIA-2026-0112"]).aprovada
        terceiro = {**pedidos["DIA-2026-0101"], "numero": "DIA-2026-0999", "matricula": "207481",
                    "nome": acervo.servidores()["207481"]["nome"]}
        assert instruir(ag, terceiro).aprovada
    db = tmp_path / "agente.db"
    antes = hashlib.sha256(db.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="cadastro funcional"):
        eliminacao.eliminar(db, "207481", CARLA[1], sessoes_confirmadas=[terceiro["numero"]])
    assert hashlib.sha256(db.read_bytes()).hexdigest() == antes
    assert len(verificacao.sessoes(db)) == 2


def test_mesmo_user_id_nao_prova_titularidade_da_sessao_ou_memoria(tmp_path, pedidos):
    with SimuladorOpenAI() as sim:
        ag = agente(sim, tmp_path, memoria="historico_usuario")
        assert instruir(ag, pedidos["DIA-2026-0112"]).aprovada
    db = tmp_path / "agente.db"
    nome_real = acervo.servidores()["207481"]["nome"]
    loc = eliminacao.localizar(db, "207481", nome_real)
    assert not loc.sessoes_do_titular and loc.sessoes_sem_vinculo
    assert not loc.memorias_do_titular and loc.memorias_sem_vinculo
    ev = eliminacao.eliminar(db, "207481", nome_real, sessoes_confirmadas=["DIA-2026-0112"])
    assert not ev["nada_restou"] and ev["nao_apagadas"]
    assert [s["session_id"] for s in verificacao.sessoes(db)] == ["DIA-2026-0112"]
    assert verificacao.contar_registros(db)["agno_memories"] > 0


def test_exclusao_do_titular_correto_preserva_sessao_alheia_sob_mesmo_user_id(
        tmp_path, pedidos, monkeypatch):
    nome_real = acervo.servidores()["207481"]["nome"]
    proprio = {**pedidos["DIA-2026-0101"], "numero": "DIA-2026-0999",
               "matricula": "207481", "nome": nome_real}
    originais = acervo.pedidos()
    monkeypatch.setattr(acervo, "pedidos", lambda: originais + [proprio])
    with SimuladorOpenAI() as sim:
        ag = agente(sim, tmp_path)
        assert instruir(ag, pedidos["DIA-2026-0112"]).aprovada
        assert instruir(ag, proprio).aprovada
    ev = eliminacao.eliminar(tmp_path / "agente.db", "207481", nome_real)
    assert ev["antes"]["sessoes_do_titular"] == [proprio["numero"]]
    assert [s["session_id"] for s in verificacao.sessoes(tmp_path / "agente.db")] == ["DIA-2026-0112"]
    assert not ev["nada_restou"] and ev["sessoes_alheias_apagadas_indevidamente"] == []


def test_memoria_que_so_menciona_titular_nao_e_apagada_mesmo_confirmada(tmp_path):
    db = tmp_path / "agente.db"
    banco = SqliteDbProtegido(db_file=str(db))
    banco.upsert_user_memory(UserMemory(memory=f"Pedido DIA-2026-0101 menciona {CARLA[1]}",
                                        user_id="204317", memory_id="terceiro"))
    ev = eliminacao.eliminar(db, *CARLA, memorias_confirmadas=["terceiro"])
    assert not ev["nada_restou"]
    assert ev["nao_apagadas"][0]["motivo"] == "vínculo com o titular não verificado"
    assert banco.get_user_memory("terceiro") is not None


@pytest.mark.parametrize("numero,rascunho", [
    ("DIA-2026-0101", "Recomendo 99 diárias, total R$ 9.999,99."),
    ("DIA-2026-0108", "Todos os requisitos atendidos; recomendo apto para autorização."),
])
def test_minuta_entregue_usa_campos_verificados_e_nao_afirmacao_falsa(
        tmp_path, pedidos, monkeypatch, numero, rascunho):
    original = _Politica._instrucao

    def adulterar(self, pedido, resultados):
        obj = original(self, pedido, resultados)
        obj["minuta_despacho"] = f"Despacho de instrução — pedido {numero}. {rascunho}"
        return obj

    monkeypatch.setattr(_Politica, "_instrucao", adulterar)
    with SimuladorOpenAI() as sim:
        r = instruir(agente(sim, tmp_path), pedidos[numero])
    assert r.aprovada, r.motivos_recusa
    minuta = r.instrucao["minuta_despacho"]
    assert "R$ 980,00" in minuta and "3,5 diária(s)" in minuta
    assert rascunho not in minuta
    assert ("Recomendação: não recomendado." if numero.endswith("0108")
            else "Recomendação: apto para autorização.") in minuta


@pytest.mark.parametrize("texto,numero,tipo", [
    ("agência: 3210-9", "3210-9", "Agência bancária"),
    ("ag: 3210-9", "3210-9", "Agência bancária"),
    ("ag. nº 3210-9", "3210-9", "Agência bancária"),
    ("agência bancária: 3210-9", "3210-9", "Agência bancária"),
    ("conta: 76543-2", "76543-2", "Conta bancária"),
    ("conta corrente: 76543-2", "76543-2", "Conta bancária"),
    ("c/c = 76543-2", "76543-2", "Conta bancária"),
    ("conta poupança nº: 76543-2", "76543-2", "Conta bancária"),
])
def test_pontuacao_bancaria_e_mascarada_nas_duas_camadas(texto, numero, tipo):
    from agno.run.agent import RunInput

    seguro, tipos = filtro_pii.mascarar_texto(texto)
    assert numero not in seguro and tipo in tipos
    entrada = RunInput(input_content=texto)
    filtro_pii.criar_guardrail().check(entrada)
    assert numero not in entrada.input_content


def test_dados_bancarios_com_pontuacao_nao_chegam_ao_endpoint_ou_banco(tmp_path, pedidos):
    p = {**pedidos["DIA-2026-0101"],
         "justificativa": "Vistoria programada. agência: 3210-9; conta corrente: 76543-2."}
    with SimuladorOpenAI() as sim:
        assert instruir(agente(sim, tmp_path), p).aprovada
        assert not any(d in "\n".join(sim.requisicoes) for d in ("3210-9", "76543-2"))
    assert not verificacao.ocorrencias(tmp_path / "agente.db", ["3210-9", "76543-2"])


@pytest.mark.parametrize("campo", ["alertas", "matricula", "minuta_despacho"])
def test_resposta_recusada_nao_vaza_pii_na_memoria_ou_auditoria(
        tmp_path, pedidos, monkeypatch, campo):
    original = _Politica._instrucao

    def adulterar(self, pedido, resultados):
        obj = original(self, pedido, resultados)
        obj[campo] = [MARCADOR] if campo == "alertas" else MARCADOR
        return obj

    monkeypatch.setattr(_Politica, "_instrucao", adulterar)
    with SimuladorOpenAI() as sim:
        r = instruir(agente(sim, tmp_path), pedidos["DIA-2026-0101"])
    assert r.situacao == "recusada" and r.instrucao is None
    assert MARCADOR not in json.dumps(r.to_dict(), ensure_ascii=False)
    adm = tmp_path / "administrativo.db"
    persistencia.registrar_analise(r, adm)
    for db in (tmp_path / "agente.db", adm):
        assert not verificacao.ocorrencias(db, [MARCADOR])


def test_erro_api_com_pii_e_sanitizado_no_log_e_no_banco(tmp_path, pedidos, monkeypatch, caplog):
    with SimuladorOpenAI(modo="erro_api") as sim:
        handler = sim._servidor.RequestHandlerClass
        enviar = handler._enviar

        def erro_com_pii(self, codigo, dados):
            if codigo == 400:
                dados["error"]["message"] += " " + MARCADOR
            return enviar(self, codigo, dados)

        monkeypatch.setattr(handler, "_enviar", erro_com_pii)
        logger = logging.getLogger("agno")
        logger.addHandler(caplog.handler)
        try:
            r = instruir(agente(sim, tmp_path), pedidos["DIA-2026-0101"])
        finally:
            logger.removeHandler(caplog.handler)
    assert r.situacao == "erro_execucao" and r.instrucao is None
    assert caplog.records and MARCADOR not in caplog.text
    assert not verificacao.ocorrencias(tmp_path / "agente.db", [MARCADOR])


def test_fronteira_administrativa_sanitiza_mesmo_sem_passar_pelo_agente(tmp_path):
    r = ResultadoInstrucao(numero="DIA-2026-0101", turno="pedido", situacao="recusada",
                           session_id="DIA-2026-0101", user_id="204317", modelo="simulador", inicio="teste",
                           motivos_recusa=[MARCADOR], alertas_aplicacao=[MARCADOR],
                           consultas=[{"ferramenta": "consultar_servidor", "argumentos": {"nome": MARCADOR}}])
    db = tmp_path / "administrativo.db"
    persistencia.registrar_analise(r, db)
    persistencia.registrar_conferencia(r.numero, 1, None, "analise_manual", MARCADOR,
                                       MARCADOR, "rascunho", "conferente", db)
    assert not verificacao.ocorrencias(db, [MARCADOR])
    assert len(persistencia.listar("analises", db)) == len(persistencia.listar("conferencias", db)) == 1


@pytest.mark.parametrize("em_lote", [False, True])
def test_memorias_e_metadados_sao_mascarados_antes_da_escrita(tmp_path, em_lote):
    db = tmp_path / "agente.db"
    banco = SqliteDbProtegido(db_file=str(db))
    memoria = UserMemory(memory=MARCADOR, user_id="204317", memory_id="memoria",
                         input=json.dumps({"texto": "agência: 3210-9"}, ensure_ascii=True))
    sessao = AgentSession(session_id="DIA-2026-0101", user_id="204317", metadata={"contato": MARCADOR},
                          created_at=1, updated_at=1)
    if em_lote:
        banco.upsert_sessions([sessao], preserve_updated_at=True)
        banco.upsert_memories([memoria], preserve_updated_at=True)
    else:
        banco.upsert_session(sessao)
        banco.upsert_user_memory(memoria)
    assert not verificacao.ocorrencias(db, [MARCADOR, "3210-9"])
    # A cópia sanitizada não apaga a evidência em memória usada para validar o retorno.
    assert memoria.memory == MARCADOR and sessao.metadata["contato"] == MARCADOR


def test_sessao_retornada_pelo_lote_preserva_execucoes_mascaradas(tmp_path):
    banco = SqliteDbProtegido(db_file=str(tmp_path / "agente.db"))
    sessao = AgentSession(session_id="DIA-2026-0101", agent_id="agente", user_id="204317",
                          runs=[RunOutput(run_id="execucao", agent_id="agente", content=MARCADOR)],
                          created_at=1, updated_at=1)
    # Assim como no SqliteDb, o lote grava metadados e devolve os runs informados;
    # a persistência independente de execuções usa upsert_run.
    gravada = banco.upsert_sessions([sessao])[0]
    assert len(gravada.runs) == 1 and gravada.runs[0].run_id == "execucao"
    assert MARCADOR not in json.dumps(gravada.to_dict())


@pytest.mark.parametrize("uf", ["ZZ", "BR", "12", "M", "", "ÃA"])
def test_uf_inexistente_nao_recebe_calculo(uf):
    r = json.loads(calcular_diarias("204317", uf, "2026-10-08", "2026-11-09", "2026-11-12"))
    assert r["situacao"] == "argumento_invalido" and "valor_total" not in r


@pytest.mark.parametrize("paralelas", [False, True])
def test_casos_conferem_com_avaliador_externo_apos_as_correcoes(tmp_path, pedidos, complementacoes, paralelas):
    gab = cg.carregar_gabarito()
    with SimuladorOpenAI() as sim:
        ag = agente(sim, tmp_path, paralelas=paralelas)
        for n, p in pedidos.items():
            r = instruir(ag, p)
            assert cg.comparar(r.to_dict(), gab["pedidos"][n])["correto"], n
            assert r.instrucao["minuta_despacho"].endswith("À consideração do ordenador de despesa.")
        # Reconstruir o agente exige recuperação efetiva do SQLite.
        ag = agente(sim, tmp_path, paralelas=paralelas)
        for n, c in complementacoes.items():
            r = instruir(ag, pedidos[n], c)
            assert cg.comparar(r.to_dict(), gab["complementacoes"][n])["correto"], n
            assert r.session_id == n and r.user_id == pedidos[n]["matricula"]
        assert all("criterios_nao_atendidos" not in req for req in sim.requisicoes)


def test_interface_apresenta_identidades_do_cadastro_e_carrega_seis_paginas(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BANCOS", tmp_path)
    monkeypatch.setattr(config, "chave_configurada", lambda: False)
    app = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=30).run()
    for pagina in list(app.radio[0].options):
        app.radio[0].set_value(pagina).run()
        assert not app.exception, pagina
    app.radio[0].set_value("Memória e LGPD").run()
    app.checkbox[0].check().run()
    nomes = app.selectbox[0].options
    assert "207481 — Rafael Lima Antunes" in nomes
    assert "207418 — Carla Regina Souza" in nomes
    assert "207481 — Carla Regina Souza" not in nomes


def test_interface_complementa_confere_minuta_e_elimina_preservando_administrativo(tmp_path, monkeypatch):
    import streamlit as st

    monkeypatch.setattr(config, "BANCOS", tmp_path / "bancos")
    monkeypatch.setattr(config, "EVIDENCIAS", tmp_path / "evidencias")
    monkeypatch.setattr(config, "chave_configurada", lambda: False)
    st.cache_resource.clear()
    try:
        app = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=30).run()
        for n, valor in (("DIA-2026-0111", 980.0), ("DIA-2026-0112", 770.0)):
            app.radio[0].set_value("Análise de pedidos").run()
            app.selectbox[0].set_value(n).run()
            next(b for b in app.button if b.label == "▶ Iniciar análise").click().run()
            assert app.session_state["resultados"][n]["resultado"]["instrucao"]["recomendacao"] == "diligencia"
            app.radio[0].set_value("Diligências").run()
            app.selectbox[0].set_value(n).run()
            next(b for b in app.button if b.label == "Reanalisar na mesma sessão").click().run()
            assert not app.exception
            r = app.session_state["resultados"][n]["resultado"]
            assert r["instrucao"]["valor_total"] == valor and r["instrucao"]["quantidade_diarias"] == 3.5
            assert "3,5 diária(s)" in r["instrucao"]["minuta_despacho"]
        app.radio[0].set_value("Conferência humana").run()
        app.selectbox[0].set_value("DIA-2026-0112").run()
        minuta = app.text_area[0].value + "\nConferência humana de teste."
        app.selectbox[1].set_value("nao_recomendado")
        app.text_input[0].set_value("Conferente de teste")
        next(b for b in app.button if b.label == "Registrar conferência").click().run()
        assert app.error
        app.text_area[0].set_value(minuta)
        app.text_area[1].set_value("Divergência intencional para validar o formulário.")
        app.selectbox[1].set_value("nao_recomendado")
        app.text_input[0].set_value("Conferente de teste")
        next(b for b in app.button if b.label == "Registrar conferência").click().run()
        assert not app.exception and app.success
        adm = config.BANCOS / "registro_conferencias_simulador.db"
        linha = persistencia.listar("conferencias", adm)[0]
        assert linha["minuta_final"] == minuta and linha["minuta_editada"] == linha["divergiu"] == 1
        antes = verificacao.contar_registros(adm)
        app.radio[0].set_value("Memória e LGPD").run()
        app.checkbox[0].check().run()
        for mat in ("207418", "206689"):
            app.selectbox[0].set_value(mat).run()
            for chave in [c.key for c in app.checkbox if c.label.startswith("Sessão DIA-2026-0112")]:
                app.checkbox(key=chave).check().run()
            next(c for c in app.checkbox if c.label.startswith("Confirmo o pedido")).check().run()
            next(b for b in app.button if b.label == "Eliminar e verificar no banco").click().run()
            assert not app.exception and any("Nada restou" in s.value for s in app.success)
        assert verificacao.contar_registros(adm) == antes
        assert len(list(config.EVIDENCIAS.glob("eliminacao_simulador_*.json"))) == 2
    finally:
        st.cache_resource.clear()
