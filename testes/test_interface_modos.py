"""A troca de modo não pode levar uma análise simulada à conferência da API real."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

import config
from agente.agente_diarias import ResultadoInstrucao


def test_analises_da_interface_sao_separadas_por_modo(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BANCOS", tmp_path)
    monkeypatch.setattr(config, "chave_configurada", lambda: True)
    app = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"),
                            default_timeout=20).run()
    assert not app.exception
    app.toggle[0].set_value(True).run()
    assert not app.exception
    numero = "DIA-2026-0101"
    resultado = ResultadoInstrucao(numero=numero, turno="pedido", situacao="recusada",
                                   session_id=numero, user_id="204317", modelo="simulador",
                                   inicio="2026-11-19T00:00:00").to_dict()
    app.session_state["resultados"][numero] = {"resultado": resultado, "analise_id": 1}
    app.run()
    assert numero in app.session_state["resultados"]

    app.toggle[0].set_value(False).run()
    assert not app.exception
    assert numero not in app.session_state["resultados"]
    app.radio[0].set_value("Conferência humana").run()
    assert not app.exception
    assert any("Nenhum pedido analisado" in e.value for e in app.info)

    resultado_api = {**resultado, "modelo": "api_de_teste"}
    app.session_state["resultados"][numero] = {"resultado": resultado_api, "analise_id": 1}
    app.run()
    assert not app.exception
    app.text_area[0].set_value("Minuta exclusiva do modo API no teste")
    app.text_area[1].set_value("Justificativa para a conferência manual do teste")
    app.text_input[0].set_value("Conferente de teste")
    next(b for b in app.button if b.label == "Registrar conferência").click().run()
    assert not app.exception
    assert any("registrada" in e.value for e in app.success)

    app.toggle[0].set_value(True).run()
    assert not app.exception
    assert app.session_state["resultados"][numero]["resultado"]["modelo"] == "simulador"
    assert app.text_area[0].value != "Minuta exclusiva do modo API no teste"

    app.radio[0].set_value("Memória e LGPD").run()
    assert not app.exception
    app.checkbox[0].check().run()
    assert not app.exception
    next(c for c in app.checkbox if c.label.startswith("Confirmo o pedido")).check().run()
    assert not app.exception
    app.toggle[0].set_value(False).run()
    assert not app.exception
    assert not app.checkbox[0].value
