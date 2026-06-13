from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
import json
import os

CONFIG_FILE = "hotkeys_config.json"

class HotkeySettingsDialog(QDialog):
    def __init__(self, current_hotkeys, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Hotkeys")
        self.current_hotkeys = current_hotkeys
        self.new_hotkeys = {}
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Instructions
        layout.addWidget(QLabel("Format: 'ctrl+shift+o', 'shift+space', etc."))
        
        # Inputs
        self.inputs = {}
        for action, key_str in self.current_hotkeys.items():
            row = QHBoxLayout()
            row.addWidget(QLabel(action.replace("_", " ").title()))
            
            line_edit = QLineEdit(key_str)
            self.inputs[action] = line_edit
            row.addWidget(line_edit)
            
            layout.addLayout(row)
            
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
    def save(self):
        for action, line_edit in self.inputs.items():
            val = line_edit.text().strip()
            if not val:
                QMessageBox.warning(self, "Error", f"Hotkey for {action} cannot be empty.")
                return
            self.new_hotkeys[action] = val
            
        self.accept()

def load_hotkey_config(default_hotkeys):
    if not os.path.exists(CONFIG_FILE):
        return default_hotkeys
        
    try:
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            # Merge with defaults to ensure all keys exist
            merged = default_hotkeys.copy()
            merged.update(data)
            return merged
    except Exception as e:
        print(f"Failed to load hotkey config: {e}")
        return default_hotkeys

def save_hotkey_config(hotkeys):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(hotkeys, f)
    except Exception as e:
        print(f"Failed to save hotkey config: {e}")
