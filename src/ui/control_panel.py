from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QSlider, QComboBox, QFileDialog, QGroupBox, QMessageBox,
    QCheckBox, QDialog, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
import json

from core.image_processor import ImageProcessor

class ControlPanel(QMainWindow):
    # Signals to request screen alignment from main AppManager
    request_screen_alignment = pyqtSignal(int) # int is number of points (1, 2, 3)
    
    def __init__(self, processor: ImageProcessor):
        super().__init__()
        self.processor = processor
        self.setWindowTitle("Image Overlay Control Panel")
        self.setMinimumSize(400, 600)
        
        # Apply dark theme stylesheet
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QLabel { color: #ffffff; }
            QGroupBox { color: #ffffff; border: 1px solid #555555; margin-top: 1ex; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QPushButton { background-color: #3d3d3d; color: white; padding: 5px; border-radius: 3px; }
            QPushButton:hover { background-color: #505050; }
            QPushButton:pressed { background-color: #2d2d2d; }
            QSlider::groove:horizontal { border: 1px solid #999999; height: 8px; background: #3d3d3d; margin: 2px 0; }
            QSlider::handle:horizontal { background: #5c85d6; border: 1px solid #5c85d6; width: 18px; margin: -2px 0; border-radius: 3px; }
            QComboBox { background-color: #3d3d3d; color: white; border: 1px solid #555555; padding: 1px 18px 1px 3px; }
        """)
        
        # Image Points State
        self.selected_image_points = []
        self.num_points_needed = 0
        self.selecting_image_points = False

        self._init_ui()

    def _init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # --- File Operations ---
        file_group = QGroupBox("File & Image Operations")
        file_layout = QHBoxLayout()
        load_btn = QPushButton("Load Image")
        load_btn.clicked.connect(self.load_image)
        load_proj_btn = QPushButton("Load Project")
        load_proj_btn.clicked.connect(self.load_project)
        save_btn = QPushButton("Save / Export")
        save_btn.clicked.connect(self.save_work)
        clear_btn = QPushButton("Clear Image")
        clear_btn.setStyleSheet("background-color: #662222;") # give it a slight red tint
        clear_btn.clicked.connect(self.clear_image)

        file_layout.addWidget(load_btn)
        file_layout.addWidget(load_proj_btn)
        file_layout.addWidget(save_btn)
        file_layout.addWidget(clear_btn)
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)
        
        # --- Image Preview ---
        self.preview_label = QLabel("No Image Loaded")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        self.preview_label.setStyleSheet("background-color: #1e1e1e; border: 1px solid #555555;")
        self.preview_label.mousePressEvent = self.on_preview_clicked
        main_layout.addWidget(self.preview_label)
        
        # --- Adjustments ---
        adj_group = QGroupBox("Adjustments")
        adj_layout = QVBoxLayout()
        
        # Opacity
        op_layout = QHBoxLayout()
        op_layout.addWidget(QLabel("Opacity"))
        self.op_slider = QSlider(Qt.Orientation.Horizontal)
        self.op_slider.setRange(0, 100)
        self.op_slider.setValue(100)
        self.op_slider.valueChanged.connect(self.on_adjustment_changed)
        op_layout.addWidget(self.op_slider)
        adj_layout.addLayout(op_layout)
        
        # Brightness
        br_layout = QHBoxLayout()
        br_layout.addWidget(QLabel("Brightness"))
        self.br_slider = QSlider(Qt.Orientation.Horizontal)
        self.br_slider.setRange(-100, 100)
        self.br_slider.setValue(0)
        self.br_slider.valueChanged.connect(self.on_adjustment_changed)
        br_layout.addWidget(self.br_slider)
        adj_layout.addLayout(br_layout)
        
        # Contrast
        ct_layout = QHBoxLayout()
        ct_layout.addWidget(QLabel("Contrast"))
        self.ct_slider = QSlider(Qt.Orientation.Horizontal)
        self.ct_slider.setRange(1, 30) # 0.1 to 3.0
        self.ct_slider.setValue(10)
        self.ct_slider.valueChanged.connect(self.on_adjustment_changed)
        ct_layout.addWidget(self.ct_slider)
        adj_layout.addLayout(ct_layout)
        
        # Filter
        fl_layout = QHBoxLayout()
        fl_layout.addWidget(QLabel("Filter"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["None", "Edge", "Grayscale", "Invert"])
        self.filter_combo.currentTextChanged.connect(self.on_adjustment_changed)
        fl_layout.addWidget(self.filter_combo)
        adj_layout.addLayout(fl_layout)
        
        # Color Keying
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("Remove Color"))
        self.key_combo = QComboBox()
        self.key_combo.addItems(["None", "Black", "White"])
        self.key_combo.currentTextChanged.connect(self.on_adjustment_changed)
        key_layout.addWidget(self.key_combo)
        
        self.key_tol_slider = QSlider(Qt.Orientation.Horizontal)
        self.key_tol_slider.setRange(0, 255)
        self.key_tol_slider.setValue(10)
        self.key_tol_slider.setToolTip("Tolerance")
        self.key_tol_slider.valueChanged.connect(self.on_adjustment_changed)
        key_layout.addWidget(self.key_tol_slider)
        adj_layout.addLayout(key_layout)

        adj_group.setLayout(adj_layout)
        main_layout.addWidget(adj_group)
        
        # --- Manual Transform ---
        transform_group = QGroupBox("Manual Transform")
        transform_layout = QVBoxLayout()
        
        # X Offset
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("X Offset"))
        self.x_slider = QSlider(Qt.Orientation.Horizontal)
        self.x_slider.setRange(-1000, 1000)
        self.x_slider.setValue(0)
        self.x_slider.valueChanged.connect(self.on_transform_changed)
        x_layout.addWidget(self.x_slider)
        transform_layout.addLayout(x_layout)

        # Y Offset
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Y Offset"))
        self.y_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_slider.setRange(-1000, 1000)
        self.y_slider.setValue(0)
        self.y_slider.valueChanged.connect(self.on_transform_changed)
        y_layout.addWidget(self.y_slider)
        transform_layout.addLayout(y_layout)

        # Scale
        s_layout = QHBoxLayout()
        s_layout.addWidget(QLabel("Scale"))
        self.s_slider = QSlider(Qt.Orientation.Horizontal)
        self.s_slider.setRange(10, 300) # 0.1x to 3.0x
        self.s_slider.setValue(100)
        self.s_slider.valueChanged.connect(self.on_transform_changed)
        s_layout.addWidget(self.s_slider)
        transform_layout.addLayout(s_layout)

        # Rotation
        r_layout = QHBoxLayout()
        r_layout.addWidget(QLabel("Rotation"))
        self.r_slider = QSlider(Qt.Orientation.Horizontal)
        self.r_slider.setRange(-180, 180)
        self.r_slider.setValue(0)
        self.r_slider.valueChanged.connect(self.on_transform_changed)
        r_layout.addWidget(self.r_slider)
        transform_layout.addLayout(r_layout)

        nudge_lbl = QLabel("Tip: You can use Arrow Keys to nudge X/Y while this window is focused. Shift+Up/Down for Scale. Ctrl+Left/Right for Rotation.")
        nudge_lbl.setWordWrap(True)
        nudge_lbl.setStyleSheet("color: #888888; font-size: 10px;")
        transform_layout.addWidget(nudge_lbl)

        transform_group.setLayout(transform_layout)
        main_layout.addWidget(transform_group)
        
        # Ensure focus so keyPress works
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # --- Tools ---
        tools_group = QGroupBox("Helpers")
        tools_layout = QHBoxLayout()
        
        self.crosshair_cb = QCheckBox("Show Center Crosshair")
        self.crosshair_cb.stateChanged.connect(self.on_tools_changed)
        tools_layout.addWidget(self.crosshair_cb)
        
        self.grid_cb = QCheckBox("Show 50px Grid")
        self.grid_cb.stateChanged.connect(self.on_tools_changed)
        tools_layout.addWidget(self.grid_cb)
        
        tools_group.setLayout(tools_layout)
        main_layout.addWidget(tools_group)

        # --- Alignment Tools ---
        align_group = QGroupBox("Alignment")
        align_layout = QVBoxLayout()
        
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Method:"))
        self.align_mode_combo = QComboBox()
        self.align_mode_combo.addItems(["1-Point", "2-Point", "3-Point"])
        mode_layout.addWidget(self.align_mode_combo)
        align_layout.addLayout(mode_layout)
        
        self.info_label = QLabel("Ready.")
        self.info_label.setWordWrap(True)
        align_layout.addWidget(self.info_label)
        
        self.start_align_btn = QPushButton("Start Alignment Process")
        self.start_align_btn.clicked.connect(self.start_alignment_process)
        align_layout.addWidget(self.start_align_btn)
        
        align_group.setLayout(align_layout)
        main_layout.addWidget(align_group)

        # --- App Actions ---
        app_actions_layout = QHBoxLayout()
        help_btn = QPushButton("Help / Instructions")
        help_btn.setStyleSheet("background-color: #005A9E; font-weight: bold;")
        help_btn.clicked.connect(self.show_help)
        exit_btn = QPushButton("Exit App")
        exit_btn.setStyleSheet("background-color: #8b0000; font-weight: bold;")
        exit_btn.clicked.connect(self.exit_app)
        app_actions_layout.addWidget(help_btn)
        app_actions_layout.addStretch()
        app_actions_layout.addWidget(exit_btn)
        main_layout.addLayout(app_actions_layout)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
    def load_image(self, file_path=None):
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.jpeg *.tif *.tiff)")
        
        if file_path:
            if self.processor.load_image(file_path):
                self.current_image_path = file_path
                self.update_preview()
                self.info_label.setText("Image loaded.")
                # We need to trigger an update to the overlay
                self.on_adjustment_changed()
            else:
                QMessageBox.critical(self, "Error", "Failed to load image.")

    def clear_image(self):
        """Clears the loaded image from the processor and UI."""
        self.processor.clear_image()
        self.current_image_path = None
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText("No Image Loaded")
        self.info_label.setText("Image cleared.")

        # Reset sliders to default without triggering update signals for each
        self.x_slider.blockSignals(True)
        self.y_slider.blockSignals(True)
        self.s_slider.blockSignals(True)
        self.r_slider.blockSignals(True)

        self.x_slider.setValue(0)
        self.y_slider.setValue(0)
        self.s_slider.setValue(100)
        self.r_slider.setValue(0)

        self.x_slider.blockSignals(False)
        self.y_slider.blockSignals(False)
        self.s_slider.blockSignals(False)
        self.r_slider.blockSignals(False)

        self.request_overlay_update()

    def exit_app(self):
        """Sends a quit signal to the main application."""
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

    def show_help(self):
        """Displays a detailed help and instructions dialog."""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Help & Instructions")
        help_dialog.setMinimumSize(500, 600)

        layout = QVBoxLayout(help_dialog)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        instructions = QLabel(
            "<h2>Image Overlay Workflow & Instructions</h2>"
            "<p>Welcome to the Image Overlay application! This tool allows you to overlay images on your screen and perfectly align them using alignment points, manual transformations, and visual adjustments.</p>"

            "<h3>1. Load an Image</h3>"
            "<p>Click <b>Load Image</b> to choose an image (PNG, JPG, TIFF) you wish to overlay on your screen.</p>"

            "<h3>2. Visual Adjustments</h3>"
            "<ul>"
            "<li><b>Opacity:</b> Adjust the transparency of the overlay image.</li>"
            "<li><b>Brightness & Contrast:</b> Fine-tune how the image looks.</li>"
            "<li><b>Filter:</b> Apply Edge detection or Grayscale. Edge detection is highly recommended for tracing workflows!</li>"
            "<li><b>Remove Color:</b> Easily remove pure white or black backgrounds using the tolerance slider.</li>"
            "</ul>"

            "<h3>3. Aligning the Image to the Screen</h3>"
            "<p>The core feature of this app is aligning an image to specific points on your screen.</p>"
            "<ol>"
            "<li>Under <b>Alignment</b>, select a Method (1-Point, 2-Point, or 3-Point alignment).</li>"
            "<li>Click <b>Start Alignment Process</b>.</li>"
            "<li>Click the required number of points on the <b>Image Preview</b> above.</li>"
            "<li>Once you finish clicking on the image preview, a large crosshair will appear on your screen.</li>"
            "<li>Click the matching points on your <b>actual screen</b>. The image will automatically warp, rotate, and scale to match your screen points!</li>"
            "</ol>"

            "<h3>4. Manual Adjustments & Nudging</h3>"
            "<p>After alignment (or instead of it), you can manually tweak the position using the <b>Manual Transform</b> sliders.</p>"
            "<p><b>Pro-tip:</b> Click anywhere inside the Control Panel so it has focus, then use your keyboard:</p>"
            "<ul>"
            "<li><b>Arrow Keys:</b> Nudge X and Y position.</li>"
            "<li><b>Shift + Up/Down:</b> Nudge Scale.</li>"
            "<li><b>Ctrl + Left/Right:</b> Nudge Rotation.</li>"
            "</ul>"

            "<h3>5. Managing Your Workspace</h3>"
            "<ul>"
            "<li><b>Clear Image:</b> Removes the active image from the overlay.</li>"
            "<li><b>Save / Export:</b> Save your current adjustments and alignments as a Project file to resume later, or Export the warped image as a PNG.</li>"
            "</ul>"

            "<h3>6. Hotkeys</h3>"
            "<ul>"
            "<li><b>Ctrl+Shift+O:</b> Show this Control Panel.</li>"
            "<li><b>Ctrl+Shift+L:</b> Toggle overlay lock (makes the overlay ignore mouse clicks so you can click through it).</li>"
            "<li><b>Ctrl+Shift+H:</b> Toggle overlay visibility (hide/show).</li>"
            "</ul>"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("font-size: 14px; line-height: 1.5;")

        content_layout.addWidget(instructions)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(help_dialog.accept)
        layout.addWidget(close_btn)

        help_dialog.exec()

    def on_tools_changed(self):
        self.processor.set_overlay_tools(self.crosshair_cb.isChecked(), self.grid_cb.isChecked())
        self.request_overlay_update()

    def on_transform_changed(self):
        x = self.x_slider.value()
        y = self.y_slider.value()
        scale = self.s_slider.value() / 100.0
        rot = self.r_slider.value()
        self.processor.set_manual_transform(x, y, scale, rot)
        self.request_overlay_update()

    def keyPressEvent(self, event):
        # Keyboard Nudging
        if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            if event.key() == Qt.Key.Key_Up:
                self.s_slider.setValue(self.s_slider.value() + 1)
            elif event.key() == Qt.Key.Key_Down:
                self.s_slider.setValue(self.s_slider.value() - 1)
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Left:
                self.r_slider.setValue(self.r_slider.value() - 1)
            elif event.key() == Qt.Key.Key_Right:
                self.r_slider.setValue(self.r_slider.value() + 1)
        else:
            # No modifiers: X/Y Nudging
            if event.key() == Qt.Key.Key_Left:
                self.x_slider.setValue(self.x_slider.value() - 1)
            elif event.key() == Qt.Key.Key_Right:
                self.x_slider.setValue(self.x_slider.value() + 1)
            elif event.key() == Qt.Key.Key_Up:
                self.y_slider.setValue(self.y_slider.value() - 1)
            elif event.key() == Qt.Key.Key_Down:
                self.y_slider.setValue(self.y_slider.value() + 1)
                
        super().keyPressEvent(event)

    def on_adjustment_changed(self):
        # Update processor state
        self.processor.set_opacity(self.op_slider.value() / 100.0)
        self.processor.set_brightness(self.br_slider.value())
        self.processor.set_contrast(self.ct_slider.value() / 10.0)
        self.processor.set_filter(self.filter_combo.currentText())
        
        key_mode = self.key_combo.currentText()
        if key_mode == "Black":
            self.processor.set_color_key((0, 0, 0), self.key_tol_slider.value())
        elif key_mode == "White":
            self.processor.set_color_key((255, 255, 255), self.key_tol_slider.value())
        else:
            self.processor.set_color_key(None, 0)
        
        self.update_preview()
        
        # The main AppManager handles pushing the processed image to the overlay
        # We need a signal for that. Let's emit a custom signal if needed, 
        # or have AppManager connect to these sliders. 
        # Since we passed processor by reference, it's updated. 
        # We just need to tell AppManager to refresh.
        self.request_overlay_update()

    def request_overlay_update(self):
        # We will handle this connection in AppManager
        if hasattr(self, 'update_callback'):
            self.update_callback()

    def update_preview(self):
        qimg = self.processor.get_preview_qimage()
        if qimg:
            pixmap = QPixmap.fromImage(qimg)
            # Scale pixmap to fit label while keeping aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.preview_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)

    def start_alignment_process(self):
        mode_text = self.align_mode_combo.currentText()
        self.num_points_needed = int(mode_text[0])
        self.selected_image_points = []
        self.selecting_image_points = True
        self.info_label.setText(f"Click {self.num_points_needed} point(s) on the image preview above.")
        self.start_align_btn.setEnabled(False)

    def on_preview_clicked(self, event):
        if not self.selecting_image_points or self.processor.current_image is None:
            return
            
        # Map label coordinates to original image coordinates
        pixmap = self.preview_label.pixmap()
        if not pixmap:
            return
            
        # Calculate offsets if the pixmap is centered and letterboxed
        label_w = self.preview_label.width()
        label_h = self.preview_label.height()
        pix_w = pixmap.width()
        pix_h = pixmap.height()
        
        offset_x = (label_w - pix_w) / 2
        offset_y = (label_h - pix_h) / 2
        
        x = event.pos().x() - offset_x
        y = event.pos().y() - offset_y
        
        if 0 <= x <= pix_w and 0 <= y <= pix_h:
            # Scale coordinates back to actual image size
            actual_w = self.processor.current_image.shape[1]
            actual_h = self.processor.current_image.shape[0]
            
            img_x = int((x / pix_w) * actual_w)
            img_y = int((y / pix_h) * actual_h)
            
            self.selected_image_points.append((img_x, img_y))
            
            pts_left = self.num_points_needed - len(self.selected_image_points)
            if pts_left > 0:
                self.info_label.setText(f"Point recorded. Select {pts_left} more point(s) on the preview.")
            else:
                self.selecting_image_points = False
                self.info_label.setText("Image points selected. Prepare to click on the screen.")
                self.start_align_btn.setEnabled(True)
                # Emit signal to AppManager to start screen capture
                self.request_screen_alignment.emit(self.num_points_needed)

    def save_work(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Save")
        msg_box.setText("What would you like to save?")
        btn_project = msg_box.addButton("Save Project Settings", QMessageBox.ButtonRole.ActionRole)
        btn_export = msg_box.addButton("Export Warped Image", QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton(QMessageBox.StandardButton.Cancel)
        msg_box.exec()
        
        clicked_button = msg_box.clickedButton()
        if clicked_button == btn_project:
            self.save_project()
        elif clicked_button == btn_export:
            self.export_image()

    def save_project(self):
        if not hasattr(self, 'current_image_path') or not self.current_image_path:
            QMessageBox.warning(self, "Error", "No image loaded to save.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "JSON Files (*.json)")
        if file_name:
            data = {
                "image_path": self.current_image_path,
                "brightness": self.processor.brightness,
                "contrast": self.processor.contrast,
                "opacity": self.processor.opacity,
                "filter": self.processor.filter_mode,
                "transform": self.processor.transform_matrix.tolist(),
                "manual_x": self.x_slider.value(),
                "manual_y": self.y_slider.value(),
                "manual_scale": self.s_slider.value(),
                "manual_rot": self.r_slider.value(),
            }
            try:
                with open(file_name, 'w') as f:
                    json.dump(data, f)
                QMessageBox.information(self, "Success", "Project saved.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project: {e}")

    def load_project(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Project", "", "JSON Files (*.json)")
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    data = json.load(f)
                
                # Load image
                if 'image_path' in data:
                    self.load_image(data['image_path'])
                else:
                    raise Exception("Invalid project file: missing image_path")

                # Set UI adjustments
                # Temporarily block signals to avoid multiple updates
                self.op_slider.blockSignals(True)
                self.br_slider.blockSignals(True)
                self.ct_slider.blockSignals(True)
                self.filter_combo.blockSignals(True)
                self.x_slider.blockSignals(True)
                self.y_slider.blockSignals(True)
                self.s_slider.blockSignals(True)
                self.r_slider.blockSignals(True)

                self.op_slider.setValue(int(data.get('opacity', 1.0) * 100))
                self.br_slider.setValue(int(data.get('brightness', 0)))
                self.ct_slider.setValue(int(data.get('contrast', 1.0) * 10))
                self.filter_combo.setCurrentText(data.get('filter', 'None'))
                
                self.x_slider.setValue(data.get('manual_x', 0))
                self.y_slider.setValue(data.get('manual_y', 0))
                self.s_slider.setValue(data.get('manual_scale', 100))
                self.r_slider.setValue(data.get('manual_rot', 0))

                self.op_slider.blockSignals(False)
                self.br_slider.blockSignals(False)
                self.ct_slider.blockSignals(False)
                self.filter_combo.blockSignals(False)
                self.x_slider.blockSignals(False)
                self.y_slider.blockSignals(False)
                self.s_slider.blockSignals(False)
                self.r_slider.blockSignals(False)

                # Set processor state
                import numpy as np
                if 'transform' in data:
                    self.processor.transform_matrix = np.array(data['transform'])
                
                self.on_adjustment_changed()
                self.on_transform_changed()
                self.info_label.setText("Project loaded successfully.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load project: {e}")

    def export_image(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Export Image", "", "PNG Files (*.png)")
        if file_name:
            if self.processor.save_image(file_name):
                QMessageBox.information(self, "Success", "Image exported successfully.")
            else:
                QMessageBox.warning(self, "Error", "Could not export image.")
