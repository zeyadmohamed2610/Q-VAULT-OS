# =============================================================
#  theme.py — Q-Vault OS  |  Design System v8 (Final Polish)
#
#  Single source of truth for ALL visual constants.
#  Changes from v7:
#    • FONT_MONO / FONT_SIZE_* constants — one definition
#    • SPACING_* constants for consistent padding
#    • Removed transparency from windows (solid #0f172a)
#    • Taskbar blur via rgba with higher opacity
#    • Unified button QSS helper functions
#    • Icon size constants (48px desktop, 24px taskbar)
#    • Improved WINDOW_STYLE — true shadow via border layering
# =============================================================

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent


def asset_path(filename: str) -> str:
    return str(ASSETS_DIR / filename)


# ── Brand ─────────────────────────────────────────────────────
BRAND_NAME     = "Q-Vault OS"
BRAND_WORDMARK = "Q-VAULT"
BRAND_MONOGRAM = "Q"
BRAND_LOGO     = asset_path("logo-qvault-primary.jpg")

# ── Animation timing ──────────────────────────────────────────
ANIMATION_FAST_MS   = 100
ANIMATION_NORMAL_MS = 160
ANIMATION_SLOW_MS   = 280

# ── Spacing / padding grid (8-pt system) ─────────────────────
SPACING_XS  = 4
SPACING_SM  = 8
SPACING_MD  = 12
SPACING_LG  = 16
SPACING_XL  = 24

# ── Border radius ─────────────────────────────────────────────
RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_LG = 8
RADIUS_XL = 12

# Deprecated aliases kept for back-compat
BORDER_RADIUS_SMALL  = RADIUS_SM
BORDER_RADIUS_MEDIUM = RADIUS_MD
BORDER_RADIUS_LARGE  = RADIUS_LG

# ── Typography ────────────────────────────────────────────────
FONT_MONO    = "'Consolas', 'Courier New', monospace"
FONT_SIZE_XS = 9
FONT_SIZE_SM = 11
FONT_SIZE_MD = 12
FONT_SIZE_LG = 13
FONT_SIZE_XL = 15
FONT_SIZE_H1 = 18
FONT_SIZE_H2 = 15
FONT_SIZE_H3 = 13

# ── Icon sizes ────────────────────────────────────────────────
ICON_SIZE_DESKTOP = 48    # px — desktop icons
ICON_SIZE_TASKBAR = 24    # px — taskbar / menu icons
ICON_SIZE_APP     = 32    # px — in-app icons

# ── Core palette ──────────────────────────────────────────────
PRIMARY   = "#22c55e"
SECONDARY = "#0ea5e9"

BG_DARK      = "#020617"
BG_PANEL     = "#0d1526"
BG_WINDOW    = "#0f172a"
BG_TITLEBAR  = "#1a2540"
BG_TITLEBAR_ACTIVE = "#243050"
BG_HOVER     = "#1e2d47"
BG_SELECTED  = "#1e3a5f"

DESKTOP_GRADIENT_START = "#020617"
DESKTOP_GRADIENT_MID   = "#0a1628"
DESKTOP_GRADIENT_END   = "#020617"

ACCENT_CYAN  = "#18d7ff"
ACCENT_GREEN = "#2cff9b"
ACCENT_RED   = "#ff5d68"
ACCENT_AMBER = "#ffbe55"
ACCENT_ICE   = "#d9ecff"
ACCENT_STEEL = "#64748b"

TEXT_PRIMARY = "#e2e8f0"
TEXT_DIM     = "#8b9dc3"

BORDER_DIM    = "#1e3a5f"
BORDER_BRIGHT = "#22c55e"

