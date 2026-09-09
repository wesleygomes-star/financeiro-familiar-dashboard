"""Visão Anual — matriz categoria × mês (Jan-Dez), estilo Controle 2026.
set_page_config + auth no router."""
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.components import barra_navegacao, COR, PLOTLY_CONFIG, faixa_titulo, fig_mobile, tema_verde_premium
from lib.data import evolucao_fixas, is_investimento, is_pagamento_fatura, is_rd, load_lancamentos, load_recorrentes

tema_verde_premium()
barra_navegacao("anual")
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

faixa_titulo("Visão anual")
_esp, c2, c3 = st.columns([2, 1, 1])
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
    "Despesas": dfa[(dfa["Tipo"].astype(str).str.lower() == "despesa") & (~dfa.apply(is_investimento, axis=1)) & (~dfa.apply(is_pagamento_fatura, axis=1)) & (~dfa.apply(is_rd, axis=1))],
    "Receitas": dfa[(dfa["Tipo"].astype(str).str.lower() == "receita") & (~dfa.apply(is_rd, axis=1))],
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

# ============== Contas fixas · evolução (aprovado 08/09/2026) ==============
# Recorrente × mês: valor PAGO (lançamento casado pelo mesmo pareamento do card Contas fixas)
# contra o ESPERADO do cadastro. Célula âmbar = pagou +5% acima; verde = −5% abaixo;
# hachura = fora da vigência (Início/Fim); "—" = não pagou / sem par no mês.
_NM_CURTO = {"01": "jan", "02": "fev", "03": "mar", "04": "abr", "05": "mai", "06": "jun",
             "07": "jul", "08": "ago", "09": "set", "10": "out", "11": "nov", "12": "dez"}
st.markdown(
    """<style>
    .fx-k{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:4px 0 10px}
    .fx-k .k5{padding:11px 13px}
    .fx-k .k5-s{font-size:12px;color:#5C6B63;margin-top:2px}
    .fx-tw{overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:14px;background:#fff;box-shadow:0 3px 14px rgba(12,60,45,0.07);padding:4px 10px 8px}
    table.fx{border-collapse:separate;border-spacing:0;font-size:12.5px;width:100%;min-width:760px;font-variant-numeric:tabular-nums}
    table.fx th,table.fx td{padding:7px 8px;text-align:right;border-bottom:1px solid #E6ECE8;white-space:nowrap}
    table.fx thead th{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:#8B978F;font-weight:600;border-bottom:2px solid #E6ECE8}
    table.fx thead th .n,table.fx td .n{display:block;font-size:10px;letter-spacing:0;text-transform:none;color:#8B978F;font-weight:400}
    table.fx tbody th{text-align:left;font-weight:600;position:sticky;left:0;background:#fff;z-index:1;max-width:200px;overflow:hidden;text-overflow:ellipsis;box-shadow:6px 0 8px -6px rgba(0,0,0,.12);color:#1F2A25}
    table.fx tbody th .ct{display:block;font-size:11px;color:#8B978F;font-weight:400}
    table.fx td.e{color:#5C6B63;font-weight:600;background:#EEF4F0}
    table.fx td.np{color:#8B978F}
    table.fx td.na{background:repeating-linear-gradient(135deg,transparent 0 4px,#E6ECE8 4px 5px)}
    table.fx td.up{background:#FBF3E3;color:#BA7517;font-weight:600}
    table.fx td.dn{background:#EEF4F0;color:#0F6E56;font-weight:600}
    table.fx tr.tot th,table.fx tr.tot td{border-top:2px solid #1F2A25;border-bottom:0;font-weight:700}
    .fx-tag{display:inline-block;font-size:10px;padding:0 6px;border-radius:999px;background:#EEF4F0;color:#185FA5;font-weight:600;margin-left:4px}
    .fx-tag.off{color:#8B978F}
    .fx-leg{display:flex;flex-wrap:wrap;gap:12px;font-size:11.5px;color:#5C6B63;margin:8px 0 2px}
    .fx-leg i{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-2px;margin-right:4px}
    ul.fx-mud{list-style:none;padding:0;margin:0 0 6px}
    ul.fx-mud li{display:grid;grid-template-columns:1fr auto;gap:2px 10px;padding:8px 0;border-bottom:1px solid #E6ECE8}
    ul.fx-mud .nm{font-weight:600;color:#1F2A25}
    ul.fx-mud .vals{grid-column:1/3;font-size:12px;color:#5C6B63}
    .fx-d{font-weight:700;border-radius:999px;padding:1px 9px;font-size:12px}
    .fx-d.up{background:#FBF3E3;color:#BA7517}
    .fx-d.dn{background:#EEF4F0;color:#0F6E56}
    @media (max-width:480px){.fx-k{grid-template-columns:1fr 1fr}.fx-k .k5:first-child{grid-column:1/3}}
    </style>""",
    unsafe_allow_html=True,
)


