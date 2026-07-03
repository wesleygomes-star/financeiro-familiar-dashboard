"""Visão Anual — matriz categoria × mês (Jan-Dez), estilo Controle 2026.
set_page_config + auth no router."""
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.components import COR, PLOTLY_CONFIG, fig_mobile, tema_verde_premium
from lib.data import is_investimento, is_pagamento_fatura, load_lancamentos

tema_verde_premium()
st.markdown(
    """<style>
    .block-container { max-width: 1100px !important; padding-top: 2.2rem !important; }
    </style>""",
    unsafe_allow_html=True,
)

MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
MNOME = {"01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr", "05": "Mai", "06": "Jun",
         "07": "Jul", "08": "Ago", "09": "Set", "10": "Out", "11": "Nov", "12": "Dez"}


def fmt(v):
    if abs(v) < 0.5:
        return ""
    return f"{v:,.0f}".replace(",", ".")


df = load_lancamentos(False)

c1, c2, c3 = st.columns([2, 1, 1])
c1.markdown("### Visão anual")
anos = sorted({str(c).split("/")[1] for c in df["Competência"] if "/" in str(c)}, reverse=True) if not df.empty else ["2026"]
ano = c2.selectbox("Ano", anos, index=anos.index("2026") if "2026" in anos else 0, label_visibility="collapsed")
modo = c3.radio("Modo", ["Competência", "Caixa"], horizontal=True, label_visibility="collapsed")

col_mes = "Mês Caixa" if modo == "Caixa" else "Competência"
dfa = df[df[col_mes].astype(str).str.endswith(f"/{ano}")].copy()
dfa["_m"] = dfa[col_mes].astype(str).str[:2]


def matriz(sub, titulo, cor_total):
    if sub.empty:
        return None, [0] * 12, 0
    piv = sub.pivot_table(index="Categoria", columns="_m", values="Valor", aggfunc="sum", fill_value=0)
    piv = piv.reindex(columns=MESES, fill_value=0)
    piv["Total"] = piv.sum(axis=1)
    piv = piv.sort_values("Total", ascending=False)
    totais_mes = [float(piv[m].sum()) for m in MESES]
    total_ano = float(piv["Total"].sum())
    # exibição: Total/Média primeiro (a decisão antes do detalhe) e zeros vazios
    disp = piv.copy()
    meses_nm = [MNOME.get(c, c) for c in MESES]
    disp.columns = meses_nm + ["Total"]
    disp["Média"] = (piv["Total"] / 12)
    disp[meses_nm] = disp[meses_nm].astype("Float64").where(lambda x: x.abs() >= 0.5)
    disp = disp[["Total", "Média"] + meses_nm]
    return disp, totais_mes, total_ano


splits = {
    "Despesas": dfa[(dfa["Tipo"].astype(str).str.lower() == "despesa") & (~dfa.apply(is_investimento, axis=1)) & (~dfa.apply(is_pagamento_fatura, axis=1))],
    "Receitas": dfa[dfa["Tipo"].astype(str).str.lower() == "receita"],
    "Investimentos": dfa[dfa.apply(is_investimento, axis=1)],
}

# KPIs anuais — grade 2×2 no estilo do mockup
desp_ano = float(splits["Despesas"]["Valor"].sum())
rec_ano = float(splits["Receitas"]["Valor"].sum())
inv_ano = float(splits["Investimentos"]["Valor"].sum())
saldo_ano = rec_ano - desp_ano - inv_ano

def _r(v):
    return "R$ " + (fmt(v) or "0")

