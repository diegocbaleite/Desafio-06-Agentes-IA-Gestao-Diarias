"""Infraestrutura comum dos scripts de avaliação: modo real x simulador e gravação honesta.

Regra: um script só mede o modelo com a API real. Sem OPENAI_API_KEY, grava um registro
"nao_executado" com o motivo e não inventa número algum. Com --simulador, roda o pipeline
contra o servidor local e grava em resultados/simulador/, com o aviso de que os números de
tokens são estimativas do simulador e não medições do modelo.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from datetime import datetime
from pathlib import Path

import config

AVISO_SIMULADOR = ("EXECUÇÃO COM SIMULADOR LOCAL: valida o pipeline (Agno, ferramentas, barreira, "
                   "memória, eliminação). Tokens, tempo e custo são do simulador e NÃO são medições "
                   "do modelo gpt-5.6-luna.")


def argumentos(descricao: str, extra=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=descricao)
    parser.add_argument("--simulador", action="store_true",
                        help="usa o simulador local da API (não mede o modelo)")
    if extra:
        extra(parser)
    return parser.parse_args()


def pasta_saida(simulador: bool) -> Path:
    pasta = config.RESULTADOS / ("simulador" if simulador else "")
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def banco_avaliacao(nome: str, simulador: bool) -> Path:
    """Separa os bancos de simulação dos bancos das medições reais."""
    pasta = config.BANCOS / ("simulador" if simulador else "")
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / nome


@contextlib.contextmanager
def ambiente(simulador: bool):
    """Entrega (base_url, api_key) para construir_agente; None, None na API real."""
    if simulador:
        from simulador.servidor_openai_simulado import SimuladorOpenAI
        with SimuladorOpenAI() as sim:
            yield sim.url, "simulador"
    else:
        yield None, None


def bloqueio_sem_chave(simulador: bool, nome_arquivo: str, etapa: str) -> bool:
    """Se não há chave e não é simulação, grava o bloqueio e devolve True."""
    if simulador or config.chave_configurada():
        return False
    registro = {"etapa": etapa, "situacao": "nao_executado",
                "motivo": "OPENAI_API_KEY ausente no ambiente e no .env; a execução contra o modelo "
                          f"{config.MODELO} não foi realizada. Nenhuma medição foi produzida.",
                "registrado_em": datetime.now().isoformat(timespec="seconds"),
                "como_executar": f"Configure OPENAI_API_KEY em .env e rode novamente: {' '.join(sys.argv)}"}
    destino = pasta_saida(False) / nome_arquivo
    if destino.exists():
        anterior = json.loads(destino.read_text(encoding="utf-8"))
        if anterior.get("situacao") != "nao_executado":
            # A ausência de chave hoje não apaga uma medição já concluída.
            destino = destino.parent / "bloqueios" / nome_arquivo
            destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[bloqueado] {registro['motivo']}\nRegistro gravado em {destino}")
    return True


def gravar(dados: dict, nome_arquivo: str, simulador: bool) -> Path:
    dados = {"modo": "simulador" if simulador else "api_real", "modelo": config.MODELO,
             "aviso": AVISO_SIMULADOR if simulador else None,
             "gerado_em": datetime.now().isoformat(timespec="seconds"), **dados}
    destino = pasta_saida(simulador) / nome_arquivo
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Gravado em {destino}")
    return destino
