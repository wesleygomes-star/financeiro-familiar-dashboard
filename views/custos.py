"""Custos da ferramenta — quanto o sistema consome por mês.
set_page_config + auth no router."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.data import load_custos

st.markdown(
    """<style>
    .block-container { max-width: 900px !important; padding-top: 3.5rem !important; }
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

# KPIs
k1, k2, k3 = st.columns(3)
k1.metric("custo mensal", fmt(total))
k2.metric("custo anual", fmt(total * 12))
pagos = ativos[ativos["Custo_num"] > 0] if "Custo_num" in ativos.columns else ativos
k3.metric("ferramentas pagas", f"{len(pagos)} de {len(ativos)}")

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
    st.plotly_chart(fig, use_container_width=True)

# Tabela completa
cols = [c for c in ["Ferramenta", "Categoria", "Custo Mensal", "Tipo", "Pago Por", "Notas"] if c in df.columns]
st.dataframe(df[cols], use_container_width=True, hide_index=True)

# ROI — custo vs valor gerado
st.subheader("Vale a pena?")
st.markdown(
    f"""
O sistema custa **{fmt(total)}/mês** (≈ {fmt(total*12)}/ano) e em troca:
- Lançamento sem fricção pelo WhatsApp (você + Sabrina)
- Conciliação automática de faturas de cartão
- Controle de contas fixas com alerta de vencimento
- Visão do ano inteiro, por mês e por categoria

Estimativa de tempo economizado: **~7h/mês** de planilha manual. A qualquer custo de oportunidade
razoável, o retorno é de muitas vezes o que se gasta.
"""
)
st.caption("ℹ️ Os custos das IAs (Anthropic/OpenAI) são variáveis — atualize na aba conforme o consumo real do mês.")
