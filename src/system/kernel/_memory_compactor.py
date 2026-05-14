from __future__ import annotations
import logging
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .memory_manager import MemoryManager, MemoryBlock

logger = logging.getLogger(__name__)

class MemoryCompactor:
    """
    Handles memory compaction (defragmentation) logic.
    """

    @staticmethod
    def compact(manager: 'MemoryManager') -> int:
        """
        Compaction: move all allocated blocks together to eliminate
        external fragmentation. Returns bytes recovered.
        """
        from .memory_manager import MemoryBlock
        from core.event_bus import EVENT_BUS

        allocated = [b for b in manager._blocks if not b.is_free]
        holes     = [b for b in manager._blocks if b.is_free]
        if not holes:
            return 0

        recovered = sum(b.size for b in holes)
        cursor    = 0
        new_blocks = []
        for blk in allocated:
            blk.start = cursor
            cursor    += blk.size
            new_blocks.append(blk)

        if cursor < manager.total_size:
            new_blocks.append(MemoryBlock(
                start=cursor, size=manager.total_size - cursor,
                pid=None, label="free"
            ))

        manager._blocks = new_blocks
        
        try:
            EVENT_BUS.emit("memory.compacted", {"recovered_bytes": recovered})
        except Exception as e:
            logger.debug(f"Failed to emit compaction event: {e}")
            
        logger.info("[MEMORY] Compacted: recovered %d bytes", recovered)
        return recovered
