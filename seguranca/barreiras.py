"""Barreira de verificação no código, independente do modelo (Aula 01, Seção 3; Aula 03).

Nenhuma instrução chega ao conferente sem passar por `verificar_instrucao`. A barreira
NÃO confia no que o modelo declara: ela lê os argumentos e os resultados das ferramentas
efetivamente executadas na execução (`RunOutput.tools`), ancora cada argumento no pedido
que a aplicação tem em mãos (e na complementação) e exige que cada número e cada
situação do objeto `Instrucao` coincida com o que as ferramentas devolveram.

Qualquer falha recusa a instrução inteira: a tela mostra a mensagem padrão e o pedido
volta à análise manual. Os motivos ficam no registro de auditoria, nunca o conteúdo
recusado.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime

from agente.modelos import CRITERIOS, CRITERIOS_DILIGENCIA, CRITERIOS_IMPEDIMENTO, Instrucao
from ferramentas import acervo
from seguranca import filtro_pii

TOLERANCIA = 0.005  # meio centavo

# Situações de urgência do art. 5º, § 1º (indícios textuais; o julgamento é do modelo e do conferente).
TERMOS_URGENCIA = [r"inc[êe]ndio", r"queimada", r"focos? ativos?", r"desastre", r"enchente",
                   r"inunda[çc][ãa]o", r"rompimento", r"derramamento", r"vazamento de",
                   r"infra[çc][ãa]o ambiental em curso", r"em flagrante", r"determina[çc][ãa]o judicial",
                   r"ordem judicial", r"decis[ãa]o judicial", r"emerg[êe]ncia"]
# Ordens dirigidas ao sistema dentro de dado não confiável (prompt injection).
MARCADORES_INJECAO = [r"sistema de an[áa]lise", r"\bignore\b", r"desconsider", r"registre .{0,60}como",
                      r"classifique", r"marque .{0,40}como", r"n[ãa]o se aplica a este pedido",
                      r"instru[çc][õo]es anteriores", r"\bprompt\b", r"voc[êe] (deve|precisa)",
                      r"\baprove\b", r"como apto", r"aten[çc][ãa]o,? (ao )?sistema"]
AUTORIZACAO_VERBAL = r"verbal"
# Verbos de decisão que pertencem ao ordenador de despesa (art. 10), proibidos na minuta.
DECISAO = [r"\bdefiro\b", r"\bindefiro\b", r"\bautorizo\b", r"\bconcedo\b", r"\bfica deferid",
           r"\bfica autorizad", r"\bdetermino o pagamento", r"\bpague-se\b", r"\bdeferido\b",
           r"\bindeferido\b"]

RE_MATRICULA_TEXTO = re.compile(r"(?<!\d)\d{6}(?!\d)")
RE_DATA_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
RE_DATA_BR = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")


def _achar(padroes: list[str], texto: str) -> list[str]:
    return [p for p in padroes if re.search(p, texto or "", flags=re.IGNORECASE)]


def indicios_urgencia(texto: str) -> list[str]:
    return _achar(TERMOS_URGENCIA, texto)


def indicios_injecao(texto: str) -> list[str]:
    return _achar(MARCADORES_INJECAO, texto)


def datas_no_texto(texto: str) -> set[str]:
    datas = set(RE_DATA_ISO.findall(texto or ""))
    for d, m, a in RE_DATA_BR.findall(texto or ""):
        datas.add(f"{a}-{m}-{d}")
    return {d for d in datas if acervo.ler_data(d)}


# ------------------------------------------------------------------ pedido efetivo


@dataclass
class PedidoEfetivo:
    """O que a aplicação sabe do pedido: o protocolado e o que a complementação acrescentou."""

    pedido: dict
    complementacao_texto: str = ""
    matriculas_permitidas: set[str] = field(default_factory=set)
    datas_permitidas: set[str] = field(default_factory=set)
    datas_retorno_possiveis: set[str] = field(default_factory=set)

    @classmethod
    def montar(cls, pedido: dict, complementacao: dict | None = None) -> "PedidoEfetivo":
        texto = (complementacao or {}).get("texto", "")
        mats = {pedido["matricula"]} | set(RE_MATRICULA_TEXTO.findall(texto))
        datas = {pedido.get("data_pedido"), pedido.get("data_partida"), pedido.get("data_retorno")}
        datas |= datas_no_texto(texto)
        retornos = ({pedido["data_retorno"]} if pedido.get("data_retorno") else set()) | datas_no_texto(texto)
        return cls(pedido=pedido, complementacao_texto=texto, matriculas_permitidas=mats,
                   datas_permitidas={d for d in datas if d}, datas_retorno_possiveis=retornos)

    @property
    def dados_completos(self) -> bool:
        p = self.pedido
        campos = ("numero", "data_pedido", "matricula", "nome", "destino_municipio", "destino_uf",
                  "data_partida")
        return all(p.get(c) for c in campos) and bool(self.datas_retorno_possiveis)

    @property
    def texto_nao_confiavel(self) -> str:
        return f"{self.pedido.get('justificativa', '')}\n{self.complementacao_texto}"


# ------------------------------------------------------------------ resultado


@dataclass
class ResultadoBarreira:
    aprovada: bool
    motivos: list[str] = field(default_factory=list)
    alertas_codigo: list[str] = field(default_factory=list)


def _resultado_json(consulta: dict) -> dict:
    try:
        return json.loads(consulta.get("resultado") or "")
    except (TypeError, ValueError):
        return {}


def _ultima(consultas: list[dict], nome: str) -> dict | None:
    achadas = [c for c in consultas if c["ferramenta"] == nome]
    return achadas[-1] if achadas else None


# ------------------------------------------------------------------ verificação


def verificar_argumentos(efetivo: PedidoEfetivo, consultas: list[dict]) -> list[str]:
    """Toda matrícula consultada e toda data usada precisam constar do pedido ou da complementação."""
    p = efetivo.pedido
    motivos = []
    cadastro_atual = None
    calculo_atual = None
    cadastro_final = _ultima(consultas, "consultar_servidor")
    matricula_final = str(((cadastro_final or {}).get("argumentos") or {}).get("matricula", "")).strip()
    for c in consultas:
        nome, args = c["ferramenta"], c.get("argumentos") or {}
        if c.get("erro"):
            motivos.append(f"{nome}: a execução da ferramenta falhou.")
        if "matricula" in args and str(args["matricula"]).strip() not in efetivo.matriculas_permitidas:
            motivos.append(f"{nome}: matrícula {args['matricula']!r} não consta do pedido nem da complementação.")
        if nome == "consultar_servidor":
            cadastro_atual = c if _resultado_json(c).get("criterio_cadastro") == "atende" else None
            calculo_atual = None
        elif nome in ("consultar_historico_diarias", "calcular_diarias"):
            matricula = str(args.get("matricula", "")).strip()
            if cadastro_atual is None:
                motivos.append(f"{nome}: consulta sem cadastro conferido antes (ordem das consultas).")
            elif matricula != str(cadastro_atual["argumentos"].get("matricula", "")).strip():
                motivos.append(f"{nome}: matrícula diferente da conferida no cadastro anterior.")
            if matricula != matricula_final:
                motivos.append(f"{nome}: matrícula diferente da matrícula efetivamente conferida na instrução.")
            if nome == "calcular_diarias":
                calculo_atual = c if _resultado_json(c).get("situacao") == "calculado" else None
        elif nome == "consultar_saldo_diarias" and calculo_atual is None:
            motivos.append("consultar_saldo_diarias: chamada antes do cálculo (ordem das consultas).")
        for chave in ("data_pedido", "data_partida", "data_retorno"):
            if chave in args and str(args[chave]).strip() and str(args[chave]).strip() not in efetivo.datas_permitidas:
                motivos.append(f"{nome}: data {args[chave]!r} ({chave}) não consta do pedido nem da complementação.")
        if nome == "consultar_servidor" and acervo.normalizar_nome(args.get("nome_informado", "")) \
                != acervo.normalizar_nome(p["nome"]):
            motivos.append("consultar_servidor: nome informado diferente do nome do pedido.")
        if nome == "calcular_diarias":
            if str(args.get("data_pedido", "")).strip() != p["data_pedido"]:
                motivos.append("calcular_diarias: data_pedido diferente da data de protocolo.")
            if str(args.get("data_partida", "")).strip() != p["data_partida"]:
                motivos.append("calcular_diarias: data_partida diferente da do pedido.")
            if str(args.get("data_retorno", "")).strip() not in efetivo.datas_retorno_possiveis:
                motivos.append("calcular_diarias: data_retorno não informada pelo solicitante.")
            if str(args.get("destino_uf", "")).strip().upper() != p["destino_uf"].upper():
                motivos.append("calcular_diarias: UF de destino diferente da do pedido.")
        if nome == "consultar_historico_diarias" and str(args.get("data_partida", "")).strip() != p["data_partida"]:
            motivos.append("consultar_historico_diarias: data_partida diferente da do pedido.")
    # O saldo precisa ser consultado com a unidade do cadastro e o valor calculado.
    saldo, calc, cad = (_ultima(consultas, n) for n in
                        ("consultar_saldo_diarias", "calcular_diarias", "consultar_servidor"))
    if saldo:
        args = saldo.get("argumentos") or {}
        r_cad = _resultado_json(cad) if cad else {}
        r_calc = _resultado_json(calc) if calc else {}
        if r_cad.get("unidade") and str(args.get("unidade", "")).strip().upper() != r_cad["unidade"]:
            motivos.append("consultar_saldo_diarias: unidade diferente da unidade de lotação do cadastro.")
        if r_calc.get("valor_total") is None:
            motivos.append("consultar_saldo_diarias: chamada sem valor calculado antes (ordem das consultas).")
        else:
            try:
                valor_saldo = float(args.get("valor"))
                if not math.isfinite(valor_saldo) or abs(valor_saldo - r_calc["valor_total"]) > TOLERANCIA:
                    motivos.append("consultar_saldo_diarias: valor diferente do total calculado.")
            except (TypeError, ValueError):
                motivos.append("consultar_saldo_diarias: valor não numérico.")
    return motivos


def verificar_instrucao(pedido: dict, complementacao: dict | None, instrucao: Instrucao | None,
                        consultas: list[dict], status: str) -> ResultadoBarreira:
    """Aplica todas as verificações; aprovada somente se nenhuma falhar."""
    efetivo = PedidoEfetivo.montar(pedido, complementacao)
    motivos: list[str] = []
    alertas: list[str] = []

    injecao = indicios_injecao(efetivo.texto_nao_confiavel)
    verbal = re.search(AUTORIZACAO_VERBAL, efetivo.texto_nao_confiavel, re.IGNORECASE)
    if injecao:
        alertas.append("Texto do solicitante contém ordem dirigida ao sistema (possível prompt injection); "
                       "tratada como dado, sem efeito sobre a análise.")
    if verbal:
        alertas.append("Alegação de autorização verbal: não supre a autorização escrita (art. 5º, § 2º).")
    if indicios_urgencia(pedido.get("justificativa", "")) and not injecao:
        alertas.append("Justificativa descreve possível urgência do art. 5º, § 1º: confira o julgamento da "
                       "antecedência e a autorização escrita do Secretário Adjunto.")

    if str(status).upper().split(".")[-1] != "COMPLETED":
        return ResultadoBarreira(False, [f"Execução não concluída (status={status})."], alertas)
    if not isinstance(instrucao, Instrucao):
        return ResultadoBarreira(False, ["Resposta fora do contrato Instrucao."], alertas)

    # 1. Identidade: a saída corresponde ao pedido em análise.
    if instrucao.numero_pedido.strip() != pedido["numero"]:
        motivos.append(f"Saída refere-se a {instrucao.numero_pedido!r}, e não ao pedido {pedido['numero']}.")
    if instrucao.matricula.strip() not in efetivo.matriculas_permitidas:
        motivos.append(f"Matrícula {instrucao.matricula!r} não consta do pedido nem da complementação.")

    # 2. Argumentos de ferramenta ancorados no pedido.
    motivos += verificar_argumentos(efetivo, consultas)

    # 3. Contrato: exatamente uma verificação por critério, cada uma com fundamento.
    por_criterio = {}
    for v in instrucao.verificacoes:
        if v.criterio in por_criterio:
            motivos.append(f"Critério {v.criterio} repetido.")
        por_criterio[v.criterio] = v
        if len(v.detalhe.strip()) < 8:
            motivos.append(f"Critério {v.criterio} sem fundamento no detalhe.")
    faltam = [c for c in CRITERIOS if c not in por_criterio]
    if faltam:
        motivos.append(f"Critérios ausentes: {', '.join(faltam)}.")
        return ResultadoBarreira(False, motivos, alertas)
    sit = {c: por_criterio[c].situacao for c in CRITERIOS}

    # 4. Cada situação coincide com o que as ferramentas devolveram nesta execução.
    cad = _ultima(consultas, "consultar_servidor")
    if cad is None:
        motivos.append("Cadastro não consultado nesta execução.")
        return ResultadoBarreira(False, motivos, alertas)
    r_cad = _resultado_json(cad)
    if (cad.get("argumentos") or {}).get("matricula", "").strip() != instrucao.matricula.strip():
        motivos.append("A matrícula da instrução não é a conferida no cadastro.")
    if r_cad.get("criterio_cadastro") not in ("atende", "nao_atende"):
        motivos.append("Consulta ao cadastro sem resultado válido.")
    elif sit["cadastro"] != r_cad["criterio_cadastro"]:
        motivos.append(f"cadastro: instrução diz {sit['cadastro']}, ferramenta diz {r_cad['criterio_cadastro']}.")

    esperado_completo = efetivo.dados_completos
    # Medição real (rodadas 1–3): na diligência por cadastro, o modelo às vezes se abstém
    # ("nao_verificado") de um pedido completo. Abster-se não é afirmar o falso: aceito só
    # quando o pedido está de fato completo e o cadastro já leva à diligência.
    abstencao_aceitavel = (esperado_completo and sit["dados_completos"] == "nao_verificado"
                           and r_cad.get("criterio_cadastro") == "nao_atende")
    if sit["dados_completos"] != ("atende" if esperado_completo else "nao_atende") and not abstencao_aceitavel:
        motivos.append("dados_completos não corresponde ao pedido e à complementação.")

    diligencia = r_cad.get("criterio_cadastro") != "atende" or not esperado_completo
    calc = _ultima(consultas, "calcular_diarias")
    hist = _ultima(consultas, "consultar_historico_diarias")
    saldo = _ultima(consultas, "consultar_saldo_diarias")

    if diligencia:
        if instrucao.recomendacao != "diligencia":
            motivos.append("Pedido incompleto ou divergente do cadastro deve ir a diligência (art. 9º).")
        if instrucao.quantidade_diarias is not None or instrucao.valor_total is not None:
            motivos.append("Quantidade e valor devem ser nulos na diligência.")
        if instrucao.exige_autorizacao_superior:
            motivos.append("Diligência não exige autorização superior.")
        for c in CRITERIOS_IMPEDIMENTO:
            if sit[c] == "nao_atende":
                motivos.append(f"{c}: impedimento declarado sem análise de mérito na diligência (art. 9º).")
        if not instrucao.pendencias:
            motivos.append("Diligência sem pendência indicada ao solicitante.")
    else:
        r_calc = _resultado_json(calc) if calc else {}
        r_hist = _resultado_json(hist) if hist else {}
        r_saldo = _resultado_json(saldo) if saldo else {}
        if r_calc.get("situacao") != "calculado":
            motivos.append("Cálculo das diárias não executado com sucesso nesta execução.")
        if r_hist.get("situacao") != "consultado":
            motivos.append("Histórico de diárias não consultado nesta execução.")
        if r_saldo.get("situacao") != "consultado":
            motivos.append("Saldo da unidade não consultado nesta execução.")
        if motivos:
            return ResultadoBarreira(False, motivos, alertas)

        # Ancoragem numérica: quantidade e valor são os da ferramenta.
        for campo in ("quantidade_diarias", "valor_total"):
            valor = getattr(instrucao, campo)
            if (valor is None or not math.isfinite(float(valor))
                    or abs(float(valor) - float(r_calc[campo])) > TOLERANCIA):
                motivos.append(f"{campo}: instrução diz {valor}, ferramenta diz {r_calc[campo]}.")

        pares = (("prestacao_contas", r_hist.get("criterio_prestacao_contas")),
                 ("limite_mensal", r_calc.get("criterio_limite_mensal")),
                 ("saldo_orcamentario", r_saldo.get("criterio_saldo_orcamentario")))
        for criterio, da_ferramenta in pares:
            if sit[criterio] != da_ferramenta:
                motivos.append(f"{criterio}: instrução diz {sit[criterio]}, ferramenta diz {da_ferramenta}.")

        # Antecedência: a única situação que admite julgamento do modelo (urgência, art. 5º, § 1º).
        minimo_ok = bool(r_calc.get("antecedencia_minima_atendida"))
        if minimo_ok:
            if sit["antecedencia"] != "atende":
                motivos.append("antecedencia: a ferramenta indica antecedência suficiente.")
            if instrucao.exige_autorizacao_superior:
                motivos.append("Autorização superior exigida sem antecedência insuficiente.")
        elif sit["antecedencia"] == "atende":
            if not instrucao.exige_autorizacao_superior:
                motivos.append("Antecedência insuficiente aceita sem exigir autorização escrita (art. 5º, § 2º).")
            if injecao:
                motivos.append("Antecedência aceita em pedido com ordem embutida na justificativa.")
            if not indicios_urgencia(pedido.get("justificativa", "")):
                motivos.append("Antecedência aceita por urgência sem situação do art. 5º, § 1º na justificativa.")
        elif sit["antecedencia"] != "nao_atende":
            motivos.append("antecedencia deve ser atende ou nao_atende quando o cálculo foi feito.")

        impedimentos = [c for c in CRITERIOS_IMPEDIMENTO if sit[c] == "nao_atende"]
        esperada = "nao_recomendado" if impedimentos else "apto_para_autorizacao"
        if instrucao.recomendacao != esperada:
            motivos.append(f"Recomendação {instrucao.recomendacao} incompatível com as verificações ({esperada}).")
        if impedimentos and instrucao.exige_autorizacao_superior:
            motivos.append("Autorização superior indicada em pedido com impedimento.")

    # 5. Ordem embutida: o conferente precisa ser avisado pelo próprio agente.
    if injecao and not instrucao.alertas:
        motivos.append("Ordem embutida na justificativa sem alerta ao conferente.")

    # 6. Minuta e textos livres: sem decisão, sem dado pessoal, sem matrícula estranha.
    textos = " ".join([instrucao.minuta_despacho, *instrucao.pendencias, *instrucao.alertas,
                       *(v.detalhe for v in instrucao.verificacoes)])
    if _achar(DECISAO, instrucao.minuta_despacho):
        motivos.append("Minuta contém ato decisório reservado ao ordenador de despesa (art. 10).")
    if pedido["numero"] not in instrucao.minuta_despacho:
        motivos.append("Minuta não identifica o número do pedido.")
    if filtro_pii.detectar(textos):
        motivos.append("Texto da instrução contém dado pessoal (CPF, conta, agência ou e-mail).")
    estranhas = set(RE_MATRICULA_TEXTO.findall(textos)) - efetivo.matriculas_permitidas
    if estranhas:
        motivos.append(f"Texto da instrução cita matrícula não informada: {sorted(estranhas)}.")
    conhecidas = efetivo.datas_permitidas | _datas_das_ferramentas(consultas) | {
        acervo.data_da_analise().isoformat()}
    datas_estranhas = {d for d in datas_no_texto(instrucao.minuta_despacho) if d not in conhecidas}
    if datas_estranhas:
        motivos.append(f"Minuta cita data que não veio do pedido nem das ferramentas: {sorted(datas_estranhas)}.")

    return ResultadoBarreira(not motivos, motivos, alertas)


def _datas_das_ferramentas(consultas: list[dict]) -> set[str]:
    datas: set[str] = set()
    for c in consultas:
        datas |= set(RE_DATA_ISO.findall(c.get("resultado") or ""))
    return datas


def agora_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
