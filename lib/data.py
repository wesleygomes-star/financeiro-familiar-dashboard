"""Acesso aos dados do Google Sheets via Service Account."""
import json
from datetime import datetime
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "1cl9heM5gZiMVbGlWa8j_BlYEa0MwBq40k_bK27H_qaA"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


@st.cache_resource
def _client():
    """Cria cliente gspread autenticado via Service Account.
    A key JSON vem dos secrets do Streamlit (em produção) ou de /tmp local.
    """
    if "gcp_service_account" in st.secrets:
        sa_info = dict(st.secrets["gcp_service_account"])
    else:
        # fallback dev local
        sa_info = json.load(open("/tmp/sa_key.json"))
    creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    return gspread.authorize(creds)


def _ws(name: str):
    return _client().open_by_key(SHEET_ID).worksheet(name)


def _parse_data(s):
    """Converte string DD/MM/YYYY pra datetime, retorna NaT se inválido."""
    if isinstance(s, str) and "/" in s:
        try:
            return datetime.strptime(s, "%d/%m/%Y")
        except Exception:
            return pd.NaT
    return pd.NaT


# Canonicalização de categorias (fix encoding inconsistente acumulado)
CATEGORIAS_CANONICAS = {
    "vestuario": "Vestuário",
    "vestuário": "Vestuário",
    "saude": "Saúde",
    "saúde": "Saúde",
    "educacao": "Educação",
    "educação": "Educação",
    "financeiro & cartao": "Financeiro & Cartão",
    "financeiro & cartão": "Financeiro & Cartão",
    "alimentacao": "Alimentação",
    "alimentação": "Alimentação",
    "auxilio familiar": "Auxílio Familiar",
    "auxílio familiar": "Auxílio Familiar",
    "assinaturas & streaming": "Assinaturas & Streaming",
    "pro-labore": "Pró-labore",
    "pró-labore": "Pró-labore",
    "outros imoveis": "Outros Imóveis",
    "outros imóveis": "Outros Imóveis",
    "investimentos em imovel": "Investimentos em Imóvel",
    "investimentos em imóvel": "Investimentos em Imóvel",
}


def _normalizar_categoria(c):
    if not c or pd.isna(c):
        return ""
    return CATEGORIAS_CANONICAS.get(str(c).strip().lower(), str(c).strip())


def _parse_valor(v):
    """Aceita '1.234,56' (PT-BR) ou '1234.56' ou int. Retorna float."""
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("R$", "").replace(" ", "")
    if "," in s and "." in s:
        # PT-BR: ponto=milhar, vírgula=decimal
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def _records_formatted(name: str):
    """Lê aba como records — FORMATTED_VALUE (default) + desliga numericise auto do gspread.
    Tudo vem como string formatada; meu parser converte com cuidado.
    """
    ws = _ws(name)
    return ws.get_all_records(numericise_ignore=["all"])


@st.cache_data(ttl=60)
def load_lancamentos(incluir_cancelados: bool = False) -> pd.DataFrame:
    rows = _records_formatted("Lançamentos")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["Valor"] = df["Valor"].apply(_parse_valor)
    df["Data_dt"] = df["Data"].apply(_parse_data)
    df["Data Caixa_dt"] = df["Data Caixa"].apply(_parse_data)
    if "Categoria" in df.columns:
        df["Categoria"] = df["Categoria"].apply(_normalizar_categoria)
    # Coluna Mês Caixa (MM/YYYY) extraída de Data Caixa pra usar como pivot na visão Caixa
    df["Mês Caixa"] = df["Data Caixa_dt"].apply(
        lambda d: f"{d.month:02d}/{d.year}" if pd.notna(d) else ""
    )
    # Coluna Status (default Ativo se ausente ou vazio) — pra preservar histórico mas excluir
    # lançamentos cancelados dos totais. Toggle UI pode incluir cancelados na visão "TODOS".
    if "Status" not in df.columns:
        df["Status"] = "Ativo"
    else:
        # Case-insensitive: aceita "Ativo", "ativo", "ATIVO" etc; normaliza vazio → Ativo
        df["Status"] = df["Status"].astype(str).str.strip().replace("", "Ativo")
    if not incluir_cancelados:
        df = df[df["Status"].str.lower() != "cancelado"].copy()
    return df


