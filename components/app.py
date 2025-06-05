"""
Main app component that integrates all other components
"""
import os
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QAction
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt, QSize, QTimer

from components.gallery import GalleryComponent
from components.gesture_recognizer import GestureRecognizer
from components.debug_window import DebugWindow
from components.utils import get_command_info

class PhotoGalleryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Gallery with Gesture Recognition")
        self.setMinimumSize(1200, 800)
        
        # Load app logo
        self.setWindowIcon(QIcon(os.path.join("assets", "logo.png")))
        
        # Initialize components
        self.gallery = GalleryComponent(os.path.join("images"))
        self.gesture_recognizer = GestureRecognizer()
        self.debug_window = DebugWindow()
        
        # Set up UI
        self.setup_ui()
        
        # Connect signals
        self.connect_signals()
        
        # Start gesture recognition
        self.gesture_timer = QTimer(self)
        self.gesture_timer.timeout.connect(self.process_gestures)
        self.gesture_timer.start(100)  # Process gestures every 100ms
        
        # Current command status
        self.status_label = QLabel("Ready")
        self.statusBar().addWidget(self.status_label)
        
        # Initialize help window
        self.help_window = None
        
    def setup_ui(self):
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        
        # Add gallery to the main layout
        main_layout.addWidget(self.gallery, 3)
        
        # Add debug window to the right side
        main_layout.addWidget(self.debug_window, 1)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
    def create_menu_bar(self):
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        # Help action
        help_action = QAction("&Gesture Commands", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
    def connect_signals(self):
        # Connect gesture recognition signals to gallery actions
        self.gesture_recognizer.next_signal.connect(self.gallery.next_image)
        self.gesture_recognizer.previous_signal.connect(self.gallery.previous_image)
        self.gesture_recognizer.increase_signal.connect(self.gallery.zoom_in)
        self.gesture_recognizer.decrease_signal.connect(self.gallery.zoom_out)
        self.gesture_recognizer.ok_signal.connect(self.gallery.confirm_action)
        self.gesture_recognizer.cancel_signal.connect(self.gallery.cancel_action)
        self.gesture_recognizer.menu_signal.connect(self.toggle_menu)
        self.gesture_recognizer.home_signal.connect(self.gallery.go_home)
        self.gesture_recognizer.undo_signal.connect(self.gallery.undo_action)
        self.gesture_recognizer.help_signal.connect(self.show_help)
        
        # Connect debug output
        self.gesture_recognizer.debug_frame_signal.connect(self.debug_window.update_frame)
        self.gesture_recognizer.status_signal.connect(self.update_status)
        
    def process_gestures(self):
        self.gesture_recognizer.process_frame()
        
    def update_status(self, status_text):
        self.status_label.setText(status_text)
        
    def toggle_menu(self):
        # Implement menu toggle functionality
        pass
    
    def show_help(self):
        # Show help window with gesture commands
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea
        
        if self.help_window is None:
            self.help_window = QDialog(self)
            self.help_window.setWindowTitle("Gesture Commands")
            self.help_window.setMinimumSize(500, 600)
            
            layout = QVBoxLayout()
            
            title = QLabel("Available Gesture Commands")
            title.setAlignment(Qt.AlignCenter)
            title.setFont(QFont("Arial", 16, QFont.Bold))
            layout.addWidget(title)
            
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            
            # Add all gesture commands with descriptions
            commands = get_command_info()
            for cmd_name, description in commands.items():
                cmd_label = QLabel(f"<b>{cmd_name}</b>: {description}")
                cmd_label.setWordWrap(True)
                scroll_layout.addWidget(cmd_label)
                
            scroll_area.setWidget(scroll_content)
            layout.addWidget(scroll_area)
            
            close_button = QPushButton("Close")
            close_button.clicked.connect(self.help_window.close)
            layout.addWidget(close_button)
            
            self.help_window.setLayout(layout)
        
        self.help_window.show()
        
    def closeEvent(self, event):
        # Clean up resources
        self.gesture_recognizer.release()
        event.accept()
