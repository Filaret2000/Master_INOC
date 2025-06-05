"""
Gallery component for displaying and navigating images
"""
import os
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtGui import QPixmap, QImage, QTransform
from PyQt5.QtCore import Qt, pyqtSignal, QSize

class GalleryComponent(QWidget):
    def __init__(self, images_dir):
        super().__init__()
        self.images_dir = images_dir
        self.image_paths = []
        self.current_index = 0
        self.zoom_factor = 1.0
        self.rotation = 0
        
        # Load image paths
        self.load_images()
        
        # History for undo functionality
        self.history = []
        
        # Set up UI
        self.setup_ui()
        
    def setup_ui(self):
        # Create layout
        layout = QVBoxLayout(self)
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label, 1)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        # Previous button
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.previous_image)
        controls_layout.addWidget(self.prev_button)
        
        # Next button
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.next_image)
        controls_layout.addWidget(self.next_button)
        
        # Zoom in button
        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        controls_layout.addWidget(self.zoom_in_button)
        
        # Zoom out button
        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        controls_layout.addWidget(self.zoom_out_button)
        
        # Home button
        self.home_button = QPushButton("Home")
        self.home_button.clicked.connect(self.go_home)
        controls_layout.addWidget(self.home_button)
        
        # Undo button
        self.undo_button = QPushButton("Undo")
        self.undo_button.clicked.connect(self.undo_action)
        controls_layout.addWidget(self.undo_button)
        
        layout.addLayout(controls_layout)
        
        # Display first image if available
        if self.image_paths:
            self.display_image()
    
    def load_images(self):
        # Get all image files from the directory
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.JPG']
        
        if os.path.exists(self.images_dir) and os.path.isdir(self.images_dir):
            for file_name in os.listdir(self.images_dir):
                ext = os.path.splitext(file_name)[1]
                if ext in valid_extensions:
                    full_path = os.path.join(self.images_dir, file_name)
                    self.image_paths.append(full_path)
        
        # Sort image paths
        self.image_paths.sort()
    
    def display_image(self):
        if not self.image_paths:
            return
        
        # Get current image path
        image_path = self.image_paths[self.current_index]
        
        # Load image
        pixmap = QPixmap(image_path)
        
        # Apply transformations
        if self.zoom_factor != 1.0 or self.rotation != 0:
            # Convert to QImage for transformation
            image = pixmap.toImage()
            
            # Apply rotation
            if self.rotation != 0:
                transform = QTransform().rotate(self.rotation)
                image = image.transformed(transform)
            
            # Apply zoom
            if self.zoom_factor != 1.0:
                new_width = int(image.width() * self.zoom_factor)
                new_height = int(image.height() * self.zoom_factor)
                image = image.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Convert back to pixmap
            pixmap = QPixmap.fromImage(image)
        
        # Resize to fit the label while maintaining aspect ratio
        pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Set pixmap to label
        self.image_label.setPixmap(pixmap)
        
        # Update window title with image name
        self.window().setWindowTitle(f"Photo Gallery - {os.path.basename(image_path)}")
    
    def add_to_history(self):
        # Save current state to history
        state = {
            'index': self.current_index,
            'zoom': self.zoom_factor,
            'rotation': self.rotation
        }
        self.history.append(state)
        
        # Limit history size
        if len(self.history) > 20:
            self.history.pop(0)
    
    def next_image(self):
        if not self.image_paths:
            return
            
        self.add_to_history()
        
        # Move to next image
        self.current_index = (self.current_index + 1) % len(self.image_paths)
        
        # Reset transformations
        self.zoom_factor = 1.0
        self.rotation = 0
        
        # Display the image
        self.display_image()
    
    def previous_image(self):
        if not self.image_paths:
            return
            
        self.add_to_history()
        
        # Move to previous image
        self.current_index = (self.current_index - 1) % len(self.image_paths)
        
        # Reset transformations
        self.zoom_factor = 1.0
        self.rotation = 0
        
        # Display the image
        self.display_image()
    
    def zoom_in(self):
        self.add_to_history()
        
        # Increase zoom factor
        self.zoom_factor *= 1.2
        
        # Display the image
        self.display_image()
    
    def zoom_out(self):
        self.add_to_history()
        
        # Decrease zoom factor
        self.zoom_factor /= 1.2
        
        # Display the image
        self.display_image()
    
    def go_home(self):
        if not self.image_paths:
            return
            
        self.add_to_history()
        
        # Reset to first image
        self.current_index = 0
        
        # Reset transformations
        self.zoom_factor = 1.0
        self.rotation = 0
        
        # Display the image
        self.display_image()
    
    def undo_action(self):
        # Restore previous state from history
        if self.history:
            state = self.history.pop()
            self.current_index = state['index']
            self.zoom_factor = state['zoom']
            self.rotation = state['rotation']
            
            # Display the image
            self.display_image()
    
    def confirm_action(self):
        # Placeholder for OK gesture
        pass
    
    def cancel_action(self):
        # Placeholder for Cancel gesture
        self.zoom_factor = 1.0
        self.rotation = 0
        self.display_image()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Update image display when widget is resized
        self.display_image()