@st.cache_data(ttl=60)
def load_recorrentes() -> pd.DataFrame:
    rows = _records_formatted("Recorrentes")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["Valor"] = df["Valor"].apply(_parse_valor)
    df["Ativo_bool"] = df["Ativo"].astype(str).str.lower().isin(["sim", "yes", "true", "1"])
    return df


@st.cache_data(ttl=60)
def load_tetos() -> pd.DataFrame:
    rows = _records_formatted("Tetos")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["Teto Mensal"] = df["Teto Mensal"].apply(_parse_valor)
    return df


def mes_anterior(competencia: str) -> str:
    """Recebe 'MM/YYYY' e retorna o mês anterior no mesmo formato.

    Ex: '05/2026' -> '04/2026'; '01/2026' -> '12/2025'.
    """
    try:
        m, y = competencia.split("/")
        m, y = int(m), int(y)
    except Exception:
        return ""
    m -= 1
    if m < 1:
        m = 12
        y -= 1
    return f"{m:02d}/{y}"


def progresso_mes(competencia: str) -> float:
    """Retorna a fração do mês já decorrida (0.0 a 1.0).

    Se o mês ainda não começou -> 0.0
    Se o mês já terminou -> 1.0
    Se é o mês atual -> dia_hoje / dias_no_mes
    """
    from calendar import monthrange
    try:
        m, y = competencia.split("/")
        m, y = int(m), int(y)
    except Exception:
        return 1.0
    hoje = datetime.now()
    if (y, m) < (hoje.year, hoje.month):
        return 1.0
    if (y, m) > (hoje.year, hoje.month):
        return 0.0
    dias_no_mes = monthrange(y, m)[1]
    return hoje.day / dias_no_mes


def meses_disponiveis(df: pd.DataFrame, modo: str = "Competência") -> list:
    """Lista de meses únicos no formato MM/YYYY.
    modo: 'Competência' usa coluna Competência, 'Caixa' usa Mês Caixa.
    """
    coluna = "Mês Caixa" if modo == "Caixa" else "Competência"
    if df.empty or coluna not in df.columns:
        return []
    valores = df[coluna].dropna()
    valores = valores[valores != ""]
    comps = valores.unique().tolist()
    def chave(c):
        try:
            m, y = c.split("/")
            return int(y) * 100 + int(m)
        except Exception:
            return 0
    return sorted(comps, key=chave, reverse=True)


def classificar_fixa_variavel(df_lancamentos: pd.DataFrame, df_recorrentes: pd.DataFrame) -> pd.DataFrame:
    """Adiciona coluna 'Tipo Despesa' = 'Fixa' ou 'Variável'.

    Heurística: um lançamento é considerado FIXO se a descrição bater
    (substring case-insensitive) com a descrição de alguma recorrente ATIVA
    e a categoria também coincidir. Caso contrário é VARIÁVEL.

    Receitas mantêm 'Tipo Despesa' = '' (não se aplica).
    """
    out = df_lancamentos.copy()
    out["Tipo Despesa"] = ""

    if df_recorrentes.empty or "Ativo_bool" not in df_recorrentes.columns:
        out.loc[out["Tipo"] == "Despesa", "Tipo Despesa"] = "Variável"
        return out

    rec_ativas = df_recorrentes[df_recorrentes["Ativo_bool"]].copy()
    if rec_ativas.empty:
        out.loc[out["Tipo"] == "Despesa", "Tipo Despesa"] = "Variável"
        return out

    # Coluna de descrição na planilha de recorrentes pode variar
    col_desc_rec = None
    for c in ("Descrição", "Descricao", "Item", "Nome"):
        if c in rec_ativas.columns:
            col_desc_rec = c
            break

    if col_desc_rec is None:
        # Fallback: matching só por Categoria
        cats_fixas = set(rec_ativas["Categoria"].dropna().astype(str).str.lower().str.strip())
        def eh_fixa_por_cat(row):
            if row.get("Tipo") != "Despesa":
                return ""
            cat = str(row.get("Categoria", "")).lower().strip()
            return "Fixa" if cat in cats_fixas else "Variável"
        out["Tipo Despesa"] = out.apply(eh_fixa_por_cat, axis=1)
        return out

    # Constrói lista de tuplas (categoria_lower, descricao_lower) das recorrentes ativas
    pares_fixos = []
    for _, r in rec_ativas.iterrows():
        cat = str(r.get("Categoria", "")).lower().strip()
        desc = str(r.get(col_desc_rec, "")).lower().strip()
        if desc:
            pares_fixos.append((cat, desc))

    def classificar(row):
        if row.get("Tipo") != "Despesa":
            return ""
        cat_l = str(row.get("Categoria", "")).lower().strip()
        desc_l = str(row.get("Descrição", "")).lower().strip()
        for cat_rec, desc_rec in pares_fixos:
            # match se descrição da recorrente está contida na do lançamento (ou vice-versa)
            # e a categoria coincide (se categoria da recorrente foi informada)
            desc_match = (desc_rec in desc_l) or (desc_l and desc_l in desc_rec)
            cat_match = (not cat_rec) or (cat_rec == cat_l)
            if desc_match and cat_match:
                return "Fixa"
        return "Variável"

    out["Tipo Despesa"] = out.apply(classificar, axis=1)
    return out


