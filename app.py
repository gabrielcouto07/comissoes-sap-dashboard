#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCIENTIFIC PRD · Sistema de Comissões v6.1
Dashboard analítico com dados prontos da planilha
"""

import io
import re
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════
st.set_page_config(
  page_title="Comissões · Scientific PRD",
  page_icon="💰",
  layout="wide",
  initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
[data-testid="stSidebar"] {
background: linear-gradient(180deg,#0f172a 0%,#1e293b 60%,#0f172a 100%);
}
[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
[data-testid="stSidebar"] hr { border-color:#334155 !important; }

.page-header {
background: linear-gradient(135deg,#0f172a 0%,#1e40af 50%,#7c3aed 100%);
border-radius:16px; padding:1.5rem 2rem; color:white;
margin-bottom:1.5rem; box-shadow:0 4px 24px rgba(30,64,175,.35);
}
.page-header h1 { color:white; margin:0; font-size:1.75rem; font-weight:800; }
.page-header p  { color:#bfdbfe; margin:.3rem 0 0; font-size:.85rem; }

.kpi-card {
background:white; border-radius:12px; padding:.9rem 1.1rem;
border-left:4px solid; box-shadow:0 2px 12px rgba(0,0,0,.08);
transition:transform .15s; margin-bottom:4px;
}
.kpi-card:hover { transform:translateY(-2px); }
.kpi-card.blue   { border-color:#3b82f6; }
.kpi-card.green  { border-color:#22c55e; }
.kpi-card.purple { border-color:#a855f7; }
.kpi-card.amber  { border-color:#f59e0b; }
.kpi-card.teal   { border-color:#14b8a6; }
.kpi-card.rose   { border-color:#f43f5e; }
.kpi-card.sky    { border-color:#0ea5e9; }
.kpi-card.indigo { border-color:#6366f1; }
.kpi-title { font-size:.63rem; font-weight:700; color:#64748b;
         text-transform:uppercase; letter-spacing:.08em; margin:0; }
.kpi-value { font-size:1.25rem; font-weight:800; color:#0f172a;
         margin:.12rem 0 0; line-height:1.2; }
.kpi-sub   { font-size:.62rem; color:#94a3b8; margin:.06rem 0 0; }

.filter-box {
background:#f8fafc; border:1px solid #e2e8f0;
border-radius:12px; padding:1rem 1.2rem; margin-bottom:1.2rem;
}

.note-box {
background:#eff6ff; border:1px solid #bfdbfe; color:#1e3a8a;
border-radius:12px; padding:.9rem 1rem; margin-bottom:1rem;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# COLUMN MAP
# ✅ FIX 1: Adicionado "NumeroNC" para mapear a nova coluna "Numero NC"
# ══════════════════════════════════════════════════════════
COL_MAP = {
  "ReceiveDate":       ["Data do Recebimento", "ReceiveDate", "Data Recebimento"],
  "BranchName":        ["Filial Recebimento", "Filial", "BranchName"],
  "ReceiptNumber":     ["Numero Recibo", "Número Recibo", "ReceiptNumber"],
  # ✅ FIX 1 — nova coluna vinda da query corrigida (C5)
  "NumeroNC":          ["Numero NC", "Número NC", "NumeroNC"],
  "EventType":         ["Tipo Evento", "EventType"],
  "InvDocNum":         ["Numero NF", "Número NF", "InvDocNum", "DocNum"],
  "ObjectType":        ["Tipo de Objeto", "ObjectType"],
  "CardCode":          ["Codigo PN", "Código PN", "CardCode"],
  "CardName":          ["Nome do PN", "CardName", "Cliente"],
  "SlpCode":           ["Codigo Vendedor", "Código Vendedor", "SlpCode"],
  "SlpName":           ["Nome do Vendedor", "Nome do vendedor", "SlpName"],
  "ItemCode":          ["Numero do Item", "Número do Item", "ItemCode"],
  "ItemDescription":   ["Descricao do Item", "Descrição do Item", "ItemDescription"],
  "Installment":       ["Parcela", "Installment"],
  "Quantity":          ["Quantidade", "Quantity"],
  "Currency":          ["Moeda", "Currency"],
  "LineTotal":         ["Valor Total da Linha NF", "LineTotal", "Valor Linha"],
  "AmountReceived":    ["Valor Recebido NF Evento", "AmountReceived", "Valor Recebido"],
  "AllocatedExpenses": ["Despesas Adicionais Rateadas", "AllocatedExpenses"],
  "PaymentBase":       ["Base de Pagamento da Linha", "PaymentBase", "Base de Pagamento"],
  "CommissionPct":     ["Percentual Comissao", "Percentual Comissão", "CommissionPct"],
  "CommissionValue":   ["Comissao Final", "Comissão Final", "CommissionValue", "Valor Comissão"],
  "GLAccount":         ["Conta Contabil Recebimento", "Conta Contábil Recebimento", "GLAccount"],
  "GLAccountName":     ["Nome Conta Contabil", "Nome Conta Contábil", "GLAccountName"],
}

REQUIRED = [
  "ReceiveDate", "InvDocNum", "SlpName", "ItemCode",
  "LineTotal", "AmountReceived", "CommissionPct", "CommissionValue",
]

# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════
def parse_num(v) -> float:
  if pd.isna(v):
      return 0.0
  s = re.sub(r"[^\d.,\-]", "", str(v).strip())
  if not s:
      return 0.0
  if re.search(r"\d{1,3}(\.\d{3})+,\d", s):
      s = s.replace(".", "").replace(",", ".")
  else:
      s = s.replace(",", ".")
  try:
      return float(s)
  except (ValueError, TypeError):
      return 0.0


def fmt_brl(v: float) -> str:
  try:
      s = f"R$ {abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
      return f"-{s}" if v < 0 else s
  except Exception:
      return "R$ 0,00"


def pct_fmt(v: float) -> str:
  try:
      return f"{float(v):.2f}%"
  except Exception:
      return "0,00%"


def smart_date(val):
  if pd.isna(val):
      return pd.NaT
  s = str(val).strip()
  # Excel serial numbers (common when exported from SAP B1)
  try:
      n = float(s)
      if 40000 < n < 60000:
          return pd.Timestamp("1899-12-30") + pd.Timedelta(days=n)
  except (ValueError, TypeError):
      pass
  for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"]:
      try:
          return pd.Timestamp(datetime.strptime(s[:10], fmt))
      except Exception:
          continue
  try:
      return pd.to_datetime(s, errors="coerce")
  except Exception:
      return pd.NaT


# ══════════════════════════════════════════════════════════
# LOADER
# ✅ FIX 2: Tenta TODAS as abas do Excel e escolhe a que tiver
#           mais colunas reconhecíveis pelo COL_MAP.
#           Resolve o problema de "Planilha2" não ser a aba 0.
# ══════════════════════════════════════════════════════════
def load_file(f):
  try:
      f.seek(0)
  except Exception:
      pass

  content = f.read()
  if not content:
      return None, "Arquivo vazio."

  name = f.name.lower()

  # Conjunto de todos os aliases em letras maiúsculas para comparação rápida
  all_aliases_upper = {
      alias.upper().strip()
      for aliases in COL_MAP.values()
      for alias in aliases
  }

  if name.endswith((".xlsx", ".xls")):
      # ✅ FIX 2 — enumera todas as abas
      try:
          xl = pd.ExcelFile(io.BytesIO(content))
          sheet_list = xl.sheet_names
      except Exception:
          sheet_list = [0]

      best_df = None
      best_score = -1

      for sheet in sheet_list:
          for hrow in [0, 1, 2]:
              try:
                  df = pd.read_excel(
                      io.BytesIO(content),
                      dtype=str,
                      header=hrow,
                      sheet_name=sheet,
                      na_filter=False,
                  )
                  df.columns = [str(c).strip() for c in df.columns]

                  if len(df.columns) < 5 or len(df) == 0:
                      continue

                  # Conta quantas colunas coincidem com aliases do COL_MAP
                  score = sum(
                      1 for col in df.columns
                      if col.upper().strip() in all_aliases_upper
                  )

                  if score > best_score:
                      best_score = score
                      best_df = df

              except Exception:
                  continue

      if best_df is not None:
          return best_df, None

  # Fallback CSV
  for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
      try:
          text = content.decode(enc, errors="replace")
          for sep in ["\t", ";", ","]:
              try:
                  df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str, na_filter=False)
                  if len(df.columns) >= 5:
                      df.columns = [str(c).strip() for c in df.columns]
                      return df, None
              except Exception:
                  continue
      except Exception:
          continue

  return None, f"Formato não reconhecido: {f.name}"


# ══════════════════════════════════════════════════════════
# NORMALIZER
# ✅ FIX 3: (a) NumeroNC em text_cols
#           (b) Filtro de linhas sem data (remove linha de total)
#           (c) InvDocNum vazio → NaN (contagem correta de NFs)
# ══════════════════════════════════════════════════════════
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
  rev = {
      alias.upper().strip(): canon
      for canon, aliases in COL_MAP.items()
      for alias in aliases
  }

  df = df.rename(columns={
      col: rev[col.upper().strip()]
      for col in df.columns
      if col.upper().strip() in rev
  }).copy()

  df.columns = [str(c).strip() for c in df.columns]

  numeric_cols = [
      "Quantity", "LineTotal", "AmountReceived", "AllocatedExpenses",
      "PaymentBase", "CommissionPct", "CommissionValue",
  ]
  for c in numeric_cols:
      if c in df.columns:
          df[c] = df[c].apply(parse_num)
      else:
          df[c] = 0.0

  if "ReceiveDate" in df.columns:
      df["ReceiveDate"] = df["ReceiveDate"].apply(smart_date)
      # ✅ FIX 3b — remove linhas sem data (linha de total/rodapé do SAP)
      df = df[df["ReceiveDate"].notna()].copy()
  else:
      df["ReceiveDate"] = pd.NaT

  # ✅ FIX 3a — NumeroNC adicionado a text_cols
  text_cols = [
      "BranchName", "ReceiptNumber", "NumeroNC", "EventType", "InvDocNum",
      "ObjectType", "CardCode", "CardName", "SlpCode", "SlpName",
      "ItemCode", "ItemDescription", "Installment", "Currency",
      "GLAccount", "GLAccountName",
  ]
  for c in text_cols:
      if c in df.columns:
          df[c] = df[c].astype(str).str.strip()
      else:
          df[c] = ""

  # ✅ FIX 3c — InvDocNum vazio → NaN para nunique() correto
  if "InvDocNum" in df.columns:
      df["InvDocNum"] = df["InvDocNum"].replace("", np.nan)

  if df["SlpName"].eq("").all() and "SlpCode" in df.columns:
      df["SlpName"] = "Vendedor " + df["SlpCode"].astype(str)

  df["ReceiveMonth"] = np.where(
      df["ReceiveDate"].notna(),
      df["ReceiveDate"].dt.to_period("M").astype(str),
      "N/D"
  )

  df["HasCommission"] = np.where(df["CommissionValue"] > 0, "Com comissão", "Sem comissão")
  df["HasReceipt"]    = np.where(df["AmountReceived"]  > 0, "Com recebimento", "Sem recebimento")

  return df


def to_excel(sheets: dict) -> bytes:
  buf = io.BytesIO()
  with pd.ExcelWriter(buf, engine="openpyxl") as writer:
      for name, data in sheets.items():
          data.to_excel(writer, sheet_name=name[:31], index=False)
  return buf.getvalue()


# ══════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════
with st.sidebar:
  st.markdown("""
  <div style="text-align:center;padding:1.2rem 0 .8rem">
    <div style="font-size:2.8rem;line-height:1">💰</div>
    <h2 style="color:#e2e8f0;margin:.3rem 0 0;font-size:1.15rem;font-weight:800">
      Comissões Analíticas
    </h2>
    <p style="color:#94a3b8;font-size:.7rem;margin:.1rem 0 0">
      Scientific PRD · v6.1
    </p>
  </div>
  """, unsafe_allow_html=True)
  st.markdown("---")

  st.subheader("📂 Planilha")
  uploaded = st.file_uploader(
      "Arquivo (.xlsx / .xls / .csv)",
      type=["xlsx", "xls", "csv"],
      help="Planilha já pronta com valores de comissão, base e percentual.",
  )

  st.markdown("---")
  st.subheader("🎛️ Visualização")
  show_zero_commission = st.checkbox("Incluir linhas sem comissão", value=True)
  show_zero_received   = st.checkbox("Incluir linhas sem recebimento", value=True)
  st.markdown("---")
  st.caption("© 2026 Scientific PRD")

# ══════════════════════════════════════════════════════════
# WELCOME SCREEN
# ══════════════════════════════════════════════════════════
if uploaded is None:
  st.markdown("""
  <div class="page-header">
    <h1>💰 Dashboard Analítico de Comissões</h1>
    <p>Leitura direta da planilha pronta · Sem recálculo de regras · Foco em análise, filtros e dashboards</p>
  </div>
  """, unsafe_allow_html=True)

  a, b, c = st.columns(3)
  a.info("**📄 Dados prontos**\n\nA planilha já traz percentual, base e comissão calculados.")
  b.info("**📊 Python enxuto**\n\nO app só soma, conta, agrupa e organiza as visualizações.")
  c.info("**🎯 Mais análise**\n\nFiltros, rankings, tendências, detalhamento e exportação.")

  st.markdown("---")
  st.markdown("#### ✅ O que este app faz agora")
  st.markdown("""
  - lê a planilha e identifica as colunas principais (**qualquer aba**);
  - normaliza nomes e tipos de dados;
  - soma **vendas, itens, NFs e comissão por vendedor**;
  - mostra dashboards por vendedor, filial, item, cliente e mês;
  - permite filtros e exportação com os dados filtrados.
  """)

  st.markdown("#### 📌 Colunas esperadas")
  st.code("""
