# 💰 Financeiro Família Gomes

Dashboard de finanças familiares conectado a uma planilha do Google Sheets, alimentada via WhatsApp (Evolution API → n8n → Google Sheets).

## Stack

- **Streamlit** 1.40+ (Python)
- **gspread** + Google Service Account (leitura)
- **Plotly** (gráficos interativos com drill-down)
- **Hospedagem**: Streamlit Community Cloud (free)

## Features

- 🔐 Auth simples por senha
- 📊 KPIs em cards (Receita / Despesa / Saldo / % Teto)
- 🚦 Semáforo verde/amarelo/vermelho por categoria vs teto
- 👆 Drill-down clicável: clica na barra de uma categoria → abre os lançamentos
- 🍩 Distribuição de despesas (donut)
- 📅 Projeção 6 meses (Receita × Despesa agrupadas)
- 🔝 Top 10 maiores despesas
- 📜 Expander com TODOS os lançamentos + busca + filtros (tipo/categoria)
- 🌙 Tema escuro elegante

## Filtros

- **Competência** (mês): qualquer mês com lançamentos
- **Visão**: Família (consolidado) / Wesley / Sabrina

## Setup local (dev)

```bash
python3 -m pip install --user -r requirements.txt
# Coloque .streamlit/secrets.toml com:
#   [auth] password = "..."
#   [gcp_service_account] ... (json da service account)
streamlit run streamlit_app.py
```

Abre em http://localhost:8501.

## Setup produção (Streamlit Cloud)

1. Push pro GitHub
2. Conecta repo no [share.streamlit.io](https://share.streamlit.io)
3. Configura **Secrets** no painel com mesmo conteúdo do `secrets.toml`
4. URL pública gerada

## Estrutura

```
.
├── streamlit_app.py       # Página principal (Família)
├── requirements.txt
├── .streamlit/
│   ├── config.toml        # Tema visual
│   └── secrets.toml       # NÃO COMMITAR (gitignored)
├── lib/
│   ├── data.py            # Conexão Sheets via Service Account
│   └── components.py      # Reusable charts
└── .gitignore
```
