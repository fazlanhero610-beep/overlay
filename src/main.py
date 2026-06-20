import sys
import os

# Add the 'src' directory to the python path so absolute imports work nicely
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QStyle
from PyQt6.QtGui import QIcon

from ui.app_manager import AppManager

def main():
    app = QApplication(sys.argv)
    # Allow the app to exit cleanly if all windows (like the main Control Panel) are closed by the user natively.
    app.setQuitOnLastWindowClosed(True)
    
    # Try to set an icon
    icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    app.setWindowIcon(icon)
    
    manager = AppManager(app)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
