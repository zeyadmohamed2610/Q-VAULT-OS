"""
assets/design_tokens.py — Q-Vault OS Design System
Strict, semantic tokenization of all visual properties.
"""

from typing import Dict, Any

# 1. SEMANTIC COLORS
COLORS = {
    "background": {
        "deep": "#06080d",
        "mid": "#0d1117",
        "surface": "#0a0f19",
        "surface_dark": "#111827",
        "surface_mid": "#1a1a2e",
        "surface_raised": "#1e293b",
        "surface_overlay": "#2a2a3e",
    },
    "text": {
        "primary": "#ffffff",
        "dim": "#9ec0d5",
        "muted": "#888888",
        "disabled": "#555555",
    },
    "border": {
        "muted": "#333333",
        "subtle": "#1a3a5c",
        "glow": "#00e6ff",
    },
    "intent": {
        "primary_glow": "#00e6ff",
        "primary_soft": "#00bcd4",
        "success": "#00ff88",
        "warning": "#ffaa00",
        "error": "#ff3366",
        "error_bright": "#ff0000",
        "error_soft": "#ff6666",
    }
}

# 2. SPACING SCALE (8-point grid)
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "2xl": 32,
    "3xl": 48,
    "4xl": 64
}

# 3. RADIUS (Rounding)
RADIUS = {
    "none": 0,
    "sm": 4,
    "md": 8,
    "lg": 12,
    "xl": 16,
    "pill": 9999
}

# 4. TYPOGRAPHY
TYPOGRAPHY = {
    "font_family": "Inter, Roboto, sans-serif",
    "sizes": {
        "xs": "10px",
        "sm": "12px",
        "md": "14px",
        "lg": "16px",
        "xl": "20px",
        "display": "24px",
    },
    "weights": {
        "regular": "400",
        "medium": "500",
        "bold": "700"
    }
}

# 5. SHADOWS
SHADOWS = {
    "sm": "0px 2px 4px rgba(0,0,0,0.2)",
    "md": "0px 4px 8px rgba(0,0,0,0.3)",
    "lg": "0px 8px 16px rgba(0,0,0,0.4)",
    "glow": "0px 0px 12px rgba(0, 230, 255, 0.4)",
}

# 6. ANIMATIONS
ANIMATIONS = {
    "duration": {
        "fast": "150ms",
        "normal": "300ms",
        "slow": "500ms"
    },
    "easing": {
        "default": "ease-in-out",
        "bounce": "cubic-bezier(0.68, -0.55, 0.265, 1.55)"
    }
}

DESIGN_TOKENS = {
    "COLORS": COLORS,
    "SPACING": SPACING,
    "RADIUS": RADIUS,
    "TYPOGRAPHY": TYPOGRAPHY,
    "SHADOWS": SHADOWS,
    "ANIMATIONS": ANIMATIONS
}
