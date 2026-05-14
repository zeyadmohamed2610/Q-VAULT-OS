from resources.design_tokens import COLORS as VAULT, FONTS as VAULT_FONTS
from resources.design_tokens import RADIUS as VAULT_RADIUS, MOTION as VAULT_MOTION

# Expose vault colors as module-level shortcuts
BG_VOID      = VAULT["bg_void"]
BG_BASE      = VAULT["bg_base"]
BG_SURFACE   = VAULT["bg_surface"]
BG_ELEVATED  = VAULT["bg_elevated"]
CYAN         = VAULT["cyan"]
CYAN_BRIGHT  = VAULT["cyan_bright"]
CYAN_DIM     = VAULT["cyan_dim"]
STEEL        = VAULT["steel"]
TEXT_PRIMARY = VAULT["text_primary"]
TEXT_SEC     = VAULT["text_secondary"]
TEXT_MUTED_V = VAULT["text_muted"]
BORDER_SUB   = VAULT["border_subtle"]
BORDER_ACT   = VAULT["border_active"]
GLOW_CYAN    = VAULT["glow_cyan"]


# ── Spacing Tokens ──
SPACE_XXS = 4
SPACE_XS  = 8
SPACE_SM  = 12
SPACE_MD  = 16
SPACE_LG  = 24
SPACE_XL  = 32
SPACE_XXL = 48

# ── Radius Tokens ──
RADIUS_SM = 4
RADIUS_MD = 8
RADIUS_LG = 12
RADIUS_XL = 24

from PyQt5.QtCore import QEasingCurve

# ── Animation Tokens ──
MOTION_SNAPPY = 150
MOTION_SMOOTH = 250
MOTION_STAGGER = 30
EASE_OUT = QEasingCurve.OutCubic
EASE_IN_OUT = QEasingCurve.InOutCubic

# ═══════════════════════════════════════════════════════════════
# SECTION 1: DESIGN TOKENS (Premium Revision)
# ═══════════════════════════════════════════════════════════════

THEME = {
    # ── Backgrounds ──
    "bg_black":        "#05070a",  # Deep void
    "bg_dark":         "#080c14",  # Atmospheric navy
    "bg_base":         BG_BASE,    # Root background
    "bg_darker":       "#040608",  # Absolute zero
    "bg_mid":          "#0f1724",

    # ── Surfaces ──
    "surface_dark":    "#0a0f19",
    "surface_mid":     "#12121f",
    "surface_raised":  "#1a1a2e",
    "surface_overlay":  "rgba(8, 12, 20, 0.95)",
    "surface_inactive": "#06080d",

    # ── Cyan Core ──
    "primary_glow":    "#00f0ff",
    "primary_soft":    "#00d2ff",
    "primary_deep":    "#007a99",
    "primary_gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f0ff, stop:1 #0095ff)",

    # ── Security Accents ──
    "accent_crimson":  "#ff3b6b",
    "accent_purple":   "#a033ff",
    "accent_pink":     "#ff2fd1",

    # ── Highlights & Text ──
    "highlight":       "#b3f9ff",
    "text_main":       "#f0f9ff",
    "text_dim":        "#a5c2d1",
    "text_muted":      "#6b8a9e",
    "text_disabled":   "#3d4d5c",

    # ── State Colors ──
    "accent_error":    "#ff3b6b",
    "error_bright":    "#ff5e8c",
    "warning":         "#ffaa00",
    "success":         "#00ffcc",

    # ── Borders ──
    "border_color":    "rgba(0, 240, 255, 0.25)",
    "border_subtle":   "rgba(0, 240, 255, 0.1)",
    "border_muted":    "rgba(255, 255, 255, 0.05)",

    # ── Overlays ──
    "hover_glow":      "rgba(0, 240, 255, 0.2)",
    "active_glow":     "rgba(0, 240, 255, 0.3)",
}

FONT = {
    "family":       "'Inter', 'Segoe UI', system-ui, sans-serif",
    "mono":         "'Consolas', 'Cascadia Code', monospace",
    "size_normal":  13,
    "size_small":   11,
    "size_heading": 24,
}

FONT_MONO = FONT["mono"]

GLOBAL_STYLE = f"""
    * {{
        font-family: {FONT["family"]};
        color: {THEME["text_main"]};
    }}

    /* ── Base UI ── */
    QWidget {{
        outline: none;
    }}

    /* ── Inputs ── */
    QLineEdit {{
        background: rgba(0, 0, 0, 0.4);
        border: 1px solid {THEME["border_subtle"]};
        border-radius: 10px;
        padding: 10px 14px;
        color: {THEME["text_main"]};
        selection-background-color: {THEME["primary_glow"]};
        selection-color: black;
    }}

    QLineEdit:focus {{
        border: 1px solid {THEME["primary_glow"]};
        background: rgba(0, 240, 255, 0.03);
    }}

    /* ── Premium Buttons ── */
    QPushButton {{
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(0, 240, 255, 0.15);
        border-radius: 10px;
        padding: 8px 24px;
        font-weight: 600;
        letter-spacing: 1px;
    }}

    QPushButton:hover {{
        background: rgba(0, 240, 255, 0.12);
        border-color: {THEME["primary_glow"]};
        color: {THEME["primary_glow"]};
    }}

    QPushButton:pressed {{
        background: rgba(0, 240, 255, 0.2);
    }}
    
    QPushButton:disabled {{
        background: rgba(255, 255, 255, 0.02);
        color: {THEME["text_disabled"]};
        border-color: rgba(255, 255, 255, 0.05);
    }}

    /* ── Primary Action Buttons ── */
    QPushButton#PrimaryBtn {{
        background: {THEME["primary_gradient"]};
        color: black;
        border: none;
        font-weight: 800;
    }}

    QPushButton#PrimaryBtn:hover {{
        background: {THEME["primary_glow"]};
    }}
    
    QPushButton.busy {{
        background: rgba(0, 240, 255, 0.1);
        color: {THEME["primary_glow"]};
        border: 1px solid {THEME["primary_glow"]};
    }}

    /* ── OS Windows ── */
    QWidget#OSWindow {{
        background: {THEME["bg_dark"]};
        border: 1px solid {THEME["border_subtle"]};
        border-radius: 14px;
    }}

    QWidget#OSWindow[active="false"] {{
        border: 1px solid rgba(255, 255, 255, 0.05);
        background: #06080b;
    }}

    /* ── Scrollbars ── */
    QScrollBar:vertical {{
        background: transparent;
        width: 4px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background: rgba(0, 240, 255, 0.2);
        border-radius: 2px;
        min-height: 40px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {THEME["primary_glow"]};
    }}

    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; }}

    /* ── Menus ── */
    QMenu {{
        background: rgba(10, 15, 25, 0.98);
        border: 1px solid {THEME["border_color"]};
        border-radius: 12px;
        padding: 8px;
    }}

    QMenu::item {{
        padding: 10px 32px 10px 16px;
        border-radius: 8px;
        margin: 2px 4px;
    }}

    QMenu::item:selected {{
        background: rgba(0, 240, 255, 0.12);
        color: {THEME["primary_glow"]};
    }}

    /* ── Tooltips ── */
    QToolTip {{
        background-color: #05070a;
        color: {THEME["text_main"]};
        border: 1px solid rgba(0, 240, 255, 0.5);
        border-radius: 8px;
        padding: 6px 12px;
        font-family: {FONT["family"]};
        font-size: 11px;
    }}
"""
