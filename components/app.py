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
        self.setMinimumSize(1600, 1000)  # Increased default window size
        
        # Modern window styling with improved color harmony
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QMenuBar {
                background-color: #343a40;
                color: #f8f9fa;
                font-weight: bold;
                padding: 6px;
                border-bottom: 1px solid #495057;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 6px 12px;
                margin: 0 2px;
            }
            QMenuBar::item:selected {
                background-color: #495057;
                border-radius: 4px;
            }
            QMenu {
                background-color: #343a40;
                color: #f8f9fa;
                border: 1px solid #495057;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #495057;
            }
        """)
        
        # Set central widget background color
        centralPalette = self.palette()
        centralPalette.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(centralPalette)
        
        # Load app logo
        self.setWindowIcon(QIcon(os.path.join("assets", "logo.png")))
        
        # Initialize components
        self.gallery = GalleryComponent(os.path.join("images"))
        self.gesture_recognizer = GestureRecognizer()
        # Make debug window a child of the main window to ensure it closes with parent
        self.debug_window = DebugWindow(self)
        
        # Set up UI
        self.setup_ui()
        
        # Connect signals
        self.connect_signals()
        
        # Start gesture recognition
        self.gesture_timer = QTimer(self)
        self.gesture_timer.timeout.connect(self.process_gestures)
        self.gesture_timer.start(100)  # Process gestures every 100ms
        
        # Remove status bar completely
        self.statusBar().hide()
        
        # Initialize help window
        self.help_window = None
        
        # Position debug window to the right of the main window
        # and make it visible on startup
        self.positionDebugWindow()
        
    def positionDebugWindow(self):
        """Position debug window to the right of the main window"""
        # First show the debug window to make sure it's initialized
        self.debug_window.show()
        
        # Position debug window to the right of main window
        main_pos = self.geometry()
        debug_pos = self.debug_window.geometry()
        
        # Set debug window position
        self.debug_window.setGeometry(
            main_pos.x() + main_pos.width() + 10,  # 10px gap between windows
            main_pos.y(),
            debug_pos.width(),
            debug_pos.height()
        )
        
    def closeEvent(self, event):
        """Override close event to close all associated windows"""
        # Forcefully terminate the gesture recognizer and its camera
        self.gesture_timer.stop()
        if hasattr(self.gesture_recognizer, 'cap') and self.gesture_recognizer.cap is not None:
            self.gesture_recognizer.cap.release()
        
        # Close debug window - make sure to use close() and also deleteLater()
        if self.debug_window:
            self.debug_window.close()
            self.debug_window.deleteLater()
        
        # Close help window if it exists
        if self.help_window and self.help_window.isVisible():
            self.help_window.close()
            self.help_window.deleteLater()
            
        # Continue with normal close
        super().closeEvent(event)
        
    def setup_ui(self):
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        
        # Add gallery to the main layout
        main_layout.addWidget(self.gallery)
        
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
        help_action.triggered.connect(self.toggle_help_and_debug)  # Changed to toggle both help and debug
        help_menu.addAction(help_action)
        
    def connect_signals(self):
        # Connect gesture recognizer signals to actions (only keeping next, previous, help, increase, decrease)
        self.gesture_recognizer.next_signal.connect(self.gallery.next_image)
        self.gesture_recognizer.previous_signal.connect(self.gallery.previous_image)
        self.gesture_recognizer.help_signal.connect(self.toggle_debug_window)
        self.gesture_recognizer.increase_signal.connect(self.increase_size)
        self.gesture_recognizer.decrease_signal.connect(self.decrease_size)
        self.gesture_recognizer.debug_frame_signal.connect(self.debug_window.update_frame)
        self.gesture_recognizer.debug_text_signal.connect(self.debug_window.update_debug_text)
        self.gesture_recognizer.status_signal.connect(self.update_status)
        
    def process_gestures(self):
        self.gesture_recognizer.process_frame()
        
    def update_status(self, status_text):
        # Do not display gesture status texts in the status bar
        # This removes the debug text at the bottom of the main window
        pass
    
    def toggle_debug_window(self):
        # Toggle only debug window visibility
        if self.debug_window.isVisible():
            self.debug_window.hide()
        else:
            self.debug_window.show()
            # Reposition the debug window if it's being shown
            self.positionDebugWindow()
    
    def toggle_help_and_debug(self):
        # Toggle debug window visibility
        self.toggle_debug_window()
        
        # Also show help window with gesture commands
        self.show_help()
        
    def increase_size(self):
        # Increase the image size in gallery
        self.gallery.zoom_in()
        
    def decrease_size(self):
        # Decrease the image size in gallery
        self.gallery.zoom_out()
        
    def on_ok_gesture(self):
        # Handle OK gesture - simple confirmation action
        self.status_label.setText("OK gesture recognized")
    
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
            
            # Add debug toggle information
            debug_info = QLabel("<b>Help gesture</b> also toggles the debug window visibility.")
            debug_info.setAlignment(Qt.AlignCenter)
            debug_info.setStyleSheet("color: #0066cc;")
            layout.addWidget(debug_info)
            
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
