"""Custos da ferramenta — quanto o sistema consome por mês.
set_page_config + auth no router."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.components import barra_navegacao, PLOTLY_CONFIG, fig_mobile, tema_verde_premium
from lib.data import load_custos

tema_verde_premium()
barra_navegacao("custos")
st.markdown(
    """<style>
    .block-container { max-width: 900px !important; padding-top: 2.2rem !important; }
    </style>""",
    unsafe_allow_html=True,
)


def fmt(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.markdown("### Custo da ferramenta")
st.caption("quanto o próprio sistema consome por mês — edite os valores na aba `Custos Ferramenta`")

df = load_custos()
if df.empty:
    st.info("Aba `Custos Ferramenta` vazia ou não encontrada.")
    st.stop()

ativos = df[df.get("Status", "Ativo").astype(str).str.lower() != "inativo"] if "Status" in df.columns else df
total = float(ativos["Custo_num"].sum()) if "Custo_num" in ativos.columns else 0.0

# Número-herói: o custo mensal domina; o resto é sublinha
pagos = ativos[ativos["Custo_num"] > 0] if "Custo_num" in ativos.columns else ativos
st.markdown(
    f"""
    <div class="heronum">
      <div class="hn-l">custo mensal do sistema</div>
      <div class="hn-v">{fmt(total)}</div>
      <div class="hn-s">{fmt(total * 12)}/ano · {len(pagos)} de {len(ativos)} ferramentas pagas</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Gráfico: custo por ferramenta (só as pagas)
if not pagos.empty:
    p = pagos.sort_values("Custo_num", ascending=True)
    fig = go.Figure(go.Bar(
        x=p["Custo_num"], y=p["Ferramenta"], orientation="h",
        marker=dict(color="#0F6E56", cornerradius=4),
        text=[fmt(v) for v in p["Custo_num"]], textposition="outside",
    ))
    fig.update_layout(height=max(200, 50 * len(p)), margin=dict(l=10, r=80, t=10, b=10),
                      template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#2C2C2A", size=12), xaxis=dict(title=""))
    st.plotly_chart(fig_mobile(fig), use_container_width=True, config=PLOTLY_CONFIG)

# Tabela completa (colapsada — o gráfico já conta a história)
with st.expander("Ver tabela completa"):
    cols = [c for c in ["Ferramenta", "Categoria", "Custo Mensal", "Tipo", "Pago Por", "Notas"] if c in df.columns]
    tab = df.copy()
    colcfg = {}
    if "Custo_num" in tab.columns and "Custo Mensal" in cols:
        tab["Custo Mensal"] = tab["Custo_num"]
        colcfg["Custo Mensal"] = st.column_config.NumberColumn(format="R$ %.2f")
    st.dataframe(tab[cols], use_container_width=True, hide_index=True, column_config=colcfg)

# ROI — custo vs valor gerado
st.subheader("Vale a pena?")
# \$ evita o markdown tratar dois R$ na mesma frase como fórmula LaTeX
# (escapado FORA da f-string — Py3.9 não aceita \ dentro de {})
_custo_mes = fmt(total).replace("R$", "R\\$")
_custo_ano = fmt(total * 12).replace("R$", "R\\$")
st.markdown(
    f"""
O sistema custa **{_custo_mes}/mês** (≈ {_custo_ano}/ano) e em troca:
- Lançamento sem fricção pelo WhatsApp (você + Sabrina)
- Conciliação automática de faturas de cartão
- Controle de contas fixas com alerta de vencimento
- Visão do ano inteiro, por mês e por categoria

Estimativa de tempo economizado: **~7h/mês** de planilha manual. A qualquer custo de oportunidade
razoável, o retorno é de muitas vezes o que se gasta.
"""
)
st.caption("Os custos das IAs (Anthropic/OpenAI) são variáveis — atualize na aba conforme o consumo real do mês.")
