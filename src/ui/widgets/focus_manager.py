class FocusManager:
    """
    Owns the visual focus state for an OSWindow.
    Single Responsibility: Toggle active/inactive styling via Qt dynamic properties.
    """

    def __init__(self, window):
        self._window = window
        self._is_active = False

    @property
    def is_active(self):
        return self._is_active

    def set_active_state(self, is_active: bool):
        """Apply focus styling. Called by WindowManager.focus_window()."""
        if self._is_active == is_active:
            return
        self._is_active = is_active
        w = self._window

        w.setProperty("active", str(is_active).lower())
        w.title_bar.setProperty("active", str(is_active).lower())

        w.style().unpolish(w); w.style().polish(w)
        w.title_bar.style().unpolish(w.title_bar); w.title_bar.style().polish(w.title_bar)
        w.update()
