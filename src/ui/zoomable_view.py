from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QRubberBand
from PyQt6.QtCore import Qt, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QWheelEvent, QMouseEvent, QPixmap

class ZoomableGraphicsView(QGraphicsView):
    clicked_point = pyqtSignal(int, int) # Emits x, y in original image coordinates
    crop_requested = pyqtSignal(int, int, int, int) # x, y, width, height

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
        self.is_cropping = False

        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.origin = None

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
        self.is_cropping = False
        if selecting:
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def set_cropping_mode(self, cropping: bool):
        self.is_cropping = cropping
        self.is_selecting = False
        if cropping:
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
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_selecting:
                scene_pos = self.mapToScene(event.pos())
                item_pos = self.pixmap_item.mapFromScene(scene_pos)
                if self.pixmap_item.boundingRect().contains(item_pos):
                    self.clicked_point.emit(int(item_pos.x()), int(item_pos.y()))
                return

            if self.is_cropping:
                self.origin = event.pos()
                self.rubber_band.setGeometry(QRect(self.origin, self.origin))
                self.rubber_band.show()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_cropping and self.origin is not None:
            self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.is_cropping and event.button() == Qt.MouseButton.LeftButton and self.origin is not None:
            self.rubber_band.hide()

            # Map view rect to scene to image coords
            view_rect = self.rubber_band.geometry()
            scene_top_left = self.mapToScene(view_rect.topLeft())
            scene_bottom_right = self.mapToScene(view_rect.bottomRight())

            item_top_left = self.pixmap_item.mapFromScene(scene_top_left)
            item_bottom_right = self.pixmap_item.mapFromScene(scene_bottom_right)

            # Clamp to image bounds
            img_rect = self.pixmap_item.boundingRect()

            x1 = max(0, int(item_top_left.x()))
            y1 = max(0, int(item_top_left.y()))
            x2 = min(int(img_rect.width()), int(item_bottom_right.x()))
            y2 = min(int(img_rect.height()), int(item_bottom_right.y()))

            w = x2 - x1
            h = y2 - y1

            if w > 5 and h > 5:
                self.crop_requested.emit(x1, y1, w, h)

            self.origin = None
            return

        super().mouseReleaseEvent(event)
