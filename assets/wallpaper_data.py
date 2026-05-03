from dataclasses import dataclass

@dataclass
class Wallpaper:
    name: str
    file: str
    accent_color: str
    secondary_color: str
    brightness: str  # "dark", "light", "medium"

# Wallpaper presets with theme colors
WALLPAPERS = [
    Wallpaper(
        name="Cyber Grid",
        file="wallpaper-high-tech.jpg",
        accent_color="#00ff88",
        secondary_color="#00d4ff",
        brightness="dark",
    ),
    Wallpaper(
        name="Neon City",
        file="wallpaper-futuristic-architecture.jpg",
        accent_color="#ff00ff",
        secondary_color="#00ff88",
        brightness="dark",
    ),
    Wallpaper(
        name="Server Room",
        file="wallpaper-server-room.jpg",
        accent_color="#00d4ff",
        secondary_color="#5f00ff",
        brightness="dark",
    ),
    Wallpaper(
        name="Data Flow",
        file="wallpaper-data-network.jpg",
        accent_color="#00ff88",
        secondary_color="#00d4ff",
        brightness="dark",
    ),
    Wallpaper(
        name="Kali Dark",
        file="",
        accent_color="#00ff88",
        secondary_color="#5f00ff",
        brightness="dark",
    ),
    Wallpaper(
        name="Matrix",
        file="",
        accent_color="#00ff00",
        secondary_color="#003300",
        brightness="dark",
    ),
]

# Transparency system
TRANSPARENCY = {
    "window": 0.92,
    "terminal": 0.90,
    "taskbar": 0.85,
    "menu": 0.95,
    "dialog": 0.95,
}
