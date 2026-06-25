"""Visão Anual — matriz categoria × mês (Jan-Dez), estilo Controle 2026.
set_page_config + auth no router."""
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.data import is_investimento, is_pagamento_fatura, load_lancamentos

st.markdown(
    """<style>
    .block-container { max-width: 1100px !important; padding-top: 3.5rem !important; }
    .stApp h2 { font-size: 1.15rem !important; }
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
    # montar dataframe de exibição
    disp = piv.copy()
    disp.columns = [MNOME.get(c, c) for c in MESES] + ["Total"]
    disp["Média"] = (piv["Total"] / 12)
    return disp, totais_mes, total_ano


splits = {
    "Despesas": dfa[(dfa["Tipo"].astype(str).str.lower() == "despesa") & (~dfa.apply(is_investimento, axis=1)) & (~dfa.apply(is_pagamento_fatura, axis=1))],
    "Receitas": dfa[dfa["Tipo"].astype(str).str.lower() == "receita"],
    "Investimentos": dfa[dfa.apply(is_investimento, axis=1)],
}

# KPIs anuais
desp_ano = float(splits["Despesas"]["Valor"].sum())
rec_ano = float(splits["Receitas"]["Valor"].sum())
inv_ano = float(splits["Investimentos"]["Valor"].sum())
k1, k2, k3, k4 = st.columns(4)
k1.metric("receita no ano", "R$ " + fmt(rec_ano))
k2.metric("despesa no ano", "R$ " + fmt(desp_ano))
k3.metric("investido no ano", "R$ " + fmt(inv_ano))
k4.metric("saldo no ano", "R$ " + fmt(rec_ano - desp_ano - inv_ano))

# Gráfico: receita vs despesa vs investido por mês
meses_lbl = [MNOME[m] for m in MESES]
def serie(sub):
    if sub.empty:
        return [0] * 12
    g = sub.groupby("_m")["Valor"].sum()
    return [float(g.get(m, 0)) for m in MESES]
fig = go.Figure()
fig.add_bar(name="Despesa", x=meses_lbl, y=serie(splits["Despesas"]), marker_color="#E24B4A")
fig.add_bar(name="Investido", x=meses_lbl, y=serie(splits["Investimentos"]), marker_color="#185FA5")
fig.add_bar(name="Receita", x=meses_lbl, y=serie(splits["Receitas"]), marker_color="#1D9E75")
fig.update_layout(barmode="group", height=260, margin=dict(l=10, r=10, t=10, b=10),
                  template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  font=dict(color="#2C2C2A", size=12),
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)

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

# Resultado mensal (receita − despesa − investido)
st.subheader("Resultado mensal")
rd = serie(splits["Receitas"]); dd = serie(splits["Despesas"]); ii = serie(splits["Investimentos"])
res = pd.DataFrame({
    "Mês": meses_lbl,
    "Receita": rd, "Despesa": dd, "Investido": ii,
    "Saldo": [rd[i] - dd[i] - ii[i] for i in range(12)],
})
st.dataframe(res, use_container_width=True, hide_index=True, column_config={
    "Receita": st.column_config.NumberColumn(format="R$ %.0f"),
    "Despesa": st.column_config.NumberColumn(format="R$ %.0f"),
    "Investido": st.column_config.NumberColumn(format="R$ %.0f"),
    "Saldo": st.column_config.NumberColumn(format="R$ %.0f"),
})

st.caption("ℹ️ Jan-Abr vêm do seu Controle 2026 (só despesas). Maio+ do uso real via Zap. "
           "Pagamento de fatura é excluído (transferência, não consumo).")
