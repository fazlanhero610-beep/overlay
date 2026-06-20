import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/src')

from PyQt6.QtWidgets import QApplication
from ui.control_panel import ControlPanel
from core.image_processor import ImageProcessor

app = QApplication(sys.argv)
processor = ImageProcessor()
window = ControlPanel(processor)
print("Successfully imported and instantiated ControlPanel")
