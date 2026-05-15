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
def load_lancamentos() -> pd.DataFrame:
    rows = _records_formatted("Lançamentos")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["Valor"] = df["Valor"].apply(_parse_valor)
    df["Data_dt"] = df["Data"].apply(_parse_data)
    df["Data Caixa_dt"] = df["Data Caixa"].apply(_parse_data)
    # Coluna Mês Caixa (MM/YYYY) extraída de Data Caixa pra usar como pivot na visão Caixa
    df["Mês Caixa"] = df["Data Caixa_dt"].apply(
        lambda d: f"{d.month:02d}/{d.year}" if pd.notna(d) else ""
    )
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
