"""
templates/ui.py — Design System: Componentes de UI profissional

Integra com config/colors.py e theme.css.
Fornece componentes reutilizáveis com consistência visual.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
from config.colors import PALETTE, CHART_COLORS, HEATMAP_COLORSCALE, get_delta_color, get_delta_arrow

# ══════════════════════════════════════════════════════════════════════════════
# 1. THEME LOADER — Executa UMA VEZ no app
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def load_theme():
    """
    Carrega CSS customizado do arquivo theme.css.
    Cache resource garante que executa apenas uma vez.
    
    FIX: Usa encoding='utf-8' para evitar UnicodeDecodeError no Windows
    """
    script_dir = Path(__file__).parent.parent
    theme_path = script_dir / "theme.css"
    
    if not theme_path.exists():
        return
    
    with open(theme_path, encoding="utf-8") as f:
        css = f.read()
    
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 2. KPI CARD COMPONENT (com delta, ícone, hierarquia)
# ══════════════════════════════════════════════════════════════════════════════

def kpi_card(
    label: str,
    value: str,
    delta: float = None,
    delta_label: str = "vs. período anterior",
    icon: str = "💰",
    prefix: str = "R$",
    color: str = "primary"
) -> None:
    """
    Renderiza um KPI card profissional com delta, ícone e hierarquia.
    
    Args:
        label: Rótulo do KPI (ex: "Faturamento")
        value: Valor formatado (ex: "R$ 150.000")
        delta: Variação percentual (ex: +12.4, -3.5, None)
        delta_label: Texto do delta (ex: "vs. mês anterior")
        icon: Emoji ou ícone (ex: "💰", "👤", "📊")
        prefix: Prefixo monetário (ex: "R$", "")
        color: Cor da borda (primary, success, warning, danger)
    
    Ex:
        kpi_card("Faturamento", "23.435.318", delta=+12.4, prefix="R$")
    """
    # Cores por tipo
    color_map = {
        "primary": PALETTE["primary"],
        "success": PALETTE["success"],
        "warning": PALETTE["warning"],
        "danger": PALETTE["danger"],
        "info": PALETTE["info"],
    }
    border_color = color_map.get(color, PALETTE["primary"])
    
    # Renderizar delta se fornecido
    delta_html = ""
    if delta is not None:
        delta_color = get_delta_color(delta)
        delta_arrow = get_delta_arrow(delta)
        delta_html = f'''
        <div style="
            color: {delta_color};
            font-size: 13px;
            font-weight: 500;
            margin-top: 0.5rem;
        ">
            {delta_arrow} {abs(delta):.1f}% {delta_label}
        </div>
        '''
    
    # Renderizar card
    st.markdown(f"""
    <div style="
        background: {PALETTE['surface']};
        border: 2px solid {border_color};
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        transition: all 0.2s ease;
    " onmouseover="this.style.borderColor='{border_color}'; this.style.background='{PALETTE['surface2']}';"
      onmouseout="this.style.borderColor='{border_color}'; this.style.background='{PALETTE['surface']}';">
        
        <div style="
            color: {PALETTE['muted']};
            font-size: 12px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.4rem;
        ">
            {icon} {label}
        </div>
        
        <div style="
            color: {PALETTE['text']};
            font-size: 28px;
            font-weight: 700;
            font-variant-numeric: tabular-nums lining-nums;
            margin: 0.4rem 0;
            font-family: 'Courier New', monospace;
        ">
            {prefix} {value}
        </div>
        
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_kpi_row(kpis: list[dict], layout: list[int] = None) -> None:
    """
    Renderiza linha de KPIs em layout proporcional.
    
    Args:
        kpis: Lista de dicts com keys (label, value, delta, icon, prefix, color)
        layout: Proporções de coluna (ex: [2, 2, 2, 1, 1] para 5 colunas)
    
    Ex:
        kpis = [
            {"label": "Faturamento", "value": "23.435.318", "delta": +12.4, "icon": "💰"},
            {"label": "Ticket Médio", "value": "14.386", "delta": -2.1, "icon": "🎯"},
            {"label": "NFs Emitidas", "value": "1.629", "delta": +8.0, "icon": "📄", "prefix": ""},
            {"label": "Vendedores", "value": "16", "icon": "👤", "prefix": ""},
            {"label": "Período", "value": "8 semanas", "icon": "📅", "prefix": ""},
        ]
        render_kpi_row(kpis, layout=[2, 2, 2, 1, 1])
    """
    if not layout:
        layout = [1] * len(kpis)
    
    cols = st.columns(layout)
    for kpi, col in zip(kpis, cols):
        with col:
            kpi_card(
                label=kpi.get("label", "—"),
                value=kpi.get("value", "—"),
                delta=kpi.get("delta"),
                delta_label=kpi.get("delta_label", "vs. período anterior"),
                icon=kpi.get("icon", "📊"),
                prefix=kpi.get("prefix", "R$"),
                color=kpi.get("color", "primary"),
            )


