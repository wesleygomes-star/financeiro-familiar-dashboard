"""Patrimônio — visão completa: investível, imobilizado, dívidas e grandes projetos.
set_page_config + auth no router."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.components import COR, PLOTLY_CONFIG, barra_navegacao, faixa_titulo, fig_mobile, tema_verde_premium
from lib.data import (
    kpis_familia,
    load_bens,
    load_lancamentos,
    load_saldo_investido,
    meses_disponiveis,
    patrimonio_imobilizado,
    rendimento_investido,
    saldo_estocado_atual,
    serie_estocado,
)

tema_verde_premium()
barra_navegacao("patrimonio")
st.markdown(
    """<style>
    .block-container { max-width: 900px !important; padding-top: 2.2rem !important; }
    </style>""",
    unsafe_allow_html=True,
)

faixa_titulo("Patrimônio")

df_lanc = load_lancamentos(False)
df_saldo = load_saldo_investido()
df_bens = load_bens()

_est = saldo_estocado_atual(df_saldo)
estocado = sum(_est.values()) if _est else 0.0
_imob = patrimonio_imobilizado(df_bens)
patr_total = estocado + _imob["total"]

_PRIV = bool(st.session_state.get("modo_privado", False))


def fmt(v):
    if _PRIV:
        return "R$ ••••"
    if v is None or pd.isna(v):
        return "—"
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt0(v):
    if _PRIV:
        return "R$ ••••"
    return "R$ " + f"{v:,.0f}".replace(",", ".")


# ============== KPIs — investível | imobilizado | total ==============
st.markdown(
    f"""
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:16px">
      <div style="background:#fff;border-radius:14px;padding:14px;box-shadow:0 2px 8px rgba(12,60,45,0.06)">
        <div style="font-size:11.5px;color:#5C6B62;font-weight:700;text-transform:uppercase;letter-spacing:.04em">Investível</div>
        <div style="font-size:19px;font-weight:800;margin-top:4px;color:{COR['investimento']}">{fmt0(estocado)}</div>
        <div style="font-size:11px;color:#8B978F;margin-top:2px">bancos e corretoras</div>
      </div>
      <div style="background:#fff;border-radius:14px;padding:14px;box-shadow:0 2px 8px rgba(12,60,45,0.06)">
        <div style="font-size:11.5px;color:#5C6B62;font-weight:700;text-transform:uppercase;letter-spacing:.04em">Imobilizado</div>
        <div style="font-size:19px;font-weight:800;margin-top:4px">{fmt0(_imob['total'])}</div>
        <div style="font-size:11px;color:#8B978F;margin-top:2px">bens − dívida</div>
      </div>
      <div style="background:linear-gradient(160deg,#0C5949,#082744);border-radius:14px;padding:14px;box-shadow:0 4px 14px rgba(12,60,45,0.18)">
        <div style="font-size:11.5px;color:#B8E8D4;font-weight:700;text-transform:uppercase;letter-spacing:.04em">Total</div>
        <div style="font-size:19px;font-weight:800;margin-top:4px;color:#fff">{fmt0(patr_total)}</div>
        <div style="font-size:11px;color:#B8E8D4;margin-top:2px">investível + imobilizado</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if _imob["total"] > 0:
    st.caption(
        f"imobilizado: {fmt(_imob['investimento'])} em bens de investimento + "
        f"{fmt(_imob['uso'])} em bens de uso".replace("R$", "R\\$")
    )

# ============== Investível — evolução ==============
st.markdown('<h3 style="margin-top:8px">Investível — evolução</h3>', unsafe_allow_html=True)
if not df_saldo.empty and "Data Snapshot_dt" in df_saldo.columns:
    _ev = serie_estocado(df_saldo)
    if len(_ev) >= 1:
        figp = go.Figure(
            go.Scatter(
                x=_ev["Data Snapshot_dt"], y=_ev["Saldo Total"], mode="lines+markers+text",
                line=dict(color=COR["investimento"], width=3), marker=dict(size=9),
                text=["" if _PRIV else fmt0(vv) for vv in _ev["Saldo Total"]], textposition="top center",
            )
        )
        figp.update_traces(cliponaxis=False)
        figp.update_layout(
            height=240, margin=dict(l=10, r=16, t=48, b=10), template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#2C2C2A", size=12), showlegend=False,
            yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
        )
        st.plotly_chart(fig_mobile(figp), use_container_width=True, config=PLOTLY_CONFIG)
    ic1, ic2, ic3 = st.columns(3)
    rend = rendimento_investido(df_saldo)
    ic1.metric("rendimento", f"+{rend['pct']:.2f}%" if rend else "—")
    ic2.metric("snapshots", str(df_saldo["Data Snapshot"].nunique()))
    if _est:
        ic3.metric("modalidades", str(df_saldo["Modalidade"].nunique()) if "Modalidade" in df_saldo.columns else "—")
    st.caption("cada print de investimento no Zap vira um ponto novo na curva")
else:
    st.info("Mande o print do app do banco no grupo do Zap — o patrimônio entra sozinho.")