Data do Recebimento
Filial Recebimento
Numero Recibo
Numero NC            ← nova coluna
Tipo Evento
Numero NF
Nome do PN
Codigo Vendedor
Nome do Vendedor
Numero do Item
Descricao do Item
Quantidade
Valor Total da Linha NF
Valor Recebido NF Evento
Base de Pagamento da Linha
Percentual Comissao
Comissao Final
  """.strip(), language="text")
  st.stop()

# ══════════════════════════════════════════════════════════
# LOAD / NORMALIZE
# ══════════════════════════════════════════════════════════
with st.spinner("🔄 Carregando planilha..."):
  df_raw, err = load_file(uploaded)
  if err or df_raw is None:
      st.error(f"❌ Erro ao ler arquivo: {err}")
      st.stop()

  df = normalize_columns(df_raw)

  missing = [c for c in REQUIRED if c not in df.columns]
  if missing:
      st.error(f"❌ Colunas obrigatórias não encontradas: {missing}")
      with st.expander("🔍 Diagnóstico"):
          st.code(", ".join(df.columns.tolist()))
          st.dataframe(df.head(5), use_container_width=True)
      st.stop()

  if not show_zero_commission:
      df = df[df["CommissionValue"] > 0]
  if not show_zero_received:
      df = df[df["AmountReceived"] > 0]

if df.empty:
  st.warning("⚠️ Nenhum dado disponível após aplicar as opções iniciais.")
  st.stop()

# ══════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════
ts_now    = datetime.now().strftime("%d/%m/%Y %H:%M")
has_dates = df["ReceiveDate"].notna().any()
d_min_str = df["ReceiveDate"].min().strftime("%d/%m/%Y") if has_dates else "—"
d_max_str = df["ReceiveDate"].max().strftime("%d/%m/%Y") if has_dates else "—"

st.markdown(f"""
<div class="page-header">
<h1>💰 Relatório Analítico de Comissões</h1>
<p>{uploaded.name} &nbsp;·&nbsp; {len(df):,} linhas &nbsp;·&nbsp; Período: {d_min_str} → {d_max_str} &nbsp;·&nbsp; {ts_now}</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# FILTERS
# ══════════════════════════════════════════════════════════
st.markdown('<div class="filter-box">', unsafe_allow_html=True)
st.markdown("**🔍 Filtros Dinâmicos**")

