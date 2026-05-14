import logging
import time

logger = logging.getLogger(__name__)

class SystemSettings:
    """
    v1.0 Stateful Settings Infrastructure.
    Features Shadow Mode, v1.0 Readiness Tracking, and Professional Silence Calibration.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SystemSettings, cls).__new__(cls)
            cls._instance._dnd = False
            cls._instance._volume = 50
            
            # v1.0 Shadow Mode (Soft Launch)
            cls._instance._shadow_mode = True
            cls._instance._shadow_start_time = time.time()
            cls._instance._v4_ready = False
            
            # v1.0 Debug/Dev Mode
            cls._instance._debug_mode = True  # Enable by default for current dev phase
            
        return cls._instance

    # ── DEBUG MODE ────────────────────────────────────────────────────────────

    def get_debug_mode(self) -> bool:
        return self._debug_mode

    def set_debug_mode(self, enabled: bool):
        logger.info(f"[Settings] DEBUG MODE: {'ENABLED' if enabled else 'DISABLED'}")
        self._debug_mode = enabled

    # ── SHADOW MODE ───────────────────────────────────────────────────────────
    
    def get_shadow_mode(self) -> bool:
        return self._shadow_mode

    def set_shadow_mode(self, enabled: bool):
        logger.info(f"[Settings] SHADOW MODE: {'ENABLED' if enabled else 'DISABLED'}")
        self._shadow_mode = enabled
        if enabled:
            self._shadow_start_time = time.time()

    def get_shadow_elapsed_hours(self) -> float:
        return (time.time() - self._shadow_start_time) / 3600

    def is_v4_ready(self) -> bool:
        """Logic check for 48h + metrics (Mocked for current session)"""
        # In a real system, this would read KPIs from shadow_logs.jsonl
        return self.get_shadow_elapsed_hours() >= 48

    # ── LEGACY DEFAULTS ───────────────────────────────────────────────────────

    def set_dnd(self, enabled: bool):
        logger.info(f"[Settings] DND: {'ENABLED' if enabled else 'DISABLED'}")
        self._dnd = enabled

    def get_dnd(self) -> bool:
        return self._dnd

    def set_volume(self, level: int):
        level = max(0, min(100, level))
        logger.info(f"[Settings] Volume: {level}%")
        self._volume = level

    def get_volume(self) -> int:
        return self._volume

# Singleton
SETTINGS = SystemSettings()
