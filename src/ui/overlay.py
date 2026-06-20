from PyQt6.QtWidgets import QWidget, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QColor, QPalette

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # Configure the window to be borderless, always on top, and allow transparency
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # Prevents it from showing in taskbar
        )
        
        # Make the background of the widget transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Initial size
        self.resize(800, 600)
        
        # Setup image label
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: transparent;")
        
        # Setup close button
        self.close_btn = QPushButton("X", self)
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 0, 0, 150);
                color: white;
                font-weight: bold;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 200);
            }
        """)
        self.close_btn.clicked.connect(self.hide)

        # We start hidden and unlocked
        self.is_locked = False
        
    def resizeEvent(self, event):
        # Ensure image label fills the window
        self.image_label.setGeometry(0, 0, self.width(), self.height())
        # Keep close button in top right
        self.close_btn.move(self.width() - 35, 5)
        super().resizeEvent(event)
        
    def set_image(self, pixmap: QPixmap):
        self.image_label.setPixmap(pixmap)
        # If the pixmap is larger than the window, we might want to resize the window
        if not pixmap.isNull():
            self.resize(pixmap.width(), pixmap.height())

    def toggle_lock(self):
        self.is_locked = not self.is_locked
        self._apply_lock_state()
        return self.is_locked

    def set_lock(self, locked: bool):
        self.is_locked = locked
        self._apply_lock_state()
        
    def _apply_lock_state(self):
        # WA_TransparentForMouseEvents makes the window click-through
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self.is_locked)
        
        # Changing flags in Qt implicitly calls destroy() and create(), hiding the window.
        # We must cache the state before modifying flags and restore it.
        was_visible = self.isVisible()

        if self.is_locked:
            # Add click-through flag
            self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, True)
        else:
            self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, False)
            
        # Re-show to apply flags if we were visible
        if was_visible:
            self.show()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
