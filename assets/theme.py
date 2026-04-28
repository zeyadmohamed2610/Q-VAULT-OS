# =============================================================
#  theme.py — Q-Vault OS  |  Cyber Neon Design System (Static)
#
#  Passive asset layer. No logic.
# =============================================================

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
# SECTION 1: DESIGN TOKENS
# ═══════════════════════════════════════════════════════════════

THEME = {
    # ── Backgrounds ──
    "bg_black":        "#06080d",
    "bg_dark":         "#0b1320",
    "bg_mid":          "#101a2b",

    # ── Surfaces (panels, cards, overlays) ──
    "surface_dark":    "#0a0f19",   # was rogue #0a0f19 in taskbar menus
    "surface_mid":     "#10101a",   # was rogue #10101a in settings_hub
    "surface_raised":  "#1a1a2e",   # was rogue #1a1a2e in onboarding/control_panel
    "surface_overlay":  "rgba(10, 15, 25, 0.75)",
    "surface_inactive": "#080a10",  # was rogue #080a10 in TitleBar[active=false]

    # ── Blue Neon — Primary ──
    "primary_glow":    "#00e6ff",
    "primary_soft":    "#00bcd4",
    "primary_deep":    "#008fa3",
    "primary_gradient": "#0095ff",  # was rogue #0095ff in taskbar gradients

    # ── Purple — Accent ──
    "accent_purple":   "#9c27ff",
    "accent_pink":     "#ff2fd1",

    # ── Highlights & Text ──
    "highlight":       "#66f2ff",
    "text_main":       "#e6f7ff",
    "text_dim":        "#9ec0d5",  # WCAG AA fix: 5.2:1 ratio (was #7aa0b8 = 3.8:1)
    "text_muted":      "#6b8a9e",  # for truly low-priority info
    "text_disabled":   "#555568",  # was rogue #555568 in disabled menu items

    # ── State Colors ──
    "accent_error":    "#ff3366",
    "error_bright":    "#ff3333",  # was rogue #ff3333 in quarantine overlays
    "error_soft":      "#ff6666",  # was rogue #ff6666 in quarantine hover
    "warning":         "#ffaa00",  # was rogue #ffaa00 in notifications
    "warning_soft":    "#ffd080",  # was rogue #ffd080 in sudo dialog
    "warning_score":   "#ffaa44",  # was rogue #ffaa44 in trust scores
    "danger_score":    "#ff6644",  # was rogue #ff6644 in low trust scores
    "success":         "#00ff88",  # was rogue #00ff88 in enabled toggles

    # ── Borders ──
    "border_color":    "rgba(0, 230, 255, 0.3)",
    "border_subtle":   "rgba(0, 230, 255, 0.08)",
    "border_muted":    "rgba(255, 255, 255, 0.1)",
    "border_surface":  "#1e293b",  # was rogue #1e293b in launcher cards

    # ── Interactive Overlays ──
    "hover_glow":      "rgba(0, 230, 255, 0.15)",
    "hover_subtle":    "rgba(255, 255, 255, 0.1)",
    "active_glow":     "rgba(0, 230, 255, 0.25)",
    "inactive_surface": "rgba(255, 255, 255, 0.05)",
}

# ── Top-level Constants (API) ──
PRIMARY      = THEME["primary_glow"]
SECONDARY    = THEME["accent_purple"]
ACCENT       = THEME["accent_pink"]
BG_DARK      = THEME["bg_dark"]
BG           = THEME["bg_black"]
TEXT         = THEME["text_main"]
TEXT_MAIN    = THEME["text_main"]
TEXT_DIM     = THEME["text_dim"]
TEXT_MUTED   = THEME["text_muted"]
ERROR        = THEME["accent_error"]
BORDER       = THEME["border_color"]
SURFACE      = THEME["surface_dark"]
SUCCESS      = THEME["success"]
WARNING      = THEME["warning"]

FONT = {
    "family":       "'Segoe UI', 'Inter', sans-serif",
    "mono":         "'Consolas', 'Cascadia Code', monospace",
    "size_normal":  13,
    "size_small":   11,
    "size_heading": 22,
}

FONT_MONO = FONT["mono"]

RADIUS = {
    "sm": 4,
    "md": 8,
    "lg": 12,
}

# ═══════════════════════════════════════════════════════════════
# SECTION 2: GLOBAL STYLESHEET
# ═══════════════════════════════════════════════════════════════