# ── Taskbar ───────────────────────────────────────────────────
TASKBAR_STYLE = f"""
    QWidget#Taskbar {{
        background-color: rgba(10, 18, 38, 252);
        border-top: 1px solid {BORDER_BRIGHT};
    }}
    QPushButton#StartBtn {{
        background-color: rgba(34, 197, 94, 0.12);
        color: {ACCENT_GREEN};
        border: 1px solid {ACCENT_GREEN};
        padding: {SPACING_XS}px {SPACING_LG}px;
        font-size: {FONT_SIZE_MD}px;
        font-weight: bold;
        font-family: {FONT_MONO};
        border-radius: {RADIUS_MD}px;
        margin: {SPACING_SM - 2}px {SPACING_XS}px;
    }}
    QPushButton#StartBtn:hover {{
        background-color: rgba(24, 215, 255, 0.18);
        color: {ACCENT_ICE};
    }}
    QPushButton#StartBtn:pressed {{
        background-color: rgba(24, 215, 255, 0.30);
    }}
    QPushButton#TaskbarBtn {{
        background-color: transparent;
        color: {TEXT_DIM};
        border: 1px solid transparent;
        border-bottom: 2px solid transparent;
        padding: {SPACING_XS}px {SPACING_MD}px;
        font-size: {FONT_SIZE_SM}px;
        font-family: {FONT_MONO};
        border-radius: {RADIUS_MD}px;
        margin: 5px 2px;
        min-width: 80px;
        max-width: 160px;
    }}
    QPushButton#TaskbarBtn:hover {{
        background-color: {BG_HOVER};
        color: {ACCENT_ICE};
        border: 1px solid {BORDER_DIM};
    }}
    QPushButton#TaskbarBtn[active="true"] {{
        color: {ACCENT_ICE};
        border: 1px solid {BORDER_BRIGHT};
        border-bottom: 2px solid {ACCENT_CYAN};
        background-color: {BG_SELECTED};
    }}
    QLabel#ClockLabel {{
        color: {ACCENT_ICE};
        font-size: {FONT_SIZE_SM}px;
        font-family: {FONT_MONO};
        padding: 0 {SPACING_LG}px 0 {SPACING_SM}px;
    }}
    QWidget#TbSep {{
        background-color: {BORDER_DIM};
    }}
"""

# ── Window ────────────────────────────────────────────────────
WINDOW_STYLE = f"""
    QWidget#OSWindow {{
        background-color: {BG_WINDOW};
        border: 1px solid {BORDER_DIM};
        border-radius: {RADIUS_LG}px;
    }}
    QWidget#OSWindow[focused="true"] {{
        border: 1px solid {ACCENT_GREEN};
    }}
    QWidget#TitleBar {{
        background-color: {BG_TITLEBAR};
        border-bottom: 1px solid {BORDER_DIM};
        border-top-left-radius:  {RADIUS_LG}px;
        border-top-right-radius: {RADIUS_LG}px;
    }}
    QWidget#TitleBar[focused="true"] {{
        background-color: {BG_TITLEBAR_ACTIVE};
        border-bottom: 1px solid {ACCENT_GREEN};
    }}
    QLabel#TitleLabel {{
        color: {TEXT_PRIMARY};
        font-size: {FONT_SIZE_MD}px;
        font-family: {FONT_MONO};
        padding-left: {SPACING_SM}px;
        background: transparent;
    }}
    QPushButton#BtnClose {{
        background-color: {ACCENT_RED};
        border: none;
        border-radius: {RADIUS_MD}px;
        min-width: 12px; max-width: 12px;
        min-height: 12px; max-height: 12px;
        margin: 2px;
    }}
    QPushButton#BtnClose:hover  {{ background-color: #ff8087; }}
    QPushButton#BtnMinimize {{
        background-color: {ACCENT_AMBER};
        border: none;
        border-radius: {RADIUS_MD}px;
        min-width: 12px; max-width: 12px;
        min-height: 12px; max-height: 12px;
        margin: 2px;
    }}
    QPushButton#BtnMinimize:hover {{ background-color: #ffd287; }}
    QPushButton#BtnMaximize {{
        background-color: {ACCENT_GREEN};
        border: none;
        border-radius: {RADIUS_MD}px;
        min-width: 12px; max-width: 12px;
        min-height: 12px; max-height: 12px;
        margin: 2px;
    }}
    QPushButton#BtnMaximize:hover {{ background-color: #71ffb6; }}
"""

