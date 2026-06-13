import sys
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QStyle
from PyQt6.QtCore import QObject

from core.hotkeys import HotkeyManager
from ui.overlay import OverlayWindow
from ui.control_panel import ControlPanel
from ui.screen_capture import ScreenCaptureWindow
from ui.hotkey_settings import HotkeySettingsDialog, load_hotkey_config, save_hotkey_config
from core.image_processor import ImageProcessor
from PyQt6.QtGui import QPixmap

class AppManager(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        
        # Initialize core
        self.image_processor = ImageProcessor()
        
        # Initialize windows
        self.overlay_window = OverlayWindow()
        self.control_panel = ControlPanel(self.image_processor)
        self.screen_capture = ScreenCaptureWindow()
        
        # Connect signals
        self.control_panel.update_callback = self.update_overlay_image
        self.control_panel.request_screen_alignment.connect(self.start_screen_alignment)
        self.screen_capture.points_selected.connect(self.process_alignment)
        
        self.setup_tray()
        
        # Load hotkeys
        default_hotkeys = {
            'show_control_panel': 'ctrl+alt+o',
            'toggle_lock': 'ctrl+shift+l',
            'toggle_visibility': 'ctrl+shift+h'
        }
        loaded_hotkeys = load_hotkey_config(default_hotkeys)
        
        self.hotkey_manager = HotkeyManager(loaded_hotkeys)
        self.hotkey_manager.show_control_panel_signal.connect(self.show_control_panel)
        self.hotkey_manager.toggle_lock_signal.connect(self.toggle_lock)
        self.hotkey_manager.toggle_visibility_signal.connect(self.toggle_visibility)
        
    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        
        # Create context menu
        self.tray_menu = QMenu()
        
        show_action = self.tray_menu.addAction("Show Control Panel (Ctrl+Alt+O)")
        show_action.triggered.connect(self.show_control_panel)
        
        settings_action = self.tray_menu.addAction("Hotkey Settings...")
        settings_action.triggered.connect(self.show_hotkey_settings)
        
        quit_action = self.tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_app)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()
        
    def show_control_panel(self):
        print("Show Control Panel triggered")
        self.control_panel.show()
        self.control_panel.raise_()
        self.control_panel.activateWindow()

    def start_screen_alignment(self, num_points):
        # We also need to tell the image processor our screen size
        geom = self.screen_capture.screen().virtualGeometry()
        self.image_processor.set_screen_size(geom.width(), geom.height())
        
        self.control_panel.hide()
        self.screen_capture.start_capture(num_points)

    def process_alignment(self, screen_points):
        self.control_panel.show()
        
        if not screen_points:
            self.control_panel.info_label.setText("Alignment cancelled.")
            return
            
        img_points = self.control_panel.selected_image_points
        num = len(screen_points)
        
        if num == 1:
            self.image_processor.calculate_1point_transform(img_points[0], screen_points[0])
        elif num == 2:
            self.image_processor.calculate_2point_transform(img_points, screen_points)
        elif num == 3:
            self.image_processor.calculate_3point_transform(img_points, screen_points)
            
        self.control_panel.info_label.setText("Alignment applied successfully. You can close or hide the control panel.")
        self.update_overlay_image()
        
        # Show overlay if it was hidden
        if not self.overlay_window.isVisible():
            self.overlay_window.show()

    def update_overlay_image(self):
        qimg = self.image_processor.get_warped_qimage()
        if qimg:
            pixmap = QPixmap.fromImage(qimg)
            self.overlay_window.set_image(pixmap)
            
            # Make sure overlay window covers the full virtual geometry so warp affine coords match screen
            if hasattr(self, 'screen_capture'):
                geom = self.screen_capture.screen().virtualGeometry()
                if self.overlay_window.geometry() != geom:
                    self.overlay_window.setGeometry(geom)
        
    def toggle_lock(self):
        print("Toggle Lock triggered")
        if self.overlay_window:
            locked = self.overlay_window.toggle_lock()
            print(f"Overlay locked: {locked}")

    def toggle_visibility(self):
        print("Toggle Visibility triggered")
        if self.overlay_window:
            self.overlay_window.toggle_visibility()
            
    def show_hotkey_settings(self):
        dialog = HotkeySettingsDialog(self.hotkey_manager.hotkeys)
        if dialog.exec():
            # Update and save
            self.hotkey_manager.update_hotkeys(dialog.new_hotkeys)
            save_hotkey_config(self.hotkey_manager.hotkeys)
            
            # Update tray tooltip or actions if needed (optional)
            self.tray_menu.actions()[0].setText(f"Show Control Panel ({self.hotkey_manager.hotkeys['show_control_panel']})")

    def quit_app(self):
        print("Quitting application...")
        if hasattr(self, 'hotkey_manager'):
            self.hotkey_manager.cleanup()
        self.app.quit()