# ══════════════════════════════════════════════════════════════════════════════
# 3. APPLY CHART STYLE — Template padrão para Plotly
# ══════════════════════════════════════════════════════════════════════════════

def apply_chart_style(
    fig: go.Figure,
    title: str = "",
    height: int = 380,
    showlegend: bool = True,
) -> go.Figure:
    """
    Aplica estilos padrão do design system em gráfico Plotly.
    
    Args:
        fig: Figure Plotly
        title: Título do gráfico
        height: Altura em pixels
        showlegend: Mostrar legenda
    
    Ex:
        fig = px.bar(df, x="Mês", y="Vendas")
        fig = apply_chart_style(fig, title="Vendas por Mês")
        st.plotly_chart(fig, use_container_width=True)
    
    Aplicações:
        • Tema dark mode
        • Paleta de cores unificada
        • Grid configurado
        • Legenda estilizada
        • Hover template customizado
    """
    fig.update_layout(
        # Cores de fundo
        paper_bgcolor=PALETTE["surface"],
        plot_bgcolor=PALETTE["surface"],
        
        # Título
        title=dict(
            text=title,
            font=dict(
                size=15,
                color=PALETTE["text"],
                family="Inter, sans-serif",
            ),
            x=0,
            xanchor="left",
            pad=dict(l=4, b=8),
        ),
        
        # Tipografia
        font=dict(
            family="Inter, sans-serif",
            size=12,
            color=PALETTE["muted"],
        ),
        
        # Layout
        height=height,
        margin=dict(l=16, r=16, t=48, b=16),
        
        # Grid
        xaxis=dict(
            gridcolor=PALETTE["border"],
            linecolor=PALETTE["border"],
            tickcolor=PALETTE["border"],
            tickfont=dict(color=PALETTE["muted"], size=11),
        ),
        yaxis=dict(
            gridcolor=PALETTE["border"],
            gridwidth=0.5,
            linecolor=PALETTE["border"],
            tickcolor=PALETTE["border"],
            tickfont=dict(color=PALETTE["muted"], size=11),
        ),
        
        # Legenda
        legend=dict(
            bgcolor=PALETTE["surface2"],
            bordercolor=PALETTE["border"],
            borderwidth=1,
            font=dict(
                size=11,
                color=PALETTE["text"],
            ),
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
        ) if showlegend else dict(visible=False),
        
        # Paleta de cores (série)
        colorway=CHART_COLORS,
        
        # Hover
        hoverlabel=dict(
            bgcolor=PALETTE["surface2"],
            bordercolor=PALETTE["border"],
            font=dict(
                size=12,
                color=PALETTE["text"],
            ),
            namelength=-1,
        ),
        
        # Animação
        transition=dict(duration=300),
    )
    
    # Update hover template se não estiver setado
    for trace in fig.data:
        if trace.hovertemplate is None:
            trace.hovertemplate = (
                "<b>%{x}</b><br>"
                "Valor: R$ %{y:,.2f}<br>"
                "<extra></extra>"
            )
    
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# 4. HEADER CUSTOMIZADO
# ══════════════════════════════════════════════════════════════════════════════