# ── Desktop icons ─────────────────────────────────────────────
ICON_STYLE = f"""
    QWidget#DesktopIcon {{
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: {RADIUS_LG}px;
    }}
    QWidget#DesktopIcon:hover {{
        background-color: rgba(34, 197, 94, 0.14);
        border: 1px solid rgba(34, 197, 94, 0.5);
    }}
    QLabel#IconEmoji {{
        font-size: 30px;
        background: transparent;
    }}
    QLabel#IconLabel {{
        color: {TEXT_PRIMARY};
        font-size: {FONT_SIZE_XS}px;
        font-family: {FONT_MONO};
        background: transparent;
    }}
"""
ICON_STYLE_HOVER = f"""
    QWidget#DesktopIcon {{
        background-color: rgba(34, 197, 94, 0.18);
        border: 1px solid {ACCENT_GREEN};
        border-radius: {RADIUS_LG}px;
    }}
    QLabel#IconEmoji {{ font-size: 30px; background: transparent; }}
    QLabel#IconLabel {{
        color: {ACCENT_GREEN};
        font-size: {FONT_SIZE_XS}px;
        font-family: {FONT_MONO};
        background: transparent;
    }}
"""
ICON_STYLE_PRESSED = f"""
    QWidget#DesktopIcon {{
        background-color: rgba(34, 197, 94, 0.28);
        border: 1px solid {ACCENT_GREEN};
        border-radius: {RADIUS_LG}px;
    }}
    QLabel#IconEmoji {{ font-size: 30px; background: transparent; }}
    QLabel#IconLabel {{
        color: {ACCENT_GREEN};
        font-size: {FONT_SIZE_XS}px;
        font-family: {FONT_MONO};
        background: transparent;
    }}
"""

# ── Desktop ───────────────────────────────────────────────────
DESKTOP_STYLE = f"""
    QWidget#Desktop {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0   {DESKTOP_GRADIENT_START},
            stop:0.5 {DESKTOP_GRADIENT_MID},
            stop:1   {DESKTOP_GRADIENT_END}
        );
    }}
"""

# ── Context menu ──────────────────────────────────────────────
CONTEXT_MENU_STYLE = f"""
    QMenu {{
        background-color: {BG_PANEL};
        border: 1px solid {BORDER_BRIGHT};
        border-radius: {RADIUS_LG}px;
        padding: {SPACING_XS}px;
        color: {TEXT_PRIMARY};
        font-size: {FONT_SIZE_MD}px;
        font-family: {FONT_MONO};
    }}
    QMenu::item {{
        padding: 6px 20px 6px {SPACING_MD}px;
        border-radius: {RADIUS_SM}px;
    }}
    QMenu::item:selected {{
        background-color: {BG_SELECTED};
        color: {ACCENT_ICE};
    }}
    QMenu::separator {{
        height: 1px;
        background: {BORDER_DIM};
        margin: {SPACING_XS}px {SPACING_SM}px;
    }}
"""

# ── Alt-Tab overlay ───────────────────────────────────────────
ALT_TAB_STYLE = f"""
    QWidget#AltTabOverlay {{
        background-color: rgba(9, 17, 38, 238);
        border: 1px solid {BORDER_BRIGHT};
        border-radius: {RADIUS_XL}px;
    }}
    QPushButton#AltTabItem {{
        background-color: transparent;
        color: {TEXT_DIM};
        border: 1px solid transparent;
        border-radius: {RADIUS_LG}px;
        padding: {SPACING_MD}px {SPACING_LG}px;
        font-size: 22px;
        font-family: {FONT_MONO};
    }}
    QPushButton#AltTabItem:hover {{
        background-color: {BG_HOVER};
        border: 1px solid {BORDER_DIM};
    }}
    QPushButton#AltTabItem[selected="true"] {{
        background-color: {BG_SELECTED};
        color: {ACCENT_ICE};
        border: 1px solid {BORDER_BRIGHT};
    }}
"""

