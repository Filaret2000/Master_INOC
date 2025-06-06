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
        # Create layout with proper spacing and margins for a modern look
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        # Image counter label at the top - making it larger and modern with improved contrast
        self.image_counter = QLabel("")
        self.image_counter.setAlignment(Qt.AlignCenter)
        self.image_counter.setStyleSheet("""
            font-size: 28px; 
            font-weight: bold; 
            color: white;
            background-color: #343a40;
            border-radius: 20px;
            padding: 12px 25px;
            margin: 10px;
            border: 2px solid #495057;
        """)
        self.main_layout.addWidget(self.image_counter)
        
        # Image display with border
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            background-color: white;
            border: 1px solid #dddddd;
            border-radius: 5px;
            padding: 10px;
        """)
        self.main_layout.addWidget(self.image_label, 1)
        
        # Add some spacing before controls
        self.main_layout.addSpacing(10)
        
        # Controls layout - centered with spacing
        controls_container = QWidget()
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(30, 0, 30, 0)
        controls_layout.setSpacing(15)
        
        # Modern button style with improved color harmony
        button_style = """
            QPushButton {
                background-color: #343a40;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 12px 25px;
                font-size: 16px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #495057;
            }
            QPushButton:pressed {
                background-color: #212529;
            }
        """
        
        # Previous button
        self.prev_button = QPushButton("← Previous")
        self.prev_button.clicked.connect(self.previous_image)
        self.prev_button.setStyleSheet(button_style)
        controls_layout.addWidget(self.prev_button)
        
        # Next button
        self.next_button = QPushButton("Next →")
        self.next_button.clicked.connect(self.next_image)
        self.next_button.setStyleSheet(button_style)
        controls_layout.addWidget(self.next_button)
        
        # Zoom in button (renamed to Fullscreen)
        self.zoom_in_button = QPushButton("⛶ Fullscreen")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_in_button.setStyleSheet(button_style)
        controls_layout.addWidget(self.zoom_in_button)
        
        # Zoom out button (renamed to Normal View)
        self.zoom_out_button = QPushButton("⊡ Normal")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.zoom_out_button.setStyleSheet(button_style)
        controls_layout.addWidget(self.zoom_out_button)
        
        # Add the controls container to the main layout
        self.main_layout.addWidget(controls_container)
        
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
        
        # Update image counter in the format "1/8"
        self.image_counter.setText(f"{self.current_index + 1}/{len(self.image_paths)}")
        
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
        self.window().setWindowTitle("Photo Gallery")
    
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
        
        # Toggle fullscreen mode - if already in fullscreen, do nothing
        if self.fullscreen_mode:
            return
            
        # Set to true fullscreen mode
        self.fullscreen_mode = True
        
        # Hide all UI elements except the image
        self.image_counter.setVisible(False)
        for button in self.all_buttons:
            button.setVisible(False)
            
        # Store original zoom factor and set to specific fullscreen zoom level
        self.original_zoom_factor = self.zoom_factor  # Store original zoom
        self.zoom_factor = 2.0  # Fixed fullscreen zoom factor
        
        # Make sure we're only showing the image in the layout with black background
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: black;
                padding: 0;
                margin: 0;
            }
        """)
        
        # Enter application fullscreen mode
        self.parentWidget().parentWidget().showFullScreen()
        
        # Update display
        self.display_image()
    
    def zoom_out(self):
        self.add_to_history()
        
        # Toggle normal mode - if not in fullscreen, do nothing
        if not self.fullscreen_mode:
            return
            
        # Exit fullscreen mode
        self.fullscreen_mode = False
        
        # Exit application fullscreen mode
        self.parentWidget().parentWidget().showNormal()
        
        # Restore original zoom factor
        if hasattr(self, 'original_zoom_factor'):
            self.zoom_factor = self.original_zoom_factor
        else:
            self.zoom_factor = 1.0
        
        # Show all UI elements again
        self.image_counter.setVisible(True)
        for button in self.all_buttons:
            button.setVisible(True)
        
        # Reset image label styling
        self.image_label.setStyleSheet("") 
        
        # Update display with normal view
        self.display_image()
    
    # Only keeping methods related to next, previous, help, increase, and decrease gestures
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Update image display when widget is resized
        self.display_image()
