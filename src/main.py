import sys
import os

# Add the 'src' directory to the python path so absolute imports work nicely
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QStyle
from PyQt6.QtGui import QIcon

from ui.app_manager import AppManager

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Keep running in the background for system tray
    
    # Try to set an icon
    icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    app.setWindowIcon(icon)
    
    manager = AppManager(app)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