def filtrar(df: pd.DataFrame, competencia: str = None, pessoa: str = None, tipo: str = None, modo: str = "Competência") -> pd.DataFrame:
    """Filtra dataframe por mês (Competência ou Caixa, conforme modo), pessoa e/ou tipo."""
    out = df.copy()
    coluna_mes = "Mês Caixa" if modo == "Caixa" else "Competência"
    if competencia and coluna_mes in out.columns:
        out = out[out[coluna_mes] == competencia]
    if pessoa and "Pessoa" in out.columns:
        out = out[out["Pessoa"] == pessoa]
    if tipo and "Tipo" in out.columns:
        out = out[out["Tipo"] == tipo]
    return out


# ============================================================================
# Loaders adicionais (Faturas, Saldo Investido)
# ============================================================================

@st.cache_data(ttl=60)
def load_faturas() -> pd.DataFrame:
    rows = _records_formatted("Faturas")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if "Total" in df.columns:
        df["Total_num"] = df["Total"].apply(_parse_valor)
    if "Vencimento" in df.columns:
        df["Vencimento_dt"] = df["Vencimento"].apply(_parse_data)
    if "Fechamento" in df.columns:
        df["Fechamento_dt"] = df["Fechamento"].apply(_parse_data)
    if "Qtd Trans" in df.columns:
        df["Qtd Trans_num"] = pd.to_numeric(df["Qtd Trans"], errors="coerce").fillna(0).astype(int)
    return df


@st.cache_data(ttl=60)
def load_saldo_investido() -> pd.DataFrame:
    try:
        rows = _records_formatted("Saldo Investido")
    except Exception:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if "Saldo Total" in df.columns:
        df["Saldo Total"] = df["Saldo Total"].apply(_parse_valor)
    if "Aportado no Mês" in df.columns:
        df["Aportado no Mês"] = df["Aportado no Mês"].apply(_parse_valor)
    if "Rendimento Calc" in df.columns:
        df["Rendimento Calc"] = df["Rendimento Calc"].apply(_parse_valor)
    if "Data Snapshot" in df.columns:
        df["Data Snapshot_dt"] = df["Data Snapshot"].apply(_parse_data)
    return df


def saldo_estocado_atual(df_saldo: pd.DataFrame) -> dict:
    """Retorna {pessoa: saldo_total} usando o último snapshot por pessoa."""
    if df_saldo.empty or "Pessoa" not in df_saldo.columns:
        return {}
    out = {}
    for pessoa, grupo in df_saldo.groupby("Pessoa"):
        if "Data Snapshot_dt" in grupo.columns:
            g = grupo.sort_values("Data Snapshot_dt", ascending=False)
        else:
            g = grupo
        # soma por modalidade na data mais recente
        if g.empty:
            continue
        ultima_data = g.iloc[0].get("Data Snapshot_dt")
        if pd.notna(ultima_data):
            no_dia = g[g["Data Snapshot_dt"] == ultima_data]
        else:
            no_dia = g.head(5)
        out[pessoa] = float(no_dia["Saldo Total"].sum()) if "Saldo Total" in no_dia.columns else 0.0
    return out


# ============================================================================
# Helpers de classificação (Investimento, Despesa real, Receita)
# ============================================================================