def _brl_int(v):
    if v is None or pd.isna(v):
        return "—"
    return "R$ " + f"{v:,.0f}".replace(",", ".")


def _html_esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


ev = evolucao_fixas(df, load_recorrentes(), ano)
st.subheader("Contas fixas · evolução")
if not ev["contas"]:
    st.caption("Sem contas recorrentes cadastradas para este ano.")
else:
    _ms = ev["meses"]; _cur = ev["em_curso"]
    _fech = _ms[-2] if (_cur and len(_ms) > 1) else _ms[-1]   # último mês fechado
    _tp, _te, _np, _nv = ev["tot_pago"], ev["tot_esp"], ev["n_pago"], ev["n_vig"]
    _lbl = lambda m: _NM_CURTO.get(m[:2], m[:2])
    _tiles = (
        f'<div class="k5"><div class="k5-l">{_lbl(_fech)} (fechado)</div><div class="k5-v">{_brl_int(_tp[_fech])}</div>'
        f'<div class="k5-s">{_np[_fech]} de {_nv[_fech]} contas · cadastro {_brl_int(_te[_fech])}</div></div>'
    )
    if _cur:
        _tiles += (
            f'<div class="k5"><div class="k5-l">{_lbl(_cur)} até agora</div><div class="k5-v">{_brl_int(_tp[_cur])}</div>'
            f'<div class="k5-s">{_np[_cur]} de {_nv[_cur]} pagas · faltam {_brl_int(max(_te[_cur] - _tp[_cur], 0))}</div></div>'
            f'<div class="k5"><div class="k5-l">cadastro de {_lbl(_cur)}</div><div class="k5-v">{_brl_int(_te[_cur])}</div>'
            f'<div class="k5-s">{_nv[_cur]} contas vigentes</div></div>'
        )
    else:
        _tiles += (
            f'<div class="k5"><div class="k5-l">total no ano</div><div class="k5-v">{_brl_int(sum(_tp.values()))}</div>'
            f'<div class="k5-s">cadastro {_brl_int(sum(_te.values()))}</div></div>'
            f'<div class="k5"><div class="k5-l">média mensal</div><div class="k5-v">{_brl_int(sum(_tp.values()) / max(len(_ms), 1))}</div>'
            f'<div class="k5-s">contas fixas pagas</div></div>'
        )
    st.markdown(f'<div class="fx-k">{_tiles}</div>', unsafe_allow_html=True)

    # Gráfico: total pago (azul) × cadastro vigente (tracejado). Mês em curso em pontilhado.
    _x = [_lbl(m) for m in _ms]
    _pago = [_tp[m] for m in _ms]; _esp_s = [_te[m] for m in _ms]
    _fx = go.Figure()
    _fx.add_scatter(name="cadastro (soma vigente)", x=_x, y=_esp_s, mode="lines",
                    line=dict(color=COR["neutro"], width=1.5, dash="dash"),
                    hovertemplate="%{x}: cadastro R$ %{y:,.0f}<extra></extra>")
    _n_fech = len(_ms) - (1 if _cur else 0)
    _fx.add_scatter(name="pago", x=_x[:_n_fech], y=_pago[:_n_fech], mode="lines+markers",
                    line=dict(color=COR["investimento"], width=2.2), marker=dict(size=7, color="#fff", line=dict(color=COR["investimento"], width=2)),
                    fill="tozeroy", fillcolor="rgba(24,95,165,0.08)",
                    hovertemplate="%{x}: pago R$ %{y:,.0f}<extra></extra>")
    if _cur:
        _fx.add_scatter(name="em curso", x=_x[_n_fech - 1:], y=_pago[_n_fech - 1:], mode="lines+markers", showlegend=False,
                        line=dict(color=COR["investimento"], width=2.2, dash="dot"), marker=dict(size=7, color="#fff", line=dict(color=COR["investimento"], width=2)),
                        hovertemplate="%{x} (em curso): pago R$ %{y:,.0f}<extra></extra>")
    _fx.update_layout(height=240, margin=dict(l=10, r=10, t=10, b=10), template="plotly_white",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#2C2C2A", size=12),
                      hovermode="x unified", legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5))
    _fx.update_yaxes(tickformat=",.0f", gridcolor="#E6ECE8", zeroline=False)
    st.plotly_chart(fig_mobile(_fx), use_container_width=True, config=PLOTLY_CONFIG)

    # Matriz conta × mês
    _head = "".join(f"<th>{_lbl(m)}{'<span class=n>em curso</span>' if m == _cur else ''}</th>" for m in _ms)
    _rows = ""
    for c in ev["contas"]:
        vig = c["vigente"]
        tag = ""
        if vig and vig[0] != _ms[0]:
            tag = f'<span class="fx-tag">desde {_lbl(vig[0])}</span>'
        if vig and vig[-1] != _ms[-1]:
            tag = f'<span class="fx-tag off">até {_lbl(vig[-1])}</span>'
        cells = ""
        for m in _ms:
            if m not in c["vals"]:
                cells += '<td class="na"></td>'; continue
            v = c["vals"][m]
            if v is None:
                cells += '<td class="np">—</td>'; continue
            e = c["esperado"]; d = (v - e) / e if e else 0
            cls = "up" if d > 0.05 else ("dn" if d < -0.05 else "")
            tip = f' title="cadastro {_brl_int(e)} · {d * 100:+.0f}%"' if cls else ""
            cells += f'<td class="{cls}"{tip}>{_brl_int(v)}</td>'
        _rows += (f'<tr><th scope="row">{_html_esc(c["nome"])}<span class="ct">{_html_esc(c["categoria"])} {tag}</span></th>'
                  f'<td class="e">{_brl_int(c["esperado"])}</td>{cells}</tr>')
    _tot = ('<tr class="tot"><th scope="row">Total pago<span class="ct">contas casadas no mês</span></th>'
            f'<td class="e">{_brl_int(_te[_ms[-1]])}</td>'
            + "".join(f'<td>{_brl_int(_tp[m])}<span class="n">{_np[m]}/{_nv[m]}</span></td>' for m in _ms) + "</tr>")
    st.markdown(
        f'<div class="fx-tw"><table class="fx"><thead><tr><th style="text-align:left">Conta</th><th>Cadastro</th>{_head}</tr></thead>'
        f'<tbody>{_rows}{_tot}</tbody></table></div>'
        '<div class="fx-leg"><span><i style="background:#FBF3E3;border:1px solid #BA7517"></i>pagou +5% acima do cadastro</span>'
        '<span><i style="background:#EEF4F0;border:1px solid #0F6E56"></i>pagou −5% abaixo</span>'
        '<span>— não pagou / sem par no mês</span>'
        '<span><i style="background:repeating-linear-gradient(135deg,transparent 0 3px,#8B978F 3px 4px)"></i>fora da vigência</span></div>',
        unsafe_allow_html=True,
    )

    # Quem fugiu do cadastro no último mês fechado (acima de 5%)
    _mud = []
    for c in ev["contas"]:
        v = c["vals"].get(_fech)
        if v is None or not c["esperado"]:
            continue
        d = (v - c["esperado"]) / c["esperado"]
        if abs(d) > 0.05:
            _mud.append((c["nome"], v, c["esperado"], d))
    _mud.sort(key=lambda t: -abs(t[3]))
    if _mud:
        st.markdown(f"**Quem fugiu do cadastro em {_lbl(_fech)}** · acima de 5%")
        st.markdown('<ul class="fx-mud">' + "".join(
            f'<li><span class="nm">{_html_esc(n)}</span><span class="fx-d {"up" if d > 0 else "dn"}">{d * 100:+.0f}%</span>'
            f'<span class="vals">{_brl_int(v)} pago em {_lbl(_fech)} · cadastro {_brl_int(e)}</span></li>'
            for n, v, e, d in _mud[:8]) + "</ul>", unsafe_allow_html=True)
    st.caption("Cada célula é o lançamento que o painel casou com a recorrente naquele mês (mesmo pareamento do card Contas fixas). "
               "Contas com Início/Fim no cadastro aparecem só na vigência.")

