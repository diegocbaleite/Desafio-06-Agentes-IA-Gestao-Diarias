"""Executa as quatro ferramentas sem agente e sem chave: `python -m ferramentas`.

Grava a saída em resultados/evidencias/ferramentas_sem_agente.txt, como evidência de que
as contas estão certas antes de o modelo entrar (Etapa 2).
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout

import config
from ferramentas import (FERRAMENTAS, calcular_diarias, consultar_historico_diarias,
                         consultar_saldo_diarias, consultar_servidor)


def _mostrar(rotulo: str, saida: str, campos: list[str]) -> None:
    dados = json.loads(saida)
    print(f"\n{rotulo}")
    print(f"  argumentos: {dados['argumentos']}")
    for c in campos:
        if c in dados:
            print(f"  {c}: {dados[c]}")


def demonstrar() -> None:
    print("Ferramentas e a primeira linha da docstring de cada uma:")
    for f in FERRAMENTAS:
        print(f"  {f.__name__:30} {f.__doc__.strip().splitlines()[0]}")

    _mostrar("[DIA-2026-0112] matrícula de outro servidor (troca de dois algarismos)",
             consultar_servidor("207481", "Carla Regina Souza"),
             ["situacao", "conferencia_nome", "criterio_cadastro", "mensagem"])
    _mostrar("[DIA-2026-0112] matrícula corrigida pela complementação",
             consultar_servidor("207418", "Carla Regina Souza"),
             ["situacao", "conferencia_nome", "criterio_cadastro", "grupo_diaria", "unidade"])
    _mostrar("[DIA-2026-0108] prestação de contas vencida",
             consultar_historico_diarias("203648", "2026-11-03"),
             ["data_da_analise", "prestacoes_pendentes", "criterio_prestacao_contas"])
    _mostrar("[DIA-2026-0102] prestação pendente ainda no prazo (contraste)",
             consultar_historico_diarias("205882", "2026-11-09"),
             ["prestacoes_pendentes", "criterio_prestacao_contas"])
    _mostrar("[DIA-2026-0103] ida e volta no mesmo dia: meia diária",
             calcular_diarias("203156", "MT", "2026-10-07", "2026-11-05", "2026-11-05"),
             ["pernoites", "quantidade_diarias", "valor_unitario", "valor_total", "antecedencia_dias",
              "antecedencia_minima_atendida"])
    calc = json.loads(calcular_diarias("205507", "RO", "2026-10-02", "2026-11-10", "2026-11-14"))
    _mostrar("[DIA-2026-0110] cálculo da viagem a outra UF", json.dumps(calc, ensure_ascii=False),
             ["classe_destino", "quantidade_diarias", "valor_unitario", "valor_total"])
    _mostrar("[DIA-2026-0110] saldo insuficiente na unidade",
             consultar_saldo_diarias("CRH", calc["valor_total"]),
             ["saldo_disponivel", "valor_pedido", "criterio_saldo_orcamentario"])
    _mostrar("[DIA-2026-0111] retorno ausente: a ferramenta recusa calcular",
             calcular_diarias("206689", "MT", "2026-10-09", "2026-11-17", ""),
             ["situacao", "campos_ausentes", "mensagem"])
    _mostrar("[DIA-2026-0109] limite mensal",
             calcular_diarias("208114", "MT", "2026-10-06", "2026-11-23", "2026-11-26"),
             ["diarias_ja_concedidas_no_mes", "quantidade_diarias", "total_no_mes_com_pedido",
              "criterio_limite_mensal"])
    _mostrar("[minimização] o cadastro nunca devolve CPF nem e-mail",
             consultar_servidor("200941", "Heitor Vasconcelos Lima"),
             ["situacao", "cargo", "grupo_diaria", "unidade"])
    print("  contém 'cpf' ou 'email'?",
          any(k in consultar_servidor("200941", "Heitor Vasconcelos Lima") for k in ("cpf", "email", "@")))


if __name__ == "__main__":
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        demonstrar()
    texto = buffer.getvalue()
    sys.stdout.reconfigure(encoding="utf-8")
    print(texto)
    config.EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    (config.EVIDENCIAS / "ferramentas_sem_agente.txt").write_text(texto, encoding="utf-8")
    print(f"Evidência gravada em {config.EVIDENCIAS / 'ferramentas_sem_agente.txt'}")
