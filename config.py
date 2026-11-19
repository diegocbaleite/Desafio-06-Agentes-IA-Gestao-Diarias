"""Configuração central do sistema de instrução de pedidos de diárias.

Lê o `.env` da raiz do projeto com `load_dotenv`. A chave da OpenAI é lida
apenas pelo SDK, a partir da variável de ambiente; este módulo nunca a expõe,
apenas informa se ela está presente.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
load_dotenv(RAIZ / ".env")
# A telemetria do Agno é desligada também no ambiente, além de telemetry=False no agente.
os.environ.setdefault("AGNO_TELEMETRY", "false")

DADOS = RAIZ / "dados"
RESULTADOS = RAIZ / "resultados"
EVIDENCIAS = RESULTADOS / "evidencias"
BANCOS = RAIZ / "bancos"

# Modelo de referência do desafio; parametrizável, sem substituição silenciosa.
MODELO = (os.getenv("MODELO_DIARIAS")
          or (os.getenv("MODELO_LLM") or "").split("/")[-1]   # aceita "openai/gpt-5.6-luna"
          or "gpt-5.6-luna")
# Endereço alternativo da API (usado apenas pelo simulador local dos testes).
BASE_URL = os.getenv("OPENAI_BASE_URL") or None

# Preços do gpt-5.6-luna informados na Aula 06, Seção 4.2 (US$ por milhão de tokens).
USD_ENTRADA_POR_MILHAO = float(os.getenv("USD_ENTRADA_POR_MILHAO", "0.20"))
USD_SAIDA_POR_MILHAO = float(os.getenv("USD_SAIDA_POR_MILHAO", "1.20"))

# Limites de execução (justificativa em desenho.md e LEIA-ME.md).
TOOL_CALL_LIMIT = int(os.getenv("TOOL_CALL_LIMIT", "6"))
NUM_HISTORY_RUNS = int(os.getenv("NUM_HISTORY_RUNS", "3"))
PARALLEL_TOOL_CALLS = os.getenv("PARALLEL_TOOL_CALLS", "false").lower() == "true"

DB_AGENTE = Path(os.getenv("DB_AGENTE", str(BANCOS / "agente_diarias.db")))
DB_CONFERENCIAS = Path(os.getenv("DB_CONFERENCIAS", str(BANCOS / "registro_conferencias.db")))

MENSAGEM_PADRAO = (
    "Não foi possível produzir uma instrução verificada para este pedido. "
    "O pedido foi devolvido à análise manual da Coordenadoria de Diárias e Passagens."
)


def chave_configurada() -> bool:
    """Informa se há chave da API no ambiente, sem jamais devolver o valor."""
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def custo_usd(entrada: int, saida: int) -> float:
    """Custo em dólares de uma quantidade de tokens de entrada e de saída."""
    return entrada / 1e6 * USD_ENTRADA_POR_MILHAO + saida / 1e6 * USD_SAIDA_POR_MILHAO
