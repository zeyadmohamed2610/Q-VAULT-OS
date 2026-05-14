from __future__ import annotations
import logging
import heapq
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .memory_manager import MemoryBlock, MemoryManager

logger = logging.getLogger(__name__)

class MemoryAllocator:
    """
    Handles the core allocation and deallocation logic for MemoryManager.
    Separated to reduce the size of the monolithic MemoryManager class.
    """

    @staticmethod
    def find_free_block(manager: 'MemoryManager', size: int) -> Optional[int]:
        """
        Return the *index* into manager._blocks of the chosen free block,
        or None if no suitable block exists.
        """
        from .memory_manager import POLICY_FIRST_FIT, POLICY_BEST_FIT, POLICY_WORST_FIT
        
        candidates = [
            (i, blk) for i, blk in enumerate(manager._blocks)
            if blk.is_free and blk.size >= size
        ]
        if not candidates:
            return None

        if manager.policy == POLICY_FIRST_FIT:
            return candidates[0][0]
        elif manager.policy == POLICY_BEST_FIT:
            return min(candidates, key=lambda x: x[1].size)[0]
        elif manager.policy == POLICY_WORST_FIT:
            return max(candidates, key=lambda x: x[1].size)[0]

        return candidates[0][0]

    @staticmethod
    def coalesce(blocks: List['MemoryBlock']) -> None:
        """
        Merge adjacent free blocks into single larger ones.
        Optimized in-place merging.
        """
        from .memory_manager import MemoryBlock
        
        if len(blocks) < 2:
            return

        i = 0
        while i < len(blocks) - 1:
            curr = blocks[i]
            nxt  = blocks[i + 1]

            if curr.is_free and nxt.is_free:
                blocks[i] = MemoryBlock(
                    start=curr.start,
                    size=curr.size + nxt.size,
                    pid=None,
                    label="free",
                )
                blocks.pop(i + 1)
            else:
                i += 1