vend_opts   = sorted([x for x in df["SlpName"].dropna().astype(str).unique().tolist() if x])
branch_opts = sorted([x for x in df["BranchName"].dropna().astype(str).unique().tolist() if x])
item_opts   = sorted([x for x in df["ItemCode"].dropna().astype(str).unique().tolist() if x])
client_opts = sorted([x for x in df["CardName"].dropna().astype(str).unique().tolist() if x])
month_opts  = sorted([x for x in df["ReceiveMonth"].dropna().astype(str).unique().tolist() if x and x != "N/D"])

r1 = st.columns([2, 2, 2, 3])
with r1[0]:
  sel_vend   = st.multiselect("👤 Vendedor",   vend_opts,   default=vend_opts)
with r1[1]:
  sel_branch = st.multiselect("🏢 Filial",     branch_opts, default=branch_opts)
with r1[2]:
  sel_month  = st.multiselect("🗓️ Mês",        month_opts,  default=month_opts if month_opts else [])
with r1[3]:
  if has_dates:
      d_min      = df["ReceiveDate"].min().date()
      d_max      = df["ReceiveDate"].max().date()
      date_range = st.date_input("📅 Período", value=(d_min, d_max), min_value=d_min, max_value=d_max)
  else:
      date_range = None

r2 = st.columns([2, 2, 2, 2])
with r2[0]:
  sel_client = st.multiselect("🏥 Cliente", client_opts, default=client_opts)