CAT_INVESTIMENTO = "Investimentos"  # modelo temporário; quando WF1 suportar Tipo='Investimento', mudar pra filtro Tipo


def is_investimento(row) -> bool:
    """Aceita modelo atual (Tipo=Despesa + Categoria=Investimentos) e modelo futuro (Tipo=Investimento)."""
    tipo = str(row.get("Tipo", "")).strip().lower()
    cat = str(row.get("Categoria", "")).strip().lower()
    return tipo == "investimento" or cat == CAT_INVESTIMENTO.lower()


def is_pagamento_fatura(row) -> bool:
    """Pagamento de fatura = transferência conta→cartão, NÃO consumo.
    As compras individuais da fatura já representam o gasto (com categoria + Data Caixa
    = vencimento). Contar o pagamento separado DUPLICA o valor. Por isso é excluído
    dos totais de despesa, igual ao investimento. (descoberto 16/06/2026)"""
    tipo = str(row.get("Tipo", "")).strip().lower()
    if tipo != "despesa":
        return False
    desc = str(row.get("Descrição", "")).strip().lower()
    return ("pagamento" in desc and "fatura" in desc)


def split_movimentos(df: pd.DataFrame) -> dict:
    """Separa em receitas, despesas reais (sem investimento e sem pagamento de fatura) e aportes."""
    if df.empty:
        return {"receitas": df, "despesas": df, "aportes": df, "pagamentos": df}
    mask_inv = df.apply(is_investimento, axis=1)
    mask_pgto = df.apply(is_pagamento_fatura, axis=1)
    mask_rec = df["Tipo"].astype(str).str.strip().str.lower() == "receita"
    mask_desp = (df["Tipo"].astype(str).str.strip().str.lower() == "despesa") & (~mask_inv) & (~mask_pgto)
    return {
        "receitas": df[mask_rec].copy(),
        "despesas": df[mask_desp].copy(),
        "aportes": df[mask_inv].copy(),
        "pagamentos": df[mask_pgto].copy(),
    }


def aportes_historico(df_lanc: pd.DataFrame, n_meses: int = 12) -> pd.DataFrame:
    """Histórico de aportes (Investimento) por mês + pessoa pros últimos n_meses."""
    if df_lanc.empty:
        return pd.DataFrame()
    aportes = df_lanc[df_lanc.apply(is_investimento, axis=1)].copy() if not df_lanc.empty else pd.DataFrame()
    if aportes.empty:
        return aportes
    if "Competência" in aportes.columns:
        agrupado = aportes.groupby(["Competência", "Pessoa"])["Valor"].sum().reset_index()
        return agrupado
    return aportes


def _lancamentos_da_fatura(cartao_str: str, mes_ref: str, df_lanc: pd.DataFrame, vencimento: str = None) -> pd.DataFrame:
    """Lançamentos de crédito que pertencem a uma fatura.

    Chave correta: Data Caixa == Vencimento da fatura (o WF1 calcula Data Caixa
    pelo ciclo do cartão exatamente pra isso). Competência NÃO serve — a fatura
    de junho carrega compras de maio (lição de 11/06: rateio não batia).
    Fallback por competência só quando o vencimento não é informado.
    """
    if df_lanc.empty or "Cartão" not in df_lanc.columns:
        return pd.DataFrame()
    primeira = cartao_str.split()[0] if cartao_str else ""
    if not primeira:
        return pd.DataFrame()
    base = df_lanc[
        df_lanc["Cartão"].astype(str).str.lower().str.contains(primeira.lower(), na=False)
        & df_lanc["Forma Pgto"].astype(str).str.lower().str.contains("crédito|credito", na=False, regex=True)
    ]
    if vencimento:
        return base[base["Data Caixa"].astype(str).str.strip() == str(vencimento).strip()]
    if mes_ref:
        return base[base["Competência"] == mes_ref]
    return pd.DataFrame()


def fatura_estimada(cartao_str: str, mes_ref: str, df_lanc: pd.DataFrame, vencimento: str = None) -> tuple:
    """Retorna (valor_estimado, qtd_lancamentos) pra uma fatura ainda não carregada."""
    sub = _lancamentos_da_fatura(cartao_str, mes_ref, df_lanc, vencimento)
    if sub.empty:
        return (0.0, 0)
    return (float(sub["Valor"].sum()), len(sub))


