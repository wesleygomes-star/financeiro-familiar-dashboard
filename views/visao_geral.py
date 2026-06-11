"""Visão Geral — painel principal v4 (família, sem 'Casal', com auditoria)."""
import re
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.data import (
    aportes_historico,
    auditar_contas_fixas,
    compromissos_proximos_meses,
    fatura_estimada,
    fatura_split_pessoa,
    kpis_familia,
    load_faturas,
    load_lancamentos,
    load_recorrentes,
    load_saldo_investido,
    meses_disponiveis,
    saldo_estocado_atual,
    split_movimentos,
)


# set_page_config + auth ficam no router (streamlit_app.py)

# ============== CSS responsivo (mobile-first) ==============
st.markdown(
    """
    <style>
    /* Reduz padding excessivo do Streamlit em qualquer tela */
    .block-container { max-width: 100% !important; padding-top: 1rem !important; }

    /* === MOBILE (≤ 768px) === */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 1rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        /* Default: colunas viram stack vertical */
        div[data-testid="stColumn"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 0.4rem !important;
        }
        /* KPI metric maior pra leitura no celular */
        div[data-testid="stMetricValue"] { font-size: 1.5rem !important; }
        div[data-testid="stMetricLabel"] { font-size: 0.85rem !important; }
        div[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }
        /* Headings menores */
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1.05rem !important; }
        .stSubheader { font-size: 1.1rem !important; }
        /* Containers com borda ganham padding interno menor */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 0.6rem 0.7rem !important;
        }
        /* Dataframes scroll horizontal sem quebrar layout */
        div[data-testid="stDataFrame"] { overflow-x: auto; }
        /* Captions mais legíveis */
        div[data-testid="stCaptionContainer"] p { font-size: 0.78rem !important; }
        /* Botões com tap-target generoso */
        button { min-height: 36px !important; }
        /* Selects/radios em row ficam responsivos */
        div[data-baseweb="select"] { min-width: 100% !important; }
        /* Plotly charts com altura mínima legível */
        .stPlotlyChart { min-height: 280px !important; }
        /* Reduzir gap entre divider e conteúdo */
        hr { margin: 0.6rem 0 !important; }
    }

    /* === TABLET (≤ 1024px) === */
    @media (max-width: 1024px) and (min-width: 769px) {
        div[data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    }

    /* === KPI / Card grids custom (HTML inline) === */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 16px;
    }
    .kpi-card {
        background: rgba(128, 128, 128, 0.08);
        border-radius: 8px;
        padding: 14px 16px;
    }
    .kpi-label {
        font-size: 11px;
        color: var(--text-color-muted, #888);
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    .kpi-value {
        font-size: 22px;
        font-weight: 500;
        line-height: 1.2;
    }
    .kpi-mini {
        border-top: 0.5px solid rgba(128, 128, 128, 0.2);
        margin-top: 8px;
        padding-top: 8px;
        font-size: 11px;
        line-height: 1.7;
    }
    .kpi-mini-row {
        display: flex;
        justify-content: space-between;
    }
    .kpi-mini-row span:first-child { opacity: 0.7; }
    .kpi-mini-row strong { font-weight: 500; }
    .kpi-card.green .kpi-value { color: #1D9E75; }
    .kpi-card.info { background: rgba(55, 138, 221, 0.10); border: 2px solid rgba(55, 138, 221, 0.35); }
    .kpi-card.info .kpi-label, .kpi-card.info .kpi-value { color: #185FA5; }
    .kpi-card.warning { background: rgba(239, 159, 39, 0.13); }
    .kpi-card.warning .kpi-label, .kpi-card.warning .kpi-value, .kpi-card.warning .kpi-mini { color: #854F0B; }
    .estimado-tag { font-size: 10px; font-style: italic; opacity: 0.85; }

    /* 3-col grid responsivo (Caixa × Competência) */
    .grid-3 {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 14px;
        margin-bottom: 14px;
    }
    .grid-3 > div {
        border: 0.5px solid rgba(128, 128, 128, 0.25);
        border-radius: 8px;
        padding: 14px 16px;
    }
    .grid-3 > div.warning {
        background: rgba(239, 159, 39, 0.13);
        border-color: rgba(239, 159, 39, 0.4);
        color: #854F0B;
    }

    /* Responsivo: 4-col → 2x2 em mobile, 3-col → stack */
    @media (max-width: 768px) {
        .kpi-grid { grid-template-columns: 1fr 1fr !important; gap: 8px; }
        .kpi-value { font-size: 18px !important; }
        .grid-3 { grid-template-columns: 1fr !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def fmt(v: float, com_cifrao: bool = True) -> str:
    s = f"{abs(v):,.0f}".replace(",", ".")
    sinal = "-" if v < 0 else ""
    return f"{sinal}R$ {s}" if com_cifrao else f"{sinal}{s}"


# ============== Carregar dados ==============
df_lanc = load_lancamentos(incluir_cancelados=False)
df_rec = load_recorrentes()
df_faturas = load_faturas()
df_saldo = load_saldo_investido()

# ============== Header + filtros ==============
st.title("💰 Visão Geral")

c_filtro, c_modo, c_refresh = st.columns([2, 2, 1])
meses_caixa = meses_disponiveis(df_lanc, modo="Caixa")
meses_comp = meses_disponiveis(df_lanc, modo="Competência")
meses_lista = meses_caixa or meses_comp or [f"{datetime.now().month:02d}/{datetime.now().year}"]
mes_corrente = f"{datetime.now().month:02d}/{datetime.now().year}"
idx_default = meses_lista.index(mes_corrente) if mes_corrente in meses_lista else 0

with c_filtro:
    competencia = st.selectbox("Mês", meses_lista, index=idx_default)
with c_modo:
    modo = st.radio("Visão", ["Caixa", "Competência"], horizontal=True, index=0,
                    help="Caixa: quando o $ sai (vencimento da fatura). Competência: data da compra.")
with c_refresh:
    st.write("")  # espaço
    if st.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

# ============== KPIs (4 cards via HTML grid responsivo) ==============
kpis = kpis_familia(df_lanc, df_saldo, competencia, modo=modo)

st.subheader("Indicadores do mês")

def _mini_rows(d: dict) -> str:
    if not d:
        return '<div class="kpi-mini-row"><span>sem lançamentos</span><strong>—</strong></div>'
    return "".join(f'<div class="kpi-mini-row"><span>{p}</span><strong>{fmt(v)}</strong></div>' for p, v in d.items())

# KPI 1: Receita
kpi_receita = f"""
<div class="kpi-card green">
  <div class="kpi-label">💵 Receita família</div>
  <div class="kpi-value">{fmt(kpis['receita_total'])}</div>
  <div class="kpi-mini">{_mini_rows(kpis['receita_por_pessoa'])}</div>
</div>
"""

# KPI 2: Gastos
kpi_gastos = f"""
<div class="kpi-card">
  <div class="kpi-label">💳 Gastos família</div>
  <div class="kpi-value">{fmt(kpis['despesa_total'])}</div>
  <div class="kpi-mini">{_mini_rows(kpis['despesa_por_pessoa'])}</div>
</div>
"""

# KPI 3: Investido (condicional — sem falso positivo)
aporte = kpis["aporte_total"]
estocado = kpis["saldo_estocado_total"]
if aporte == 0 and estocado == 0:
    kpi_invest = """
    <div class="kpi-card info">
      <div class="kpi-label">📈 Investido</div>
      <div class="kpi-value" style="font-size: 14px; line-height: 1.4;">Categoria Investimentos ainda não rastreada</div>
      <div class="kpi-mini">
        <div>➕ Lançar 1º aporte</div>
        <div>👁 Ver histórico ↓</div>
      </div>
    </div>
    """
else:
    aporte_mini = _mini_rows(kpis["aporte_por_pessoa"])
    estocado_html = f'<div class="kpi-mini-row" style="border-top: 0.5px solid rgba(128,128,128,0.2); margin-top: 4px; padding-top: 4px;"><span>📦 estocado</span><strong>{fmt(estocado)}</strong></div>' if estocado > 0 else ''
    kpi_invest = f"""
    <div class="kpi-card info">
      <div class="kpi-label">📈 Investido</div>
      <div class="kpi-value">{fmt(aporte) if aporte > 0 else '—'}</div>
      <div class="kpi-mini">{aporte_mini}{estocado_html}</div>
    </div>
    """

# KPI 4: Faturas
faturas_html_rows = ""
total_pend = 0
qtd_pend = 0
is_estimado = False
if not df_faturas.empty and "Status" in df_faturas.columns and "Vencimento_dt" in df_faturas.columns:
    # "A debitar" = ainda vai sair $ — inclui Carregada com vencimento futuro
    # (Carregada ≠ paga; só Carregada COM vencimento passado já debitou)
    ab = df_faturas[df_faturas["Status"].astype(str).str.lower().isin(["pendente", "carregada"])].copy()
    hoje = pd.Timestamp(datetime.now().date())
    ab["_dias"] = (ab["Vencimento_dt"] - hoje).dt.days
    ab["_carregada"] = ab["Status"].astype(str).str.lower() == "carregada"
    pend = ab[~(ab["_carregada"] & (ab["_dias"] < 0))]
    pend = pend[(pend["_dias"] >= -30) & (pend["_dias"] <= 30)].sort_values("_dias")
    qtd_pend = len(pend)
    # buckets
    em_5 = pend[(pend["_dias"] >= 0) & (pend["_dias"] <= 5)]
    em_7 = pend[(pend["_dias"] > 5) & (pend["_dias"] <= 7)]
    em_30 = pend[(pend["_dias"] > 7) & (pend["_dias"] <= 30)]
    _flag = [False]
    def soma_bucket(df_):
        s = 0.0
        for _, r in df_.iterrows():
            v = float(r.get("Total_num", 0) or 0)
            if v <= 0:
                v_est, _ = fatura_estimada(str(r.get("Cartão", "")), str(r.get("Mês Referência", "")), df_lanc)
                v = v_est
                if v > 0:
                    _flag[0] = True
            s += v
        return s
    t5, t7, t30 = soma_bucket(em_5), soma_bucket(em_7), soma_bucket(em_30)
    total_pend = t5 + t7 + t30
    is_estimado = _flag[0]
    if len(em_5):
        faturas_html_rows += f'<div class="kpi-mini-row"><span>{len(em_5)} em até 5d</span><strong>{fmt(t5)}</strong></div>'
    if len(em_7):
        faturas_html_rows += f'<div class="kpi-mini-row"><span>{len(em_7)} em 7d</span><strong>{fmt(t7)}</strong></div>'
    if len(em_30):
        faturas_html_rows += f'<div class="kpi-mini-row"><span>{len(em_30)} em 30d</span><strong>{fmt(t30)}</strong></div>'

valor_label = (f'~ {fmt(total_pend)}' if is_estimado else fmt(total_pend)) if total_pend > 0 else '—'
estimado_label = '<div class="estimado-tag">estimado de lançamentos individuais</div>' if is_estimado else ''
kpi_faturas = f"""
<div class="kpi-card warning">
  <div class="kpi-label">⚠️ Faturas a debitar</div>
  <div class="kpi-value">{valor_label}</div>
  {estimado_label}
  <div class="kpi-mini">{faturas_html_rows or '<div class="kpi-mini-row"><span>Nenhuma na janela 30d</span></div>'}</div>
</div>
"""

# Achata o HTML em 1 linha — markdown trata linhas com 4+ espaços de indentação
# como code block e renderiza o HTML cru (bug visto em produção 11/06)
_kpi_html = re.sub(r"\n\s*", "", f'<div class="kpi-grid">{kpi_receita}{kpi_gastos}{kpi_invest}{kpi_faturas}</div>')
st.markdown(_kpi_html, unsafe_allow_html=True)

st.divider()

# ============== Caixa × Competência ==============
st.subheader("Caixa × competência")

splits_caixa = split_movimentos(df_lanc[df_lanc["Mês Caixa"] == competencia]) if "Mês Caixa" in df_lanc.columns else {"despesas": pd.DataFrame()}
splits_comp = split_movimentos(df_lanc[df_lanc["Competência"] == competencia]) if "Competência" in df_lanc.columns else {"despesas": pd.DataFrame()}

caixa_total = float(splits_caixa["despesas"]["Valor"].sum()) if not splits_caixa["despesas"].empty else 0.0
comp_total = float(splits_comp["despesas"]["Valor"].sum()) if not splits_comp["despesas"].empty else 0.0
empurrado = comp_total - caixa_total

empurrado_class = "warning" if empurrado > 0 else ""
if empurrado > 0:
    empurrado_sub = "parcelas que vão pesar próximos meses"
elif empurrado < 0:
    empurrado_sub = "caixa pagou compromissos de meses anteriores (faturas)"
else:
    empurrado_sub = "tudo decidido foi pago"

cx_html = f"""
<div class="grid-3">
  <div>
    <div class="kpi-label">🪙 Caixa do mês</div>
    <div style="font-size: 20px; font-weight: 500;">{fmt(caixa_total)}</div>
    <div style="font-size: 11px; opacity: 0.7; margin-top: 4px;">o que saiu em $ esse mês (vencimentos + débitos)</div>
  </div>
  <div>
    <div class="kpi-label">📅 Competência do mês</div>
    <div style="font-size: 20px; font-weight: 500;">{fmt(comp_total)}</div>
    <div style="font-size: 11px; opacity: 0.7; margin-top: 4px;">o que foi decidido (data da compra)</div>
  </div>
  <div class="{empurrado_class}">
    <div class="kpi-label">{'🟠' if empurrado > 0 else '🟢'} Empurrado pro futuro</div>
    <div style="font-size: 20px; font-weight: 500;">{fmt(empurrado)}</div>
    <div style="font-size: 11px; opacity: 0.75; margin-top: 4px;">{empurrado_sub}</div>
  </div>
</div>
"""
st.markdown(re.sub(r"\n\s*", "", cx_html), unsafe_allow_html=True)

st.divider()

# ============== Contas Fixas — Auditoria ==============
st.subheader("Contas fixas · auditoria de pagamento")

audit = auditar_contas_fixas(df_lanc, df_rec, competencia)
if audit.empty:
    st.info("Sem recorrentes cadastrados (aba Recorrentes vazia ou sem Ativo='Sim').")
else:
    # Detecta se TODAS as recorrentes têm o mesmo Dia Cobrança (sinal de placeholder não revisado)
    dias_unicos = audit["Dia Cobrança"].nunique()
    todos_dia_5 = (dias_unicos == 1 and int(audit["Dia Cobrança"].iloc[0]) == 5)

    if todos_dia_5:
        # Mostra banner + funde Atrasada em Pendente (sem distinção até Wesley revisar)
        col_warn, col_btn = st.columns([5, 1])
        with col_warn:
            st.warning(
                f"**{len(audit)} das {len(audit)} recorrentes estão como Dia Cobrança = 5** — "
                "enquanto isso, _atrasada_ vs _pendente_ ficam indistinguíveis. "
                "Status \"Atrasada\" volta automático quando você corrigir os Dias.",
                icon="📅",
            )
        with col_btn:
            if st.button("Revisar agora", key="rev_dias", use_container_width=True):
                st.session_state["revisar_dias"] = True
        audit_show = audit.copy()
        audit_show.loc[audit_show["Status"] == "Atrasada", "Status"] = "Pendente"
    else:
        audit_show = audit

    pagas = audit_show[audit_show["Status"] == "Paga"]
    pend = audit_show[audit_show["Status"] == "Pendente"]
    atras = audit_show[audit_show["Status"] == "Atrasada"]

    if todos_dia_5:
        cs1, cs2, cs3 = st.columns(3)
        cs1.metric("✅ Pagas", len(pagas), fmt(float(pagas["Valor Pago"].sum())) if not pagas.empty else "R$ 0")
        cs2.metric("⏳ Pendentes", len(pend), fmt(float(pend["Valor Esperado"].sum())) if not pend.empty else "R$ 0")
        total_esp = float(audit_show["Valor Esperado"].sum())
        total_pago = float(audit_show["Valor Pago"].sum())
        pct = (total_pago / total_esp * 100) if total_esp > 0 else 0
        cs3.metric("Esperado / pago", fmt(total_esp), f"{pct:.0f}% pago")
    else:
        cs1, cs2, cs3, cs4 = st.columns(4)
        cs1.metric("✅ Pagas", len(pagas), fmt(float(pagas["Valor Pago"].sum())) if not pagas.empty else "R$ 0")
        cs2.metric("⏳ Pendentes", len(pend), fmt(float(pend["Valor Esperado"].sum())) if not pend.empty else "R$ 0")
        cs3.metric("🔴 Atrasadas", len(atras), fmt(float(atras["Valor Esperado"].sum())) if not atras.empty else "R$ 0")
        total_esp = float(audit_show["Valor Esperado"].sum())
        total_pago = float(audit_show["Valor Pago"].sum())
        pct = (total_pago / total_esp * 100) if total_esp > 0 else 0
        cs4.metric("Esperado / pago", fmt(total_esp), f"{pct:.0f}% pago")

    # Lista ordenada: atrasadas → pendentes → pagas
    audit_sort = audit_show.copy()
    audit_sort["_ord"] = audit_sort["Status"].map({"Atrasada": 0, "Pendente": 1, "Paga": 2})
    audit_sort = audit_sort.sort_values(["_ord", "Dia Cobrança"]).drop(columns=["_ord"])

    with st.expander(f"📋 Detalhe das {len(audit_show)} contas fixas", expanded=False):
        st.dataframe(
            audit_sort[["Status", "Descrição", "Categoria", "Pessoa Esperada", "Valor Esperado", "Dia Cobrança", "Data Pagamento", "Pessoa Pagou", "Valor Pago"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Valor Esperado": st.column_config.NumberColumn(format="R$ %.0f"),
                "Valor Pago": st.column_config.NumberColumn(format="R$ %.0f"),
            },
        )

st.divider()

# ============== Faturas em aberto + auditoria ==============
st.subheader("Faturas em aberto · auditoria fatura × lançamentos")
if df_faturas.empty:
    st.info("Aba Faturas vazia.")
else:
    pend_f = df_faturas[df_faturas["Status"].astype(str).str.lower().isin(["pendente", "carregada"])]
    if not pend_f.empty and "Vencimento_dt" in pend_f.columns:
        hoje = pd.Timestamp(datetime.now().date())
        pend_f = pend_f.assign(_dias=(pend_f["Vencimento_dt"] - hoje).dt.days)
        pend_f = pend_f[(pend_f["_dias"] >= -30) & (pend_f["_dias"] <= 30)].sort_values("_dias")

        for _, r in pend_f.iterrows():
            cartao = str(r.get("Cartão", "?"))
            mes_ref = str(r.get("Mês Referência", "?"))
            d = int(r["_dias"])
            total = float(r.get("Total_num", 0))
            audit_st = str(r.get("Status Auditoria", "")).strip()
            carregada = str(r.get("Status", "")).lower() == "carregada"

            # Carregada e já vencida = debitada, fecha o ciclo — linha compacta
            if carregada and d < 0:
                st.success(f"✔ **{cartao} · {mes_ref}** — {fmt(total)} debitado em {r.get('Vencimento','?')} (fatura carregada e reconciliada)")
                continue

            # Estima valor + conta lançamentos + rateio por pessoa (chave: Data Caixa == Vencimento)
            venc_str = str(r.get("Vencimento", "")).strip()
            total_estimado, qtd_lanc = fatura_estimada(cartao, mes_ref, df_lanc, vencimento=venc_str)
            rateio = fatura_split_pessoa(cartao, mes_ref, df_lanc, vencimento=venc_str)

            label_prazo = f"venceu há {abs(d)}d" if d < 0 else (f"em {d}d" if d > 0 else "HOJE")
            emoji = "✅" if carregada else ("🔴" if d < 0 else ("🟠" if d <= 5 else "🟡" if d <= 15 else "⚪"))

            with st.container(border=True):
                cf1, cf2, cf3 = st.columns([3, 2, 1])
                with cf1:
                    st.markdown(f"**{emoji} {cartao} · {mes_ref}**")
                    st.caption(f"vence {r.get('Vencimento','?')} · {label_prazo}")
                    if carregada:
                        st.caption(f"✅ fatura carregada · debita {label_prazo} · {qtd_lanc} lançamentos")
                        sobra = (float(df_lanc[
                            df_lanc["Cartão"].astype(str).str.lower().str.contains(cartao.split()[0].lower(), na=False)
                            & (df_lanc["Data Caixa"].astype(str).str.strip() == venc_str)
                        ]["Valor"].sum()) - total) if total > 0 else 0
                        if abs(sobra) > 1:
                            st.caption(f"⚠️ {fmt(abs(sobra))} de lançamentos no Zap {'acima' if sobra > 0 else 'abaixo'} do total da fatura — auditar divergência")
                    elif audit_st:
                        st.caption(f"🔍 auditoria: {audit_st}")
                    else:
                        st.caption(f"⏳ aguardando fatura · **{qtd_lanc} lançamentos individuais** no Zap")
                    if len(rateio) > 1:
                        rotulo = "👥 rateio aproximado: " if carregada else "👥 "
                        st.caption(rotulo + " · ".join(f"{p}: {fmt(v)}" for p, v in rateio.items()))
                with cf2:
                    if total > 0:
                        st.metric("Total fatura", fmt(total), help="total real reconciliado")
                        st.caption("total real reconciliado")
                    elif total_estimado > 0:
                        st.metric("Total fatura", f"~ {fmt(total_estimado)}", help="estimado pelos lançamentos individuais")
                        st.caption(f"_estimado de {qtd_lanc} lançamentos_")
                    else:
                        st.caption("fatura ainda não carregada · sem lançamentos pra estimar")
                with cf3:
                    st.write("")
                    st.write("")
                    if st.button("Abrir", key=f"open_{cartao}_{mes_ref}"):
                        st.session_state["fatura_open"] = f"{cartao}|{mes_ref}"
    else:
        st.success("✅ Nenhuma fatura pendente nos próximos 30 dias.")

st.divider()

# ============== Drill-down Investimentos ==============
expanded_inv = (kpis["aporte_total"] == 0 and kpis["saldo_estocado_total"] == 0)
with st.expander("📈 Drill-down · Investimentos da família", expanded=expanded_inv):
    st.caption("aporte mensal + saldo estocado + rendimento (calculado entre snapshots)")

    di1, di2, di3 = st.columns(3)
    with di1.container(border=True):
        st.caption("**Aporte do mês**")
        if kpis["aporte_total"] > 0:
            st.markdown(f"### {fmt(kpis['aporte_total'])}")
            for p, v in kpis["aporte_por_pessoa"].items():
                st.caption(f"{p}: {fmt(v)}")
        else:
            st.markdown(":blue[aguardando 1º lançamento]")
    with di2.container(border=True):
        st.caption("**Saldo estocado**")
        if kpis["saldo_estocado_total"] > 0:
            st.markdown(f"### {fmt(kpis['saldo_estocado_total'])}")
            for p, v in kpis["saldo_estocado"].items():
                st.caption(f"{p}: {fmt(v)}")
        else:
            st.markdown("preencher aba `Saldo Investido`")
    with di3.container(border=True):
        st.caption("**Rendimento 12m**")
        if len(df_saldo) >= 2:
            # cálculo simples: saldo atual - saldo mais antigo - soma de aportes desde então
            st.markdown("calcular…")
        else:
            st.markdown("precisa ≥ 2 snapshots")

    # Histórico de aportes
    hist = aportes_historico(df_lanc)
    if not hist.empty:
        st.markdown("**Aportes por mês**")
        pivot = hist.pivot_table(index="Competência", columns="Pessoa", values="Valor", aggfunc="sum").fillna(0)
        st.bar_chart(pivot, height=200)

        with st.expander("Tabela completa", expanded=False):
            st.dataframe(
                hist.sort_values("Competência", ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={"Valor": st.column_config.NumberColumn(format="R$ %.0f")},
            )
    else:
        st.caption("— sem lançamentos de aporte ainda —")

    cta1, cta2 = st.columns(2)
    cta1.info("💬 No Zap, mande: `aporte 5000 CDB XP` pra registrar")
    cta2.info("📊 Atualize a aba `Saldo Investido` pra ver saldo estocado aqui")

st.divider()

# ============== Compromissos próximos 6 meses ==============
st.subheader("Compromissos contraídos · próximos 6 meses")
st.caption("O que já está no caixa antes do mês começar — barras empilhadas = compromisso total, linha verde = receita projetada (média 3m).")

cron = compromissos_proximos_meses(df_lanc, df_rec, df_faturas, n_meses=6, partir_de=competencia)
if cron.empty:
    st.info("Sem dados suficientes pra projeção.")
else:
    # Receita projetada = média dos últimos 3 meses
    receita_proj = 0.0
    if "Competência" in df_lanc.columns and not df_lanc.empty:
        receitas = df_lanc[df_lanc["Tipo"].astype(str).str.lower() == "receita"]
        if not receitas.empty:
            por_mes = receitas.groupby("Competência")["Valor"].sum().tail(3)
            if not por_mes.empty:
                receita_proj = float(por_mes.mean())

    fig = go.Figure()
    fig.add_bar(name="Parcelas em curso", x=cron["Mês"], y=cron["Parcelas em curso"], marker_color="#888780")
    fig.add_bar(name="Contas fixas", x=cron["Mês"], y=cron["Contas fixas"], marker_color="#B4B2A9")
    fig.add_bar(name="Faturas em aberto", x=cron["Mês"], y=cron["Faturas em aberto"], marker_color="#EF9F27")
    if receita_proj > 0:
        fig.add_scatter(name="Receita projetada", x=cron["Mês"], y=[receita_proj] * len(cron),
                        mode="lines", line=dict(color="#1D9E75", width=2, dash="dash"))
    fig.update_layout(
        barmode="stack",
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_title="R$",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Mini cards de saldo livre por mês
    if receita_proj > 0:
        cols = st.columns(len(cron))
        for i, (_, r) in enumerate(cron.iterrows()):
            livre = receita_proj - r["Total"]
            cor = "normal" if livre >= 0 else "inverse"
            cols[i].metric(f"livre {r['Mês'][:2]}", fmt(livre), delta_color=cor)

st.divider()

# ============== Contribuição individual ==============
st.subheader("Contribuição individual")
ci1, ci2 = st.columns(2)
for col, pessoa in zip([ci1, ci2], ["Wesley", "Sabrina"]):
    with col.container(border=True):
        rec = kpis["receita_por_pessoa"].get(pessoa, 0)
        desp = kpis["despesa_por_pessoa"].get(pessoa, 0)
        apo = kpis["aporte_por_pessoa"].get(pessoa, 0)
        saldo = rec - desp - apo
        taxa = (saldo / rec * 100) if rec > 0 else 0

        st.markdown(f"### {pessoa}")
        st.write(f"⬆️ Receita: **{fmt(rec)}**")
        st.write(f"⬇️ Gastos: **{fmt(desp)}**")
        st.write(f"📈 Investido: **{fmt(apo) if apo > 0 else '—'}**")
        st.write(f"💰 Saldo: **{fmt(saldo)}**")
        if rec > 0:
            st.progress(min(max(taxa / 100, 0), 1.0), text=f"Taxa de poupança: {taxa:.0f}%")

st.caption("ℹ️ Metas serão calibradas após carregar histórico Jan-Mai 2026.")
