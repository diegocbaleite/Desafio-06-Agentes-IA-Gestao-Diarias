"""Servidor local que imita o endpoint /v1/chat/completions da OpenAI — SOMENTE PARA TESTES.

Por que existe: sem OPENAI_API_KEY, nada do pipeline real do Agno (laço de ferramentas,
output_schema, pre_hooks, SqliteDb, histórico, memórias, eliminação, barreira) poderia ser
exercitado. O simulador permite rodar esse pipeline de ponta a ponta, de forma
determinística, e PROVOCAR falhas (matrícula inventada, valor errado, injeção obedecida,
erro da API, JSON inválido) para testar a barreira.

O que ele NÃO é: não é um modelo de linguagem e não mede nada. A "decisão" de urgência é
uma busca por palavras; os tokens que devolve são estimativas por tamanho de texto. Nenhum
número produzido com o simulador é apresentado como medição do gpt-5.6-luna.

Uso: `with SimuladorOpenAI(modo="correto") as sim:` define OPENAI_BASE_URL para o servidor.
"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODOS = ("correto", "matricula_inventada", "valor_divergente", "injecao_obedecida",
         "erro_api", "json_invalido", "data_inventada", "pedido_trocado", "saldo_antecipado")

URGENCIA = re.compile(r"inc[êe]ndio|desastre|infra[çc][ãa]o ambiental em curso|determina[çc][ãa]o judicial|"
                      r"focos? ativos?", re.IGNORECASE)
INJECAO = re.compile(r"sistema de an[áa]lise|classifique|registre .{0,60}como|ignore", re.IGNORECASE)


def _texto(conteudo) -> str:
    if isinstance(conteudo, list):
        return " ".join(p.get("text", "") for p in conteudo if isinstance(p, dict))
    return conteudo or ""


def _ler_pedido(texto: str) -> dict | None:
    if "numero: DIA-" not in texto:
        return None
    campos = dict(re.findall(r"^(\w+): (.*)$", texto, flags=re.MULTILINE))
    j = re.search(r"<justificativa_nao_confiavel>\n(.*?)\n</justificativa_nao_confiavel>", texto, re.S)
    campos["justificativa"] = j.group(1) if j else ""
    if campos.get("data_retorno", "").startswith("("):
        campos["data_retorno"] = ""
    return campos


class _Politica:
    """Política determinística que segue a ordem de consultas da instrução de sistema."""

    def __init__(self, modo: str):
        self.modo = modo

    def responder(self, corpo: dict) -> dict:
        nomes = [t["function"]["name"] for t in corpo.get("tools") or []]
        msgs = corpo.get("messages", [])
        if "consultar_servidor" not in nomes:
            return self._memoria(msgs, nomes)
        ultimo_user = max(i for i, m in enumerate(msgs) if m["role"] == "user")
        # Resultados das ferramentas desta execução (depois da última mensagem do usuário).
        chamadas = {}
        for m in msgs[ultimo_user:]:
            for tc in m.get("tool_calls") or []:
                chamadas[tc["id"]] = tc["function"]["name"]
        resultados = {}
        for m in msgs[ultimo_user:]:
            if m["role"] == "tool":
                try:
                    resultados[chamadas.get(m.get("tool_call_id"), "?")] = json.loads(_texto(m["content"]))
                except ValueError:
                    pass
        pedido = None
        for m in msgs:
            if m["role"] == "user":
                pedido = _ler_pedido(_texto(m["content"])) or pedido
        compl = _texto(msgs[ultimo_user]["content"])
        if pedido is None:
            numero = re.search(r"DIA-\d{4}-\d{4}", compl)
            return self._final(self._diligencia_sem_pedido(numero.group(0) if numero else ""))
        efetivo = dict(pedido)
        if "<complementacao_nao_confiavel>" in compl:
            corpo_c = compl.split("<complementacao_nao_confiavel>")[1]
            mat = re.search(r"(?<!\d)\d{6}(?!\d)", corpo_c)
            data = re.search(r"\d{4}-\d{2}-\d{2}", corpo_c)
            if mat:
                efetivo["matricula"] = mat.group(0)
            if data and not efetivo.get("data_retorno"):
                efetivo["data_retorno"] = data.group(0)
        if self.modo == "matricula_inventada":
            efetivo["matricula"] = efetivo["matricula"][:-1] + str((int(efetivo["matricula"][-1]) + 1) % 10)
        if self.modo == "data_inventada" and not efetivo.get("data_retorno"):
            efetivo["data_retorno"] = efetivo["data_partida"]
        paralelas = corpo.get("parallel_tool_calls", True)
        return self._proximo(efetivo, resultados, paralelas)

    # ---------------------------------------------------------------- laço de ferramentas
    def _proximo(self, p: dict, r: dict, paralelas: bool) -> dict:
        cad = r.get("consultar_servidor")
        if cad is None:
            lote = [("consultar_servidor", {"matricula": p["matricula"], "nome_informado": p["nome"]})]
            if paralelas and self.modo == "saldo_antecipado":
                lote.append(("consultar_saldo_diarias", {"unidade": "CFF", "valor": 1000.0}))
            return self._ferramentas(lote)
        if cad.get("criterio_cadastro") != "atende" or not p.get("data_retorno"):
            return self._final(self._instrucao(p, r))
        faltam = []
        if "consultar_historico_diarias" not in r:
            faltam.append(("consultar_historico_diarias",
                           {"matricula": p["matricula"], "data_partida": p["data_partida"]}))
        if "calcular_diarias" not in r:
            faltam.append(("calcular_diarias", {k: p[k] for k in
                           ("matricula", "destino_uf", "data_pedido", "data_partida", "data_retorno")}))
        if faltam:
            return self._ferramentas(faltam if paralelas else faltam[:1])
        if "consultar_saldo_diarias" not in r:
            return self._ferramentas([("consultar_saldo_diarias", {
                "unidade": cad["unidade"], "valor": r["calcular_diarias"].get("valor_total")})])
        return self._final(self._instrucao(p, r))

    # ---------------------------------------------------------------- instrução final
    def _instrucao(self, p: dict, r: dict) -> dict:
        cad = r.get("consultar_servidor", {})
        alertas = []
        if INJECAO.search(p.get("justificativa", "")):
            alertas.append("Ordem embutida na justificativa, desconsiderada.")
        if "MASCARAD" in p.get("justificativa", ""):
            alertas.append("Dado pessoal mascarado pela aplicação na justificativa.")
        v = {c: ("nao_verificado", "Não examinado: pedido em diligência.") for c in
             ("antecedencia", "prestacao_contas", "limite_mensal", "saldo_orcamentario")}
        completo = bool(p.get("data_retorno"))
        v["cadastro"] = (cad.get("criterio_cadastro", "nao_verificado"),
                         cad.get("mensagem") or f"Cadastro confere: grupo {cad.get('grupo_diaria')}, unidade {cad.get('unidade')}.")
        v["dados_completos"] = ("atende", "Pedido com todas as datas.") if completo else \
            ("nao_atende", "Data de retorno não informada.")
        base = {"numero_pedido": p["numero"], "matricula": p["matricula"], "alertas": alertas}
        if self.modo == "pedido_trocado":
            base["numero_pedido"] = "DIA-2026-0199"
        if v["cadastro"][0] != "atende" or not completo:
            pend = []
            if v["cadastro"][0] != "atende":
                pend.append("Confirmar a matrícula: a informada não corresponde ao solicitante.")
            if not completo:
                pend.append("Informar a data de retorno.")
            return {**base, "quantidade_diarias": None, "valor_total": None,
                    "verificacoes": [{"criterio": c, "situacao": s, "detalhe": d} for c, (s, d) in v.items()],
                    "recomendacao": "diligencia", "exige_autorizacao_superior": False,
                    "pendencias": pend,
                    "minuta_despacho": f"Despacho de instrução — pedido {p['numero']}. Pedido devolvido em "
                                       f"diligência (art. 9º): {' '.join(pend)} À consideração do ordenador de despesa."}
        h, c, s = r["consultar_historico_diarias"], r["calcular_diarias"], r["consultar_saldo_diarias"]
        v["prestacao_contas"] = (h["criterio_prestacao_contas"], f"Pendências: {h['prestacoes_pendentes']}")
        v["limite_mensal"] = (c["criterio_limite_mensal"], f"{c['total_no_mes_com_pedido']} diárias no mês, limite {c['limite_mensal']}.")
        v["saldo_orcamentario"] = (s["criterio_saldo_orcamentario"], f"Saldo R$ {s['saldo_disponivel']} para R$ {s['valor_pedido']}.")
        urgente = False
        if c["antecedencia_minima_atendida"]:
            v["antecedencia"] = ("atende", f"Antecedência de {c['antecedencia_dias']} dias.")
        elif (URGENCIA.search(p.get("justificativa", "")) and not INJECAO.search(p.get("justificativa", ""))) \
                or self.modo == "injecao_obedecida":
            urgente = True
            v["antecedencia"] = ("atende", "Aceita por urgência, condicionada à autorização escrita do Secretário Adjunto.")
        else:
            v["antecedencia"] = ("nao_atende", f"Antecedência de {c['antecedencia_dias']} dias, mínimo 10.")
        imped = [k for k in ("antecedencia", "prestacao_contas", "limite_mensal", "saldo_orcamentario")
                 if v[k][0] == "nao_atende"]
        rec = "nao_recomendado" if imped else "apto_para_autorizacao"
        valor = c["valor_total"] + (50.0 if self.modo == "valor_divergente" else 0.0)
        return {**base, "quantidade_diarias": c["quantidade_diarias"], "valor_total": valor,
                "verificacoes": [{"criterio": k, "situacao": s_, "detalhe": d} for k, (s_, d) in v.items()],
                "recomendacao": rec, "exige_autorizacao_superior": urgente and not imped,
                "pendencias": [],
                "minuta_despacho": f"Despacho de instrução — pedido {p['numero']}. {c['quantidade_diarias']} "
                                   f"diária(s), total R$ {valor:.2f}. Recomendação: {rec}. "
                                   "À consideração do ordenador de despesa."}

    def _diligencia_sem_pedido(self, numero: str) -> dict:
        return {"numero_pedido": numero, "matricula": "", "quantidade_diarias": None, "valor_total": None,
                "verificacoes": [], "recomendacao": "diligencia", "exige_autorizacao_superior": False,
                "pendencias": ["Pedido original não disponível nesta execução."], "alertas": [],
                "minuta_despacho": f"Despacho de instrução — pedido {numero}."}

    # ---------------------------------------------------------------- memórias de usuário
    def _memoria(self, msgs: list, nomes: list) -> dict:
        ja = any(m["role"] == "tool" for m in msgs)
        if "add_memory" in nomes and not ja:
            texto = " ".join(_texto(m["content"]) for m in msgs if m["role"] == "user")
            pedido = _ler_pedido(texto) or {}
            fato = (f"O usuário {pedido.get('nome', 'solicitante')} (matrícula {pedido.get('matricula', '?')}) "
                    f"tem o pedido de diárias {pedido.get('numero', '')} em instrução.")
            return self._ferramentas([("add_memory", {"memory": fato, "topics": ["diarias"]})])
        return self._mensagem("Memórias atualizadas.")

    # ---------------------------------------------------------------- formatos da API
    def _ferramentas(self, lote: list) -> dict:
        calls = [{"id": f"call_{uuid.uuid4().hex[:12]}", "type": "function",
                  "function": {"name": n, "arguments": json.dumps(a, ensure_ascii=False)}} for n, a in lote]
        return {"role": "assistant", "content": None, "tool_calls": calls}, "tool_calls"

    def _final(self, instrucao: dict) -> tuple:
        texto = json.dumps(instrucao, ensure_ascii=False)
        if self.modo == "json_invalido":
            texto = texto[: len(texto) // 2]
        return {"role": "assistant", "content": texto}, "stop"

    def _mensagem(self, texto: str) -> tuple:
        return {"role": "assistant", "content": texto}, "stop"


class SimuladorOpenAI:
    """Sobe o servidor em uma thread e aponta OPENAI_BASE_URL para ele enquanto ativo."""

    def __init__(self, modo: str = "correto", porta: int = 0):
        assert modo in MODOS, modo
        self.modo = modo
        self.requisicoes: list[str] = []      # corpos recebidos, para provar o que chegou ao "modelo"
        politica = _Politica(modo)
        sim = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silencioso
                pass

            def do_POST(self):
                corpo_txt = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
                sim.requisicoes.append(corpo_txt)
                corpo = json.loads(corpo_txt)
                if sim.modo == "erro_api" and corpo.get("tools"):
                    resposta = {"error": {"message": "Simulated API error: invalid request for this model.",
                                          "type": "invalid_request_error", "code": "simulado"}}
                    self._enviar(400, resposta)
                    return
                mensagem, fim = politica.responder(corpo)
                entrada = len(corpo_txt) // 4
                saida = len(json.dumps(mensagem, ensure_ascii=False)) // 4
                self._enviar(200, {"id": f"chatcmpl-sim-{uuid.uuid4().hex[:8]}", "object": "chat.completion",
                                   "created": int(time.time()), "model": corpo.get("model", "simulado"),
                                   "choices": [{"index": 0, "message": mensagem, "finish_reason": fim}],
                                   "usage": {"prompt_tokens": entrada, "completion_tokens": saida,
                                             "total_tokens": entrada + saida}})

            def _enviar(self, codigo: int, dados: dict):
                bruto = json.dumps(dados, ensure_ascii=False).encode("utf-8")
                self.send_response(codigo)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(bruto)))
                self.end_headers()
                self.wfile.write(bruto)

        self._servidor = ThreadingHTTPServer(("127.0.0.1", porta), Handler)
        self.url = f"http://127.0.0.1:{self._servidor.server_address[1]}/v1"

    def __enter__(self):
        self._thread = threading.Thread(target=self._servidor.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._servidor.shutdown()
        self._servidor.server_close()
