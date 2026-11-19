"""Formulário de conferência da instrução de pedidos de diárias — SEMA-MT (Desafio 01).

Execução: streamlit run app.py

A tela não conversa com o Agno: chama `instruir` e recebe um resultado já verificado pela
barreira. A chave da API é lida do .env pelo SDK e nunca é exibida.
"""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import streamlit as st

import config
from agente.agente_diarias import construir_agente, instruir
from agente.modelos import CRITERIOS
from ferramentas import acervo
from memoria import eliminacao, persistencia, verificacao
from seguranca import filtro_pii

st.set_page_config(page_title="Instrução de Diárias · SEMA-MT", page_icon="🌿", layout="wide")

CSS = """
<style>
:root { --verde:#0b5d3b; --verde-claro:#e8f3ee; --ambar:#8a5a00; --ambar-claro:#fff4dc;
        --vermelho:#9b1c1c; --vermelho-claro:#fdecec; --azul:#1e4e8c; --azul-claro:#e9f0fa; }
.block-container { padding-top: 1.6rem; max-width: 1280px; }
.cabecalho { background: linear-gradient(90deg, #0b5d3b, #13794f); color: #fff; padding: 18px 24px;
             border-radius: 12px; margin-bottom: 18px; }
.cabecalho h1 { color:#fff; font-size: 1.55rem; margin: 0; }
.cabecalho p { margin: 4px 0 0 0; opacity: .92; font-size: .95rem; }
.cartao { border: 1px solid #d9e2dc; border-radius: 10px; padding: 14px 16px; background: #fff; height: 100%; }
.cartao .rotulo { font-size: .78rem; text-transform: uppercase; letter-spacing: .04em; color: #5b6b62; }
.cartao .valor { font-size: 1.5rem; font-weight: 700; color: #1d2b23; }
.selo { display:inline-block; padding: 4px 12px; border-radius: 999px; font-weight: 700; font-size: .9rem; }
.selo-apto { background: var(--verde-claro); color: var(--verde); border: 1px solid #9fd0b8; }
.selo-diligencia { background: var(--ambar-claro); color: var(--ambar); border: 1px solid #f0cf8a; }
.selo-nao { background: var(--vermelho-claro); color: var(--vermelho); border: 1px solid #f2b4b4; }
.agente { border-left: 5px solid var(--azul); background: var(--azul-claro); padding: 12px 16px; border-radius: 8px; }
.humano { border-left: 5px solid var(--verde); background: var(--verde-claro); padding: 12px 16px; border-radius: 8px; }
.aviso-sim { background: #fff4dc; border: 1px dashed #c98a00; padding: 8px 12px; border-radius: 8px; font-size: .9rem; }
@media (prefers-color-scheme: dark) {
  .cartao { background: #1b211e; border-color: #33403a; }
  .cartao .valor { color: #eef5f0; } .cartao .rotulo { color: #a9b8af; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

ROTULOS_FERRAMENTA = {
    "consultar_servidor": "Consultando o cadastro funcional",
    "consultar_historico_diarias": "Consultando o histórico de diárias e prestações de contas",
    "calcular_diarias": "Calculando quantidade, valor, antecedência e limite mensal",
    "consultar_saldo_diarias": "Consultando o saldo da dotação da unidade",
}
ROTULOS_REC = {"apto_para_autorizacao": ("Apto para autorização", "selo-apto"),
               "diligencia": ("Diligência", "selo-diligencia"),
               "nao_recomendado": ("Não recomendado", "selo-nao")}
ENCAMINHAMENTOS = {"apto_para_autorizacao": "Apto para autorização — segue ao ordenador",
                   "diligencia": "Diligência — devolver ao solicitante",
                   "nao_recomendado": "Não recomendado — segue ao ordenador com impedimento",
                   "analise_manual": "Análise manual — instrução refeita pelo servidor"}
SITUACAO_ICONE = {"atende": "✅ atende", "nao_atende": "❌ não atende", "nao_verificado": "➖ não verificado"}


# ------------------------------------------------------------------ recursos em cache


@st.cache_resource
def simulador_local():
    from simulador.servidor_openai_simulado import SimuladorOpenAI
    return SimuladorOpenAI().__enter__()


@st.cache_resource
def agente_em_cache(modo: str):
    """Um único agente por modo. Seguro em cache: session_id e user_id vão em cada run."""
    if modo == "simulador":
        sim = simulador_local()
        return construir_agente(db_file=config.BANCOS / "agente_diarias_simulador.db",
                                base_url=sim.url, api_key="simulador")
    return construir_agente()


def banco_do_modo(modo: str):
    return config.BANCOS / ("agente_diarias_simulador.db" if modo == "simulador" else "agente_diarias.db")


def registro_do_modo(modo: str):
    return config.BANCOS / ("registro_conferencias_simulador.db" if modo == "simulador"
                            else "registro_conferencias.db")


PEDIDOS = {p["numero"]: p for p in acervo.pedidos()}
COMPLEMENTACOES = {c["numero"]: c for c in acervo.complementacoes()}
estado = st.session_state
estado.setdefault("resultados_por_modo", {})
estado.setdefault("pedido_atual", next(iter(PEDIDOS)))


# ------------------------------------------------------------------ barra lateral

with st.sidebar:
    st.markdown("### 🌿 SEMA-MT")
    st.caption("Coordenadoria de Diárias e Passagens")
    pagina = st.radio("Navegação", ["Painel", "Análise de pedidos", "Conferência humana", "Diligências",
                                    "Memória e LGPD", "Resultados e auditoria"], label_visibility="collapsed")
    st.divider()
    chave = config.chave_configurada()
    st.markdown(f"**API OpenAI:** {'🟢 configurada' if chave else '🔴 indisponível (sem chave)'}")
    st.markdown(f"**Modelo:** `{config.MODELO}`")
    modo = "api" if chave else "indisponivel"
    usar_sim = st.toggle("Modo demonstração (simulador local)", value=not chave,
                         help="Executa o pipeline real do Agno contra um simulador determinístico da API. "
                              "Não é o modelo de linguagem e não produz medições.")
    if usar_sim:
        modo = "simulador"
    st.caption(f"Paralelas: {'ligadas' if config.PARALLEL_TOOL_CALLS else 'desligadas'} · "
               f"tool_call_limit={config.TOOL_CALL_LIMIT} · num_history_runs={config.NUM_HISTORY_RUNS}")

# Cada análise pertence ao mesmo modo que o banco em que foi registrada.
estado.resultados = estado.resultados_por_modo.setdefault(modo, {})

st.markdown(
    "<div class='cabecalho'><h1>Instrução de Pedidos de Diárias</h1>"
    "<p>Agente Agno de apoio à conferência · IN SEMA nº 07/2026 (hipotética) · "
    "a decisão pertence exclusivamente ao ordenador de despesa</p></div>", unsafe_allow_html=True)
if modo == "simulador":
    st.markdown("<div class='aviso-sim'>⚠️ <b>Modo demonstração:</b> as instruções são produzidas por um "
                "simulador local da API, para exercitar ferramentas, barreira, memória e eliminação sem chave. "
                "Não representam o comportamento do modelo nem servem como medição.</div>",
                unsafe_allow_html=True)


def cartao(rotulo: str, valor) -> None:
    st.markdown(f"<div class='cartao'><div class='rotulo'>{rotulo}</div><div class='valor'>{valor}</div></div>",
                unsafe_allow_html=True)


def selo(recomendacao: str | None) -> str:
    texto, classe = ROTULOS_REC.get(recomendacao, ("Sem instrução verificada", "selo-nao"))
    return f"<span class='selo {classe}'>{texto}</span>"


def moeda(v) -> str:
    return "—" if v is None else f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def exigir_modo() -> bool:
    if modo == "indisponivel":
        st.error("A API do modelo não está configurada (OPENAI_API_KEY ausente). Ative o modo demonstração "
                 "na barra lateral ou configure o .env conforme o LEIA-ME.")
        return False
    return True


def executar(numero: str, complementacao: dict | None = None) -> None:
    """Executa a instrução com progresso visível e registra a análise."""
    agente = agente_em_cache(modo)
    titulo = "Instruindo a complementação" if complementacao else "Instruindo o pedido"
    with st.status(f"{titulo} {numero}", expanded=True) as status:
        st.write("Mascarando dados pessoais do texto livre e enviando ao agente…")
        resultado = instruir(agente, PEDIDOS[numero], complementacao,
                             ao_chamar_ferramenta=lambda nome, args: st.write(
                                 f"🔎 {ROTULOS_FERRAMENTA.get(nome, nome)} — argumentos: `{json.dumps(args, ensure_ascii=False)}`"))
        st.write("Conferindo a instrução na barreira de verificação…")
        analise_id = persistencia.registrar_analise(resultado, registro_do_modo(modo))
        rotulo = {"aprovada": "concluída e verificada", "recusada": "recusada pela barreira",
                  "erro_execucao": "com erro de execução"}[resultado.situacao]
        status.update(label=f"Instrução {rotulo} em {resultado.metricas.get('segundos', '?')} s",
                      state="complete" if resultado.aprovada else "error", expanded=False)
    estado.resultados[numero] = {"resultado": resultado.to_dict(), "analise_id": analise_id}


# ------------------------------------------------------------------ páginas


def pagina_painel() -> None:
    analises = persistencia.listar("analises", registro_do_modo(modo)) if modo != "indisponivel" else []
    divergencia = persistencia.taxa_divergencia(registro_do_modo(modo)) if modo != "indisponivel" else {}
    c = st.columns(5)
    with c[0]:
        cartao("Pedidos protocolados", len(PEDIDOS))
    with c[1]:
        cartao("Complementações", len(COMPLEMENTACOES))
    with c[2]:
        cartao("Análises registradas", len(analises))
    with c[3]:
        cartao("Recusadas pela barreira", sum(a["situacao"] != "aprovada" for a in analises))
    with c[4]:
        taxa = divergencia.get("taxa")
        cartao("Divergência do conferente", "—" if taxa is None else f"{taxa:.0%}")
    st.write("")
    esq, dir_ = st.columns([3, 2])
    with esq:
        st.subheader("Finalidade")
        st.markdown(
            "O sistema recebe o pedido de diárias **como foi protocolado**, consulta o cadastro funcional, o "
            "histórico de diárias e prestações de contas, calcula quantidade, valor, antecedência e limite "
            "mensal, confere o saldo da unidade e devolve uma **instrução para conferência**: as seis "
            "verificações da norma, a recomendação (*apto para autorização*, *diligência* ou *não recomendado*) "
            "e a minuta do despacho.\n\n"
            "Toda instrução passa por uma **barreira no código** antes de chegar à tela. O agente **não decide**: "
            "a decisão é do ordenador de despesa (art. 10).")
        st.subheader("Pedidos do acervo")
        linhas = []
        for n, p in PEDIDOS.items():
            r = estado.resultados.get(n, {}).get("resultado")
            linhas.append({"Pedido": n, "Solicitante": p["nome"], "Destino": f"{p['destino_municipio']}/{p['destino_uf']}",
                           "Partida": p["data_partida"], "Retorno": p["data_retorno"] or "não informado",
                           "Situação nesta sessão": "não analisado" if not r else
                           (ROTULOS_REC.get((r.get("instrucao") or {}).get("recomendacao"), ("análise manual",))[0])})
        st.dataframe(pd.DataFrame(linhas), hide_index=True, width="stretch")
    with dir_:
        st.subheader("Atendimento selecionado")
        n = estado.pedido_atual
        r = estado.resultados.get(n, {}).get("resultado")
        st.markdown(f"**{n}** — {PEDIDOS[n]['nome']}")
        if r:
            st.markdown(selo((r.get("instrucao") or {}).get("recomendacao")), unsafe_allow_html=True)
            st.caption(f"Sessão `{r['session_id']}` · user_id `{r['user_id']}` · {r['turno']}")
        else:
            st.caption("Ainda não analisado nesta sessão da aplicação.")
        st.subheader("Última avaliação contra o gabarito")
        for arquivo, rot in ((config.RESULTADOS / "execucao_casos_paralelas_desligadas.json", "API real"),
                             (config.RESULTADOS / "simulador" / "execucao_casos_paralelas_desligadas.json",
                              "Simulador (não é medição)")):
            if arquivo.exists():
                d = json.loads(arquivo.read_text(encoding="utf-8"))
                if d.get("situacao") == "nao_executado":
                    st.warning(f"{rot}: não executada — {d['motivo']}")
                else:
                    corretos = [r_["resumo"]["corretos"] for r_ in d["rodadas"]]
                    st.info(f"{rot}: corretos por rodada {corretos} de 14 · gerado em {d['gerado_em']}")


def pagina_analise() -> None:
    numero = st.selectbox("Pedido", list(PEDIDOS), index=list(PEDIDOS).index(estado.pedido_atual),
                          format_func=lambda n: f"{n} — {PEDIDOS[n]['nome']}")
    estado.pedido_atual = numero
    p = PEDIDOS[numero]
    st.subheader("Dados protocolados")
    a, b, c, d = st.columns(4)
    a.metric("Matrícula", p["matricula"])
    b.metric("Destino", f"{p['destino_municipio']}/{p['destino_uf']}")
    c.metric("Partida", p["data_partida"])
    d.metric("Retorno", p["data_retorno"] or "não informado")
    st.caption(f"Solicitante: {p['nome']} · protocolado em {p['data_pedido']} · transporte: {p['transporte']}")
    justificativa, mascarados = filtro_pii.mascarar_texto(p["justificativa"])
    st.text_area("Justificativa (dado não confiável; exibida com dados pessoais mascarados)", justificativa,
                 disabled=True, height=90)
    if mascarados:
        st.caption(f"🔒 Mascarado antes do envio ao modelo: {', '.join(mascarados)}")
    if st.button("▶ Iniciar análise", type="primary", disabled=modo == "indisponivel"):
        if exigir_modo():
            executar(numero)
    if modo == "indisponivel":
        exigir_modo()
    registro = estado.resultados.get(numero)
    if registro:
        mostrar_resultado(registro["resultado"])


def mostrar_resultado(r: dict) -> None:
    st.divider()
    if r["situacao"] != "aprovada":
        st.error(f"**{config.MENSAGEM_PADRAO}**")
        st.caption("O conteúdo recusado não é exibido. O registro técnico está em *Resultados e auditoria*.")
        return
    inst = r["instrucao"]
    topo = st.columns([2, 1, 1, 1])
    with topo[0]:
        st.markdown("<div class='agente'><b>Recomendação do agente</b> (sugestão, não decisão)<br>"
                    f"{selo(inst['recomendacao'])}</div>", unsafe_allow_html=True)
    topo[1].metric("Quantidade de diárias", "—" if inst["quantidade_diarias"] is None else
                   f"{inst['quantidade_diarias']:g}".replace(".", ","))
    topo[2].metric("Valor total", moeda(inst["valor_total"]))
    topo[3].metric("Autorização superior", "exigida" if inst["exige_autorizacao_superior"] else "não")
    st.subheader("Verificações da norma")
    st.dataframe(pd.DataFrame([{"Critério": v["criterio"], "Situação": SITUACAO_ICONE[v["situacao"]],
                                "Fundamento (como veio da ferramenta)": v["detalhe"]}
                               for v in sorted(inst["verificacoes"], key=lambda v: CRITERIOS.index(v["criterio"]))]),
                 hide_index=True, width="stretch")
    e, d = st.columns(2)
    with e:
        st.subheader("Pendências")
        for item in inst["pendencias"] or ["Nenhuma."]:
            st.markdown(f"- {item}")
    with d:
        st.subheader("Alertas")
        for item in inst["alertas"]:
            st.warning(f"Agente: {item}")
        for item in r["alertas_aplicacao"]:
            st.info(f"Aplicação: {item}")
        if not inst["alertas"] and not r["alertas_aplicacao"]:
            st.markdown("Nenhum.")
    st.subheader("Consultas realizadas (fontes da instrução)")
    for c in r["consultas"]:
        with st.expander(f"{ROTULOS_FERRAMENTA.get(c['ferramenta'], c['ferramenta'])} — "
                         f"`{json.dumps(c['argumentos'], ensure_ascii=False)}`"):
            try:
                st.json(json.loads(c["resultado"]))
            except ValueError:
                st.code(c["resultado"])
    st.subheader("Minuta do despacho (proposta)")
    st.code(inst["minuta_despacho"], language=None, wrap_lines=True)
    m = r["metricas"]
    st.caption(f"Sessão `{r['session_id']}` · user_id `{r['user_id']}` · {m.get('chamadas_modelo')} chamadas ao "
               f"modelo · {m.get('chamadas_ferramenta')} ferramentas · entrada {m.get('tokens_entrada')} / saída "
               f"{m.get('tokens_saida')} tokens · {m.get('segundos')} s · US$ {m.get('custo_usd')}"
               + (" (simulador — não é medição)" if modo == "simulador" else ""))
    st.info("Para registrar a conferência, abra **Conferência humana** na barra lateral.")


def pagina_conferencia() -> None:
    analisados = list(estado.resultados)
    if not analisados:
        st.info("Nenhum pedido analisado nesta sessão. Comece em **Análise de pedidos**.")
        return
    numero = st.selectbox("Pedido analisado", analisados,
                          index=analisados.index(estado.pedido_atual) if estado.pedido_atual in analisados else 0)
    reg = estado.resultados[numero]
    r = reg["resultado"]
    inst = r.get("instrucao")
    rec = inst["recomendacao"] if inst else None
    minuta_original = inst["minuta_despacho"] if inst else (
        f"Despacho de instrução — pedido {numero}. Instrução automática não verificada; pedido instruído "
        "manualmente pelo servidor. À consideração do ordenador de despesa.")
    col_ag, col_hum = st.columns(2)
    with col_ag:
        st.markdown("<div class='agente'><b>🤖 Recomendação do agente</b><br>" + (selo(rec) if inst else
                    "<span class='selo selo-nao'>Recusada pela barreira — análise manual</span>") + "</div>",
                    unsafe_allow_html=True)
        if inst:
            st.caption(f"Valor {moeda(inst['valor_total'])} · autorização superior: "
                       f"{'exigida' if inst['exige_autorizacao_superior'] else 'não'}")
    with col_hum:
        st.markdown("<div class='humano'><b>👤 Decisão do conferente</b><br>Registro humano, ao lado da "
                    "sugestão. A decisão final continua com o ordenador de despesa.</div>", unsafe_allow_html=True)
    with st.form(f"conferencia_{modo}_{numero}"):
        minuta = st.text_area("Minuta do despacho (editável)", minuta_original, height=180)
        opcoes = list(ENCAMINHAMENTOS)
        encaminhamento = st.selectbox("Encaminhamento decidido pelo servidor", opcoes,
                                      index=opcoes.index(rec) if rec in opcoes else opcoes.index("analise_manual"),
                                      format_func=ENCAMINHAMENTOS.get)
        justificativa = st.text_area("Justificativa (obrigatória se divergir do agente ou sem instrução verificada)")
        conferente = st.text_input("Servidor conferente (nome ou matrícula funcional)")
        enviado = st.form_submit_button("Registrar conferência", type="primary")
    if enviado:
        try:
            cid = persistencia.registrar_conferencia(numero, reg["analise_id"], rec, encaminhamento, justificativa,
                                                     minuta, minuta_original, conferente, registro_do_modo(modo))
        except ValueError as erro:
            st.error(str(erro))
        else:
            divergiu = rec is not None and encaminhamento != rec
            st.success(f"Conferência nº {cid} registrada" + (" — **diverge do agente**." if divergiu else "."))
            st.download_button("Baixar minuta conferida", minuta, file_name=f"despacho_{numero}.txt")
    hist = persistencia.listar("conferencias", registro_do_modo(modo), numero)
    if hist:
        st.subheader("Conferências registradas deste pedido")
        st.dataframe(pd.DataFrame(hist)[["id", "recomendacao_agente", "encaminhamento_servidor", "divergiu",
                                         "justificativa", "minuta_editada", "conferente", "registrado_em"]],
                     hide_index=True, width="stretch")


def pagina_diligencias() -> None:
    em_diligencia = [n for n, reg in estado.resultados.items()
                     if (reg["resultado"].get("instrucao") or {}).get("recomendacao") == "diligencia"]
    st.markdown("A complementação é enviada **na mesma sessão** do pedido (`session_id` = número do pedido); "
                "o agente recupera o pedido original pelo histórico da sessão.")
    opcoes = em_diligencia or list(COMPLEMENTACOES)
    if not em_diligencia:
        st.info("Nenhum pedido em diligência nesta sessão. Os pedidos com complementação no acervo estão listados; "
                "analise-os antes em **Análise de pedidos** para que a sessão exista.")
    numero = st.selectbox("Pedido em diligência", opcoes)
    sessoes = {s["session_id"]: s["user_id"] for s in verificacao.sessoes(banco_do_modo(modo))}
    if numero in sessoes:
        st.success(f"Sessão anterior recuperada: `{numero}` gravada sob user_id `{sessoes[numero]}`.")
        if sessoes[numero] != PEDIDOS[numero]["matricula"]:
            st.warning("A sessão está associada a uma matrícula diferente da protocolada.")
    else:
        st.warning("Não há sessão gravada para este pedido no banco do agente.")
    padrao = COMPLEMENTACOES.get(numero, {})
    with st.form(f"complementacao_{modo}"):
        texto = st.text_area("Complementação apresentada pelo solicitante", padrao.get("texto", ""), height=100)
        data = st.text_input("Data de recebimento (AAAA-MM-DD)", padrao.get("data", datetime.now().date().isoformat()))
        enviar = st.form_submit_button("Reanalisar na mesma sessão", type="primary", disabled=modo == "indisponivel")
    if enviar and exigir_modo():
        if not texto.strip():
            st.error("Informe a complementação.")
        else:
            executar(numero, {"numero": numero, "data": data, "texto": texto})
            r = estado.resultados[numero]["resultado"]
            if r["user_id"] != PEDIDOS[numero]["matricula"]:
                st.warning(f"Atenção: execução sob user_id {r['user_id']}.")
            mostrar_resultado(r)


def pagina_lgpd() -> None:
    db = banco_do_modo(modo)
    st.markdown(f"Banco de trabalho do agente: `{db.name}`. **Inspeção autorizada** — use apenas para "
                "atender pedido do titular ou auditoria.")
    st.caption("Alcance: a eliminação atinge somente o banco do agente (cópia de trabalho). O processo de diárias, "
               "as análises e as conferências são registro administrativo de despesa pública e seguem a guarda "
               "legal da prestação de contas.")
    autorizado = st.checkbox("Declaro que a inspeção é autorizada (pedido do titular ou auditoria)",
                             key=f"inspecao_autorizada_{modo}")
    if not autorizado:
        return
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Registros por tabela")
        st.dataframe(pd.DataFrame([{"tabela": t, "registros": n} for t, n in verificacao.contar_registros(db).items()]),
                     hide_index=True, width="stretch")
    with c2:
        st.subheader("Sessões gravadas")
        st.dataframe(pd.DataFrame(verificacao.sessoes(db)), hide_index=True, width="stretch")
    st.subheader("Eliminação dos dados de um titular")
    titulares = {p["matricula"]: p["nome"] for p in PEDIDOS.values()}
    titulares.update({"207418": "Carla Regina Souza"})
    matricula = st.selectbox("Titular", sorted(titulares), format_func=lambda m: f"{m} — {titulares[m]}",
                            key=f"titular_{modo}")
    nome = titulares[matricula]
    loc = eliminacao.localizar(db, matricula, nome)
    a, b, c = st.columns(3)
    a.metric("Sessões sob o user_id do titular", len(loc.sessoes_do_titular))
    b.metric("Sessões que o citam sob outro user_id", len(loc.sessoes_sob_outro_user_id))
    c.metric("Memórias do titular", len(loc.memorias_do_titular) + len(loc.memorias_sob_outro_user_id))
    confirmadas = []
    for s in loc.sessoes_sob_outro_user_id:
        rotulo = (f"Sessão {s['session_id']} gravada sob user_id {', '.join(s['user_ids'])} — "
                  f"vínculo pelo pedido: {'verificado' if s['vinculo_verificado'] else 'NÃO verificado'}")
        if st.checkbox(rotulo, key=f"conf_{modo}_{matricula}_{s['session_id']}",
                       disabled=not s["vinculo_verificado"]):
            confirmadas.append(s["session_id"])
    memorias_alheias = [m["memory_id"] for m in loc.memorias_sob_outro_user_id]
    incluir_memorias = bool(memorias_alheias) and st.checkbox(
        f"Incluir {len(memorias_alheias)} memória(s) sob outro user_id que citam o titular",
        key=f"incluir_memorias_{modo}_{matricula}")
    confirma = st.checkbox("Confirmo o pedido de eliminação do titular e a verificação do vínculo",
                           key=f"confirmar_eliminacao_{modo}_{matricula}")
    if st.button("Eliminar e verificar no banco", type="primary", disabled=not confirma):
        ev = eliminacao.eliminar(db, matricula, nome, confirmadas,
                                 memorias_alheias if incluir_memorias else [], executado_por="formulário")
        config.EVIDENCIAS.mkdir(parents=True, exist_ok=True)
        arquivo = config.EVIDENCIAS / f"eliminacao_{modo}_{matricula}_{datetime.now():%Y%m%d%H%M%S}.json"
        arquivo.write_text(json.dumps(ev, ensure_ascii=False, indent=2), encoding="utf-8")
        (st.success if ev["nada_restou"] else st.error)(
            "Nada restou no banco do agente." if ev["nada_restou"] else
            "Ainda há ocorrências do titular no banco — veja abaixo o que não foi apagado e por quê.")
        st.json({"ações": ev["acoes"], "não apagadas": ev["nao_apagadas"], "antes": ev["antes"]["ocorrencias"],
                 "depois": ev["depois"]["ocorrencias"], "registros depois": ev["depois"]["registros_por_tabela"]})
        st.caption(f"Evidência gravada em resultados/evidencias/{arquivo.name}")


def pagina_resultados() -> None:
    abas = st.tabs(["Avaliação contra o gabarito", "Memória", "Falhas provocadas", "Histórico de análises",
                    "Evidências de testes"])
    pastas = [("API real", config.RESULTADOS), ("Simulador (não é medição)", config.RESULTADOS / "simulador")]

    def carregar(nome):
        for rot, pasta in pastas:
            arq = pasta / nome
            yield rot, (json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else None)

    with abas[0]:
        for rot, d in carregar("execucao_casos_paralelas_desligadas.json"):
            st.markdown(f"#### {rot}")
            if not d:
                st.caption("Arquivo não gerado.")
            elif d.get("situacao") == "nao_executado":
                st.warning(d["motivo"])
            else:
                st.dataframe(pd.DataFrame([{"rodada": r_["rodada"], **{k: v for k, v in r_["resumo"].items()
                                            if not isinstance(v, (dict, list))}} for r_ in d["rodadas"]]),
                             hide_index=True, width="stretch")
                st.dataframe(pd.DataFrame([{"caso": c["caso"], "esperado": c["esperado"], "obtido": c["obtido"],
                                            "situação": c["situacao"], "correto": c["comparacao"]["correto"]}
                                           for c in d["rodadas"][0]["casos"]]), hide_index=True, width="stretch")
        for rot, d in carregar("comparacao_desempenho.json"):
            if d and d.get("comparacao_paralelas"):
                st.markdown(f"#### Chamadas paralelas — {rot}")
                st.json(d["comparacao_paralelas"], expanded=False)
    with abas[1]:
        for rot, d in carregar("medicao_memoria.json"):
            st.markdown(f"#### {rot}")
            if not d:
                st.caption("Arquivo não gerado.")
            elif d.get("situacao") == "nao_executado":
                st.warning(d["motivo"])
            else:
                st.dataframe(pd.DataFrame([{"configuração": l["configuracao"], "pedido": l["pedido"],
                                            "entrada T1": l["turno1"].get("tokens_entrada"),
                                            "entrada T2": l["turno2"].get("tokens_entrada"),
                                            "aplicada ao pedido certo": l["complementacao_aplicada_ao_pedido_certo"]}
                                           for l in d["linhas"]]), hide_index=True, width="stretch")
                for n in ("DIA-2026-0111", "DIA-2026-0112"):
                    e = d["eliminacao"].get(n)
                    if e:
                        st.markdown(f"**Eliminação {n}:** sem confirmação → nada restou = "
                                    f"`{e['sem_confirmacao']['nada_restou']}`; com vínculo confirmado → "
                                    f"`{e['com_confirmacao']['nada_restou']}`")
    with abas[2]:
        for rot, d in carregar("falhas_provocadas.json"):
            st.markdown(f"#### {rot}")
            if not d:
                st.caption("Arquivo não gerado.")
            elif d.get("situacao") == "nao_executado":
                st.warning(d["motivo"])
            else:
                st.dataframe(pd.DataFrame([{"id": f["id"], "falha": f["falha"], "situação": f["situacao"],
                                            "entregue ao conferente": f["recomendacao_entregue"],
                                            "detectada ou inofensiva": f["detectada_ou_inofensiva"],
                                            "motivos (auditoria)": "; ".join(f["motivos_recusa"])[:200]}
                                           for f in d["falhas"]]), hide_index=True, width="stretch")
    with abas[3]:
        if modo == "indisponivel":
            st.caption("Sem registros (API indisponível e modo demonstração desligado).")
        else:
            analises = persistencia.listar("analises", registro_do_modo(modo))
            if analises:
                df = pd.DataFrame(analises)[["id", "numero", "turno", "situacao", "recomendacao", "valor_total",
                                             "motivos_recusa", "registrado_em"]]
                st.dataframe(df, hide_index=True, width="stretch")
                st.caption("A coluna motivos_recusa é registro técnico de auditoria; o conteúdo recusado nunca é "
                           "apresentado ao conferente como instrução.")
            st.json(persistencia.taxa_divergencia(registro_do_modo(modo)))
    with abas[4]:
        for arq in sorted(config.EVIDENCIAS.glob("*.txt")):
            with st.expander(arq.name):
                st.code(arq.read_text(encoding="utf-8")[-6000:], language=None)


{"Painel": pagina_painel, "Análise de pedidos": pagina_analise, "Conferência humana": pagina_conferencia,
 "Diligências": pagina_diligencias, "Memória e LGPD": pagina_lgpd,
 "Resultados e auditoria": pagina_resultados}[pagina]()