# ============== Imobilizado — bens e dívidas ==============
st.markdown('<h3 style="margin-top:20px">Bens e dívidas</h3>', unsafe_allow_html=True)
if not df_bens.empty and "Valor de Mercado" in df_bens.columns:
    _bt = df_bens[df_bens["Valor de Mercado"].fillna(0) > 0][
        ["Nome", "Finalidade", "Valor de Mercado", "Saldo Devedor"]
    ].copy()
    _bt["Equity"] = _bt["Valor de Mercado"] - _bt["Saldo Devedor"].fillna(0)
    _bt = _bt.sort_values("Equity", ascending=False)

    def _brl(v):
        if _PRIV:
            return "R$ ••••"
        if pd.isna(v):
            return "—"
        return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    _sty = _bt.style.format({c: _brl for c in ("Valor de Mercado", "Saldo Devedor", "Equity")})
    st.dataframe(_sty, use_container_width=True, hide_index=True)

    _dividas = _bt[_bt["Saldo Devedor"].fillna(0) > 0]
    if not _dividas.empty:
        total_divida = _dividas["Saldo Devedor"].sum()
        st.caption(
            (f"dívida total em aberto: {fmt(total_divida)} — carro amortiza sozinho todo dia 1º "
             f"(tabela Price); AP Cláudio segue o cronograma contratual.").replace("R$", "R\\$")
        )

    if _imob["n_pendentes"] > 0:
        _pend = df_bens[df_bens["Valor de Mercado"].fillna(0) <= 0]["Nome"].tolist()
        st.caption(f"⏳ sem avaliação (fora do total): {', '.join(str(p) for p in _pend[:4])}")
else:
    st.info("Nenhum bem avaliado ainda na aba Bens.")

# ============== Grandes projetos — AP Cláudio ==============
st.markdown('<h3 style="margin-top:20px">Grandes projetos</h3>', unsafe_allow_html=True)


def _tributos_pj(ganho: float) -> dict:
    """Ganho de capital PJ na alienação de bem do ativo não circulante — tributado pelo
    valor TOTAL do ganho (sem presunção, vale pra Lucro Real e Presumido) via IRPJ (15% +
    adicional 10% acima de R$240k/ano) + CSLL (9% flat). Regime da ARTH não confirmado,
    mas a regra do ganho de capital converge nos dois regimes — estimativa, não apuração."""
    if ganho <= 0:
        return {"irpj_base": 0.0, "irpj_adicional": 0.0, "csll": 0.0, "total": 0.0}
    LIMITE_ADICIONAL = 240_000.0
    excedente = max(ganho - LIMITE_ADICIONAL, 0.0)
    irpj_base = ganho * 0.15
    irpj_adicional = excedente * 0.10
    csll = ganho * 0.09
    return {"irpj_base": irpj_base, "irpj_adicional": irpj_adicional, "csll": csll,
            "total": irpj_base + irpj_adicional + csll}


_ap = df_bens[df_bens["Nome"].astype(str).str.contains("501", na=False)] if not df_bens.empty else pd.DataFrame()
if not _ap.empty:
    r = _ap.iloc[0]
    vm = float(r.get("Valor de Mercado", 0) or 0)
    custo = float(r.get("Custo Aquisição", 0) or 0)
    saldo_dev = float(r.get("Saldo Devedor", 0) or 0)
    ganho = max(vm - custo, 0.0)
    trib = _tributos_pj(ganho)
    liquido = vm - saldo_dev - trib["total"]
    st.markdown(
        f"""
        <div style="background:#fff;border-radius:14px;padding:16px;box-shadow:0 2px 8px rgba(12,60,45,0.06)">
          <div style="font-weight:800;font-size:14.5px;margin-bottom:8px">🏠 {r.get('Nome', 'AP 501')} · ARTH Participações (PJ)</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;font-size:13px">
            <div style="color:#5C6B62">Valor de mercado</div><div style="text-align:right;font-weight:700">{fmt(vm)}</div>
            <div style="color:#5C6B62">Custo de aquisição</div><div style="text-align:right;font-weight:700">{fmt(custo)}</div>
            <div style="color:#5C6B62">Saldo devedor</div><div style="text-align:right;font-weight:700">{fmt(saldo_dev)}</div>
            <div style="color:#5C6B62">Ganho de capital estimado</div><div style="text-align:right;font-weight:700">{fmt(ganho)}</div>
            <div style="color:#5C6B62">IRPJ (15% + adicional 10%)</div><div style="text-align:right;font-weight:700;color:{COR['despesa']}">{fmt(trib['irpj_base'] + trib['irpj_adicional'])}</div>
            <div style="color:#5C6B62">CSLL (9%)</div><div style="text-align:right;font-weight:700;color:{COR['despesa']}">{fmt(trib['csll'])}</div>
            <div style="color:#5C6B62;font-weight:700">Total tributos estimado</div><div style="text-align:right;font-weight:800;color:{COR['despesa']}">{fmt(trib['total'])}</div>
            <div style="border-top:1px solid #E1EAE4;margin-top:4px;padding-top:6px;color:#1C2420;font-weight:800">Líquido estimado na venda</div>
            <div style="border-top:1px solid #E1EAE4;margin-top:4px;padding-top:6px;text-align:right;font-weight:800;color:{COR['receita']}">{fmt(liquido)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        ("Investimento em nome da ARTH Participações (PJ) — tributos calculados na empresa, não pessoa física. "
         "Ganho de capital na venda de ativo não circulante é tributado pelo valor TOTAL (sem presunção), "
         "vale tanto pra Lucro Real quanto Presumido: IRPJ 15% + adicional 10% sobre o que exceder R$240mil/ano "
         "de ganho + CSLL 9% flat — bem mais pesado que o IR pessoa física. Estimativa de planejamento; a apuração "
         "real da ARTH pode variar com regime, período de apuração e outros resultados da empresa no exercício — "
         "confirmar com o contador antes de decidir o preço de venda. Não confundir com o breakeven do custo de "
         "capital (visão gerencial, no dossiê do AP)."
         ).replace("R$", "R\\$")
    )
else:
    st.info("AP Cláudio não encontrado na aba Bens.")
