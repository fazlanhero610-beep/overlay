import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

class HotkeyManager(QObject):
    # Signals to be emitted when hotkeys are pressed
    show_control_panel_signal = pyqtSignal()
    toggle_lock_signal = pyqtSignal()
    toggle_visibility_signal = pyqtSignal()
    nudge_up_signal = pyqtSignal()
    nudge_down_signal = pyqtSignal()
    nudge_left_signal = pyqtSignal()
    nudge_right_signal = pyqtSignal()
    opacity_up_signal = pyqtSignal()
    opacity_down_signal = pyqtSignal()

    def __init__(self, hotkey_config=None):
        super().__init__()
        
        # Default hotkeys
        self.hotkeys = {
            'show_control_panel': 'ctrl+shift+o',
            'toggle_lock': 'ctrl+shift+l',
            'toggle_visibility': 'ctrl+shift+h',
            'nudge_up': 'alt+up',
            'nudge_down': 'alt+down',
            'nudge_left': 'alt+left',
            'nudge_right': 'alt+right',
            'opacity_up': 'alt+page up',
            'opacity_down': 'alt+page down'
        }
        
        if hotkey_config:
            self.hotkeys.update(hotkey_config)
            
        self.setup_hotkeys()

    def setup_hotkeys(self):
        self.cleanup() # Unhook any existing before adding
        
        try:
            keyboard.add_hotkey(self.hotkeys['show_control_panel'], self._on_show_control_panel)
            keyboard.add_hotkey(self.hotkeys['toggle_lock'], self._on_toggle_lock)
            keyboard.add_hotkey(self.hotkeys['toggle_visibility'], self._on_toggle_visibility)
            keyboard.add_hotkey(self.hotkeys['nudge_up'], lambda: self.nudge_up_signal.emit())
            keyboard.add_hotkey(self.hotkeys['nudge_down'], lambda: self.nudge_down_signal.emit())
            keyboard.add_hotkey(self.hotkeys['nudge_left'], lambda: self.nudge_left_signal.emit())
            keyboard.add_hotkey(self.hotkeys['nudge_right'], lambda: self.nudge_right_signal.emit())
            keyboard.add_hotkey(self.hotkeys['opacity_up'], lambda: self.opacity_up_signal.emit())
            keyboard.add_hotkey(self.hotkeys['opacity_down'], lambda: self.opacity_down_signal.emit())
            print(f"Hotkeys loaded: {self.hotkeys}")
        except Exception as e:
            print(f"Error setting up hotkeys. Format might be invalid or permissions lacking. {e}")

    def update_hotkeys(self, new_config):
        self.hotkeys.update(new_config)
        self.setup_hotkeys()

    def _on_show_control_panel(self):
        self.show_control_panel_signal.emit()

    def _on_toggle_lock(self):
        self.toggle_lock_signal.emit()

    def _on_toggle_visibility(self):
        self.toggle_visibility_signal.emit()
        
    def cleanup(self):
        try:
            keyboard.unhook_all()
        except:
            pass
