try:
    import psutil
except ImportError:
    psutil = None

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
import logging

logger = logging.getLogger(__name__)

class CpuService(QObject):
    cpu_updated = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self._update)
        self.timer.start(1000)

    def _update(self):
        if psutil:
            try:
                usage = psutil.cpu_percent()
                self.cpu_updated.emit(int(usage))
            except Exception as e:
                logger.error(f"CpuService error: {e}")
        else:
            self.cpu_updated.emit(0)
