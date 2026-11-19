"""Ferramentas do agente: funções Python comuns, sem dependência do framework."""

from ferramentas.cadastro import consultar_servidor
from ferramentas.calculos import calcular_diarias
from ferramentas.historico import consultar_historico_diarias
from ferramentas.orcamento import consultar_saldo_diarias

FERRAMENTAS = [consultar_servidor, consultar_historico_diarias, calcular_diarias,
               consultar_saldo_diarias]

__all__ = ["FERRAMENTAS", "consultar_servidor", "consultar_historico_diarias",
           "calcular_diarias", "consultar_saldo_diarias"]
