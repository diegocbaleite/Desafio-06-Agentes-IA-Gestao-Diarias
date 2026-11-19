"""Contrato Pydantic entre o agente, a barreira, a tela e o avaliador.

Os campos e tipos seguem o contrato mínimo do enunciado (Etapa 3). Nenhum campo foi
acrescentado ao objeto que o modelo preenche: o que a tela precisa além disso (consultas
realizadas, métricas, motivo de recusa) vem do código, em `ResultadoInstrucao`, e não do
modelo — assim nada que o conferente lê como "fonte" depende do que o modelo declarou.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

CRITERIOS = ("cadastro", "dados_completos", "antecedencia", "prestacao_contas",
             "limite_mensal", "saldo_orcamentario")
CRITERIOS_DILIGENCIA = ("cadastro", "dados_completos")
CRITERIOS_IMPEDIMENTO = ("antecedencia", "prestacao_contas", "limite_mensal", "saldo_orcamentario")


class Verificacao(BaseModel):
    criterio: Literal["cadastro", "dados_completos", "antecedencia", "prestacao_contas",
                      "limite_mensal", "saldo_orcamentario"]
    situacao: Literal["atende", "nao_atende", "nao_verificado"]
    detalhe: str = Field(description="O dado que fundamenta a situação, como veio da ferramenta")


class Instrucao(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    numero_pedido: str = Field(description="Número do pedido em análise, como DIA-2026-0101")
    matricula: str = Field(description="Matrícula efetivamente conferida no cadastro")
    quantidade_diarias: Optional[float] = Field(description="Da ferramenta calcular_diarias; nulo na diligência")
    valor_total: Optional[float] = Field(description="Da ferramenta calcular_diarias, em reais; nulo na diligência")
    verificacoes: list[Verificacao] = Field(description="Exatamente uma verificação por critério, os seis")
    recomendacao: Literal["apto_para_autorizacao", "diligencia", "nao_recomendado"]
    exige_autorizacao_superior: bool = Field(
        description="Verdadeiro somente se a antecedência foi aceita por urgência (art. 5º, § 2º)")
    pendencias: list[str] = Field(description="O que o solicitante precisa corrigir")
    alertas: list[str] = Field(
        description="Ordens embutidas, dados mascarados, o que o conferente precisa ver")
    minuta_despacho: str = Field(description="Minuta de despacho de instrução, sem decidir pelo ordenador")