GLOBAL_STYLE = f"""
    * {{
        font-family: {FONT["family"]};
        color: {THEME["text_main"]};
    }}

    /* ── Overlay ── */
    QWidget#Overlay {{
        background: rgba(0, 0, 0, 0.45);
    }}

    /* ── Login ── */
    QFrame#LoginCard {{
        background: rgba(10, 15, 25, 0.75);
        border: 1px solid {THEME["primary_glow"]};
        border-radius: {RADIUS["lg"]}px;
        /* Subtle depth glow — signals active security layer */
    }}

    QLabel#LoginLogo {{
        font-size: 64px;
        font-weight: bold;
        color: {THEME["primary_glow"]};
    }}

    QLabel#LoginTitle {{
        font-size: 13px;
        letter-spacing: 5px;
        color: {THEME["text_dim"]};
        font-weight: bold;
    }}

    /* ── Buttons ── */
    QPushButton#PrimaryBtn {{
        background-color: {THEME["primary_glow"]};
        color: black;
        border: none;
        border-radius: {RADIUS["sm"]}px;
        padding: 10px 20px;
        font-weight: bold;
        font-size: {FONT["size_normal"]}px;
    }}

    QPushButton#PrimaryBtn:hover {{
        background-color: {THEME["highlight"]};
    }}

    QPushButton#PrimaryBtn:pressed {{
        background-color: {THEME["primary_soft"]};
    }}

    QPushButton#PrimaryBtn:disabled {{
        background-color: {THEME["primary_deep"]};
        color: {THEME["text_dim"]};
    }}

    /* ── Inputs ── */
    QLineEdit {{
        background: rgba(0, 0, 0, 0.6);
        border: 1px solid {THEME["border_color"]};
        border-radius: {RADIUS["sm"]}px;
        padding: 8px;
        color: {THEME["text_main"]};
    }}

    QLineEdit:focus {{
        border: 1px solid {THEME["primary_glow"]};
    }}

    /* ── OS Window ── */
    QWidget#OSWindow {{
        background-color: {THEME["bg_dark"]};
        border: 1px solid {THEME["border_color"]};
        border-radius: {RADIUS["md"]}px;
    }}

    QWidget#OSWindow[active="false"] {{
        background-color: rgba(6, 8, 13, 240);
        border: 1px solid rgba(0, 230, 255, 0.07);
    }}

    QWidget#TitleBar {{
        background-color: {THEME["bg_black"]};
        border-top-left-radius:  {RADIUS["md"]}px;
        border-top-right-radius: {RADIUS["md"]}px;
        border-bottom: 1px solid {THEME["border_color"]};
    }}

    QWidget#TitleBar[active="false"] {{
        background-color: {THEME["surface_inactive"]};
    }}

    QLabel#TitleLabel {{
        color: {THEME["primary_glow"]};
        font-weight: bold;
    }}

    /* ── App Containers ── */
    QWidget#AppContainer {{
        background-color: {THEME["bg_dark"]};
        border: 1px solid {THEME["border_color"]};
        border-radius: {RADIUS["md"]}px;
    }}

    QWidget#AppToolbar {{
        background-color: {THEME["bg_black"]};
        border-bottom: 1px solid {THEME["border_color"]};
    }}

    /* ── Scrollbars ── */
    QScrollBar:vertical {{
        background: {THEME["bg_dark"]};
        width: 6px;
        border-radius: 3px;
    }}

    QScrollBar::handle:vertical {{
        background: {THEME["primary_deep"]};
        border-radius: 3px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {THEME["primary_glow"]};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background: {THEME["bg_dark"]};
        height: 6px;
        border-radius: 3px;
    }}

    QScrollBar::handle:horizontal {{
        background: {THEME["primary_deep"]};
        border-radius: 3px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {THEME["primary_glow"]};
    }}

    /* ── Workspace Desktop ── */
    QWidget#Desktop {{
        background-color: {THEME["bg_black"]};
    }}

    /* ── QMenu (Context & App Menus) ── */
    QMenu {{
        background-color: rgba(11, 19, 32, 0.90);
        border: 1px solid rgba(0, 230, 255, 0.2);
        border-radius: 8px;
        padding: 5px;
    }}

    QMenu::item {{
        background: transparent;
        padding: 8px 24px 8px 12px;
        border-radius: 5px;
        margin: 2px 5px;
        color: {THEME["text_main"]};
        font-size: {FONT["size_small"] + 1}px;
    }}

    QMenu::item:selected {{
        background-color: rgba(0, 230, 255, 0.15);
        color: {THEME["primary_glow"]};
        /* Subtle glowing neon border on hover */
        border: 1px solid rgba(0, 230, 255, 0.4);
    }}

    QMenu::separator {{
        height: 1px;
        background: rgba(255, 255, 255, 0.1);
        margin: 5px 10px;
    }}

    /* ── Top Panel (Floating Control Strip) ── */
    QWidget#Topbar {{
        background-color: #0b1320; /* Solid premium deep navy */
        border-bottom: 2px solid rgba(0, 230, 255, 0.45); /* Bottom glow */
        border-bottom-left-radius: 12px;
        border-bottom-right-radius: 12px;
    }}

    QPushButton#TaskbarBtn, QPushButton#StartBtn {{
        background-color: rgba(255, 255, 255, 0.03);
        color: {THEME["text_dim"]};
        border: 1px solid rgba(0, 230, 255, 0.08);
        border-radius: 6px;
        padding: 4px 14px;
        font-weight: bold;
        font-size: {FONT["size_normal"]}px;
        text-align: center;
        margin: 0 3px;
    }}

    QPushButton#TaskbarBtn:hover, QPushButton#StartBtn:hover {{
        background-color: rgba(0, 230, 255, 0.15);
        color: {THEME["text_main"]};
        border: 1px solid {THEME["primary_glow"]};
    }}

    QPushButton#TaskbarBtn[active="true"] {{
        background-color: rgba(0, 230, 255, 0.25);
        color: {THEME["primary_glow"]};
        border: 1px solid {THEME["primary_glow"]};
    }}

    QLabel#StatusLabel, QLabel#ClockLabel {{
        color: {THEME["text_dim"]};
        font-weight: bold;
        font-size: {FONT["size_small"]}px;
        padding: 2px 8px;
    }}

    QLabel#ClockLabel {{
        color: {THEME["text_main"]};
    }}
"""