with r2[1]:
  comm_min = st.number_input("💰 Comissão mínima (R$)", value=0.0, step=100.0)
with r2[2]:
  recv_min = st.number_input("💳 Recebimento mínimo (R$)", value=0.0, step=100.0)
with r2[3]:
  top_n = st.slider("📌 Top ranking", min_value=5, max_value=30, value=10)

st.markdown("</div>", unsafe_allow_html=True)

# Apply filters
filtered = df.copy()
if sel_vend:
  filtered = filtered[filtered["SlpName"].isin(sel_vend)]
if sel_branch:
  filtered = filtered[filtered["BranchName"].isin(sel_branch)]
if sel_month and month_opts:
  filtered = filtered[filtered["ReceiveMonth"].isin(sel_month)]
if sel_client:
  filtered = filtered[filtered["CardName"].isin(sel_client)]
if comm_min > 0:
  filtered = filtered[filtered["CommissionValue"].abs() >= comm_min]
if recv_min > 0:
  filtered = filtered[filtered["AmountReceived"].abs() >= recv_min]
if has_dates and date_range and len(date_range) == 2:
  filtered = filtered[
      filtered["ReceiveDate"].between(pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))
  ]

if filtered.empty:
  st.warning("⚠️ Nenhum dado encontrado com os filtros selecionados.")
  st.stop()

