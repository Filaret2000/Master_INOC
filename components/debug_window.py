"""
Debug window component for displaying camera feed and gesture detection visualization
"""
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, pyqtSlot

class DebugWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # Set up UI
        self.setup_ui()
    
    def setup_ui(self):
        # Create layout
        layout = QVBoxLayout(self)
        
        # Title label
        title_label = QLabel("Debug View")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Video display
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(320, 240)
        layout.addWidget(self.video_label)
        
        # Description
        desc_label = QLabel("This window shows the video feed with detected landmarks for debugging purposes.")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
    
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
    
    def resizeEvent(self, event):
        """Handle resize events to update the frame display"""
        super().resizeEvent(event)
        
        # If we have a pixmap, resize it to fit the new size
        if self.video_label.pixmap() and not self.video_label.pixmap().isNull():
            pixmap = self.video_label.pixmap().scaled(
                self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.video_label.setPixmap(pixmap)
