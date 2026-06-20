from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QSlider, QComboBox, QFileDialog, QGroupBox, QMessageBox,
    QCheckBox, QDialog, QScrollArea, QSplitter, QTabWidget, QColorDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QColor
import json

from core.image_processor import ImageProcessor
from ui.zoomable_view import ZoomableGraphicsView

class ControlPanel(QMainWindow):
    # Signals to request screen alignment from main AppManager
    request_screen_alignment = pyqtSignal(int) # int is number of points (1, 2, 3)
    request_screen_snip = pyqtSignal()
    request_tracking_start = pyqtSignal()
    request_tracking_stop = pyqtSignal()
    
    def __init__(self, processor: ImageProcessor):
        super().__init__()
        self.processor = processor
        self.setWindowTitle("Image Overlay Control Panel")
        self.setMinimumSize(400, 600)
        
        # Apply modern dark theme stylesheet
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #202020; color: #E0E0E0; font-family: 'Segoe UI', Arial, sans-serif; }
            QLabel { color: #E0E0E0; }
            QGroupBox {
                color: #E0E0E0;
                border: 1px solid #3A3A3A;
                border-radius: 6px;
                margin-top: 1.5ex;
                font-weight: bold;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #8AB4F8;
            }
            QPushButton {
                background-color: #383838;
                color: #FFFFFF;
                padding: 6px 12px;
                border: 1px solid #454545;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #484848; border: 1px solid #555555; }
            QPushButton:pressed { background-color: #2D2D2D; }
            QPushButton:disabled { background-color: #252525; color: #666666; border: 1px solid #303030; }
            QSlider::groove:horizontal {
                border: 1px solid #3A3A3A;
                height: 6px;
                background: #151515;
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #8AB4F8;
                border: 1px solid #8AB4F8;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover { background: #A0C4FF; border: 1px solid #A0C4FF; }
            QComboBox {
                background-color: #303030;
                color: #E0E0E0;
                border: 1px solid #454545;
                border-radius: 4px;
                padding: 3px 10px;
            }
            QComboBox::drop-down { border: 0px; }
            QTabWidget::pane { border: 1px solid #3A3A3A; border-radius: 4px; top: -1px; background: #252525; }
            QTabBar::tab {
                background: #2D2D2D;
                color: #AAAAAA;
                border: 1px solid #3A3A3A;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #252525;
                color: #FFFFFF;
                border-bottom-color: #252525;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected { background: #353535; }
            QSplitter::handle { background-color: #3A3A3A; }
            QSplitter::handle:horizontal { width: 2px; }
            QCheckBox { spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #555; border-radius: 3px; background: #303030; }
            QCheckBox::indicator:checked { background: #8AB4F8; border: 1px solid #8AB4F8; }
        """)
        
        # Image Points State
        self.selected_image_points = []
        self.num_points_needed = 0
        self.selecting_image_points = False

        # Debounce timer for adjustments to fix lag
        self.adjustment_timer = QTimer()
        self.adjustment_timer.setSingleShot(True)
        self.adjustment_timer.timeout.connect(self._apply_adjustments)

        self._init_ui()

    def _init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # --- Left Side: Image Preview ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.preview_view = ZoomableGraphicsView()
        self.preview_view.setMinimumHeight(300)
        self.preview_view.setMinimumWidth(300)
        self.preview_view.setStyleSheet("background-color: #1e1e1e; border: 1px solid #555555;")
        self.preview_view.clicked_point.connect(self.on_preview_clicked_point)
        self.preview_view.crop_requested.connect(self.perform_crop)
        left_layout.addWidget(self.preview_view)

        # Add crop button below preview
        crop_btn_layout = QHBoxLayout()
        self.start_crop_btn = QPushButton("Crop Image Tool")
        self.start_crop_btn.clicked.connect(self.toggle_crop_mode)
        self.start_crop_btn.setCheckable(True)
        self.start_crop_btn.setEnabled(False) # Disabled until image loaded
        crop_btn_layout.addStretch()
        crop_btn_layout.addWidget(self.start_crop_btn)
        left_layout.addLayout(crop_btn_layout)

        splitter.addWidget(left_widget)

        # --- Right Side: Controls in Tabs ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Layer Management
        layer_group = QGroupBox("Layers")
        layer_layout = QVBoxLayout(layer_group)
        self.layer_combo = QComboBox()
        self.layer_combo.currentIndexChanged.connect(self.on_layer_changed)

        layer_btn_layout = QHBoxLayout()
        add_layer_btn = QPushButton("Add Layer")
        add_layer_btn.clicked.connect(self.load_image)
        remove_layer_btn = QPushButton("Remove Layer")
        remove_layer_btn.clicked.connect(self.remove_layer)
        layer_btn_layout.addWidget(add_layer_btn)
        layer_btn_layout.addWidget(remove_layer_btn)

        layer_layout.addWidget(self.layer_combo)
        layer_layout.addLayout(layer_btn_layout)
        right_layout.addWidget(layer_group)

        self.tabs = QTabWidget()
        right_layout.addWidget(self.tabs)
        splitter.addWidget(right_widget)

        # Set splitter sizes (give more space to the image)
        splitter.setSizes([600, 300])

        # === Tab 1: File & App ===
        file_tab = QWidget()
        file_tab_layout = QVBoxLayout(file_tab)

        # File Operations Group
        file_group = QGroupBox("File Operations")
        file_group_layout = QVBoxLayout()

        snip_btn = QPushButton("Snip Screen to Load")
        snip_btn.clicked.connect(self.request_screen_snip.emit)
        load_proj_btn = QPushButton("Load Project")
        load_proj_btn.clicked.connect(self.load_project)
        save_btn = QPushButton("Save / Export")
        save_btn.clicked.connect(self.save_work)
        clear_btn = QPushButton("Clear All Layers")
        clear_btn.setStyleSheet("background-color: #662222;") # slight red tint
        clear_btn.clicked.connect(self.clear_all_layers)

        file_group_layout.addWidget(snip_btn)
        file_group_layout.addWidget(load_proj_btn)
        file_group_layout.addWidget(save_btn)
        file_group_layout.addWidget(clear_btn)
        file_group.setLayout(file_group_layout)
        file_tab_layout.addWidget(file_group)

        # App Actions Group
        app_group = QGroupBox("Application Actions")
        app_group_layout = QVBoxLayout()

        self.always_on_top_cb = QCheckBox("Keep Control Panel Always on Top")
        self.always_on_top_cb.stateChanged.connect(self.toggle_always_on_top)

        help_btn = QPushButton("Help / Instructions")
        help_btn.setStyleSheet("background-color: #005A9E; font-weight: bold;")
        help_btn.clicked.connect(self.show_help)
        exit_btn = QPushButton("Exit App")
        exit_btn.setStyleSheet("background-color: #8b0000; font-weight: bold;")
        exit_btn.clicked.connect(self.exit_app)

        app_group_layout.addWidget(self.always_on_top_cb)
        app_group_layout.addWidget(help_btn)
        app_group_layout.addWidget(exit_btn)
        app_group.setLayout(app_group_layout)
        file_tab_layout.addWidget(app_group)

        file_tab_layout.addStretch()
        self.tabs.addTab(file_tab, "File")

        # === Tab 2: Adjustments ===
        adj_tab = QWidget()
        adj_layout = QVBoxLayout(adj_tab)

        # Helper for slider values
        def add_slider_with_label(layout_parent, title, slider, formatter):
            row = QHBoxLayout()
            row.addWidget(QLabel(title))
            row.addWidget(slider)
            val_label = QLabel(formatter(slider.value()))
            val_label.setMinimumWidth(40)
            val_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            slider.valueChanged.connect(lambda v: val_label.setText(formatter(v)))
            row.addWidget(val_label)
            layout_parent.addLayout(row)

        # Opacity
        self.op_slider = QSlider(Qt.Orientation.Horizontal)
        self.op_slider.setRange(0, 100)
        self.op_slider.setValue(100)
        self.op_slider.valueChanged.connect(self.on_adjustment_changed)
        add_slider_with_label(adj_layout, "Opacity", self.op_slider, lambda v: f"{v}%")
        
        # Brightness
        self.br_slider = QSlider(Qt.Orientation.Horizontal)
        self.br_slider.setRange(-100, 100)
        self.br_slider.setValue(0)
        self.br_slider.valueChanged.connect(self.on_adjustment_changed)
        add_slider_with_label(adj_layout, "Brightness", self.br_slider, lambda v: f"{v}")
        
        # Contrast
        self.ct_slider = QSlider(Qt.Orientation.Horizontal)
        self.ct_slider.setRange(1, 30) # 0.1 to 3.0
        self.ct_slider.setValue(10)
        self.ct_slider.valueChanged.connect(self.on_adjustment_changed)
        add_slider_with_label(adj_layout, "Contrast", self.ct_slider, lambda v: f"{v/10.0:.1f}x")
        
        # Filter & Flip
        fl_layout = QHBoxLayout()
        fl_layout.addWidget(QLabel("Filter"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["None", "Edge", "Grayscale", "Invert", "Blur", "Sharpen", "Red Tint", "Green Tint", "Blue Tint"])
        self.filter_combo.currentTextChanged.connect(self.on_adjustment_changed)
        fl_layout.addWidget(self.filter_combo)

        self.flip_h_cb = QCheckBox("Flip H")
        self.flip_v_cb = QCheckBox("Flip V")
        self.flip_h_cb.stateChanged.connect(self.on_adjustment_changed)
        self.flip_v_cb.stateChanged.connect(self.on_adjustment_changed)
        fl_layout.addWidget(self.flip_h_cb)
        fl_layout.addWidget(self.flip_v_cb)

        adj_layout.addLayout(fl_layout)
        
        # Color Keying
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("Remove Color"))
        self.key_combo = QComboBox()
        self.key_combo.addItems(["None", "Black", "White", "Custom..."])
        self.key_combo.setToolTip("Removes a specific color from the image")
        self.key_combo.currentTextChanged.connect(self.on_color_key_combo_changed)
        key_layout.addWidget(self.key_combo)
        
        self.custom_color = None

        self.key_tol_slider = QSlider(Qt.Orientation.Horizontal)
        self.key_tol_slider.setRange(0, 255)
        self.key_tol_slider.setValue(10)
        self.key_tol_slider.setToolTip("Tolerance for color removal")
        self.key_tol_slider.valueChanged.connect(self.on_adjustment_changed)
        key_layout.addWidget(self.key_tol_slider)
        adj_layout.addLayout(key_layout)

        adj_layout.addStretch()
        self.tabs.addTab(adj_tab, "Adjustments")
        
        # === Tab 3: Transform ===
        transform_tab = QWidget()
        transform_layout = QVBoxLayout(transform_tab)
        
        # X Offset
        self.x_slider = QSlider(Qt.Orientation.Horizontal)
        self.x_slider.setRange(-1000, 1000)
        self.x_slider.setValue(0)
        self.x_slider.valueChanged.connect(self.on_transform_changed)
        add_slider_with_label(transform_layout, "X Offset", self.x_slider, lambda v: f"{v}px")

        # Y Offset
        self.y_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_slider.setRange(-1000, 1000)
        self.y_slider.setValue(0)
        self.y_slider.valueChanged.connect(self.on_transform_changed)
        add_slider_with_label(transform_layout, "Y Offset", self.y_slider, lambda v: f"{v}px")

        # Scale
        self.s_slider = QSlider(Qt.Orientation.Horizontal)
        self.s_slider.setRange(10, 300) # 0.1x to 3.0x
        self.s_slider.setValue(100)
        self.s_slider.valueChanged.connect(self.on_transform_changed)
        add_slider_with_label(transform_layout, "Scale", self.s_slider, lambda v: f"{v}%")

        # Rotation
        self.r_slider = QSlider(Qt.Orientation.Horizontal)
        self.r_slider.setRange(-180, 180)
        self.r_slider.setValue(0)
        self.r_slider.valueChanged.connect(self.on_transform_changed)
        add_slider_with_label(transform_layout, "Rotation", self.r_slider, lambda v: f"{v}°")

        nudge_lbl = QLabel("Tip: You can use Arrow Keys to nudge X/Y while this window is focused. Shift+Up/Down for Scale. Ctrl+Left/Right for Rotation.")
        nudge_lbl.setWordWrap(True)
        nudge_lbl.setStyleSheet("color: #888888; font-size: 10px;")
        transform_layout.addWidget(nudge_lbl)

        transform_layout.addStretch()
        self.tabs.addTab(transform_tab, "Transform")
        
        # Ensure focus so keyPress works
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # === Tab 4: Alignment & Tools ===
        align_tab = QWidget()
        align_layout = QVBoxLayout(align_tab)

        # Tools Group
        tools_group = QGroupBox("Helpers")
        tools_layout = QHBoxLayout()
        
        self.crosshair_cb = QCheckBox("Show Center Crosshair")
        self.crosshair_cb.stateChanged.connect(self.on_tools_changed)
        tools_layout.addWidget(self.crosshair_cb)
        
        self.grid_cb = QCheckBox("Show 50px Grid")
        self.grid_cb.stateChanged.connect(self.on_tools_changed)
        tools_layout.addWidget(self.grid_cb)
        
        tools_group.setLayout(tools_layout)
        align_layout.addWidget(tools_group)

        # Alignment Tools Group
        align_group = QGroupBox("Alignment")
        align_group_layout = QVBoxLayout()
        
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Method:"))
        self.align_mode_combo = QComboBox()
        self.align_mode_combo.addItems(["1-Point", "2-Point", "3-Point"])
        mode_layout.addWidget(self.align_mode_combo)
        align_group_layout.addLayout(mode_layout)
        
        self.info_label = QLabel("Ready.")
        self.info_label.setWordWrap(True)
        align_group_layout.addWidget(self.info_label)
        
        self.start_align_btn = QPushButton("Start Alignment Process")
        self.start_align_btn.clicked.connect(self.start_alignment_process)
        align_group_layout.addWidget(self.start_align_btn)

        align_group.setLayout(align_group_layout)
        align_layout.addWidget(align_group)

        # Tracking Group
        track_group = QGroupBox("Live Tracking")
        track_group_layout = QVBoxLayout()

        track_info = QLabel("Draw a box around a distinct feature on your screen. The app will visually track that feature and auto-move your image.")
        track_info.setWordWrap(True)
        track_group_layout.addWidget(track_info)

        btn_layout = QHBoxLayout()
        start_track_btn = QPushButton("Start Live Tracking")
        start_track_btn.clicked.connect(self.request_tracking_start.emit)
        stop_track_btn = QPushButton("Stop Tracking")
        stop_track_btn.clicked.connect(self.request_tracking_stop.emit)

        btn_layout.addWidget(start_track_btn)
        btn_layout.addWidget(stop_track_btn)
        track_group_layout.addLayout(btn_layout)

        track_group.setLayout(track_group_layout)
        align_layout.addWidget(track_group)

        align_layout.addStretch()
        self.tabs.addTab(align_tab, "Alignment")
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Initialize smart disabling state
        self.set_tabs_enabled(False)

    def set_tabs_enabled(self, enabled: bool):
        """Enables or disables tabs that require an image to be loaded."""
        # Tab 0 is File, always enabled. Tab 1, 2, 3 require image
        for i in range(1, self.tabs.count()):
            self.tabs.setTabEnabled(i, enabled)
        self.start_crop_btn.setEnabled(enabled)
        if not enabled:
            self.start_crop_btn.setChecked(False)
            self.preview_view.set_cropping_mode(False)

    def update_layer_combo(self):
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
        for i, layer in enumerate(self.processor.layers):
            self.layer_combo.addItem(f"Layer {i+1}: {layer.name}", userData=i)

        if self.processor.layers:
            self.layer_combo.setCurrentIndex(self.processor.active_layer_idx)
            self.set_tabs_enabled(True)
        else:
            self.set_tabs_enabled(False)
            self.preview_view.scene.clear()
            from PyQt6.QtWidgets import QGraphicsPixmapItem
            self.preview_view.pixmap_item = QGraphicsPixmapItem()
            self.preview_view.scene.addItem(self.preview_view.pixmap_item)

        self.layer_combo.blockSignals(False)

    def on_layer_changed(self, index):
        if index >= 0:
            self.processor.set_active_layer(index)
            self.update_ui_from_active_layer()

    def update_ui_from_active_layer(self):
        layer = self.processor.get_active_layer()
        if not layer:
            return

        self.op_slider.blockSignals(True)
        self.br_slider.blockSignals(True)
        self.ct_slider.blockSignals(True)
        self.filter_combo.blockSignals(True)
        self.flip_h_cb.blockSignals(True)
        self.flip_v_cb.blockSignals(True)
        self.x_slider.blockSignals(True)
        self.y_slider.blockSignals(True)
        self.s_slider.blockSignals(True)
        self.r_slider.blockSignals(True)

        self.op_slider.setValue(int(layer.opacity * 100))
        self.br_slider.setValue(int(layer.brightness))
        self.ct_slider.setValue(int(layer.contrast * 10))
        self.filter_combo.setCurrentText(layer.filter_mode)

        self.flip_h_cb.setChecked(layer.flip_h)
        self.flip_v_cb.setChecked(layer.flip_v)

        self.x_slider.setValue(int(layer.manual_offset_x))
        self.y_slider.setValue(int(layer.manual_offset_y))
        self.s_slider.setValue(int(layer.manual_scale * 100))
        self.r_slider.setValue(int(layer.manual_rotation))

        self.op_slider.blockSignals(False)
        self.br_slider.blockSignals(False)
        self.ct_slider.blockSignals(False)
        self.filter_combo.blockSignals(False)
        self.flip_h_cb.blockSignals(False)
        self.flip_v_cb.blockSignals(False)
        self.x_slider.blockSignals(False)
        self.y_slider.blockSignals(False)
        self.s_slider.blockSignals(False)
        self.r_slider.blockSignals(False)

        self.update_preview()

    def load_image(self, file_path=None):
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.jpeg *.tif *.tiff)")
        
        if file_path:
            if self.processor.add_layer(file_path):
                self.update_layer_combo()
                self.update_ui_from_active_layer()
                self.info_label.setText("Layer added.")
                self.request_overlay_update()
            else:
                QMessageBox.critical(self, "Error", "Failed to load image.")

    def remove_layer(self):
        idx = self.layer_combo.currentIndex()
        if idx >= 0:
            self.processor.remove_layer(idx)
            self.update_layer_combo()
            if self.processor.layers:
                self.update_ui_from_active_layer()
            else:
                self.info_label.setText("No layers remaining.")
            self.request_overlay_update()

    def clear_all_layers(self):
        """Clears all layers from the processor and UI."""
        self.processor.clear_all()
        self.update_layer_combo()
        self.tabs.setCurrentIndex(0) # Go back to File tab

        self.info_label.setText("All layers cleared.")

    def toggle_always_on_top(self, state):
        if state == Qt.CheckState.Checked.value:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
        self.show() # Toggling flags hides the window, need to show again

    def perform_autosave(self):
        """Saves current state to a default autosave.json file."""
        import os
        if not self.processor.layers:
            return

        save_dir = os.path.join(os.path.expanduser("~"), ".overlay_app")
        os.makedirs(save_dir, exist_ok=True)
        autosave_path = os.path.join(save_dir, "autosave.json")
        self._save_project_data(autosave_path, show_msg=False)

    def load_autosave(self):
        """Loads state from default autosave.json file if it exists."""
        import os
        autosave_path = os.path.join(os.path.expanduser("~"), ".overlay_app", "autosave.json")
        if os.path.exists(autosave_path):
            self._load_project_data(autosave_path, show_msg=False)

    def exit_app(self):
        """Sends a quit signal to the main application."""
        self.perform_autosave()
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

    def on_color_key_combo_changed(self, text):
        if text == "Custom...":
            color = QColorDialog.getColor(parent=self, title="Select Color to Remove")
            if color.isValid():
                # Store as BGR for OpenCV
                self.custom_color = (color.blue(), color.green(), color.red())
            else:
                # If they cancelled, go back to None
                self.key_combo.blockSignals(True)
                self.key_combo.setCurrentText("None")
                self.key_combo.blockSignals(False)
                self.custom_color = None
        self.on_adjustment_changed()

    def on_adjustment_changed(self):
        # Start or restart the debounce timer
        self.adjustment_timer.start(50) # 50ms delay

    def _apply_adjustments(self):
        # Update processor state
        self.processor.set_opacity(self.op_slider.value() / 100.0)
        self.processor.set_brightness(self.br_slider.value())
        self.processor.set_contrast(self.ct_slider.value() / 10.0)
        self.processor.set_filter(self.filter_combo.currentText())
        self.processor.set_flip(self.flip_h_cb.isChecked(), self.flip_v_cb.isChecked())
        
        key_mode = self.key_combo.currentText()
        if key_mode == "Black":
            self.processor.set_color_key((0, 0, 0), self.key_tol_slider.value())
        elif key_mode == "White":
            self.processor.set_color_key((255, 255, 255), self.key_tol_slider.value())
        elif key_mode == "Custom..." and self.custom_color is not None:
            self.processor.set_color_key(self.custom_color, self.key_tol_slider.value())
        else:
            self.processor.set_color_key(None, 0)
        
        self.update_preview()
        
        self.request_overlay_update()

    def request_overlay_update(self):
        # We will handle this connection in AppManager
        if hasattr(self, 'update_callback'):
            self.update_callback()

    def update_preview(self):
        qimg = self.processor.get_preview_qimage()
        if qimg:
            pixmap = QPixmap.fromImage(qimg)
            self.preview_view.set_image(pixmap)

    def start_alignment_process(self):
        mode_text = self.align_mode_combo.currentText()
        self.num_points_needed = int(mode_text[0])
        self.selected_image_points = []
        self.selecting_image_points = True
        self.preview_view.set_selecting_mode(True)
        self.info_label.setText(f"Click {self.num_points_needed} point(s) on the image preview above.")
        self.start_align_btn.setEnabled(False)

    def toggle_crop_mode(self, checked):
        if checked:
            self.preview_view.set_cropping_mode(True)
            self.start_crop_btn.setText("Cancel Crop")
        else:
            self.preview_view.set_cropping_mode(False)
            self.start_crop_btn.setText("Crop Image Tool")

    def perform_crop(self, x, y, w, h):
        self.processor.crop_image(x, y, w, h)
        self.start_crop_btn.setChecked(False)
        self.toggle_crop_mode(False)
        self.update_preview()
        self.request_overlay_update()
        self.info_label.setText("Image cropped successfully.")

    def on_preview_clicked_point(self, img_x, img_y):
        if not self.selecting_image_points or self.processor.current_image is None:
            return
            
        self.selected_image_points.append((img_x, img_y))
        
        pts_left = self.num_points_needed - len(self.selected_image_points)
        if pts_left > 0:
            self.info_label.setText(f"Point recorded. Select {pts_left} more point(s) on the preview.")
        else:
            self.selecting_image_points = False
            self.preview_view.set_selecting_mode(False)
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
        if not self.processor.layers:
            QMessageBox.warning(self, "Error", "No layers loaded to save.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "JSON Files (*.json)")
        if file_name:
            self._save_project_data(file_name, show_msg=True)

    def _save_project_data(self, file_name, show_msg=True):
        layers_data = []
        for layer in self.processor.layers:
            layers_data.append({
                "image_path": layer.file_path,
                "name": layer.name,
                "brightness": layer.brightness,
                "contrast": layer.contrast,
                "opacity": layer.opacity,
                "filter": layer.filter_mode,
                "flip_h": layer.flip_h,
                "flip_v": layer.flip_v,
                "transform": layer.transform_matrix.tolist(),
                "manual_x": layer.manual_offset_x,
                "manual_y": layer.manual_offset_y,
                "manual_scale": layer.manual_scale,
                "manual_rot": layer.manual_rotation,
            })

        data = {
            "version": 2,
            "layers": layers_data,
            "active_layer_idx": self.processor.active_layer_idx
        }

        try:
            with open(file_name, 'w') as f:
                json.dump(data, f)
            if show_msg:
                QMessageBox.information(self, "Success", "Project saved.")
        except Exception as e:
            if show_msg:
                QMessageBox.critical(self, "Error", f"Failed to save project: {e}")

    def load_project(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Project", "", "JSON Files (*.json)")
        if file_name:
            self._load_project_data(file_name, show_msg=True)

    def _load_project_data(self, file_name, show_msg=True):
        try:
            with open(file_name, 'r') as f:
                data = json.load(f)

            self.clear_all_layers()

            # Handle version 1 (single image) vs version 2 (layers)
            import numpy as np
            if data.get('version', 1) == 1:
                if 'image_path' in data:
                    self.processor.add_layer(data['image_path'])
                    layer = self.processor.get_active_layer()
                    layer.opacity = data.get('opacity', 1.0)
                    layer.brightness = data.get('brightness', 0)
                    layer.contrast = data.get('contrast', 1.0)
                    layer.filter_mode = data.get('filter', 'None')
                    layer.flip_h = data.get('flip_h', False)
                    layer.flip_v = data.get('flip_v', False)
                    layer.manual_offset_x = data.get('manual_x', 0)
                    layer.manual_offset_y = data.get('manual_y', 0)
                    layer.manual_scale = data.get('manual_scale', 100) / 100.0
                    layer.manual_rotation = data.get('manual_rot', 0)
                    if 'transform' in data:
                        layer.transform_matrix = np.array(data['transform'])
            else:
                for l_data in data.get('layers', []):
                    if 'image_path' in l_data and self.processor.add_layer(l_data['image_path'], name=l_data.get('name')):
                        layer = self.processor.get_active_layer()
                        layer.opacity = l_data.get('opacity', 1.0)
                        layer.brightness = l_data.get('brightness', 0)
                        layer.contrast = l_data.get('contrast', 1.0)
                        layer.filter_mode = l_data.get('filter', 'None')
                        layer.flip_h = l_data.get('flip_h', False)
                        layer.flip_v = l_data.get('flip_v', False)
                        layer.manual_offset_x = l_data.get('manual_x', 0)
                        layer.manual_offset_y = l_data.get('manual_y', 0)
                        layer.manual_scale = l_data.get('manual_scale', 1.0)
                        layer.manual_rotation = l_data.get('manual_rot', 0)
                        if 'transform' in l_data:
                            layer.transform_matrix = np.array(l_data['transform'])
                
                self.processor.set_active_layer(data.get('active_layer_idx', 0))

            self.processor.apply_all_transforms()
            self.update_layer_combo()
            self.update_ui_from_active_layer()
            self.request_overlay_update()

            if show_msg:
                self.info_label.setText("Project loaded successfully.")

        except Exception as e:
            if show_msg:
                QMessageBox.critical(self, "Error", f"Failed to load project: {e}")

    def export_image(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Export Image", "", "PNG Files (*.png)")
        if file_name:
            if self.processor.save_image(file_name):
                QMessageBox.information(self, "Success", "Image exported successfully.")
            else:
                QMessageBox.warning(self, "Error", "Could not export image.")
