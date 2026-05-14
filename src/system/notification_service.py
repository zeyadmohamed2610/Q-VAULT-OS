import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal
from system.config import get_qvault_home
from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger(__name__)

from dataclasses import dataclass, field
from typing import List, Dict, Optional

class NotificationLevel:
    INFO = "INFO"      # Cyan / Neutral
    WARNING = "WARNING" # Amber / Caution
    DANGER = "DANGER"   # Red / Critical

@dataclass
class NotificationData:
    id: str
    title: str
    message: str
    level: str
    timestamp: float
    time_str: str
    actions: Optional[List[Dict[str, str]]] = field(default_factory=list)

class NotificationService(QObject):
    """
    v1.0 'System Soul' Layer: Persistent Notification Service.
    Handles queuing, deduplication, and JSON history (capped at 200).
    """
    new_notification = pyqtSignal(dict)
    history_updated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._history = []
        self._max_history = 200
        self._db_path = os.path.join(get_qvault_home(), ".config", "notification_history.json")
        self._history_hashes = {}
        
        self._load_history()

    def notify(self, message: str, title: str = "System", level: str = NotificationLevel.INFO, actions: list = None, notif_id: str = None):
        """
        v1.0 Active Feedback API with structured model.
        """
        # Deduplication logic (Don't spam identical critical warnings)
        now = time.time()
        sig = f"{title}:{message}"
        if level in [NotificationLevel.WARNING, NotificationLevel.DANGER] and not notif_id:
            if sig in self._history_hashes and (now - self._history_hashes[sig]) < 30:
                return
        self._history_hashes[sig] = now

        n_id = notif_id if notif_id else f"notif_{int(now * 1000)}"
        
        payload = NotificationData(
            id=n_id,
            title=title,
            message=message,
            level=level,
            timestamp=now,
            time_str=datetime.now().strftime("%H:%M:%S"),
            actions=actions or []
        )

        self._history.append(payload.__dict__)
        
        # Enforce cap
        if len(self._history) > self._max_history:
            self._history.pop(0)

        self._save_history()
        self.new_notification.emit(payload.__dict__)
        EVENT_BUS.emit(SystemEvent.NOTIFICATION_SENT, {"notification": payload}, source="NotificationService")
        self.history_updated.emit()
        
        logger.info(f"Notification Sent: [{level}] {title}")

    def get_history(self):
        return list(reversed(self._history))

    def clear_history(self):
        self._history = []
        self._save_history()
        self.history_updated.emit()

    def _load_history(self):
        try:
            if os.path.exists(self._db_path):
                with open(self._db_path, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load notification history: {e}")
            self._history = []

    def _save_history(self):
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            with open(self._db_path, "w", encoding="utf-8") as f:
                json.dump(self._history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save notification history: {e}")

# Global Singleton Access
NOTIFICATION_SERVICE = NotificationService()