IC_UP = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M8 13V3M4 7l4-4 4 4"/></svg>'
IC_DN = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M8 3v10M4 9l4 4 4-4"/></svg>'
IC_CH = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 13l4-5 3 3 5-7"/></svg>'
IC_WA = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="2" y="5" width="12" height="8" rx="2"/><path d="M5 5V3.5A1.5 1.5 0 016.5 2h3A1.5 1.5 0 0111 3.5V5"/></svg>'
cor_saldo_ano = COR["receita"] if saldo_ano >= 0 else COR["despesa"]
st.markdown(
    f"""
    <div class="k5grid">
      <div class="k5"><div class="k5-l">{IC_UP} receita no ano</div><div class="k5-v" style="color:{COR['receita']}">{_r(rec_ano)}</div></div>
      <div class="k5"><div class="k5-l">{IC_DN} despesa no ano</div><div class="k5-v">{_r(desp_ano)}</div></div>
      <div class="k5"><div class="k5-l">{IC_CH} investido no ano</div><div class="k5-v" style="color:{COR['investimento']}">{_r(inv_ano)}</div></div>
      <div class="k5"><div class="k5-l">{IC_WA} saldo no ano</div><div class="k5-v" style="color:{cor_saldo_ano}">{_r(saldo_ano)}</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Gráfico: receita vs despesa vs investido por mês
meses_lbl = [MNOME[m] for m in MESES]
def serie(sub):
    if sub.empty:
        return [0] * 12
    g = sub.groupby("_m")["Valor"].sum()
    return [float(g.get(m, 0)) for m in MESES]
fig = go.Figure()
fig.add_bar(name="Despesa", x=meses_lbl, y=serie(splits["Despesas"]), marker_color=COR["despesa"])
fig.add_bar(name="Investido", x=meses_lbl, y=serie(splits["Investimentos"]), marker_color=COR["investimento"])
fig.add_bar(name="Receita", x=meses_lbl, y=serie(splits["Receitas"]), marker_color=COR["receita"])
fig.update_layout(barmode="group", height=280, margin=dict(l=10, r=10, t=10, b=10),
                  template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  font=dict(color="#2C2C2A", size=12),
                  legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5))
st.plotly_chart(fig_mobile(fig), use_container_width=True, config=PLOTLY_CONFIG)

# Tabelas matriz
NUMCOLS = {c: st.column_config.NumberColumn(format="%.0f", width="small") for c in meses_lbl}
NUMCOLS["Total"] = st.column_config.NumberColumn(format="R$ %.0f")
NUMCOLS["Média"] = st.column_config.NumberColumn(format="R$ %.0f")

for nome, cor in [("Despesas", "#E24B4A"), ("Receitas", "#1D9E75"), ("Investimentos", "#185FA5")]:
    disp, totais, total = matriz(splits[nome], nome, cor)
    if disp is None or disp.empty:
        continue
    st.subheader(f"{nome} · R$ {fmt(total)} no ano")
    st.dataframe(disp.round(0), use_container_width=True, column_config=NUMCOLS,
                 height=min(40 + len(disp) * 35, 560))

# Resultado mensal (receita − despesa − investido) — Saldo colorido salta da grade
st.subheader("Resultado mensal")
rd = serie(splits["Receitas"]); dd = serie(splits["Despesas"]); ii = serie(splits["Investimentos"])
res = pd.DataFrame({
    "Mês": meses_lbl,
    "Receita": rd, "Despesa": dd, "Investido": ii,
    "Saldo": [rd[i] - dd[i] - ii[i] for i in range(12)],
})

def _fmt_saldo(v):
    s = f"{abs(v):,.0f}".replace(",", ".")
    return ("-" if v < -0.5 else "") + f"R$ {s}"

def _cor_saldo(col):
    return [
        f"color: {COR['receita'] if v >= 0 else COR['despesa']}; font-weight: 600;"
        for v in col
    ]

saldo_view = res[["Mês", "Saldo"]].copy()
styled = saldo_view.style.apply(_cor_saldo, subset=["Saldo"]).format({"Saldo": _fmt_saldo})
st.dataframe(styled, use_container_width=True, hide_index=True)

with st.expander("Detalhe: receita × despesa × investido por mês"):
    st.dataframe(res, use_container_width=True, hide_index=True, column_config={
        "Receita": st.column_config.NumberColumn(format="R$ %.0f"),
        "Despesa": st.column_config.NumberColumn(format="R$ %.0f"),
        "Investido": st.column_config.NumberColumn(format="R$ %.0f"),
        "Saldo": st.column_config.NumberColumn(format="R$ %.0f"),
    })

st.caption("Jan-Abr vêm do seu Controle 2026 (só despesas). Maio+ do uso real via Zap. "
           "Pagamento de fatura é excluído (transferência, não consumo).")