def fatura_split_pessoa(cartao_str: str, mes_ref: str, df_lanc: pd.DataFrame, vencimento: str = None) -> dict:
    """Rateio do consumo da fatura por pessoa (cartão único com portadores múltiplos, ex.: XP Visa).
    Retorna {pessoa: total}.

    ATENÇÃO: pra fatura CARREGADA o rateio exato exige que a carga marque as
    duplicatas com o lote hash (pendente no WF1) — até lá esse rateio é
    aproximação pelos lançamentos com Data Caixa == Vencimento."""
    sub = _lancamentos_da_fatura(cartao_str, mes_ref, df_lanc, vencimento)
    if sub.empty or "Pessoa" not in sub.columns:
        return {}
    return sub.groupby("Pessoa")["Valor"].sum().sort_values(ascending=False).to_dict()


# ============================================================================
# Auditoria de Contas Fixas (Recorrentes) vs Lançamentos
# ============================================================================

# Categorias da aba Recorrentes que são RECEITAS (não viram conta fixa pra auditar)
CATEGORIAS_RECEITA = {
    "salário wesley", "salario wesley", "salário sabrina", "salario sabrina",
    "pró-labore", "pro-labore", "pro labore",
    "freelance", "freelance/extra", "freelance extra",
    "rendimentos",
    "outras receitas",
}


def _norm(s: str) -> str:
    import unicodedata
    s = str(s or "").strip().lower()
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def _recorrentes_despesa(df_rec: pd.DataFrame) -> pd.DataFrame:
    """Filtra recorrentes ativas que sejam despesa (exclui categorias de receita)."""
    if df_rec.empty:
        return df_rec
    ativas = df_rec[df_rec.get("Ativo_bool", False)].copy() if "Ativo_bool" in df_rec.columns else df_rec.copy()
    if ativas.empty:
        return ativas
    cat_lower = ativas["Categoria"].astype(str).str.strip().str.lower()
    return ativas[~cat_lower.isin(CATEGORIAS_RECEITA)].copy()


def auditar_contas_fixas(df_lanc: pd.DataFrame, df_rec: pd.DataFrame, competencia: str) -> pd.DataFrame:
    """Retorna DataFrame com 1 linha por recorrente ATIVA, status do mês.

    Status: 'Paga' / 'Pendente' / 'Atrasada' (Pendente se ainda há prazo, Atrasada se Dia Cobrança já passou).

    Match: descrição da recorrente (normalizada, substring) bate com descrição do lançamento + categoria.
    """
    if df_rec.empty:
        return pd.DataFrame()

    rec_ativas = _recorrentes_despesa(df_rec)
    if rec_ativas.empty:
        return pd.DataFrame()

    # Filtra lançamentos da competência alvo (modo Caixa pra refletir quando $ saiu)
    lanc_mes = df_lanc[df_lanc["Mês Caixa"] == competencia] if "Mês Caixa" in df_lanc.columns else df_lanc
    lanc_mes = lanc_mes[lanc_mes["Tipo"].astype(str).str.lower() == "despesa"] if "Tipo" in lanc_mes.columns else lanc_mes

    try:
        m, y = competencia.split("/")
        m, y = int(m), int(y)
    except Exception:
        m, y = datetime.now().month, datetime.now().year

    hoje = datetime.now()
    eh_mes_corrente = (hoje.month == m and hoje.year == y)
    dia_hoje = hoje.day if eh_mes_corrente else 31  # se mês passado, considera "fim do mês"

    out_rows = []
    for _, rec in rec_ativas.iterrows():
        desc_rec = str(rec.get("Descrição") or rec.get("Descricao") or rec.get("Item") or rec.get("Nome") or "").strip()
        cat_rec = str(rec.get("Categoria", "")).strip()
        pessoa_rec = str(rec.get("Pessoa", "")).strip()
        valor_esp = float(rec.get("Valor", 0) or 0)
        try:
            dia_cobranca = int(rec.get("Dia Cobrança") or rec.get("Dia") or 0)
        except Exception:
            dia_cobranca = 0

        # Match em lançamentos
        desc_n = _norm(desc_rec)
        cat_n = _norm(cat_rec)
        match = None
        for _, lan in lanc_mes.iterrows():
            ld = _norm(lan.get("Descrição", ""))
            lc = _norm(lan.get("Categoria", ""))
            desc_match = (desc_n and (desc_n in ld or ld in desc_n))
            cat_match = (not cat_n) or (cat_n == lc)
            if desc_match and cat_match:
                match = lan
                break

        if match is not None:
            status = "Paga"
            data_pagamento = match.get("Data Caixa") or match.get("Data")
            valor_pago = float(match.get("Valor", 0) or 0)
            pessoa_pagou = str(match.get("Pessoa", "")).strip()
        else:
            data_pagamento = None
            valor_pago = 0.0
            pessoa_pagou = ""
            if dia_cobranca > 0 and dia_cobranca < dia_hoje:
                status = "Atrasada"
            else:
                status = "Pendente"

        out_rows.append({
            "Descrição": desc_rec,
            "Categoria": cat_rec,
            "Pessoa Esperada": pessoa_rec,
            "Valor Esperado": valor_esp,
            "Dia Cobrança": dia_cobranca,
            "Status": status,
            "Data Pagamento": data_pagamento or "",
            "Pessoa Pagou": pessoa_pagou,
            "Valor Pago": valor_pago,
        })

    return pd.DataFrame(out_rows)


