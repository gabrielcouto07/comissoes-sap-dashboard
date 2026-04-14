"""
Power BI Automático Multi-Modelos — Nova versão modular

Fluxo:
1. Sidebar: upload arquivo + selecionar modelo
2. Load arquivo genérico
3. Instanciar modelo escolhido
4. Pipeline: normalize → validate → aggregate
5. Render UI conforme modelo
"""

import streamlit as st
from datetime import datetime
import pandas as pd

from utils import load_file
from models.comissao_model import ComissaoModel
from models.vendas_model import VendasModel
from templates import render_header, render_kpis, render_filters, render_export_tab

# ══════════════════════════════════════════════════════════
# PAGE CONFIG & CSS
# ══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Power BI Automático",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
.kpi-card.emerald { border-color:#10b981; }
.kpi-card.purple { border-color:#a855f7; }
.kpi-card.amber  { border-color:#f59e0b; }
.kpi-card.teal   { border-color:#14b8a6; }
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
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# MODELS REGISTRY
# ══════════════════════════════════════════════════════════

MODELS = {
    "💰 Comissões": ComissaoModel,
    "📈 Vendas": VendasModel,
}

# ══════════════════════════════════════════════════════════
# SIDEBAR: File upload + Model selection
# ══════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:1.2rem 0 .8rem">
      <div style="font-size:2.8rem;line-height:1">📊</div>
      <h2 style="color:#e2e8f0;margin:.3rem 0 0;font-size:1.15rem;font-weight:800">
        Power BI Automático
      </h2>
      <p style="color:#94a3b8;font-size:.7rem;margin:.1rem 0 0">
        Multi-modelos · Análise inteligente
      </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("📂 Planilha")
    uploaded = st.file_uploader(
        "Arquivo (.xlsx / .csv)",
        type=["xlsx", "xls", "csv"],
        help="Carregue sua planilha de dados",
    )
    
    st.markdown("---")
    st.subheader("🎯 Modelo de Análise")
    model_key = st.selectbox(
        "Escolha o tipo de análise:",
        list(MODELS.keys()),
        help="Cada modelo tem configurações e visualizações específicas",
    )
    
    st.markdown("---")
    st.caption("© 2026 · Power BI Automático")


# ══════════════════════════════════════════════════════════
# WELCOME PAGE (se sem arquivo)
# ══════════════════════════════════════════════════════════

if uploaded is None:
    st.markdown("""
    <div class="page-header">
      <h1>📊 Power BI Automático Multi-Modelos</h1>
      <p>Carregue sua planilha · Escolha o modelo · Análise automática</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    col1.info("**📄 Múltiplos Modelos**\n\nComissões, Vendas, Compras, Despesas e mais.")
    col2.info("**🔄 Deduplicação**\n\nAuto-remove duplicatas onde necessário.")
    col3.info("**📊 Exportação**\n\nExcel, CSV e relatórios prontos.")
    
    st.stop()


# ══════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════

# Step 1: Load arquivo
with st.spinner("🔄 Carregando arquivo..."):
    @st.cache_data(show_spinner=False)
    def _cached_load(file_bytes: bytes, filename: str):
        df, err = load_file(
            type('FakeFile', (), {
                'read': lambda: file_bytes,
                'seek': lambda pos: None,
                'name': filename,
            })()
        )
        return df, err
    
    file_bytes = uploaded.read()
    df_raw, load_err = _cached_load(file_bytes, uploaded.name)
    
    if load_err or df_raw is None:
        st.error(f"❌ Erro ao ler: {load_err}")
        st.stop()

# Step 2: Instanciar modelo
ModelClass = MODELS[model_key]
model = ModelClass(df_raw)

# Step 3: Load modelo (normalize + dedup)
model.load()

# Step 4: Validar
ok, missing = model.validate()
if not ok:
    st.error(f"❌ Colunas obrigatórias faltando: {missing}")
    st.info(f"Colunas disponíveis: {', '.join(df_raw.columns.tolist()[:15])}")
    st.stop()

# Step 5: Set session state para uso em callbacks
st.session_state.ts_now = datetime.now().strftime("%d/%m/%Y %H:%M")

# ══════════════════════════════════════════════════════════
# RENDER UI: Header + Filters
# ══════════════════════════════════════════════════════════

render_header(model, model.df)

st.markdown("---")

# Filtros
filters = render_filters(model.df, model.FILTER_COLS)
filtered = model.apply_filters(filters)

if filtered.empty:
    st.warning("⚠️ Nenhum dado com os filtros selecionados")
    st.stop()

# ══════════════════════════════════════════════════════════
# KPIs + Aggregations
# ══════════════════════════════════════════════════════════

kpis = model.get_kpis(filtered)
render_kpis(kpis)

aggs = model.get_aggregations(filtered)

st.markdown("---")

# ══════════════════════════════════════════════════════════
# TABS (delegado ao modelo)
# ══════════════════════════════════════════════════════════

tabs = st.tabs(model.TABS)

# Usar um índice simples: exportar sempre na última tab
for i, tab in enumerate(tabs[:-1]):
    with tab:
        st.info(f"✅ Tab renderizada pelo modelo {model.MODEL_NAME.upper()}")
        # Cada modelo pode renderizar sua lógica customizada aqui
        # Por enquanto, apenas placeholder

# Tab final: EXPORTAR (genérica para todos)
with tabs[-1]:
    render_export_tab(model, filtered)
