from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QWheelEvent, QMouseEvent, QPixmap

class ZoomableGraphicsView(QGraphicsView):
    clicked_point = pyqtSignal(int, int) # Emits x, y in original image coordinates

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Panning settings
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(Qt.GlobalColor.black)

        self.current_zoom = 1.0
        self.is_selecting = False

    def set_image(self, qpixmap: QPixmap):
        self.pixmap_item.setPixmap(qpixmap)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())

        # Only fit in view if this is a fresh load (zoom == 1.0 roughly or lower)
        # Actually, let's always fit on first load
        if self.current_zoom == 1.0:
            self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            # update zoom factor tracking
            self.current_zoom = self.transform().m11()

    def set_selecting_mode(self, selecting: bool):
        self.is_selecting = selecting
        if selecting:
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            factor = 1.25
        else:
            factor = 0.8

        self.scale(factor, factor)
        self.current_zoom = self.transform().m11()

    def mousePressEvent(self, event: QMouseEvent):
        if self.is_selecting and event.button() == Qt.MouseButton.LeftButton:
            # Map view coordinates to scene coordinates
            scene_pos = self.mapToScene(event.pos())
            # Map scene coordinates to pixmap item coordinates
            item_pos = self.pixmap_item.mapFromScene(scene_pos)

            # Check if clicked inside the image
            if self.pixmap_item.boundingRect().contains(item_pos):
                self.clicked_point.emit(int(item_pos.x()), int(item_pos.y()))
            return # Don't propagate to base class so we don't start dragging

        super().mousePressEvent(event)
