"""
Templates — Componentes reutilizáveis Streamlit.
"""

from .dashboard_template import (
    render_header,
    render_kpis,
    render_filters,
    render_dataframe_display,
    render_search_filter,
)
from .export_template import render_export_tab

__all__ = [
    "render_header",
    "render_kpis",
    "render_filters",
    "render_dataframe_display",
    "render_search_filter",
    "render_export_tab",
]