# ============================================================================
# Auditoria Fatura × Lançamentos individuais
# ============================================================================

def auditar_fatura_vs_lancamentos(linhas_fatura: list, df_lanc: pd.DataFrame, cartao_substring: str, competencia: str, tol_valor: float = 0.01, tol_dias: int = 1) -> dict:
    """Compara linhas de uma fatura (já extraída) com lançamentos individuais.

    linhas_fatura: lista de dicts {data: 'DD/MM/YYYY', valor: float, descricao: str}
    Retorna: {bateu: [...], faltando_na_planilha: [...], extra_na_planilha: [...]}
    """
    if df_lanc.empty:
        return {"bateu": [], "faltando_na_planilha": linhas_fatura, "extra_na_planilha": []}

    # Filtra lançamentos do cartão + competência + Crédito
    df = df_lanc.copy()
    if "Cartão" in df.columns:
        df = df[df["Cartão"].astype(str).str.lower().str.contains(cartao_substring.lower(), na=False)]
    if "Competência" in df.columns:
        df = df[df["Competência"] == competencia]
    if "Forma Pgto" in df.columns:
        df = df[df["Forma Pgto"].astype(str).str.lower().str.contains("crédito|credito", na=False, regex=True)]

    lanc_pendentes = df.to_dict("records")
    bateu = []
    for lf in linhas_fatura:
        v_f = float(lf.get("valor", 0))
        d_f = _parse_data(lf.get("data", "")) if isinstance(lf.get("data"), str) else lf.get("data")
        match_idx = None
        for i, ln in enumerate(lanc_pendentes):
            if abs(float(ln.get("Valor", 0)) - v_f) > tol_valor:
                continue
            d_l = ln.get("Data_dt")
            if pd.notna(d_f) and pd.notna(d_l):
                if abs((d_l - d_f).days) > tol_dias:
                    continue
            match_idx = i
            break
        if match_idx is not None:
            bateu.append({"fatura": lf, "lancamento": lanc_pendentes.pop(match_idx)})

    faltando = [lf for lf in linhas_fatura if not any(b["fatura"] is lf for b in bateu)]
    return {
        "bateu": bateu,
        "faltando_na_planilha": faltando,
        "extra_na_planilha": lanc_pendentes,
    }


# ============================================================================
# Compromissos previstos pros próximos N meses
# ============================================================================