# ══════════════════════════════════════════════════════════
# AGGREGATIONS HELPER
# ══════════════════════════════════════════════════════════
def _get_first_mode(x):
  mode_vals = x.mode()
  return mode_vals.iloc[0] if len(mode_vals) > 0 else ""

# ══════════════════════════════════════════════════════════
# AGGREGATIONS
# ══════════════════════════════════════════════════════════
resumo_vend = (
  filtered.groupby("SlpName")
  .agg(
      Vendas=("LineTotal",       "sum"),
      Itens=("Quantity",         "sum"),
      NFs=("InvDocNum",          "nunique"),
      Comissao=("CommissionValue","sum"),
      Recebido=("AmountReceived", "sum"),
      BasePagamento=("PaymentBase","sum"),
      PctMedio=("CommissionPct",  "mean"),
      Clientes=("CardCode",       "nunique"),
  )
  .reset_index()
  .rename(columns={"SlpName": "Vendedor"})
  .sort_values("Comissao", ascending=False)
)
resumo_vend["TicketMedioNF"]          = (resumo_vend["Vendas"] / resumo_vend["NFs"].replace(0, np.nan)).fillna(0)
resumo_vend["ComissaoSobreVendaPct"]  = (resumo_vend["Comissao"] / resumo_vend["Vendas"].replace(0, np.nan) * 100).fillna(0)

resumo_filial = (
  filtered.groupby("BranchName")
  .agg(
      Vendas=("LineTotal",       "sum"),
      Itens=("Quantity",         "sum"),
      NFs=("InvDocNum",          "nunique"),
      Comissao=("CommissionValue","sum"),
      Recebido=("AmountReceived", "sum"),
  )
  .reset_index()
  .rename(columns={"BranchName": "Filial"})
  .sort_values("Comissao", ascending=False)
)

resumo_item = (
  filtered.groupby("ItemCode")
  .agg(
      Descricao=("ItemDescription", _get_first_mode),
      Vendas=("LineTotal",           "sum"),
      Itens=("Quantity",             "sum"),
      NFs=("InvDocNum",              "nunique"),
      Comissao=("CommissionValue",   "sum"),
      Recebido=("AmountReceived",    "sum"),
  )
  .reset_index()
  .sort_values("Comissao", ascending=False)
)

resumo_cliente = (
  filtered.groupby("CardName")
  .agg(
      Vendas=("LineTotal",       "sum"),
      Itens=("Quantity",         "sum"),
      NFs=("InvDocNum",          "nunique"),
      Comissao=("CommissionValue","sum"),
      Recebido=("AmountReceived", "sum"),
  )
  .reset_index()
  .rename(columns={"CardName": "Cliente"})
  .sort_values("Comissao", ascending=False)
)

resumo_mes = pd.DataFrame()
if filtered["ReceiveMonth"].ne("N/D").any():
  resumo_mes = (
      filtered.groupby(["ReceiveMonth", "SlpName"])
      .agg(
          Vendas=("LineTotal",       "sum"),
          Itens=("Quantity",         "sum"),
          NFs=("InvDocNum",          "nunique"),
          Comissao=("CommissionValue","sum"),
          Recebido=("AmountReceived", "sum"),
      )
      .reset_index()
      .rename(columns={"SlpName": "Vendedor"})
  )

# ══════════════════════════════════════════════════════════
# KPIs
# ══════════════════════════════════════════════════════════
total_vendas   = filtered["LineTotal"].sum()
total_itens    = filtered["Quantity"].sum()
total_nfs      = filtered["InvDocNum"].nunique()
total_comissao = filtered["CommissionValue"].sum()
total_recebido = filtered["AmountReceived"].sum()
media_pct      = filtered["CommissionPct"].mean() if len(filtered) else 0
n_vendedores   = filtered["SlpName"].nunique()

kpis = [
  ("💼 Vendas",    fmt_brl(total_vendas),                           "indigo", f"{total_nfs} NFs"),
  ("📦 Itens",     f"{total_itens:,.0f}".replace(",", "."),          "sky",    f"{len(filtered):,} linhas".replace(",", ".")),
  ("📄 NFs",       f"{total_nfs}",                                   "blue",   f"{n_vendedores} vendedores"),
  ("💳 Recebido",  fmt_brl(total_recebido),                          "teal",   "valor já vindo da planilha"),
  ("💰 Comissão",  fmt_brl(total_comissao),                          "green",  "somatório do campo final"),
  ("📊 % Médio",   pct_fmt(media_pct),                               "amber",  "média simples da planilha"),
]

