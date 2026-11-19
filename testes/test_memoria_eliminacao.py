"""Etapa 4/5: memória persistente e eliminação verificável, com DIA-2026-0111 e DIA-2026-0112."""

from __future__ import annotations

import pytest

from agente.agente_diarias import construir_agente, instruir
from memoria import eliminacao, persistencia, verificacao
from simulador.servidor_openai_simulado import SimuladorOpenAI

BEATRIZ = ("206689", "Beatriz Moraes Cunha")   # DIA-2026-0111
CARLA = ("207418", "Carla Regina Souza")       # DIA-2026-0112 (digitou 207481)


@pytest.fixture
def banco(tmp_path, pedidos, complementacoes):
    db = tmp_path / "agente.db"
    with SimuladorOpenAI() as sim:
        ag = construir_agente(memoria="historico_usuario", db_file=db, base_url=sim.url, api_key="simulador")
        for n in ("DIA-2026-0101", "DIA-2026-0111", "DIA-2026-0112"):
            assert instruir(ag, pedidos[n]).aprovada
        for n in ("DIA-2026-0111", "DIA-2026-0112"):
            assert instruir(ag, pedidos[n], complementacoes[n]).aprovada
    return db


def test_tabelas_do_agente(banco):
    contagem = verificacao.contar_registros(banco)
    assert contagem["agno_sessions"] == 3 and contagem["agno_runs"] == 5
    assert contagem["agno_memories"] >= 3


def test_eliminacao_0111_titular_com_user_id_correto(banco):
    antes = verificacao.contar_registros(banco)
    ev = eliminacao.eliminar(banco, *BEATRIZ)
    assert ev["nada_restou"], ev["depois"]
    assert ev["antes"]["sessoes_do_titular"] == ["DIA-2026-0111"]
    assert not verificacao.ocorrencias(banco, list(BEATRIZ))
    # Os outros titulares permanecem intactos.
    assert set(ev["sessoes_de_outros_preservadas"]) == {"DIA-2026-0101", "DIA-2026-0112"}
    assert ev["sessoes_alheias_apagadas_indevidamente"] == []
    assert verificacao.contar_registros(banco)["agno_runs"] == antes["agno_runs"] - 2


def test_eliminacao_0112_busca_por_user_id_nao_basta(banco):
    loc = eliminacao.localizar(banco, *CARLA)
    assert loc.sessoes_do_titular == []                      # a busca pelo user_id da titular falha
    assert [s["session_id"] for s in loc.sessoes_sob_outro_user_id] == ["DIA-2026-0112"]
    assert loc.sessoes_sob_outro_user_id[0]["user_ids"] == ["207481"]
    assert loc.sessoes_sob_outro_user_id[0]["vinculo_verificado"] is True

    # Sem confirmação, nada sob o user_id de outro servidor é apagado, e a evidência mostra o resíduo.
    ev = eliminacao.eliminar(banco, *CARLA)
    assert not ev["nada_restou"]
    assert any(n.get("session_id") == "DIA-2026-0112" for n in ev["nao_apagadas"])

    # Com vínculo verificado e confirmação, a eliminação é completa.
    memorias = [m["memory_id"] for m in loc.memorias_sob_outro_user_id]
    ev = eliminacao.eliminar(banco, *CARLA, sessoes_confirmadas=["DIA-2026-0112"],
                             memorias_confirmadas=memorias, executado_por="teste")
    assert ev["nada_restou"], ev["depois"]
    assert not verificacao.ocorrencias(banco, list(CARLA))
    assert "DIA-2026-0101" in ev["sessoes_de_outros_preservadas"]


def test_confirmacao_sem_vinculo_nao_apaga_dado_alheio(banco):
    # Ana Paula (204317) pede eliminação e "confirma" a sessão do 0112, que não é dela.
    ev = eliminacao.eliminar(banco, "204317", "Ana Paula Figueiredo", sessoes_confirmadas=["DIA-2026-0112"])
    assert "DIA-2026-0112" in ev["sessoes_de_outros_preservadas"]
    assert ev["sessoes_alheias_apagadas_indevidamente"] == []


def test_evidencia_nao_repete_nome_do_titular(banco):
    ev = eliminacao.eliminar(banco, *BEATRIZ)
    assert BEATRIZ[1] not in str(ev)


def test_registro_administrativo_nao_e_alcancado(tmp_path, banco):
    db_adm = tmp_path / "registro.db"
    persistencia.registrar_conferencia("DIA-2026-0111", None, "apto_para_autorizacao",
                                       "apto_para_autorizacao", "", "minuta", "minuta", "conferente",
                                       db_file=db_adm)
    eliminacao.eliminar(banco, *BEATRIZ)
    assert len(persistencia.listar("conferencias", db_adm)) == 1


def test_conferencia_divergente_exige_justificativa(tmp_path):
    db_adm = tmp_path / "registro.db"
    with pytest.raises(ValueError):
        persistencia.registrar_conferencia("DIA-2026-0105", 1, "nao_recomendado", "apto_para_autorizacao",
                                           "", "m", "m", "servidor", db_file=db_adm)
    persistencia.registrar_conferencia("DIA-2026-0105", 1, "nao_recomendado", "apto_para_autorizacao",
                                       "Autorização escrita juntada.", "m2", "m", "servidor", db_file=db_adm)
    linha = persistencia.listar("conferencias", db_adm)[0]
    assert linha["divergiu"] == 1 and linha["minuta_editada"] == 1
    assert persistencia.taxa_divergencia(db_adm) == {"conferencias": 1, "divergencias": 1, "taxa": 1.0}
