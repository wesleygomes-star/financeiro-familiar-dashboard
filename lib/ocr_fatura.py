"""OCR de Faturas de Cartão de Crédito — via Claude Sonnet 4.5 OU GPT-4o.

Extrai transações de PDFs de fatura e retorna JSON estruturado.
Faz dedupe contra lançamentos existentes na planilha (cartão + data ±1d + valor ±0,01).
Provider escolhido automaticamente baseado em qual API key está em st.secrets.

Schema de saída:
    {
        "fatura": {banco, cartao_titular, ciclo_fechamento, ciclo_vencimento, total},
        "transacoes": [{data, descricao, valor, moeda_origem, parcela_atual, parcela_total,
                        is_iof, is_pagamento_anterior, is_estorno, categoria_sugerida}]
    }
"""
import base64
import json
import re
from typing import Optional

import pandas as pd
import streamlit as st


SYSTEM_PROMPT = """Você é um extrator de transações de faturas de cartão de crédito brasileiro.

Recebe PDF de fatura (XP, Itaú, Visa, Master, Azul, Nubank, Inter, C6, etc) e devolve JSON estruturado.

FORMATO DE SAÍDA — APENAS JSON, sem markdown, sem explicação:
{
  "fatura": {
    "banco": "XP" | "Itaú" | "Visa" | "Master" | "Azul" | "Nubank" | "Inter" | "C6" | string,
    "cartao_titular": "Nome do titular completo",
    "ciclo_fechamento": "DD/MM/YYYY",
    "ciclo_vencimento": "DD/MM/YYYY",
    "total": float
  },
  "transacoes": [
    {
      "data": "DD/MM/YYYY",
      "descricao": "string (estabelecimento limpo, sem código de processador)",
      "valor": float,
      "moeda_origem": "BRL" | "USD" | "EUR" | etc,
      "parcela_atual": int | null,
      "parcela_total": int | null,
      "is_iof": bool,
      "is_pagamento_anterior": bool,
      "is_estorno": bool,
      "categoria_sugerida": "string"
    }
  ]
}

CATEGORIAS válidas (use exatamente uma dessas):
- Moradia (luz, água, gás, internet, condomínio, IPTU, manutenção apartamento)
- Outros Imóveis (custos de imóvel que não é moradia principal)
- Investimentos em Imóvel (aporte, entrada, reforma valorizadora)
- Auxílio Familiar (Unimed mãe, faxineira mãe, plano saúde família)
- Alimentação (supermercado, feira, padaria, hortifruti, açougue)
- Transporte (combustível, Uber, ônibus, estacionamento, manutenção carro)
- Saúde (plano de saúde, medicamentos, farmácia, consultas, academia, personal)
- Educação (escola, faculdade, cursos, livros, material didático)
- Lazer & Restaurantes (restaurante, iFood, cinema, viagem, bar, shows, jogo futebol)
- Vestuário (roupas, calçados, acessórios)
- Pessoal & Beleza (cabelo, salão, higiene, cosméticos, estética)
- Assinaturas & Streaming (Netflix, Spotify, Amazon Prime, apps)
- Financeiro & Cartão (anuidade cartão, IOF avulso, juros)
- Outros (loterias, doações, presentes, imprevistos)

REGRAS CRÍTICAS:

1. NUNCA INCLUA linhas de "PAGAMENTO DE FATURA ANTERIOR" / "Pagamento recebido" / "Recebimento de pagamento" como transação real — marque is_pagamento_anterior=true (mas inclua na lista pra rastreabilidade).

2. IOF: linhas tipo "IOF s/ compra internacional" ou "IOF" devem ter is_iof=true. O valor fica na linha do IOF, mas conceitualmente está pareada com a compra acima.

3. ESTORNO: se aparecer linha negativa (valor com sinal negativo na fatura ou descrição "Estorno", "Cancelamento"), marque is_estorno=true. NÃO inverta o sinal — mantenha valor positivo, só sinalize.

4. PARCELAMENTO: se descrição contém "1/12", "Parcela 2 de 12", "PARC 03/06" etc, preencha parcela_atual e parcela_total. Cada parcela é UMA transação (não some).

5. INTERNACIONAL: se transação está em moeda diferente de BRL, identifique moeda_origem e use o VALOR EM REAIS já convertido que aparece na fatura (não tente recalcular).

6. CATEGORIA: classifique pelo estabelecimento. Exemplos:
   - "Uber", "99 Pop", "Auto Posto" → Transporte
   - "iFood", "Cinemark", "Outback" → Lazer & Restaurantes
   - "Drogasil", "Drogaria" → Saúde
   - "Netflix", "Spotify", "Amazon Prime" → Assinaturas & Streaming
   - "Carrefour", "Pão de Açúcar", "Atacadão" → Alimentação
   - "Renner", "Zara", "Riachuelo" → Vestuário
   - Desconhecido → Outros
"""

