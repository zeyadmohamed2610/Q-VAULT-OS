"""
components/motion.py
─────────────────────────────────────────────────────────────────────────────
Q-Vault OS Phase 9 — Motion & UX Language Engine

The MotionController translates system state into physical UI animations.
It bridges the logical Trust Engine (Phase 8) with the graphical shell.
─────────────────────────────────────────────────────────────────────────────
"""

from PyQt5.QtCore import QPropertyAnimation, QParallelAnimationGroup, QRect, Qt
from assets import theme

class MotionController:
    """State-aware procedural animation engine using direct Geometry properties."""
    
    @staticmethod
    def spawn_window(window, final_geometry: QRect):
        window.show()
        window.setWindowOpacity(0.0)
        
        # 0.96 scale start
        start_geom = QRect(
            final_geometry.x() + int(final_geometry.width() * 0.02),
            final_geometry.y() + int(final_geometry.height() * 0.02) + 10,
            int(final_geometry.width() * 0.96),
            int(final_geometry.height() * 0.96)
        )
        window.setGeometry(start_geom)
        
        anim_group = QParallelAnimationGroup(window)
        
        opacity_anim = QPropertyAnimation(window, b"windowOpacity")
        opacity_anim.setDuration(theme.MOTION_SMOOTH)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(theme.EASE_OUT)
        
        geom_anim = QPropertyAnimation(window, b"geometry")
        geom_anim.setDuration(theme.MOTION_SMOOTH)
        geom_anim.setStartValue(start_geom)
        geom_anim.setEndValue(final_geometry)
        geom_anim.setEasingCurve(theme.EASE_OUT)
        
        anim_group.addAnimation(opacity_anim)
        anim_group.addAnimation(geom_anim)
        
        window._spawn_anim = anim_group
        anim_group.start()
        return anim_group

    @staticmethod
    def fade_focus(window, active: bool):
        """
        v1.0 Focus Physics: Scale (0.985 -> 1.0) + Opacity (0.92 -> 1.0).
        Uses snappy 150ms transitions.
        """
        if hasattr(window, "_focus_anim") and window._focus_anim.state() == QPropertyAnimation.Running:
            window._focus_anim.stop()
            
        target_opacity = 1.0 if active else 0.92
        target_geom = window.geometry() # Current geometry is baseline
        
        # Calculate subtle scale offset (0.985)
        # We only apply scale if active is FALSE (shrinking it) 
        # or if resetting to TRUE.
        # Actually, let's keep it simple: just animate opacity and we'll handle 
        # the geometric snap in the WM/OSWindow logic to avoid coordinate drift.
        
        group = QParallelAnimationGroup(window)
        
        anim = QPropertyAnimation(window, b"windowOpacity")
        anim.setDuration(theme.MOTION_SNAPPY)
        anim.setStartValue(window.windowOpacity())
        anim.setEndValue(target_opacity)
        anim.setEasingCurve(theme.EASE_OUT)
        
        group.addAnimation(anim)
        window._focus_anim = group
        group.start()
        return group

    @staticmethod
    def quarantine_drop(overlay_frame, final_rect: QRect):
        """
        The signature Quarantine action. Drops the overlay from the top
        with a heavy ease-out indicating system lockdown.
        """
        overlay_frame.show()
        
        # Start above the window height
        start_geom = QRect(
            final_rect.x(),
            final_rect.y() - final_rect.height(),
            final_rect.width(),
            final_rect.height()
        )
        overlay_frame.setGeometry(start_geom)
        
        anim = QPropertyAnimation(overlay_frame, b"geometry")
        anim.setDuration(theme.ANIM_SLOW)
        anim.setStartValue(start_geom)
        anim.setEndValue(final_rect)
        # Bouncing or strong curve
        anim.setEasingCurve(theme.EASE_OUT)
        
        overlay_frame._drop_anim = anim
        anim.start()
    @staticmethod
    def minimize_window(window):
        """Scale down + fade out towards the bottom (simulating taskbar direction)."""
        if hasattr(window, "_min_anim") and window._min_anim.state() == QPropertyAnimation.Running:
            return
        
        # Save geometry for restore
        window._pre_minimize_geom = window.geometry()
        
        # Bypass WM constraint layer during animation
        window._is_applying_geometry = True
        
        group = QParallelAnimationGroup(window)
        
        # Scale down to 0.7
        start_geom = window.geometry()
        target_geom = QRect(
            start_geom.x() + int(start_geom.width() * 0.15),
            start_geom.y() + int(start_geom.height() * 0.8),
            int(start_geom.width() * 0.7),
            int(start_geom.height() * 0.2)
        )
        
        geom_anim = QPropertyAnimation(window, b"geometry")
        geom_anim.setDuration(theme.MOTION_SMOOTH)
        geom_anim.setStartValue(start_geom)
        geom_anim.setEndValue(target_geom)
        geom_anim.setEasingCurve(theme.EASE_OUT)
        
        op_anim = QPropertyAnimation(window, b"windowOpacity")
        op_anim.setDuration(theme.MOTION_SMOOTH)
        op_anim.setStartValue(1.0)
        op_anim.setEndValue(0.0)
        op_anim.setEasingCurve(theme.EASE_OUT)
        
        group.addAnimation(geom_anim)
        group.addAnimation(op_anim)
        
        def _on_minimize_done():
            window._is_applying_geometry = False
            window.hide()
            # Restore original geometry while hidden so it's ready for restore
            if hasattr(window, "_pre_minimize_geom"):
                window._is_applying_geometry = True
                window._internal_set_geometry(window._pre_minimize_geom)
                window._is_applying_geometry = False
        
        group.finished.connect(_on_minimize_done)
        
        window._min_anim = group
        group.start()
        return group

    @staticmethod
    def restore_window(window, target_geometry: QRect):
        """Smooth re-entry from minimized state."""
        # Bypass WM constraint layer during animation
        window._is_applying_geometry = True
        
        window.show()
        window.setWindowOpacity(0.0)
        
        # Start slightly shifted/scaled
        start_geom = QRect(
            target_geometry.x() + int(target_geometry.width() * 0.05),
            target_geometry.y() + 20,
            int(target_geometry.width() * 0.9),
            int(target_geometry.height() * 0.9)
        )
        window._internal_set_geometry(start_geom)
        
        group = QParallelAnimationGroup(window)
        
        op_anim = QPropertyAnimation(window, b"windowOpacity")
        op_anim.setDuration(theme.MOTION_SMOOTH)
        op_anim.setStartValue(0.0)
        op_anim.setEndValue(1.0)
        op_anim.setEasingCurve(theme.EASE_OUT)
        
        geom_anim = QPropertyAnimation(window, b"geometry")
        geom_anim.setDuration(theme.MOTION_SMOOTH)
        geom_anim.setStartValue(start_geom)
        geom_anim.setEndValue(target_geometry)
        geom_anim.setEasingCurve(theme.EASE_OUT)
        
        group.addAnimation(op_anim)
        group.addAnimation(geom_anim)
        
        def _on_restore_done():
            window._is_applying_geometry = False
        
        group.finished.connect(_on_restore_done)
        
        window._restore_anim = group
        group.start()
        return group

    @staticmethod
    def focus_pulse(window):
        """Subtle shadow/highlight pulse for focus confirmation."""
        if hasattr(window, "_pulse_anim") and window._pulse_anim.state() == QPropertyAnimation.Running:
            return
            
        anim = QPropertyAnimation(window, b"windowOpacity")
        anim.setDuration(150)
        anim.setStartValue(1.0)
        anim.setKeyValueAt(0.5, 0.95)
        anim.setEndValue(1.0)
        anim.setEasingCurve(theme.EASE_OUT)
        
        window._pulse_anim = anim
        anim.start()
        return anim
