"""Patrimônio — visão completa: investível, imobilizado, dívidas e grandes projetos.
set_page_config + auth no router."""
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.components import COR, PLOTLY_CONFIG, barra_navegacao, faixa_titulo, fig_mobile, tema_verde_premium
from lib.data import (
    MUTUO_EMPRESTA_INICIO,
    MUTUO_EMPRESTA_PRINCIPAL,
    SITIO_JA_PAGO,
    SITIO_PAGAMENTO_PENDENTE,
    SITIO_PREJUIZO_4,
    SITIO_A_RECEBER,
    TAXA_CDI_MUTUO,
    caixa_pelada_atual,
    custo_capital_corrigido,
    kpis_familia,
    load_ap_claudio_aportes,
    load_bens,
    load_lancamentos,
    load_saldo_investido,
    meses_disponiveis,
    patrimonio_imobilizado,
    rendimento_investido,
    saldo_estocado_atual,
    serie_estocado,
    valor_a_receber_hoje,
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
# A receber = recebíveis de prazo incerto (mútuo Empresta + sítio) — bucket próprio, não é
# Investível (sem liquidez de banco) nem Imobilizado (não é bem físico).
a_receber = valor_a_receber_hoje()
_df_mutuo = pd.DataFrame([{"Valor Pago": MUTUO_EMPRESTA_PRINCIPAL, "Data_dt": MUTUO_EMPRESTA_INICIO}])
mutuo_empresta_hoje = custo_capital_corrigido(_df_mutuo, TAXA_CDI_MUTUO, datetime.now())
patr_total = estocado + _imob["total"] + a_receber

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


# ============== KPIs — investível | a receber | imobilizado | total ==============
st.markdown(
    f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px">
      <div style="background:#fff;border-radius:14px;padding:14px;box-shadow:0 2px 8px rgba(12,60,45,0.06)">
        <div style="font-size:11.5px;color:#5C6B62;font-weight:700;text-transform:uppercase;letter-spacing:.04em">Investível</div>
        <div style="font-size:19px;font-weight:800;margin-top:4px;color:{COR['investimento']}">{fmt0(estocado)}</div>
        <div style="font-size:11px;color:#8B978F;margin-top:2px">bancos e corretoras</div>
      </div>
      <div style="background:#fff;border-radius:14px;padding:14px;box-shadow:0 2px 8px rgba(12,60,45,0.06)">
        <div style="font-size:11.5px;color:#5C6B62;font-weight:700;text-transform:uppercase;letter-spacing:.04em">A Receber</div>
        <div style="font-size:19px;font-weight:800;margin-top:4px;color:{COR['alerta']}">{fmt0(a_receber)}</div>
        <div style="font-size:11px;color:#8B978F;margin-top:2px">recebíveis de prazo incerto</div>
      </div>
      <div style="background:#fff;border-radius:14px;padding:14px;box-shadow:0 2px 8px rgba(12,60,45,0.06)">
        <div style="font-size:11.5px;color:#5C6B62;font-weight:700;text-transform:uppercase;letter-spacing:.04em">Imobilizado</div>
        <div style="font-size:19px;font-weight:800;margin-top:4px">{fmt0(_imob['total'])}</div>
        <div style="font-size:11px;color:#8B978F;margin-top:2px">bens − dívida</div>
      </div>
      <div style="background:linear-gradient(160deg,#0C5949,#082744);border-radius:14px;padding:14px;box-shadow:0 4px 14px rgba(12,60,45,0.18)">
        <div style="font-size:11.5px;color:#B8E8D4;font-weight:700;text-transform:uppercase;letter-spacing:.04em">Total</div>
        <div style="font-size:19px;font-weight:800;margin-top:4px;color:#fff">{fmt0(patr_total)}</div>
        <div style="font-size:11px;color:#B8E8D4;margin-top:2px">investível + a receber + imobilizado</div>
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

# ============== Onde está — por pessoa + instituição (só o que é Investível de verdade) ==============
st.markdown('<h4 style="margin-top:14px">Onde está</h4>', unsafe_allow_html=True)
_linhas_banco = []
if not df_saldo.empty and "Modalidade" in df_saldo.columns and "Pessoa" in df_saldo.columns:
    _tem_data = "Data Snapshot_dt" in df_saldo.columns
    # agrupa por PESSOA + banco — mesma instituição pra Wesley e Sabrina são contas diferentes,
    # nunca devem se misturar numa linha só (bug 10/08: o Inter da Sabrina sumia atrás do do Wesley)
    for (pessoa_g, mod), g in df_saldo.groupby(["Pessoa", "Modalidade"]):
        g2 = g.sort_values("Data Snapshot_dt", ascending=False) if _tem_data else g
        ultimo = g2.iloc[0]
        _rend = float(ultimo.get("Rendimento Calc", 0) or 0)
        _linhas_banco.append({
            "Pessoa": pessoa_g,
            "Instituição": mod,
            "Alocação": str(ultimo.get("Produto", "") or "—"),
            "Saldo": fmt(float(ultimo.get("Saldo Total", 0) or 0)),
            "Rendimento": fmt(_rend) if _rend > 0 else "—",
            "Atualizado em": ultimo.get("Data Snapshot", "—"),
            "_saldo_sort": float(ultimo.get("Saldo Total", 0) or 0),
        })
if _linhas_banco:
    _df_banco = pd.DataFrame(_linhas_banco).sort_values("_saldo_sort", ascending=False).drop(columns=["_saldo_sort"])
    st.dataframe(_df_banco, use_container_width=True, hide_index=True)
    st.caption("cada banco mostra o último print recebido no Zap, separado por pessoa.")

# ============== A Receber — recebíveis de prazo incerto ==============
st.markdown('<h3 style="margin-top:20px">A Receber</h3>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div style="background:#fff;border-radius:14px;padding:16px;box-shadow:0 2px 8px rgba(12,60,45,0.06);margin-bottom:10px">
      <div style="font-size:12.5px;color:#5C6B62;font-weight:700;text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">Mútuo Empresta (sócio)</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;font-size:13px">
        <div style="color:#5C6B62">Principal</div><div style="text-align:right;font-weight:700">{fmt(MUTUO_EMPRESTA_PRINCIPAL)}</div>
        <div style="color:#5C6B62">Taxa aplicada</div><div style="text-align:right;font-weight:700">{TAXA_CDI_MUTUO*100:.0f}% a.a. (proxy do CDI)</div>
        <div style="color:#5C6B62">Desde</div><div style="text-align:right;font-weight:700">{MUTUO_EMPRESTA_INICIO.strftime('%d/%m/%Y')}</div>
        <div style="border-top:1px solid #E1EAE4;margin-top:4px;padding-top:6px;color:#1C2420;font-weight:800">Valor corrigido hoje</div>
        <div style="border-top:1px solid #E1EAE4;margin-top:4px;padding-top:6px;text-align:right;font-weight:800;color:{COR['alerta']}">{fmt(mutuo_empresta_hoje)}</div>
      </div>
    </div>
    <div style="background:#fff;border-radius:14px;padding:16px;box-shadow:0 2px 8px rgba(12,60,45,0.06)">
      <div style="font-size:12.5px;color:#5C6B62;font-weight:700;text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">Sítio — regularização ITCD</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;font-size:13px">
        <div style="color:#5C6B62">Já pago (cartório + parcelas Nov/25-Fev/26)</div><div style="text-align:right;font-weight:700">{fmt(SITIO_JA_PAGO)}</div>
        <div style="color:#5C6B62">+ Pagamento confirmado (CDA Wesley, 12/08/26)</div><div style="text-align:right;font-weight:700">{fmt(SITIO_PAGAMENTO_PENDENTE)}</div>
        <div style="color:#5C6B62">− Prejuízo dos 4 herdeiros (assumido pelo Wesley)</div><div style="text-align:right;font-weight:700;color:{COR['alerta']}">-{fmt(SITIO_PREJUIZO_4)}</div>
        <div style="border-top:1px solid #E1EAE4;margin-top:4px;padding-top:6px;color:#1C2420;font-weight:800">Total reembolsável na venda</div>
        <div style="border-top:1px solid #E1EAE4;margin-top:4px;padding-top:6px;text-align:right;font-weight:800;color:{COR['alerta']}">{fmt(SITIO_A_RECEBER)}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(
    "recebíveis de prazo incerto — sem a liquidez de um saldo em banco (não dá pra sacar quando "
    "quiser), mas também não são bem físico (não é Imobilizado). Mútuo Empresta: a empresa paga "
    "conforme disponibilidade de caixa. Sítio: reembolsável quando o imóvel for vendido — detalhe "
    "do cálculo em Pagamentos Sítio/ANALISE_PROTESTO_ITCD_11-08.md."
)

# ============== Sob custódia — não é patrimônio (caixa da pelada) ==============
_pelada = caixa_pelada_atual()
if _pelada.get("ok") and (_pelada["operacional"] > 0 or _pelada["festa"] > 0):
    st.markdown('<h3 style="margin-top:20px">Sob custódia (não é seu)</h3>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="background:#fff;border-radius:14px;padding:16px;box-shadow:0 2px 8px rgba(12,60,45,0.06)">
          <div style="font-size:12.5px;color:#5C6B62;font-weight:700;text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">Caixa da Pelada de Futevôlei</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;font-size:13px">
            <div style="color:#5C6B62">Operacional</div><div style="text-align:right;font-weight:700">{fmt(_pelada['operacional'])}</div>
            <div style="color:#5C6B62">Fundo da festa</div><div style="text-align:right;font-weight:700">{fmt(_pelada['festa'])}</div>
            <div style="border-top:1px solid #E1EAE4;margin-top:4px;padding-top:6px;color:#1C2420;font-weight:800">Total sob custódia</div>
            <div style="border-top:1px solid #E1EAE4;margin-top:4px;padding-top:6px;text-align:right;font-weight:800;color:{COR['alerta']}">{fmt(_pelada['operacional'] + _pelada['festa'])}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "dinheiro da galera (mensalidades + avulsos) que passa pela sua gestão — não é seu "
        "patrimônio, fica aqui só pra deixar explícito que parte do que está no banco não é "
        "dinheiro livre. Não entra no total do Patrimônio acima. Fonte: planilha Caixa Pelada "
        "Futevôlei, mesmo cálculo do dashboard n8n (atualiza a cada 5min)."
    )

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
            <div style="border-top:1px solid #E1EAE4;margin-top:4px;padding-top:6px;color:#1C2420;font-weight:800">Líquido nominal na venda</div>
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
         "confirmar com o contador antes de decidir o preço de venda. Não inclui os custos de regularização "
         "(ITBI, escritura, registro) — ver simulação completa abaixo."
         ).replace("R$", "R\\$")
    )

    # ---------- Custos de regularização (2 cenários do ITBI) ----------
    ESCRITURA = 4_373.0
    REGISTRO = 4_373.0
    DESPACHANTE = 1_200.0
    ITBI_EMITIDO = 28_557.72
    ITBI_REVISAO = 5_657.93
    regularizacao_emitido = ITBI_EMITIDO + ESCRITURA + REGISTRO + DESPACHANTE
    regularizacao_revisao = ITBI_REVISAO + ESCRITURA + REGISTRO + DESPACHANTE

    st.markdown('<h3 style="margin-top:20px">Custos de regularização</h3>', unsafe_allow_html=True)
    _reg = pd.DataFrame(
        [
            {"Item": "ITBI", "Guia emitida (PBH)": ITBI_EMITIDO, "Se a revisão for aceita": ITBI_REVISAO},
            {"Item": "Escritura pública (≈)", "Guia emitida (PBH)": ESCRITURA, "Se a revisão for aceita": ESCRITURA},
            {"Item": "Registro 4º RI (≈)", "Guia emitida (PBH)": REGISTRO, "Se a revisão for aceita": REGISTRO},
            {"Item": "Despachante (Oiti)", "Guia emitida (PBH)": DESPACHANTE, "Se a revisão for aceita": DESPACHANTE},
            {"Item": "Total", "Guia emitida (PBH)": regularizacao_emitido, "Se a revisão for aceita": regularizacao_revisao},
        ]
    )
    st.dataframe(
        _reg.style.format({c: (lambda v: fmt(v)) for c in ("Guia emitida (PBH)", "Se a revisão for aceita")}),
        use_container_width=True, hide_index=True,
    )
    st.caption(
        ("PBH lançou o ITBI como se o imóvel estivesse pronto (base R$951.924, valor venal cadastral) — "
         "despachante já protocolou revisão pra base correta (fração declarada R$188.597,67). Enquanto não sai "
         "a decisão, os dois valores ficam em aberto — ver pendências abaixo. Escritura e registro são estimativas "
         "de tabela (TJMG). Pra PJ, esses custos são CAPITALIZADOS no custo de aquisição do imóvel (reduzem o ganho "
         "de capital tributável), não são despesa dedutível corrente — refletido na simulação abaixo."
         ).replace("R$", "R\\$")
    )

    # ---------- O que foi investido + custo do dinheiro ----------
    df_aportes = load_ap_claudio_aportes()
    TAXA_CAPITAL = 0.12
    hoje = datetime.now()
    total_aportado = float(df_aportes["Valor Pago"].sum()) if not df_aportes.empty else 0.0
    n_aportes = int((df_aportes["Valor Pago"] > 0).sum()) if not df_aportes.empty else 0
    primeiro_aporte = df_aportes["Data_dt"].min() if not df_aportes.empty else pd.NaT
    custo_corrigido = custo_capital_corrigido(df_aportes, TAXA_CAPITAL, hoje) if not df_aportes.empty else 0.0
    breakeven = custo_corrigido + saldo_dev

    st.markdown('<h3 style="margin-top:20px">O que foi investido</h3>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="background:#fff;border-radius:14px;padding:16px;box-shadow:0 2px 8px rgba(12,60,45,0.06)">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;font-size:13px">
            <div style="color:#5C6B62">Total já aportado ({n_aportes} pagamentos)</div><div style="text-align:right;font-weight:700">{fmt(total_aportado)}</div>
            <div style="color:#5C6B62">Primeiro aporte</div><div style="text-align:right;font-weight:700">{primeiro_aporte.strftime('%d/%m/%Y') if pd.notna(primeiro_aporte) else '—'}</div>
            <div style="color:#5C6B62">Saldo a pagar (quitação final)</div><div style="text-align:right;font-weight:700">{fmt(saldo_dev)}</div>
            <div style="color:#5C6B62;font-weight:700">Total contratado (nominal)</div><div style="text-align:right;font-weight:800">{fmt(custo)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<h3 style="margin-top:20px">Custo do dinheiro</h3>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="background:#fff;border-radius:14px;padding:16px;box-shadow:0 2px 8px rgba(12,60,45,0.06)">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;font-size:13px">
            <div style="color:#5C6B62">Taxa de custo de capital usada</div><div style="text-align:right;font-weight:700">{TAXA_CAPITAL*100:.0f}% a.a.</div>
            <div style="color:#5C6B62">Aportes corrigidos até hoje</div><div style="text-align:right;font-weight:700">{fmt(custo_corrigido)}</div>
            <div style="color:#5C6B62">(+) saldo a pagar</div><div style="text-align:right;font-weight:700">{fmt(saldo_dev)}</div>
            <div style="border-top:1px solid #E1EAE4;margin-top:4px;padding-top:6px;color:#1C2420;font-weight:800">Breakeven mínimo de venda</div>
            <div style="border-top:1px solid #E1EAE4;margin-top:4px;padding-top:6px;text-align:right;font-weight:800;color:{COR['alerta']}">{fmt(breakeven)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        ("cada aporte corrigido da data do pagamento até hoje, capitalização diária composta — "
         "é quanto esse dinheiro valeria se tivesse rendido a taxa acima em vez de ter ido pro imóvel. "
         "abaixo do breakeven, a venda perde dinheiro em termos reais mesmo dando lucro no papel."
         ).replace("R$", "R\\$")
    )

    # ---------- Top 10 dividendos B3 2025 (dados reais) ----------
    TOP10_DIVIDENDOS_2025 = [
        ("Syn Prop & Tech", "SYNE3", 54.87),
        ("Guararapes", "GUAR3", 49.98),
        ("JSL", "JSLG3", 35.33),
        ("Vulcabras", "VULC3", 35.12),
        ("Grendene", "GRND3", 34.90),
        ("Alpargatas", "ALPA4", 29.90),
        ("Direcional", "DIRR3", 29.77),
        ("Lavvi", "LAVV3", 27.57),
        ("Unipar", "UNIP6", 26.11),
        ("Cury S/A", "CURY3", 25.99),
    ]
    TAXA_ACOES_DIV = sum(dy for _, _, dy in TOP10_DIVIDENDOS_2025) / len(TOP10_DIVIDENDOS_2025) / 100

    st.markdown('<h3 style="margin-top:20px">Top 10 dividendos B3 2025 · cenário de stress</h3>', unsafe_allow_html=True)
    st.caption(
        "isto NÃO é uma expectativa de retorno — é um teste de estresse pegando o melhor cenário real observado "
        "em 2025, pra ver se mesmo o topo do topo supera o imóvel. simulação, não recomendação de investimento."
    )
    _df_top10 = pd.DataFrame(
        [{"Empresa": nome, "Ticker": tk, "Dividend Yield 2025": f"{dy:.2f}%"} for nome, tk, dy in TOP10_DIVIDENDOS_2025]
    )
    st.dataframe(_df_top10, use_container_width=True, hide_index=True)
    st.caption(
        (f"yield REALIZADO em 2025 (não é promessa nem média de longo prazo) — média simples dos 10: {TAXA_ACOES_DIV*100:.2f}% a.a. "
         "vários desses yields vieram de distribuição extraordinária (ex: venda de ativo), não é o que se repete todo ano — "
         "esse número só entra no comparativo abaixo como cenário de stress. fonte: B3 (Bora Investir)."
         )
    )

    # ---------- Comparativo com outras aplicações (mesmo fluxo de caixa, taxas alternativas) ----------
    TAXA_CDB = 0.11  # CDB ~100% CDI — ajustar conforme CDI vigente
    equity_imovel = vm - saldo_dev
    cdb_corrigido = custo_capital_corrigido(df_aportes, TAXA_CDB, hoje) if not df_aportes.empty else 0.0
    acoes_corrigido = custo_capital_corrigido(df_aportes, TAXA_ACOES_DIV, hoje) if not df_aportes.empty else 0.0

    st.markdown('<h3 style="margin-top:20px">Comparativo com outras aplicações</h3>', unsafe_allow_html=True)
    _comp = pd.DataFrame(
        [
            {"Aplicação": "AP 501 (equity atual, bruto)", "Taxa considerada": "ganho real do imóvel", "Valor hoje": equity_imovel, "vs. imóvel": 0.0},
            {"Aplicação": "CDB (100% CDI)", "Taxa considerada": f"{TAXA_CDB*100:.0f}% a.a.", "Valor hoje": cdb_corrigido, "vs. imóvel": cdb_corrigido - equity_imovel},
            {"Aplicação": "Top 10 dividendos B3 2025 (stress)", "Taxa considerada": f"{TAXA_ACOES_DIV*100:.2f}% a.a. (melhor caso real, não expectativa)", "Valor hoje": acoes_corrigido, "vs. imóvel": acoes_corrigido - equity_imovel},
        ]
    )
    st.dataframe(
        _comp.style.format({c: (lambda v: fmt(v)) for c in ("Valor hoje", "vs. imóvel")}),
        use_container_width=True, hide_index=True,
    )
    st.caption(
        (f"mesmo fluxo de aportes ({fmt(total_aportado)}, nas mesmas datas) corrigido pela taxa de cada aplicação até hoje, "
         f"comparado com o equity bruto do imóvel hoje ({fmt(equity_imovel)} = valor de mercado − saldo devedor, sem tributos "
         "de venda). CDB é baixo risco e o rendimento é praticamente garantido pelo emissor; mesmo no stress dos "
         "10 melhores pagadores de dividendos de 2025 (tabela acima), o imóvel ainda ganha. nenhum dos três desconta o "
         "imposto de saída de cada aplicação (IR regressivo no CDB, ganho de capital nas ações) — só a venda do imóvel "
         "tem essa conta feita, na simulação abaixo."
         ).replace("R$", "R\\$")
    )

    # ---------- Simulação de resultado: nominal × custo de capital, cada um nos 2 cenários de ITBI ----------
    st.markdown('<h3 style="margin-top:20px">Simulação de resultado</h3>', unsafe_allow_html=True)

    def _cenario(nome: str, regularizacao: float, custo_base_cash: float) -> dict:
        """custo_base_cash = saldo_dev (nominal) ou breakeven (custo de capital) — o que sai
        do caixa na venda, sem contar regularização. Ganho de capital (fiscal) sempre usa o
        custo TOTAL contratado + regularização capitalizada — regra PJ, igual nos 2 lentes."""
        custo_fiscal = custo + regularizacao
        ganho_c = max(vm - custo_fiscal, 0.0)
        trib_c = _tributos_pj(ganho_c)
        liquido_c = vm - custo_base_cash - regularizacao - trib_c["total"]
        return {
            "Cenário": nome,
            "Ganho de capital (PJ)": ganho_c,
            "Tributos (PJ)": trib_c["total"],
            "Custos de regularização": regularizacao,
            "Líquido estimado": liquido_c,
        }

    _sim = pd.DataFrame(
        [
            _cenario("Nominal · guia ITBI emitida", regularizacao_emitido, saldo_dev),
            _cenario("Nominal · revisão do ITBI aceita", regularizacao_revisao, saldo_dev),
            _cenario("Custo de capital · guia ITBI emitida", regularizacao_emitido, breakeven),
            _cenario("Custo de capital · revisão do ITBI aceita", regularizacao_revisao, breakeven),
        ]
    )
    _cols_money = ("Ganho de capital (PJ)", "Tributos (PJ)", "Custos de regularização", "Líquido estimado")
    st.dataframe(
        _sim.style.format({c: (lambda v: fmt(v)) for c in _cols_money}),
        use_container_width=True, hide_index=True,
    )
    _liq_nom_emit = _sim.loc[0, "Líquido estimado"]
    _liq_nom_rev = _sim.loc[1, "Líquido estimado"]
    _liq_real_emit = _sim.loc[2, "Líquido estimado"]
    _liq_real_rev = _sim.loc[3, "Líquido estimado"]
    margem_real = (_liq_real_rev / breakeven * 100) if breakeven > 0 else 0.0
    st.caption(
        (f"vendendo hoje por {fmt(vm)}: no nominal, o líquido vai de {fmt(_liq_nom_emit)} (se o ITBI ficar como a PBH "
         f"lançou) a {fmt(_liq_nom_rev)} (se a revisão for aceita) — diferença de {fmt(_liq_nom_rev - _liq_nom_emit)}. "
         f"Descontando o custo de capital, o líquido REAL vai de {fmt(_liq_real_emit)} a {fmt(_liq_real_rev)} "
         f"({margem_real:.1f}% de margem real sobre o breakeven, no cenário da revisão). "
         "cada cenário de ITBI recalcula o ganho de capital porque, sendo PJ, ITBI/escritura/registro/despachante "
         "entram no custo de aquisição do imóvel — reduzem o ganho tributável, não são despesa separada."
         ).replace("R$", "R\\$")
    )

    # ---------- Pendências ----------
    st.markdown('<h3 style="margin-top:20px">Pendências</h3>', unsafe_allow_html=True)
    _pendencias = [
        (True, "Contratos (PCV + Construção) assinados por Wesley e pela DMA — validado 05/08"),
        (True, "1ª parcela do despachante (R$ 600) paga — 30/07"),
        (False, "ITBI em disputa: guia da PBH de R$ 28.557,72 (avaliou como imóvel pronto) vs. R$ 5.657,93 esperado — aguardando revisão (protocolo 70/044293-26-80)"),
        (False, "Enviar ao despachante: CNH, certidão de casamento atualizada e qualificação"),
        (False, f"Quitar saldo final ({fmt(saldo_dev)} + INCC) e negociar outorga da escritura — evitar cessão (3% DMA)"),
    ]
    _linhas_pend = "".join(
        f"""<div style="display:flex;gap:8px;padding:6px 0;border-bottom:1px solid #F0F3F1;font-size:13px">
              <div>{'✅' if done else '⬜'}</div>
              <div style="color:{'#8B978F' if done else '#1C2420'}">{texto}</div>
            </div>"""
        for done, texto in _pendencias
    )
    st.markdown(
        f'<div style="background:#fff;border-radius:14px;padding:16px 16px 8px;box-shadow:0 2px 8px rgba(12,60,45,0.06)">{_linhas_pend}</div>',
        unsafe_allow_html=True,
    )
    st.caption("snapshot manual — fonte de verdade é o DOSSIE - AP 501 Ed Claudio de Paula.md na pasta do investimento")
else:
    st.info("AP Cláudio não encontrado na aba Bens.")
