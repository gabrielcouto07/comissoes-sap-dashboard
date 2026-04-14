"""
colors.py — Design System: Paleta centralizada de cores
════════════════════════════════════════════════════════════════════════════

Toda referência visual do app sai daqui. Mudança em um lugar = mudança em tudo.
"""

# ══════════════════════════════════════════════════════════════════════════════
# PALETA PRINCIPAL (Dark Mode Profissional)
# ══════════════════════════════════════════════════════════════════════════════

PALETTE = {
    "bg":          "#0f1117",   # Fundo principal (dark navy quase preto)
    "surface":     "#1a1d27",   # Cards, painéis, surfaces
    "surface2":    "#20242f",   # Inputs, tabelas, elevação
    "surface3":    "#282d38",   # Elementos em hover
    "border":      "#2d3144",   # Divisórias, borders
    "primary":     "#4f8ef7",   # Destaque principal (azul)
    "primary_dark": "#3d6bc4",  # Hover state do primary
    "success":     "#34c97e",   # Positivo, aumento (verde)
    "warning":     "#f5a623",   # Atenção (amber)
    "danger":      "#e05c5c",   # Negativo, queda (vermelho)
    "info":        "#22d3ee",   # Informativo (cyan)
    "text":        "#e8eaf0",   # Texto principal (branco suave)
    "text_secondary": "#a8afc0", # Texto secundário (cinza médio)
    "muted":       "#8b90a8",   # Texto desabilitado (cinza escuro)
}

# Sequência de cores para gráficos multi-série (vendedores, itens, etc)
# Alternância entre primary, success, warning, danger, purple, cyan + variações
CHART_COLORS = [
    "#4f8ef7",  # Primary Blue
    "#34c97e",  # Success Green
    "#f5a623",  # Warning Amber
    "#e05c5c",  # Danger Red
    "#a78bfa",  # Purple
    "#22d3ee",  # Cyan
    "#7c3aed",  # Violet
    "#06b6d4",  # Sky
]

# Paleta de status (para badges, flags, indicators)
STATUS_COLORS = {
    "pending":  "#f5a623",   # Aguardando
    "active":   "#34c97e",   # Ativo
    "inactive": "#8b90a8",   # Inativo
    "error":    "#e05c5c",   # Erro
    "warning":  "#f5a623",   # Aviiso
}

# ══════════════════════════════════════════════════════════════════════════════
# GRADIENT & EFFECTS
# ══════════════════════════════════════════════════════════════════════════════

GRADIENTS = {
    "primary_to_secondary": f"linear-gradient(135deg, {PALETTE['primary']}, {PALETTE['info']})",
    "success_fade": f"linear-gradient(135deg, {PALETTE['success']}, {PALETTE['success']}33)",
    "danger_fade": f"linear-gradient(135deg, {PALETTE['danger']}, {PALETTE['danger']}33)",
}

# ══════════════════════════════════════════════════════════════════════════════
# HEATMAP COLORSCALE (para imshow, heatmap, etc)
# ══════════════════════════════════════════════════════════════════════════════

HEATMAP_COLORSCALE = [
    [0.0,  PALETTE["surface"]],      # Mínimo → surface
    [0.25, PALETTE["primary_dark"]], # Intermediário I
    [0.5,  PALETTE["primary"]],      # Intermediário II
    [0.75, PALETTE["info"]],         # Alto
    [1.0,  "#22d3ee"],               # Máximo → bright cyan
]

# ══════════════════════════════════════════════════════════════════════════════
# HELPER: Formatar cor com opacity
# ══════════════════════════════════════════════════════════════════════════════

def hex_with_alpha(hex_color: str, alpha: float = 1.0) -> str:
    """
    Converte #RRGGBB para rgba com alpha (0.0-1.0).
    
    Ex: hex_with_alpha("#4f8ef7", 0.5) = "rgba(79, 142, 247, 0.5)"
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def get_delta_color(delta: float) -> str:
    """Retorna cor baseada em delta (positivo/negativo)."""
    return PALETTE["success"] if delta >= 0 else PALETTE["danger"]


def get_delta_arrow(delta: float) -> str:
    """Retorna seta baseada em delta."""
    if delta > 0:
        return "↑"
    elif delta < 0:
        return "↓"
    else:
        return "→"


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT: Dicionário de cores para Matplotlib/Seaborn (se usar)
# ══════════════════════════════════════════════════════════════════════════════

MATPLOTLIB_COLORS = {color: hex_val for color, hex_val in PALETTE.items()}
