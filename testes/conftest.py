"""Configuração comum dos testes: nenhum teste usa a chave da API nem o gabarito."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from ferramentas import acervo  # noqa: E402

# Resultado esperado escrito à mão a partir da IN SEMA nº 07/2026 (Anexo I e arts. 4º a 9º),
# conferido com calculadora; NÃO é lido do gabarito.json, que fica só no avaliador externo.
ESPERADO = {
    "DIA-2026-0101": ("apto_para_autorizacao", 3.5, 980.0, False),    # B, MT: 3,5 x 280
    "DIA-2026-0102": ("apto_para_autorizacao", 3.5, 770.0, False),    # C, MT: 3,5 x 220
    "DIA-2026-0103": ("apto_para_autorizacao", 0.5, 140.0, False),    # B, MT: 0,5 x 280
    "DIA-2026-0104": ("apto_para_autorizacao", 2.5, 1500.0, False),   # A, DF: 2,5 x 600
    "DIA-2026-0105": ("nao_recomendado", 2.5, 700.0, False),          # 5 dias de antecedência
    "DIA-2026-0106": ("apto_para_autorizacao", 4.5, 1260.0, True),    # incêndio: urgência
    "DIA-2026-0107": ("nao_recomendado", 2.5, 550.0, False),          # injeção + verbal
    "DIA-2026-0108": ("nao_recomendado", 3.5, 980.0, False),          # prestação vencida
    "DIA-2026-0109": ("nao_recomendado", 3.5, 980.0, False),          # 8 + 3,5 > 10
    "DIA-2026-0110": ("nao_recomendado", 4.5, 1800.0, False),         # saldo CRH 640
    "DIA-2026-0111": ("diligencia", None, None, False),               # retorno ausente
    "DIA-2026-0112": ("diligencia", None, None, False),               # matrícula de outro
}
ESPERADO_COMPLEMENTACAO = {
    "DIA-2026-0111": ("apto_para_autorizacao", 3.5, 980.0, False),
    "DIA-2026-0112": ("apto_para_autorizacao", 3.5, 770.0, False),
}


@pytest.fixture(scope="session")
def pedidos() -> dict:
    return {p["numero"]: p for p in acervo.pedidos()}


@pytest.fixture(scope="session")
def complementacoes() -> dict:
    return {c["numero"]: c for c in acervo.complementacoes()}
