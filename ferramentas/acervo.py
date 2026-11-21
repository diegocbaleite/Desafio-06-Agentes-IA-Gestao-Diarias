"""Leitura do acervo do órgão (dados hipotéticos de `dados/`) e regras puras da IN SEMA nº 07/2026.

Este módulo não é ferramenta do agente: é a camada de dados e de aritmética que as
ferramentas usam e que a barreira de verificação reutiliza para recalcular, de forma
independente do modelo, o que o agente afirmou. Nenhuma função aqui lê a resposta
esperada do avaliador externo.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path

from config import DADOS

RE_MATRICULA = re.compile(r"^\d{6}$")
RE_DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CENTAVO = Decimal("0.01")
UFS = frozenset("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split())


# ------------------------------------------------------------------ leitura


@lru_cache(maxsize=None)
def _ler_csv(nome: str, pasta: str) -> tuple[dict, ...]:
    with open(Path(pasta) / nome, encoding="utf-8", newline="") as f:
        return tuple(csv.DictReader(f))


@lru_cache(maxsize=None)
def _ler_json(nome: str, pasta: str):
    return json.loads((Path(pasta) / nome).read_text(encoding="utf-8"))


def servidores(pasta: Path = DADOS) -> dict[str, dict]:
    """Cadastro funcional indexado por matrícula (contém CPF e e-mail: uso interno)."""
    return {s["matricula"]: s for s in _ler_csv("servidores.csv", str(pasta))}


def historico(pasta: Path = DADOS) -> tuple[dict, ...]:
    return _ler_csv("historico_diarias.csv", str(pasta))


def tabela(pasta: Path = DADOS) -> dict:
    return _ler_json("tabela_diarias.json", str(pasta))


def unidades(pasta: Path = DADOS) -> dict:
    return _ler_json("unidades.json", str(pasta))


def pedidos(pasta: Path = DADOS) -> list[dict]:
    return list(_ler_json("pedidos.json", str(pasta)))


def complementacoes(pasta: Path = DADOS) -> list[dict]:
    return list(_ler_json("complementacoes.json", str(pasta)))


def norma(pasta: Path = DADOS) -> str:
    return (Path(pasta) / "normas.md").read_text(encoding="utf-8")


def data_da_analise() -> date:
    return date.fromisoformat(tabela()["data_da_analise"])


# ------------------------------------------------------------------ validação de argumentos


def matricula_valida(matricula: str) -> bool:
    return bool(RE_MATRICULA.match((matricula or "").strip()))


def ler_data(texto: str) -> date | None:
    """Converte AAAA-MM-DD em date; devolve None se ausente ou fora do formato."""
    texto = (texto or "").strip()
    if not RE_DATA_ISO.match(texto):
        return None
    try:
        return date.fromisoformat(texto)
    except ValueError:
        return None


def normalizar_nome(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
    return " ".join(sem_acento.casefold().split())


# ------------------------------------------------------------------ regras da norma


def classe_destino(uf: str) -> str:
    """Classe do destino no Anexo I: interior_mt, distrito_federal ou outra_uf."""
    uf = (uf or "").strip().upper()
    if uf == "MT":
        return "interior_mt"
    if uf == "DF":
        return "distrito_federal"
    return "outra_uf"


def quantidade_diarias(partida: date, retorno: date) -> Decimal:
    """Art. 4º: uma diária por pernoite e meia no retorno; sem pernoite, meia diária."""
    pernoites = (retorno - partida).days
    return Decimal("0.5") if pernoites == 0 else Decimal(pernoites) + Decimal("0.5")


def valor_unitario(grupo: str, uf: str) -> Decimal:
    """Anexo I: valor da diária inteira conforme o grupo do cargo e a classe do destino."""
    return Decimal(str(tabela()["valores"][grupo][classe_destino(uf)])).quantize(CENTAVO)


def somar_dias_uteis(inicio: date, dias: int) -> date:
    """Soma dias úteis (segunda a sexta), sem considerar feriados."""
    atual = inicio
    while dias:
        atual += timedelta(days=1)
        if atual.weekday() < 5:
            dias -= 1
    return atual


def antecedencia_dias(data_pedido: date, partida: date) -> int:
    """Art. 5º: dias corridos entre o protocolo do pedido e a partida."""
    return (partida - data_pedido).days


def dinheiro(valor: Decimal) -> float:
    """Converte Decimal monetário em float com duas casas, para JSON."""
    return float(valor.quantize(CENTAVO, rounding=ROUND_HALF_UP))
