from PyQt6.QtWidgets import QWidget, QLabel, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPixmap

class ScreenCaptureWindow(QWidget):
    points_selected = pyqtSignal(list) # Emits list of (x,y) tuples
    region_captured = pyqtSignal(QPixmap) # Emits captured region when in snipping mode
    
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
        
        # Snipping mode state
        self.snipping_mode = False
        self.snip_start = QPoint()
        self.snip_current = QPoint()
        self.is_dragging = False

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
        self.snipping_mode = False
        self._setup_window()
        self.num_points_needed = num_points
        self.selected_points = []
        
        self.update_label_text()
        self.label.move(self.width() // 2 - self.label.width() // 2, 50)
        
        self.loupe_timer.start(30) # ~30fps loupe update

    def start_snip(self):
        self.snipping_mode = True
        self._setup_window()
        self.is_dragging = False

        self.label.setText("Click and drag to select a region to capture. Press ESC to cancel.")
        self.label.adjustSize()
        self.label.move(self.width() // 2 - self.label.width() // 2, 50)

        self.loupe_timer.stop() # No loupe in snipping mode

    def _setup_window(self):
        screen = self.screen()
        geom = screen.virtualGeometry()
        self.setGeometry(geom)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.show()
        self.raise_()
        self.activateWindow()

    def update_label_text(self):
        pts_left = self.num_points_needed - len(self.selected_points)
        self.label.setText(f"Click on the screen. {pts_left} point(s) remaining. Press ESC to cancel.")
        self.label.adjustSize()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.bg_color)
        
        if self.snipping_mode:
            if self.is_dragging:
                # Clear the rect area (make it fully transparent so user sees screen)
                rect = QRect(self.snip_start, self.snip_current).normalized()
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                painter.fillRect(rect, Qt.GlobalColor.transparent)

                # Draw border
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                painter.setPen(QColor(0, 255, 0))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(rect)
            return

        # Draw selected points (Alignment mode)
        painter.setBrush(QColor(255, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        for pt in self.selected_points:
            painter.drawEllipse(pt[0] - 5, pt[1] - 5, 10, 10)

        # Draw Loupe
        if self.mouse_pos is not None and not self.snipping_mode:
            mx, my = self.mouse_pos.x(), self.mouse_pos.y()
            loupe_size = 150
            zoom = 4
            
            # Grab screen under mouse
            screen = QApplication.primaryScreen()
            if screen:
                # Capture area around mouse
                capture_size = loupe_size // zoom
                rect = QRect(
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
        if self.snipping_mode and self.is_dragging:
            self.snip_current = event.pos()
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.snipping_mode:
                self.snip_start = event.pos()
                self.snip_current = event.pos()
                self.is_dragging = True
            else:
                x, y = event.pos().x(), event.pos().y()
                self.selected_points.append((x, y))
                self.update() # Trigger paint to show the dot

                if len(self.selected_points) >= self.num_points_needed:
                    self.loupe_timer.stop()
                    self.hide()
                    self.points_selected.emit(self.selected_points)
                else:
                    self.update_label_text()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.snipping_mode and self.is_dragging:
            self.is_dragging = False
            self.snip_current = event.pos()
            
            rect = QRect(self.snip_start, self.snip_current).normalized()
            if rect.width() > 5 and rect.height() > 5:
                # Capture the region
                self.hide() # Hide overlay so we don't capture the overlay UI itself

                # Small delay to ensure hide completes
                QApplication.processEvents()

                screen = QApplication.primaryScreen()
                if screen:
                    pixmap = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
                    self.region_captured.emit(pixmap)
            else:
                self.hide()
                self.region_captured.emit(QPixmap()) # Cancelled/Too small

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.loupe_timer.stop()
            self.hide()
            if self.snipping_mode:
                self.region_captured.emit(QPixmap())
            else:
                self.points_selected.emit([]) # Empty list means cancelled