cols = st.columns(6)
for (label, value, color, sub), col in zip(kpis, cols):
  with col:
      st.markdown(f"""
      <div class="kpi-card {color}">
        <p class="kpi-title">{label}</p>
        <p class="kpi-value">{value}</p>
        <p class="kpi-sub">{sub}</p>
      </div>
      """, unsafe_allow_html=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════
t_dash, t_vend, t_filial, t_item, t_cli, t_det, t_exp = st.tabs([
  "📊 Dashboard", "👤 Vendedores", "🏢 Filiais",
  "📦 Itens", "🏥 Clientes", "📋 Detalhado", "📥 Exportar",
])

# ── DASHBOARD ─────────────────────────────────────────────
with t_dash:
  c1, c2 = st.columns(2)

  chart_v = resumo_vend.head(top_n).sort_values("Comissao")
  fig_v   = px.bar(
      chart_v, x="Comissao", y="Vendedor", orientation="h",
      title=f"💰 Top {top_n} vendedores por comissão",
      text=chart_v["Comissao"].apply(fmt_brl),
      color="Comissao", color_continuous_scale=["#bfdbfe", "#1d4ed8"],
      labels={"Comissao": "R$", "Vendedor": ""},
  )
  fig_v.update_traces(textposition="outside")
  fig_v.update_layout(showlegend=False, coloraxis_showscale=False, height=420,
                      plot_bgcolor="white", paper_bgcolor="white")
  c1.plotly_chart(fig_v, use_container_width=True)

  pie_data = resumo_vend[resumo_vend["Comissao"] > 0].head(top_n)
  fig_pie  = px.pie(
      pie_data, values="Comissao", names="Vendedor", hole=0.52,
      title="🥧 Participação da comissão por vendedor",
      color_discrete_sequence=px.colors.qualitative.Set3,
  )
  fig_pie.update_traces(textinfo="percent+label")
  fig_pie.update_layout(height=420, showlegend=False, paper_bgcolor="white")
  c2.plotly_chart(fig_pie, use_container_width=True)

  if not resumo_mes.empty:
      mes_total = resumo_mes.groupby("ReceiveMonth")[["Vendas","Recebido","Comissao"]].sum().reset_index()
      fig_mes   = px.line(
          mes_total, x="ReceiveMonth",
          y=["Vendas", "Recebido", "Comissao"], markers=True,
          title="📈 Evolução mensal",
          labels={"value": "R$", "variable": "Indicador", "ReceiveMonth": "Mês"},
      )
      fig_mes.update_layout(height=340, plot_bgcolor="white", paper_bgcolor="white")
      st.plotly_chart(fig_mes, use_container_width=True)

  d1, d2 = st.columns(2)

  top_items = resumo_item.head(top_n).sort_values("Comissao")
  fig_items = px.bar(
      top_items, x="Comissao", y="ItemCode", orientation="h",
      title=f"🏆 Top {top_n} itens por comissão",
      text=top_items["Comissao"].apply(fmt_brl),
      hover_data={"Descricao": True},
      color="Comissao", color_continuous_scale=["#fde68a", "#b45309"],
      labels={"Comissao": "R$", "ItemCode": ""},
  )
  fig_items.update_traces(textposition="outside")
  fig_items.update_layout(showlegend=False, coloraxis_showscale=False, height=400,
                           plot_bgcolor="white", paper_bgcolor="white")
  d1.plotly_chart(fig_items, use_container_width=True)

  if len(resumo_vend) > 1:
      fig_sc = px.scatter(
          resumo_vend, x="Vendas", y="Comissao", size="NFs", color="Vendedor",
          hover_data=["Itens", "Recebido", "Clientes"],
          title="🎯 Vendas x comissão por vendedor",
          labels={"Vendas": "Vendas (R$)", "Comissao": "Comissão (R$)"},
      )
      fig_sc.update_layout(height=400, plot_bgcolor="white", paper_bgcolor="white", showlegend=False)
      d2.plotly_chart(fig_sc, use_container_width=True)

# ── VENDEDORES ────────────────────────────────────────────
with t_vend:
  st.caption(f"{len(resumo_vend)} vendedores no período filtrado")

  disp = resumo_vend.copy()
  for c in ["Vendas", "Recebido", "BasePagamento", "Comissao", "TicketMedioNF"]:
      disp[c] = disp[c].apply(fmt_brl)
  disp["PctMedio"]              = disp["PctMedio"].apply(pct_fmt)
  disp["ComissaoSobreVendaPct"] = disp["ComissaoSobreVendaPct"].apply(pct_fmt)
  st.dataframe(disp, use_container_width=True, height=320)

  st.markdown("---")
  st.subheader("🔎 Deep dive por vendedor")

  vendedor_sel = st.selectbox("Selecione o vendedor", resumo_vend["Vendedor"].tolist())
  if vendedor_sel:
      dv = filtered[filtered["SlpName"] == vendedor_sel].copy()
      m1, m2, m3, m4 = st.columns(4)
      m1.metric("Vendas",   fmt_brl(dv["LineTotal"].sum()))
      m2.metric("Itens",    f"{dv['Quantity'].sum():,.0f}".replace(",", "."))
      m3.metric("NFs",      int(dv["InvDocNum"].nunique()))
      m4.metric("Comissão", fmt_brl(dv["CommissionValue"].sum()))

      drill = (
          dv.groupby(["ItemCode", "CommissionPct"])
          .agg(
              Descricao=("ItemDescription", _get_first_mode),
              Vendas=("LineTotal",           "sum"),
              Itens=("Quantity",             "sum"),
              NFs=("InvDocNum",              "nunique"),
              Recebido=("AmountReceived",    "sum"),
              Comissao=("CommissionValue",   "sum"),
          )
          .reset_index()
          .sort_values("Comissao", ascending=False)
      )

      search_item = st.text_input("Buscar item do vendedor")
      if search_item:
          mask = (
              drill["ItemCode"].astype(str).str.contains(search_item, case=False, na=False) |
              drill["Descricao"].astype(str).str.contains(search_item, case=False, na=False)
          )
          drill = drill[mask]

      dd = drill.copy()
      for c in ["Vendas", "Recebido", "Comissao"]:
          dd[c] = dd[c].apply(fmt_brl)
      dd["CommissionPct"] = dd["CommissionPct"].apply(pct_fmt)
      st.dataframe(dd, use_container_width=True, height=380)

# ── FILIAIS ───────────────────────────────────────────────
with t_filial:
  chart_f = resumo_filial.sort_values("Comissao")
  fig_f   = px.bar(
      chart_f, x="Comissao", y="Filial", orientation="h",
      title="💰 Comissão por filial",
      text=chart_f["Comissao"].apply(fmt_brl),
      color="Comissao", color_continuous_scale=["#c4b5fd", "#4f46e5"],
      labels={"Comissao": "R$", "Filial": ""},
  )
  fig_f.update_traces(textposition="outside")
  fig_f.update_layout(showlegend=False, coloraxis_showscale=False,
                      height=max(320, len(chart_f) * 60),
                      plot_bgcolor="white", paper_bgcolor="white")
  st.plotly_chart(fig_f, use_container_width=True)

  filial_vendor = (
      filtered.groupby(["BranchName","SlpName"])
      .agg(Comissao=("CommissionValue","sum"))
      .reset_index()
  )
  fig_stack = px.bar(
      filial_vendor, x="BranchName", y="Comissao", color="SlpName", barmode="stack",
      title="💼 Comissão por filial x vendedor",
      labels={"BranchName": "Filial", "Comissao": "R$", "SlpName": "Vendedor"},
  )
  fig_stack.update_layout(height=380, plot_bgcolor="white", paper_bgcolor="white")
  st.plotly_chart(fig_stack, use_container_width=True)

  disp_f = resumo_filial.copy()
  for c in ["Vendas", "Recebido", "Comissao"]:
      disp_f[c] = disp_f[c].apply(fmt_brl)
  st.dataframe(disp_f, use_container_width=True, height=280)

# ── ITENS ─────────────────────────────────────────────────
with t_item:
  search_global_item = st.text_input("🔍 Buscar item por código ou descrição")
  di = resumo_item.copy()
  if search_global_item:
      mask = (
          di["ItemCode"].astype(str).str.contains(search_global_item, case=False, na=False) |
          di["Descricao"].astype(str).str.contains(search_global_item, case=False, na=False)
      )
      di = di[mask]

  di_disp = di.copy()
  for c in ["Vendas", "Recebido", "Comissao"]:
      di_disp[c] = di_disp[c].apply(fmt_brl)
  st.caption(f"{len(di)} itens distintos")
  st.dataframe(di_disp, use_container_width=True, height=500)

# ── CLIENTES ──────────────────────────────────────────────
with t_cli:
  top_cli = resumo_cliente.head(top_n).sort_values("Comissao")
  fig_cli = px.bar(
      top_cli, x="Comissao", y="Cliente", orientation="h",
      title=f"🏥 Top {top_n} clientes por comissão",
      text=top_cli["Comissao"].apply(fmt_brl),
      color="Comissao", color_continuous_scale=["#fecaca","#be123c"],
      labels={"Comissao": "R$", "Cliente": ""},
  )
  fig_cli.update_traces(textposition="outside")
  fig_cli.update_layout(showlegend=False, coloraxis_showscale=False, height=420,
                        plot_bgcolor="white", paper_bgcolor="white")
  st.plotly_chart(fig_cli, use_container_width=True)

  cli_disp = resumo_cliente.copy()
  for c in ["Vendas", "Recebido", "Comissao"]:
      cli_disp[c] = cli_disp[c].apply(fmt_brl)
  st.dataframe(cli_disp, use_container_width=True, height=350)

# ── DETALHADO ─────────────────────────────────────────────
with t_det:
  # ✅ FIX 4: "NumeroNC" adicionado após "ReceiptNumber"
  show_cols = [c for c in [
      "ReceiveDate", "ReceiveMonth", "BranchName",
      "ReceiptNumber",
      "NumeroNC",         # ✅ FIX 4 — número da NC para eventos CREDIT
      "EventType", "InvDocNum",
      "CardCode", "CardName", "SlpCode", "SlpName",
      "ItemCode", "ItemDescription",
      "Installment", "Quantity", "Currency",
      "LineTotal", "AmountReceived", "AllocatedExpenses",
      "PaymentBase", "CommissionPct", "CommissionValue",
      "GLAccount", "GLAccountName",
  ] if c in filtered.columns]

  detail = filtered[show_cols].copy()

  a, b, c = st.columns([3, 2, 2])
  search_all = a.text_input("🔍 Buscar em todos os campos")
  vend_d     = b.selectbox("Vendedor", ["Todos"] + vend_opts)
  branch_d   = c.selectbox("Filial",   ["Todos"] + branch_opts)

  if search_all:
      mask = detail.astype(str).apply(
          lambda col: col.str.contains(search_all, case=False, na=False)
      ).any(axis=1)
      detail = detail[mask]
  if vend_d   != "Todos":
      detail = detail[detail["SlpName"]    == vend_d]
  if branch_d != "Todos":
      detail = detail[detail["BranchName"] == branch_d]

  detail_disp = detail.copy()
  for c in ["LineTotal", "AmountReceived", "AllocatedExpenses", "PaymentBase", "CommissionValue"]:
      if c in detail_disp.columns:
          detail_disp[c] = detail_disp[c].apply(fmt_brl)
  if "CommissionPct" in detail_disp.columns:
      detail_disp["CommissionPct"] = detail_disp["CommissionPct"].apply(pct_fmt)

  st.caption(f"{len(detail_disp):,} linhas exibidas".replace(",", "."))
  st.dataframe(detail_disp, use_container_width=True, height=580)

# ── EXPORTAR ──────────────────────────────────────────────
with t_exp:
  ts_file = datetime.now().strftime("%Y%m%d_%H%M")
  st.subheader("📥 Exportar relatórios")
  st.caption(f"Exportando {len(filtered):,} linhas filtradas".replace(",", "."))

  e1, e2, e3 = st.columns(3)
  with e1:
      st.download_button(
          "📊 Excel completo",
          data=to_excel({
              "Resumo_Vendedor": resumo_vend,
              "Resumo_Filial":   resumo_filial,
              "Resumo_Item":     resumo_item,
              "Resumo_Cliente":  resumo_cliente,
              "Detalhado":       filtered,
          }),
          file_name=f"comissoes_analitico_{ts_file}.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          use_container_width=True,
      )
  with e2:
      st.download_button(
          "📄 Resumo vendedores CSV",
          data=resumo_vend.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
          file_name=f"resumo_vendedores_{ts_file}.csv",
          mime="text/csv",
          use_container_width=True,
      )
  with e3:
      st.download_button(
          "📋 Detalhado CSV",
          data=filtered.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
          file_name=f"detalhado_{ts_file}.csv",
          mime="text/csv",
          use_container_width=True,
      )

  prev = resumo_vend.copy()
  for c in ["Vendas", "Recebido", "BasePagamento", "Comissao", "TicketMedioNF"]:
      prev[c] = prev[c].apply(fmt_brl)
  prev["PctMedio"]              = prev["PctMedio"].apply(pct_fmt)
  prev["ComissaoSobreVendaPct"] = prev["ComissaoSobreVendaPct"].apply(pct_fmt)

  st.markdown("---")
  st.subheader("📊 Prévia — resumo por vendedor")
  st.dataframe(prev, use_container_width=True, height=340)