# ── Terminal ──────────────────────────────────────────────────
TERMINAL_STYLE = f"""
    QWidget#Terminal {{
        background-color: #060a10;
    }}
    QTextEdit#TermOutput {{
        background-color: #060a10;
        color: {ACCENT_GREEN};
        font-family: {FONT_MONO};
        font-size: {FONT_SIZE_LG}px;
        border: none;
        padding: {SPACING_SM}px;
        selection-background-color: {BG_SELECTED};
        line-height: 1.4;
    }}
    QLineEdit#TermInput {{
        background-color: #060a10;
        color: {ACCENT_GREEN};
        font-family: {FONT_MONO};
        font-size: {FONT_SIZE_LG}px;
        border: none;
        border-top: 1px solid {BORDER_DIM};
        padding: 6px {SPACING_SM}px;
        selection-background-color: {BG_SELECTED};
    }}
    QScrollBar:vertical {{
        background: {BG_DARK};
        width: 6px;
        border: none;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER_DIM};
        border-radius: 3px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {ACCENT_STEEL}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""

# ── File Explorer ─────────────────────────────────────────────
FILE_EXPLORER_STYLE = f"""
    QWidget#FileExplorer {{
        background-color: {BG_WINDOW};
    }}
    QWidget#FEToolbar {{
        background: {BG_PANEL};
        border-bottom: 1px solid {BORDER_DIM};
    }}
    QLineEdit#AddrBar {{
        background-color: {BG_DARK};
        color: {ACCENT_ICE};
        font-family: {FONT_MONO};
        font-size: {FONT_SIZE_MD}px;
        border: 1px solid {BORDER_DIM};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XS}px {SPACING_SM}px;
    }}
    QLineEdit#AddrBar:focus {{ border: 1px solid {BORDER_BRIGHT}; }}
    QListWidget#FileList {{
        background-color: {BG_WINDOW};
        color: {TEXT_PRIMARY};
        font-family: {FONT_MONO};
        font-size: {FONT_SIZE_MD}px;
        border: none;
        padding: {SPACING_XS}px;
        outline: none;
    }}
    QListWidget#FileList::item {{
        padding: 5px {SPACING_SM}px;
        border-radius: {RADIUS_SM}px;
    }}
    QListWidget#FileList::item:selected {{
        background-color: {BG_SELECTED};
        color: {ACCENT_ICE};
    }}
    QListWidget#FileList::item:hover {{
        background-color: {BG_HOVER};
    }}
    QPushButton#FEBtn {{
        background-color: transparent;
        color: {TEXT_DIM};
        border: 1px solid {BORDER_DIM};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XS}px {SPACING_SM}px;
        font-size: {FONT_SIZE_SM}px;
        font-family: {FONT_MONO};
        min-width: 28px;
    }}
    QPushButton#FEBtn:hover {{
        background-color: {BG_HOVER};
        color: {TEXT_PRIMARY};
        border-color: {ACCENT_CYAN};
    }}
    QLabel#FEStatus {{
        color: {TEXT_DIM};
        font-size: {FONT_SIZE_XS}px;
        font-family: {FONT_MONO};
        padding: 2px {SPACING_SM}px;
    }}
    QSplitter::handle {{ background-color: {BORDER_DIM}; width: 1px; }}
"""

# ── Start Menu ────────────────────────────────────────────────
START_MENU_STYLE = f"""
    QWidget#StartMenu {{
        background-color: rgba(9, 17, 38, 245);
        border: 1px solid {BORDER_BRIGHT};
        border-radius: {RADIUS_XL + 2}px;
    }}
    QLineEdit#SearchBox {{
        background-color: rgba(4, 9, 19, 220);
        color: {TEXT_PRIMARY};
        font-family: {FONT_MONO};
        font-size: {FONT_SIZE_LG}px;
        border: 1px solid {BORDER_DIM};
        border-radius: {RADIUS_MD}px;
        padding: {SPACING_SM - 2}px {SPACING_MD - 2}px;
    }}
    QLineEdit#SearchBox:focus {{ border: 1px solid {BORDER_BRIGHT}; }}
    QPushButton#AppBtn {{
        background-color: transparent;
        color: {TEXT_PRIMARY};
        border: 1px solid transparent;
        border-radius: {RADIUS_LG}px;
        padding: {SPACING_MD - 2}px {SPACING_MD}px;
        font-size: {FONT_SIZE_SM}px;
        font-family: {FONT_MONO};
        text-align: center;
    }}
    QPushButton#AppBtn:hover {{
        background-color: {BG_HOVER};
        color: {ACCENT_ICE};
        border: 1px solid {BORDER_BRIGHT};
    }}
    QLabel#MenuHeader {{
        color: {TEXT_DIM};
        font-size: {FONT_SIZE_XS}px;
        font-family: {FONT_MONO};
        padding: 2px {SPACING_XS}px;
        letter-spacing: 1px;
    }}
    QPushButton#PowerBtn {{
        background-color: transparent;
        color: {ACCENT_STEEL};
        border: 1px solid {BORDER_DIM};
        border-radius: {RADIUS_MD}px;
        padding: 5px {SPACING_LG - 2}px;
        font-size: {FONT_SIZE_SM}px;
        font-family: {FONT_MONO};
    }}
    QPushButton#PowerBtn:hover {{
        background-color: {BG_HOVER};
        color: {ACCENT_ICE};
        border: 1px solid {BORDER_BRIGHT};
    }}