def compromissos_proximos_meses(df_lanc: pd.DataFrame, df_rec: pd.DataFrame, df_faturas: pd.DataFrame, n_meses: int = 6, partir_de: str = None) -> pd.DataFrame:
    """Retorna DataFrame com colunas: Mês, Parcelas, Contas Fixas, Faturas em Aberto, Total."""
    hoje = datetime.now()
    if partir_de:
        try:
            mes_atual, ano_atual = partir_de.split("/")
            mes_atual, ano_atual = int(mes_atual), int(ano_atual)
        except Exception:
            mes_atual, ano_atual = hoje.month, hoje.year
    else:
        mes_atual, ano_atual = hoje.month, hoje.year

    fixas_mes = 0.0
    rec_desp = _recorrentes_despesa(df_rec)
    if not rec_desp.empty and "Valor" in rec_desp.columns:
        fixas_mes = float(rec_desp["Valor"].sum())

    out = []
    m, y = mes_atual, ano_atual
    for _ in range(n_meses):
        comp = f"{m:02d}/{y}"

        parcelas = 0.0
        if not df_lanc.empty and "Mês Caixa" in df_lanc.columns:
            no_mes = df_lanc[
                (df_lanc["Mês Caixa"] == comp)
                & (df_lanc["Tipo"].astype(str).str.lower() == "despesa")
                & (df_lanc.get("Parcela", pd.Series([""] * len(df_lanc), index=df_lanc.index)).astype(str).str.strip() != "")
            ]
            parcelas = float(no_mes["Valor"].sum())

        faturas_abertas = 0.0
        if not df_faturas.empty and "Vencimento_dt" in df_faturas.columns:
            f_mes = df_faturas[
                (df_faturas["Vencimento_dt"].dt.month == m)
                & (df_faturas["Vencimento_dt"].dt.year == y)
                & (df_faturas["Status"].astype(str).str.lower() == "pendente")
            ]
            for _, fr in f_mes.iterrows():
                total_fat = float(fr.get("Total_num", 0) or 0)
                if total_fat <= 0 and not df_lanc.empty:
                    # estima pelo somatório de lançamentos individuais (cartão+mês_ref+crédito)
                    cartao_str = str(fr.get("Cartão", "")).strip()
                    mes_ref = str(fr.get("Mês Referência", "")).strip()
                    primeira = cartao_str.split()[0] if cartao_str else ""
                    if primeira and mes_ref:
                        sub = df_lanc[
                            df_lanc["Cartão"].astype(str).str.lower().str.contains(primeira.lower(), na=False)
                            & (df_lanc["Competência"] == mes_ref)
                            & df_lanc["Forma Pgto"].astype(str).str.lower().str.contains("crédito|credito", na=False, regex=True)
                        ]
                        total_fat = float(sub["Valor"].sum())
                faturas_abertas += total_fat

        out.append({
            "Mês": comp,
            "Parcelas em curso": parcelas,
            "Contas fixas": fixas_mes,
            "Faturas em aberto": faturas_abertas,
            "Total": parcelas + fixas_mes + faturas_abertas,
        })

        m += 1
        if m > 12:
            m = 1
            y += 1

    return pd.DataFrame(out)


# ============================================================================
# KPIs da família (Visão Geral)
# ============================================================================

def kpis_familia(df_lanc: pd.DataFrame, df_saldo: pd.DataFrame, competencia: str, modo: str = "Caixa") -> dict:
    """Retorna dict com KPIs principais separados por pessoa."""
    coluna_mes = "Mês Caixa" if modo == "Caixa" else "Competência"
    no_mes = df_lanc[df_lanc[coluna_mes] == competencia].copy() if not df_lanc.empty else df_lanc

    splits = split_movimentos(no_mes)
    receitas = splits["receitas"]
    despesas = splits["despesas"]
    aportes = splits["aportes"]

    def por_pessoa(df):
        if df.empty or "Pessoa" not in df.columns:
            return {}
        return df.groupby("Pessoa")["Valor"].sum().to_dict()

    rec_pessoa = por_pessoa(receitas)
    desp_pessoa = por_pessoa(despesas)
    aporte_pessoa = por_pessoa(aportes)
    saldo_estocado = saldo_estocado_atual(df_saldo)

    return {
        "competencia": competencia,
        "modo": modo,
        "receita_total": float(receitas["Valor"].sum()) if not receitas.empty else 0.0,
        "receita_por_pessoa": rec_pessoa,
        "despesa_total": float(despesas["Valor"].sum()) if not despesas.empty else 0.0,
        "despesa_por_pessoa": desp_pessoa,
        "aporte_total": float(aportes["Valor"].sum()) if not aportes.empty else 0.0,
        "aporte_por_pessoa": aporte_pessoa,
        "saldo_estocado": saldo_estocado,
        "saldo_estocado_total": sum(saldo_estocado.values()),
        "saldo_mes": float(receitas["Valor"].sum() if not receitas.empty else 0) - float(despesas["Valor"].sum() if not despesas.empty else 0) - float(aportes["Valor"].sum() if not aportes.empty else 0),
    }
