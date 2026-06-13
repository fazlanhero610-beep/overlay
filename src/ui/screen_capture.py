from PyQt6.QtWidgets import QWidget, QLabel, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QPixmap

class ScreenCaptureWindow(QWidget):
    points_selected = pyqtSignal(list) # Emits list of (x,y) tuples
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        # We don't want to be fully transparent for mouse, we need to catch clicks
        # But we do want to be translucent so the user sees the screen
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Dimming color
        self.bg_color = QColor(0, 0, 0, 100) # Slightly dark, semi-transparent
        
        self.num_points_needed = 0
        self.selected_points = []
        
        # Simple instructions
        self.label = QLabel("Click on the screen", self)
        self.label.setStyleSheet("color: white; font-size: 24px; font-weight: bold; background: rgba(0,0,0,150); padding: 10px;")
        self.label.adjustSize()
        
        self.mouse_pos = None
        self.setMouseTracking(True)
        
        # Timer to update loupe
        self.loupe_timer = QTimer(self)
        self.loupe_timer.timeout.connect(self.update)
        
    def start_capture(self, num_points):
        # Determine total screen geometry across all monitors
        # In a multi-monitor setup, this needs to cover everything
        screen = self.screen()
        geom = screen.virtualGeometry()
        self.setGeometry(geom)
        
        self.num_points_needed = num_points
        self.selected_points = []
        
        self.update_label_text()
        self.label.move(geom.width() // 2 - self.label.width() // 2, 50)
        
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.show()
        self.raise_()
        self.activateWindow()
        self.loupe_timer.start(30) # ~30fps loupe update

    def update_label_text(self):
        pts_left = self.num_points_needed - len(self.selected_points)
        self.label.setText(f"Click on the screen. {pts_left} point(s) remaining. Press ESC to cancel.")
        self.label.adjustSize()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.bg_color)
        
        # Draw selected points
        painter.setBrush(QColor(255, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        for pt in self.selected_points:
            painter.drawEllipse(pt[0] - 5, pt[1] - 5, 10, 10)

        # Draw Loupe
        if self.mouse_pos is not None:
            mx, my = self.mouse_pos.x(), self.mouse_pos.y()
            loupe_size = 150
            zoom = 4
            
            # Grab screen under mouse
            screen = QApplication.primaryScreen()
            if screen:
                # Capture area around mouse
                capture_size = loupe_size // zoom
                rect = Qt.QRect(
                    int(mx - capture_size // 2), 
                    int(my - capture_size // 2), 
                    capture_size, 
                    capture_size
                )
                pixmap = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
                
                if not pixmap.isNull():
                    scaled = pixmap.scaled(loupe_size, loupe_size)
                    
                    # Draw loupe offset from mouse
                    lx = mx + 20
                    ly = my + 20
                    
                    # Prevent going off screen
                    if lx + loupe_size > self.width(): lx = mx - loupe_size - 20
                    if ly + loupe_size > self.height(): ly = my - loupe_size - 20
                    
                    painter.drawPixmap(lx, ly, scaled)
                    
                    # Draw border and crosshair on loupe
                    painter.setPen(QColor(0, 255, 0))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(lx, ly, loupe_size, loupe_size)
                    painter.drawLine(lx + loupe_size//2, ly, lx + loupe_size//2, ly + loupe_size)
                    painter.drawLine(lx, ly + loupe_size//2, lx + loupe_size, ly + loupe_size//2)

    def mouseMoveEvent(self, event):
        self.mouse_pos = event.pos()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            x, y = event.pos().x(), event.pos().y()
            # If multi-monitor, pos() might be relative to widget, but since widget covers virtual geometry, 
            # we need to map to global if we are passing this to image processor that assumes full screen coords.
            # actually event.pos() is relative to the widget top-left.
            # So if widget starts at (0,0), it's fine. 
            self.selected_points.append((x, y))
            self.update() # Trigger paint to show the dot
            
            if len(self.selected_points) >= self.num_points_needed:
                self.loupe_timer.stop()
                self.hide()
                self.points_selected.emit(self.selected_points)
            else:
                self.update_label_text()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.loupe_timer.stop()
            self.hide()
            self.points_selected.emit([]) # Empty list means cancelled
