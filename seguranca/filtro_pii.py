"""Filtro de dados pessoais: CPF, agência e conta bancária, configurado para o caso brasileiro.

Duas camadas usam os MESMOS padrões:

1. `mascarar_texto` — aplicado pela aplicação ao texto do pedido ANTES de chamar o agente,
   de modo que o dado não chega ao modelo, ao banco de memória, aos registros nem às
   evidências.
2. `criar_guardrail` — PIIDetectionGuardrail do Agno nos `pre_hooks`, com os padrões
   norte-americanos desligados (SSN, cartão, telefone). É a defesa em profundidade: se
   algum chamador esquecer a camada 1, o guardrail mascara a entrada antes do modelo e
   antes da persistência (o Agno grava o `run_input` já modificado pelo hook).

O CPF é reconhecido pela máscara, sem conferir dígitos verificadores: os CPFs do acervo
são inválidos de propósito e, ainda assim, são dados pessoais a proteger.
Matrícula (6 dígitos), número do pedido (DIA-AAAA-NNNN) e datas (AAAA-MM-DD) não casam
com nenhum padrão — isso é verificado nos testes.
"""

from __future__ import annotations

import re

from agno.guardrails import PIIDetectionGuardrail

# CPF formatado (000.000.000-00) ou com 11 algarismos seguidos, isolados.
PADRAO_CPF = r"(?<!\d)(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})(?!\d)"
# Agência: a palavra "agência"/"ag." seguida do número, com dígito opcional.
PADRAO_AGENCIA = r"(?i)\bag(?:[êe]ncia|\.)\s*(?:n[º°o]\.?\s*)?(?:banc[áa]ria\s*)?\d{3,5}(?:-[\dxX])?"
# Conta: "conta", "c/c" ou "conta corrente/poupança" seguida do número, com dígito opcional.
PADRAO_CONTA = (r"(?i)\b(?:conta(?:\s+(?:corrente|poupan[çc]a|banc[áa]ria))?|c/c)\s*"
                r"(?:n[º°o]\.?\s*)?\d{3,12}(?:-[\dxX])?")

PADROES = {"CPF": PADRAO_CPF, "Agência bancária": PADRAO_AGENCIA, "Conta bancária": PADRAO_CONTA}
_COMPILADOS = {nome: re.compile(p) for nome, p in PADROES.items()}
_RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

ROTULOS = {"CPF": "[CPF MASCARADO]", "Agência bancária": "[AGÊNCIA MASCARADA]",
           "Conta bancária": "[CONTA BANCÁRIA MASCARADA]", "E-mail": "[E-MAIL MASCARADO]"}


def detectar(texto: str) -> list[str]:
    """Lista os tipos de dado pessoal encontrados no texto (sem devolver o dado)."""
    achados = [nome for nome, rx in _COMPILADOS.items() if rx.search(texto or "")]
    if _RE_EMAIL.search(texto or ""):
        achados.append("E-mail")
    return achados


def mascarar_texto(texto: str) -> tuple[str, list[str]]:
    """Substitui CPF, agência, conta e e-mail por rótulos legíveis e informa o que mascarou.

    Os rótulos (em vez de asteriscos) permitem ao modelo registrar em `alertas` que houve
    dado mascarado, sem jamais ver o dado.
    """
    if not texto:
        return texto, []
    encontrados: list[str] = []
    # A conta é tratada antes do CPF para que "conta 12345678901" vire conta, não CPF.
    for nome in ("Agência bancária", "Conta bancária", "CPF"):
        texto, n = _COMPILADOS[nome].subn(ROTULOS[nome], texto)
        if n:
            encontrados.append(nome)
    texto, n = _RE_EMAIL.subn(ROTULOS["E-mail"], texto)
    if n:
        encontrados.append("E-mail")
    return texto, encontrados


def criar_guardrail() -> PIIDetectionGuardrail:
    """PIIDetectionGuardrail com padrões dos EUA desligados e padrões brasileiros próprios."""
    return PIIDetectionGuardrail(
        mask_pii=True,
        enable_ssn_check=False,
        enable_credit_card_check=False,
        enable_phone_check=False,
        enable_email_check=True,
        custom_patterns=dict(PADROES),
    )