USER_PROMPT = "Extraia TODAS as transações desta fatura como JSON. Seja minucioso — não pule nenhuma linha."


def _strip_markdown_json(s: str) -> str:
    """Remove cercas ```json``` se presentes."""
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _extract_claude(pdf_bytes: bytes) -> dict:
    from anthropic import Anthropic

    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não está em st.secrets")

    client = Anthropic(api_key=api_key)
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode()

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {"type": "text", "text": USER_PROMPT},
                ],
            }
        ],
    )
    content = msg.content[0].text
    return json.loads(_strip_markdown_json(content))


def _extract_openai(pdf_bytes: bytes) -> dict:
    from openai import OpenAI

    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY não está em st.secrets")

    client = OpenAI(api_key=api_key)
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode()

    msg = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=8192,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {
                        "type": "file",
                        "file": {
                            "filename": "fatura.pdf",
                            "file_data": f"data:application/pdf;base64,{pdf_b64}",
                        },
                    },
                ],
            },
        ],
    )
    return json.loads(msg.choices[0].message.content)


def extract_transactions(pdf_bytes: bytes, provider: str = "auto") -> dict:
    """Extrai transações de PDF de fatura.

    Args:
        pdf_bytes: bytes do PDF
        provider: 'claude' (Sonnet 4.5), 'openai' (GPT-4o), ou 'auto'

    Returns:
        dict no schema do SYSTEM_PROMPT

    Raises:
        ValueError se nenhuma API key estiver configurada
    """
    if provider == "auto":
        if st.secrets.get("ANTHROPIC_API_KEY"):
            provider = "claude"
        elif st.secrets.get("OPENAI_API_KEY"):
            provider = "openai"
        else:
            raise ValueError(
                "Nenhuma API key configurada. Adicione ANTHROPIC_API_KEY ou "
                "OPENAI_API_KEY em .streamlit/secrets.toml"
            )

    if provider == "claude":
        return _extract_claude(pdf_bytes)
    elif provider == "openai":
        return _extract_openai(pdf_bytes)
    raise ValueError(f"Provider desconhecido: {provider}")


def dedupe_against_existing(
    transacoes: list,
    df_lancamentos: Optional[pd.DataFrame],
    cartao_match: Optional[str] = None,
) -> list:
    """Marca cada transação extraída com flag 'duplicata_provavel'.

    Match: Cartão similar + Data ±1 dia + Valor ±0,01

    Args:
        transacoes: lista do schema OCR
        df_lancamentos: DataFrame do load_lancamentos
        cartao_match: substring do nome do cartão (case-insensitive); se None, não filtra por cartão

    Returns:
        mesmas transações com 'duplicata_provavel' e 'duplicata_row' (row_number do match) adicionados
    """
    if df_lancamentos is None or df_lancamentos.empty:
        for t in transacoes:
            t["duplicata_provavel"] = False
            t["duplicata_row"] = None
        return transacoes

    df = df_lancamentos.copy()
    if "Data_dt" not in df.columns:
        df["Data_dt"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
    df["Valor_f"] = pd.to_numeric(df["Valor"], errors="coerce")

    if cartao_match:
        cm = cartao_match.lower()
        df["__cartao_match"] = df["Cartão"].astype(str).str.lower().str.contains(cm, na=False)
        df = df[df["__cartao_match"]]

    for t in transacoes:
        if t.get("is_pagamento_anterior"):
            t["duplicata_provavel"] = False
            t["duplicata_row"] = None
            continue
        try:
            data_t = pd.to_datetime(t["data"], format="%d/%m/%Y")
            valor_t = float(t["valor"])
            mask = (
                (df["Data_dt"] >= data_t - pd.Timedelta(days=1))
                & (df["Data_dt"] <= data_t + pd.Timedelta(days=1))
                & (df["Valor_f"].between(valor_t - 0.01, valor_t + 0.01))
            )
            matches = df[mask]
            if not matches.empty:
                t["duplicata_provavel"] = True
                t["duplicata_row"] = (
                    int(matches.iloc[0]["row_number"]) if "row_number" in matches.columns else None
                )
            else:
                t["duplicata_provavel"] = False
                t["duplicata_row"] = None
        except (ValueError, KeyError, TypeError):
            t["duplicata_provavel"] = False
            t["duplicata_row"] = None
    return transacoes
