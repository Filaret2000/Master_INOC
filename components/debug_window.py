"""
Debug window component for displaying camera feed and gesture detection visualization
"""
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QMainWindow, QTextEdit, QScrollArea
from PyQt5.QtGui import QPixmap, QImage, QIcon, QFont
from PyQt5.QtCore import Qt, pyqtSlot

class DebugWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gesture Recognition Debug")
        
        # Set window size and position
        self.setMinimumSize(640, 720)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Set up UI
        layout = QVBoxLayout(central_widget)
        
        # Title label
        title_label = QLabel("Debug View")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Video display
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(460, 360)
        layout.addWidget(self.video_label)
        
        # Debug text area label
        debug_label = QLabel("Debug Information:")
        debug_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(debug_label)
        
        # Debug text area - scrollable
        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        self.debug_text.setMinimumHeight(200)
        self.debug_text.setFont(QFont("Courier New", 10))
        layout.addWidget(self.debug_text)
        
        # Description
        desc_label = QLabel("This window shows the video feed with detected landmarks and debug information.")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Show by default
        self.show()
    
    @pyqtSlot(QImage)
    def update_frame(self, frame):
        """Update the debug window with a new frame"""
        if frame.isNull():
            return
            
        # Resize the frame to fit the label while maintaining aspect ratio
        pixmap = QPixmap.fromImage(frame)
        pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Set the pixmap to the label
        self.video_label.setPixmap(pixmap)
        
    @pyqtSlot(str)
    def update_debug_text(self, text):
        """Update the debug text area with new information"""
        self.debug_text.setText(text)
        # Automatically scroll to the bottom to show latest debug info
        self.debug_text.verticalScrollBar().setValue(self.debug_text.verticalScrollBar().maximum())
    
    def resizeEvent(self, event):
        """Handle resize events to update the frame display"""
        super().resizeEvent(event)
        
        # If we have a pixmap, resize it to fit the new size
        if self.video_label.pixmap() and not self.video_label.pixmap().isNull():
            pixmap = self.video_label.pixmap().scaled(
                self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.video_label.setPixmap(pixmap)
