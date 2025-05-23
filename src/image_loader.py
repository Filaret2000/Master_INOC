import cv2
import os
import numpy as np
from typing import List, Optional
import pathlib

class ImageLoader:
    """Handles loading and resizing of gallery images."""
    
    def __init__(self, image_folder: str = "../images"):
        """Initialize the image loader.
        
        Args:
            image_folder: Path to folder containing gallery images
        """
        # Get absolute path to the images folder
        base_path = pathlib.Path(__file__).parent.parent
        self.image_folder = os.path.join(base_path, "images")
        print(f"Looking for images in: {self.image_folder}")
        
        # Verify the images folder exists
        if not os.path.exists(self.image_folder):
            # Try to create the folder if it doesn't exist
            try:
                os.makedirs(self.image_folder, exist_ok=True)
                print(f"Created images folder at: {self.image_folder}")
            except Exception as e:
                print(f"Error creating images folder: {e}")
                
        self.images = self._load_images()
        self.current_index = 0
    
    def _load_images(self) -> List[str]:
        """Load all images from the images folder.
        
        Returns:
            List of image paths
        """
        images = [os.path.join(self.image_folder, img) for img in os.listdir(self.image_folder)
                 if img.lower().endswith(('.jpg', '.jpeg', '.png'))]
        print(f"Numarul imaginilor din galerie: {len(images)}")
        
        if not images:
            print("No images found in the 'images' folder.")
            exit()
        return images
    
    def next_image(self) -> None:
        """Move to the next image in the gallery."""
        self.current_index = (self.current_index + 1) % len(self.images)
    
    def prev_image(self) -> None:
        """Move to the previous image in the gallery."""
        self.current_index = (self.current_index - 1) % len(self.images)
    
    def get_current_image_path(self) -> str:
        """Get the path to the current image.
        
        Returns:
            Path to current image
        """
        return self.images[self.current_index]
    
    def get_total_images(self) -> int:
        """Get the total number of images.
        
        Returns:
            Total number of images in gallery
        """
        return len(self.images)
    
    def load_and_resize_image(self, target_width: int, target_height: int) -> np.ndarray:
        """Load and resize the current image while maintaining aspect ratio.
        
        Args:
            target_width: Target width for the image
            target_height: Target height for the image
            
        Returns:
            Resized image
        """
        # Get current image path
        image_path = self.get_current_image_path()
        
        try:
            # Load the image
            img = cv2.imread(image_path)
            
            if img is None:
                raise FileNotFoundError(f"Could not load image: {image_path}")
                
            # Get original dimensions
            h, w = img.shape[:2]
            
            # Calculate aspect ratio
            aspect = w / h
            
            # Calculate new dimensions to fit in target area while preserving aspect ratio
            if target_width / target_height > aspect:
                # Target area is wider than image
                new_h = target_height
                new_w = int(aspect * new_h)
            else:
                # Target area is taller than image
                new_w = target_width
                new_h = int(new_w / aspect)
            
            # Resize the image
            resized = cv2.resize(img, (new_w, new_h))
            
            # Create a blank canvas of the target size
            canvas = np.ones((target_height, target_width, 3), dtype=np.uint8) * 255
            
            # Calculate position to place resized image (centered)
            y_offset = (target_height - new_h) // 2
            x_offset = (target_width - new_w) // 2
            
            # Place the resized image on the canvas
            canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
            
            return canvas
            
        except Exception as e:
            print(f"Error loading image: {e}")
            # Return error display
            error_img = np.ones((target_height, target_width, 3), dtype=np.uint8) * 200
            cv2.putText(error_img, "Imaginea nu a putut fi incarcata", 
                       (target_width//2 - 150, target_height//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
            return error_img
