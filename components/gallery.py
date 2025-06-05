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
        self.fullscreen_mode = False  # Track if we're in fullscreen mode
        
        # Load image paths
        self.load_images()
        
        # History for undo functionality
        self.history = []
        
        # Set up UI
        self.setup_ui()
        
    def setup_ui(self):
        # Create layout
        self.main_layout = QVBoxLayout(self)
        
        # Image counter label at the top
        self.image_counter = QLabel("")
        self.image_counter.setAlignment(Qt.AlignCenter)
        self.image_counter.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        self.main_layout.addWidget(self.image_counter)
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.image_label, 1)
        
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
        
        # Zoom in button (renamed to Increase)
        self.zoom_in_button = QPushButton("Increase")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        controls_layout.addWidget(self.zoom_in_button)
        
        # Zoom out button (renamed to Decrease)
        self.zoom_out_button = QPushButton("Decrease")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        controls_layout.addWidget(self.zoom_out_button)
        
        self.main_layout.addLayout(controls_layout)
        
        # Store all buttons for hiding/showing
        self.all_buttons = [
            self.prev_button,
            self.next_button,
            self.zoom_in_button,
            self.zoom_out_button
        ]
        
        # Store control layout for show/hide functionality
        self.controls_layout = controls_layout
        
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
        
        # Update image counter
        self.image_counter.setText(f"Image {self.current_index + 1} of {len(self.image_paths)}")
        
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
        
        # Increase zoom factor by 20%
        self.zoom_factor *= 1.2
        
        # Cap the maximum zoom level to 5x
        if self.zoom_factor > 5.0:
            self.zoom_factor = 5.0
            
        # Update display with new zoom
        self.display_image()
        
        # Only go into fullscreen mode if zoom is significantly increased
        if self.zoom_factor >= 1.5 and not self.fullscreen_mode:
            self.fullscreen_mode = True
            # Hide buttons when in fullscreen mode
            for button in self.all_buttons:
                button.setVisible(False)
    
    def zoom_out(self):
        self.add_to_history()
        
        # Decrease zoom factor by 20%
        self.zoom_factor /= 1.2
        
        # Minimum zoom level
        if self.zoom_factor < 0.5:
            self.zoom_factor = 0.5
            
        # Update display with new zoom
        self.display_image()
        
        # Exit fullscreen mode if zoom is reduced enough
        if self.zoom_factor <= 1.0 and self.fullscreen_mode:
            self.fullscreen_mode = False
            # Show buttons again when exiting fullscreen
            for button in self.all_buttons:
                button.setVisible(True)
    
    # Only keeping methods related to next, previous, help, increase, and decrease gestures
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Update image display when widget is resized
        self.display_image()