"""

# ── Lock Screen ───────────────────────────────────────────────
LOCK_SCREEN_STYLE = f"""
    QWidget#LockScreen {{ background-color: rgba(5, 8, 12, 248); }}
    QLabel#LockClock {{
        color: {TEXT_PRIMARY};
        font-size: 56px;
        font-weight: bold;
        font-family: {FONT_MONO};
        background: transparent;
    }}
    QLabel#LockDate {{
        color: {TEXT_DIM};
        font-size: {FONT_SIZE_XL}px;
        font-family: {FONT_MONO};
        background: transparent;
    }}
    QLabel#LockUser {{
        color: {ACCENT_ICE};
        font-size: {FONT_SIZE_LG}px;
        font-family: {FONT_MONO};
        background: transparent;
    }}
    QLineEdit#PinInput {{
        background-color: rgba(9, 17, 29, 230);
        color: {TEXT_PRIMARY};
        font-family: {FONT_MONO};
        font-size: 20px;
        border: 1px solid {BORDER_DIM};
        border-radius: {RADIUS_MD}px;
        padding: {SPACING_MD - 2}px {SPACING_LG}px;
        letter-spacing: 8px;
        min-width: 260px; max-width: 260px;
    }}
    QLineEdit#PinInput:focus {{ border: 1px solid {BORDER_BRIGHT}; }}
    QPushButton#UnlockBtn {{
        background-color: {ACCENT_CYAN};
        color: {BG_DARK};
        border: none;
        border-radius: {RADIUS_MD}px;
        padding: {SPACING_MD - 2}px {SPACING_XL + 8}px;
        font-size: {FONT_SIZE_LG}px;
        font-weight: bold;
        font-family: {FONT_MONO};
        min-width: 260px; max-width: 260px;
    }}
    QPushButton#UnlockBtn:hover {{ background-color: #43e0ff; }}
    QLabel#LockError {{
        color: {ACCENT_RED};
        font-size: {FONT_SIZE_SM}px;
        font-family: {FONT_MONO};
        background: transparent;
    }}
    QLabel#LockHint {{
        color: {TEXT_DIM};
        font-size: {FONT_SIZE_XS}px;
        font-family: {FONT_MONO};
        background: transparent;
    }}
"""

# ── Generic buttons ───────────────────────────────────────────
BUTTON_PRIMARY = f"""
    QPushButton {{
        background: {ACCENT_CYAN};
        color: {BG_DARK};
        border: none;
        border-radius: {RADIUS_MD}px;
        padding: {SPACING_SM}px {SPACING_XL}px;
        font-size: {FONT_SIZE_LG}px;
        font-weight: bold;
        font-family: {FONT_MONO};
    }}
    QPushButton:hover  {{ background: #43e0ff; }}
    QPushButton:pressed {{ background: #0ab6e2; }}
"""
BUTTON_SECONDARY = f"""
    QPushButton {{
        background: {BG_PANEL};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_DIM};
        border-radius: {RADIUS_MD}px;
        padding: {SPACING_SM}px {SPACING_XL}px;
        font-size: {FONT_SIZE_LG}px;
        font-family: {FONT_MONO};
    }}
    QPushButton:hover {{
        background: {BG_HOVER};
        border: 1px solid {BORDER_BRIGHT};
    }}
"""
BUTTON_DANGER = f"""
    QPushButton {{
        background: transparent;
        color: {ACCENT_RED};
        border: 1px solid {ACCENT_RED};
        border-radius: {RADIUS_MD}px;
        padding: {SPACING_SM}px {SPACING_XL}px;
        font-size: {FONT_SIZE_LG}px;
        font-family: {FONT_MONO};
    }}
    QPushButton:hover {{
        background: {ACCENT_RED};
        color: white;
    }}
"""

# ── Misc helpers ──────────────────────────────────────────────
VIGNETTE_STYLE = """
    QLabel#Vignette {
        background: qradialgradient(
            cx:0.5, cy:0.5, radius:0.7,
            stop:0 transparent, stop:0.5 transparent,
            stop:1 rgba(0,0,0,0.55)
        );
    }
"""
PHASE3_ROW_STYLE = f"""
    background: {BG_DARK};
    border-bottom: 1px solid {BORDER_DIM};
    padding: {SPACING_XS}px 0;
"""