def render_header(model, filtered_df, show_metadata: bool = True) -> None:
    """
    Renderiza header profissional com ícone, periodo, contadores.
    
    Args:
        model: Instância do modelo (BaseModel)
        filtered_df: DataFrame filtrado
        show_metadata: Mostrar período e contadores
    """
    ts_now = st.session_state.get("ts_now", "—")
    date_info = "—"
    
    # Tentar extrair período do DataFrame
    for col in ["ReceiveDate", "SaleDate", "PurchaseDate", "ExpenseDate"]:
        if col in filtered_df.columns and filtered_df[col].notna().any():
            try:
                d_min = filtered_df[col].min().strftime("%d/%m/%Y")
                d_max = filtered_df[col].max().strftime("%d/%m/%Y")
                date_info = f"{d_min} → {d_max}"
                break
            except Exception:
                pass
    
    header_html = f"""
    <div style="
        background: linear-gradient(135deg, {PALETTE['primary']}, {PALETTE['info']});
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(79, 142, 247, 0.15);
    ">
        <div style="
            font-size: 32px;
            font-weight: 600;
            color: white;
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
        ">
            {model.MODEL_ICON} Relatório {model.MODEL_NAME.title()}
        </div>
        
        <div style="
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
        ">
            <span>📊 {len(filtered_df):,} linhas</span>
            <span>📅 Período: {date_info}</span>
            <span>🕐 {ts_now}</span>
        </div>
    </div>
    """
    
    st.markdown(header_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 5. PERIOD FILTER COM PRESETS
# ══════════════════════════════════════════════════════════════════════════════

def render_period_filter(
    df: pd.DataFrame,
    date_col: str = "SaleDate",
    key_prefix: str = ""
) -> tuple:
    """
    Renderiza filtro de período com presets inteligentes.
    
    Args:
        df: DataFrame com coluna de data
        date_col: Nome da coluna de data
        key_prefix: Prefixo para st.session_state keys
    
    Returns:
        (data_inicio, data_fim) como tupla de dates
    """
    if date_col not in df.columns or df[date_col].isna().all():
        return (None, None)
    
    d_min = df[date_col].min().date()
    d_max = df[date_col].max().date()
    hoje = pd.Timestamp.now().date()
    
    st.sidebar.markdown("### 📅 Período")
    
    # Radio com presets
    preset = st.sidebar.radio(
        "Escolha período",
        ["Todo período", "Últimos 30 dias", "Últimos 3 meses", "Este ano", "Personalizado"],
        horizontal=False,
        label_visibility="collapsed",
        key=f"{key_prefix}period_preset",
    )
    
    # Calcular período baseado em preset
    if preset == "Últimos 30 dias":
        d0, d1 = hoje - timedelta(30), hoje
    elif preset == "Últimos 3 meses":
        d0, d1 = hoje - timedelta(90), hoje
    elif preset == "Este ano":
        d0, d1 = pd.Timestamp(hoje.year, 1, 1).date(), hoje
    elif preset == "Personalizado":
        dr = st.sidebar.date_input(
            "Intervalo",
            value=(d_min, d_max),
            min_value=d_min,
            max_value=d_max,
            key=f"{key_prefix}period_custom",
        )
        d0, d1 = (dr[0], dr[1]) if len(dr) == 2 else (d_min, d_max)
    else:  # Todo período
        d0, d1 = d_min, d_max
    
    # Caption com datas selecionadas
    dias_diff = (d1 - d0).days
    st.sidebar.caption(
        f"📅 {d0.strftime('%d/%m/%y')} → {d1.strftime('%d/%m/%y')} ({dias_diff} dias)"
    )
    
    return (d0, d1)


# ══════════════════════════════════════════════════════════════════════════════
# 6. SEPARATOR COM TÍTULO
# ══════════════════════════════════════════════════════════════════════════════

def render_separator(title: str = "", in_sidebar: bool = False) -> None:
    """
    Renderiza separador visual com título opcional.
    
    Args:
        title: Título da seção (opcional)
        in_sidebar: Se True, renderiza em st.sidebar
    """
    target = st.sidebar if in_sidebar else st
    
    if title:
        target.markdown(f"""
        <div style="
            border-top: 1px solid {PALETTE['border']};
            margin: 1rem 0;
            padding-top: 0.8rem;
        ">
            <span style="
                color: {PALETTE['muted']};
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.1em;
            ">
                {title}
            </span>
        </div>
        """, unsafe_allow_html=True)
    else:
        target.divider()


# ══════════════════════════════════════════════════════════════════════════════
# 7. BADGE COMPONENT
# ══════════════════════════════════════════════════════════════════════════════

def render_badge(
    text: str,
    variant: str = "primary",
    icon: str = ""
) -> None:
    """
    Renderiza badge estilizado.
    
    Args:
        text: Texto do badge
        variant: primary, success, danger, warning, info
        icon: Emoji ou ícone
    """
    color_map = {
        "primary": (PALETTE["primary"], "rgba(79, 142, 247, 0.15)"),
        "success": (PALETTE["success"], "rgba(52, 201, 126, 0.15)"),
        "danger": (PALETTE["danger"], "rgba(224, 92, 92, 0.15)"),
        "warning": (PALETTE["warning"], "rgba(245, 166, 35, 0.15)"),
        "info": (PALETTE["info"], "rgba(34, 211, 238, 0.15)"),
    }
    
    color, bg = color_map.get(variant, color_map["primary"])
    
    st.markdown(f"""
    <span style="
        background: {bg};
        color: {color};
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.05em;
        border: 1px solid {color};
        display: inline-block;
    ">
        {icon} {text}
    </span>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 8. HELPER: Detectar granularidade temporal (para gráficos adaptativos)
# ══════════════════════════════════════════════════════════════════════════════

def detect_time_granularity(df: pd.DataFrame, date_col: str = "SaleDate") -> dict:
    """
    Detecta granularidade ideal de um período (diário, semanal, mensal).
    
    Útil para escolher entre line/bar charts adaptativos.
    
    Returns:
        {
            "tipo": "diário|semanal|mensal",
            "freq": "D|W|M",
            "chart_type": "area|bar|line",
            "label_format": "%d/%m|%b/%Y",
            "dias_total": int,
            "periodo_str": "45 dias|12 semanas|8 meses"
        }
    """
    if date_col not in df.columns or df[date_col].isna().all():
        return {
            "tipo": "mensal",
            "freq": "M",
            "chart_type": "bar",
            "label_format": "%b/%Y",
            "dias_total": 0,
            "periodo_str": "Período desconhecido",
        }
    
    d_min = df[date_col].dropna().min()
    d_max = df[date_col].dropna().max()
    dias = (d_max - d_min).days if pd.notnull(d_min) and pd.notnull(d_max) else 0
    
    if dias <= 45:
        return {
            "tipo": "diário",
            "freq": "D",
            "chart_type": "area",
            "label_format": "%d/%m",
            "dias_total": dias,
            "periodo_str": f"{dias} dias",
        }
    elif dias <= 120:
        return {
            "tipo": "semanal",
            "freq": "W",
            "chart_type": "bar",
            "label_format": "%d/%m",
            "dias_total": dias,
            "periodo_str": f"{dias // 7} semanas",
        }
    else:
        return {
            "tipo": "mensal",
            "freq": "M",
            "chart_type": "bar",
            "label_format": "%b/%Y",
            "dias_total": dias,
            "periodo_str": f"{dias // 30} meses",
        }
