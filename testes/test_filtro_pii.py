"""Etapa 3/4: filtro de dados pessoais — CPF, agência e conta mascarados; identificadores legíveis."""

from __future__ import annotations

from agno.run.agent import RunInput

from seguranca import filtro_pii

CPF_0104 = "052.318.947-20"


def test_0104_mascara_cpf_conta_agencia(pedidos):
    texto = pedidos["DIA-2026-0104"]["justificativa"]
    mascarado, tipos = filtro_pii.mascarar_texto(texto)
    assert CPF_0104 not in mascarado
    assert "98765-4" not in mascarado and "1234-5" not in mascarado
    assert set(tipos) == {"CPF", "Agência bancária", "Conta bancária"}
    assert "Conselho Nacional do Meio Ambiente" in mascarado  # o resto continua legível


def test_cpf_invalido_e_sem_pontuacao_tambem_e_mascarado():
    # Dígitos verificadores errados de propósito: a máscara não depende da validade.
    for cpf in ("123.456.789-00", "111.111.111-11", "05231894720"):
        assert cpf not in filtro_pii.mascarar_texto(f"CPF {cpf}.")[0]


def test_identificadores_administrativos_permanecem_legiveis(pedidos):
    for p in pedidos.values():
        texto = (f"Pedido {p['numero']}, matrícula {p['matricula']}, protocolado em {p['data_pedido']}, "
                 f"partida {p['data_partida']}, retorno {p.get('data_retorno')}.")
        mascarado, tipos = filtro_pii.mascarar_texto(texto)
        assert mascarado == texto and tipos == []


def test_so_o_0104_tem_dado_pessoal(pedidos):
    com_pii = [n for n, p in pedidos.items() if filtro_pii.detectar(p["justificativa"])]
    assert com_pii == ["DIA-2026-0104"]


def test_guardrail_agno_mascara_cpf_e_preserva_identificadores(pedidos):
    guardrail = filtro_pii.criar_guardrail()
    p = pedidos["DIA-2026-0104"]
    entrada = RunInput(input_content=f"numero: {p['numero']}\nmatricula: {p['matricula']}\n"
                                     f"data_partida: {p['data_partida']}\n{p['justificativa']}")
    guardrail.check(entrada)
    saida = entrada.input_content
    assert CPF_0104 not in saida and "98765-4" not in saida and "1234-5" not in saida
    for ident in (p["numero"], p["matricula"], p["data_partida"]):
        assert ident in saida


def test_guardrail_padroes_norte_americanos_desligados():
    g = filtro_pii.criar_guardrail()
    assert not {"SSN", "Credit Card", "Phone"} & set(g.pii_patterns)
    assert {"CPF", "Agência bancária", "Conta bancária"} <= set(g.pii_patterns)
    # O padrão de telefone dos EUA mascarava números de 10 dígitos (Aula 06, 5.2); aqui não.
    entrada = RunInput(input_content="Protocolo 2026005678, pedido DIA-2026-0101.")
    g.check(entrada)
    assert entrada.input_content == "Protocolo 2026005678, pedido DIA-2026-0101."