# Tabelas matriz — formato pt-BR (milhar com ponto), células vazias sem "None"
def _mil(v):
    if pd.isna(v):
        return "—"
    return f"{v:,.0f}".replace(",", ".")


def _brl0(v):
    if pd.isna(v):
        return "—"
    return "R$ " + f"{v:,.0f}".replace(",", ".")


for nome, cor in [("Despesas", "#E24B4A"), ("Receitas", "#1D9E75"), ("Investimentos", "#185FA5")]:
    disp, totais, total = matriz(splits[nome], nome, cor)
    if disp is None or disp.empty:
        continue
    st.subheader(f"{nome} · R$ {fmt(total)} no ano")
    _fmt_cols = {"Total": _brl0, "Média": _brl0}
    _fmt_cols.update({m: _mil for m in meses_lbl})
    st.dataframe(disp.round(0).style.format(_fmt_cols), use_container_width=True,
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
    st.dataframe(res.style.format({c: _brl0 for c in ("Receita", "Despesa", "Investido", "Saldo")}),
                 use_container_width=True, hide_index=True)

st.caption("Jan–Jul: custos fixos (histórico Controle) + detalhe real dos cartões (faturas Itaú/XP) "
           "+ lançamentos do Zap. Pagamento de fatura é excluído (transferência, não consumo).")
