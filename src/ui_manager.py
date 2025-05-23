import cv2
import numpy as np
from typing import List, Tuple

class UIManager:
    """Handles the UI components for the gallery application."""
    
    def __init__(self, canvas_width=1000, canvas_height=800):
        """Initialize the UI manager.
        
        Args:
            canvas_width: Width of the main canvas
            canvas_height: Height of the main canvas
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        
        # Initialize font
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.6
        self.font_thickness = 1
        self.font_color = (0, 0, 0)
        
        # Header dimensions
        self.header_height = 120
        
        # Image dimensions
        self.image_width = 960
        self.image_height = 600
        
        # Calculate counter position (below header)
        self.counter_y = self.header_height + 20
        self.counter_x = (self.canvas_width - 100) // 2
        
        # Calculate image position (centered below counter)
        self.image_y = self.counter_y + 40
        self.image_x = (self.canvas_width - self.image_width) // 2
        
        # Try to load logo from assets folder
        import os
        import pathlib
        
        # Get the path to the assets folder
        base_path = pathlib.Path(__file__).parent.parent.parent
        logo_path = os.path.join(base_path, "assets", "logo.png")
        print(f"Looking for logo at: {logo_path}")
        
        # Load the logo
        self.logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
        if self.logo is not None:
            # Resize logo to a reasonable height while maintaining aspect ratio
            logo_height = 100
            aspect_ratio = self.logo.shape[1] / self.logo.shape[0]
            self.logo = cv2.resize(self.logo, (int(logo_height * aspect_ratio), logo_height))
        else:
            print(f"Could not load logo from {logo_path}")
        
        # Header text
        self.header_text = [
            "Universitatea \"Stefan cel Mare\" din Suceava",
            "Specializarea: Stiinta si Ingineria Calculatoarelor",
            "Disciplina: Interactiunea naturala om-calculator",
            "Student: Filaret-Niculai Crainiciuc"
        ]
        
        # Try to load Times New Roman font
        try:
            from PIL import ImageFont, ImageDraw, Image
            self.pil_font = ImageFont.truetype("times.ttf", 16)
            self.use_pil_font = True
        except (ImportError, OSError):
            print("PIL not available or Times New Roman not found, using default font")
            self.use_pil_font = False
    
    def create_counter_display(self, current_index: int, total_images: int) -> np.ndarray:
        """Create and return the counter display.
        
        Args:
            current_index: Current image index (0-based)
            total_images: Total number of images
            
        Returns:
            Counter display image
        """
        # Create counter background
        counter_bg = np.ones((30, 100, 3), dtype=np.uint8) * 240
        
        # Display counter text
        counter_text = f"{current_index + 1}/{total_images}"
        cv2.putText(counter_bg, counter_text, (30, 20), 
                   self.font, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
        
        return counter_bg
    
    def create_header(self, width: int, show_debug: bool) -> np.ndarray:
        """Create the header with logo and text.
        
        Args:
            width: Width of the header
            show_debug: Whether debug mode is enabled
            
        Returns:
            Header image
        """
        # Create white header background
        header = np.ones((self.header_height, width, 3), dtype=np.uint8) * 255
        
        # Create blue gradient from left (white) to right (blue)
        # Increase white area by starting gradient later (at 20% instead of 0%)
        blue_color = (240, 170, 50)  # BGR format for a nice blue
        gradient_start_pct = 0.2  # Start gradient at 20% of width
        
        for x in range(width):
            # Keep first part completely white
            if x < width * gradient_start_pct:
                continue
                
            # Calculate gradient intensity based on position (adjusted for the delayed start)
            gradient_intensity = (x - width * gradient_start_pct) / (width * (1 - gradient_start_pct))
            gradient_intensity = min(1.0, max(0.0, gradient_intensity))  # Ensure between 0-1
            
            for c in range(3):
                header[:, x, c] = (1 - gradient_intensity) * 255 + gradient_intensity * blue_color[c]
        
        # Add logo if available
        if self.logo is not None:
            logo_y = (self.header_height - self.logo.shape[0]) // 2
            logo_x = 20
            
            # Handle alpha channel if present
            if self.logo.shape[2] == 4:
                # Create a region that's the same size as the logo
                logo_region = header[logo_y:logo_y+self.logo.shape[0], logo_x:logo_x+self.logo.shape[1]]
                
                # Extract alpha channel
                alpha = self.logo[:, :, 3] / 255.0
                
                # Create alpha channels for logo and background
                alpha_logo = np.stack([alpha, alpha, alpha], axis=2)
                alpha_bg = 1.0 - alpha_logo
                
                # Blend logo with background
                logo_rgb = self.logo[:, :, 0:3]
                blended = logo_rgb * alpha_logo + logo_region * alpha_bg
                
                # Place blended image back into header
                header[logo_y:logo_y+self.logo.shape[0], logo_x:logo_x+self.logo.shape[1]] = blended
            else:
                # No alpha channel, just copy the logo
                header[logo_y:logo_y+self.logo.shape[0], logo_x:logo_x+self.logo.shape[1]] = self.logo
        
        # Add text next to the logo
        text_x = 20 + (self.logo.shape[1] if self.logo is not None else 0) + 10
        
        if self.use_pil_font:
            # Convert OpenCV image to PIL Image
            from PIL import Image, ImageDraw, ImageFont
            pil_img = Image.fromarray(header)
            draw = ImageDraw.Draw(pil_img)
            
            # Calculate line height based on font size
            # Using getbbox instead of deprecated getsize
            line_height = self.pil_font.getbbox("A")[3] + 5
            
            # Draw each line of text
            for i, line in enumerate(self.header_text):
                text_y = (self.header_height - (len(self.header_text) * line_height)) // 2 + i * line_height
                draw.text((text_x, text_y), line, font=self.pil_font, fill=(0, 0, 0))
            
            # Convert back to OpenCV format
            header = np.array(pil_img)
        else:
            # Draw with OpenCV's simple font
            line_height = 25
            for i, line in enumerate(self.header_text):
                text_y = (self.header_height - (len(self.header_text) * line_height)) // 2 + i * line_height
                cv2.putText(header, line, (text_x, text_y), 
                           self.font, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
        
        # Add text-only debug button
        button_text = "Degub OFF" if show_debug else "Debug ON"
        
        # Use Times New Roman if available, otherwise default font
        if self.use_pil_font:
            # Convert the specific region to PIL
            button_region = header[20:60, width-150:width-20].copy()
            pil_button = Image.fromarray(button_region)
            draw_button = ImageDraw.Draw(pil_button)
            
            # Draw text with Time New Roman (bigger font size)
            button_font = self.pil_font
            try:
                button_font = ImageFont.truetype("times.ttf", 20)  
            except:
                pass  # Fall back to self.pil_font if times.ttf not available
            
            # Get text dimensions for centering
            text_bbox = button_font.getbbox(button_text)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # Center text in button area
            text_x = (button_region.shape[1] - text_width) // 2
            text_y = (button_region.shape[0] - text_height) // 2
            
            # Draw text with proper color
            text_color = (0, 0, 0)  # Black color for all button states
            draw_button.text((text_x, text_y), button_text, font=button_font, fill=text_color)
            
            # Put the button region back
            header[20:60, width-150:width-20] = np.array(pil_button)
        else:
            # Simple OpenCV text
            text_color = (0, 0, 0)  # Black color for all button states
            text_size = cv2.getTextSize(button_text, self.font, 0.7, 2)[0]
            text_x = width - 150 + (130 - text_size[0]) // 2
            text_y = 40 + text_size[1] // 2
            
            cv2.putText(header, button_text, (text_x, text_y), 
                       self.font, 0.7, text_color, 2, cv2.LINE_AA)
        
        return header
    
    def create_error_display(self) -> np.ndarray:
        """Create an error display when image loading fails.
        
        Returns:
            Error display image
        """
        error_img = np.ones((self.image_height, self.image_width, 3), dtype=np.uint8) * 200
        cv2.putText(error_img, "Imaginea nu a putut fi incarcata", (int(self.image_width/2) - 150, int(self.image_height/2)), 
                   self.font, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        return error_img
    
    def draw_exit_confirmation(self, frame: np.ndarray, time_left: float) -> None:
        """Draw exit confirmation overlay.
        
        Args:
            frame: Frame to draw on
            time_left: Time left for confirmation
        """
        # Draw semi-transparent overlay for entire frame
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 0), -1)
        frame[:] = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)
        
        # Create a popup box with border
        popup_width, popup_height = 400, 250
        popup_x = (frame.shape[1] - popup_width) // 2
        popup_y = (frame.shape[0] - popup_height) // 2
        
        # Define the blue color for buttons (matching the header gradient)
        button_blue = (240, 170, 50)  # BGR format
        
        # Draw outer border with blue color
        cv2.rectangle(frame, 
                     (popup_x-5, popup_y-5), 
                     (popup_x+popup_width+5, popup_y+popup_height+5), 
                     button_blue, 
                     3)
        
        # Draw popup background (white as requested)
        cv2.rectangle(frame, 
                     (popup_x, popup_y), 
                     (popup_x+popup_width, popup_y+popup_height), 
                     (255, 255, 255), 
                     -1)
        
        # Add title with background
        title_y = popup_y + 40
        title_text = "CONFIRMARE IEȘIRE"
        # Title background in blue
        cv2.rectangle(frame, 
                     (popup_x, popup_y), 
                     (popup_x+popup_width, title_y+10), 
                     button_blue, 
                     -1)
        
        # Use Times New Roman if available
        if self.use_pil_font:
            # Convert the frame to PIL for custom font
            from PIL import Image, ImageDraw, ImageFont
            
            # Create PIL image for drawing text
            pil_img = Image.fromarray(frame)
            draw = ImageDraw.Draw(pil_img)
            
            # Try to load Times New Roman with larger size for title
            try:
                title_font = ImageFont.truetype("times.ttf", 22)
                normal_font = ImageFont.truetype("times.ttf", 16)
            except:
                # Fall back to default PIL font if not available
                title_font = self.pil_font
                normal_font = self.pil_font
            
            # Draw title text
            text_bbox = title_font.getbbox(title_text)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = popup_x + (popup_width - text_width) // 2
            draw.text((text_x, popup_y + 10), title_text, font=title_font, fill=(255, 255, 255))
            
            # Add countdown with progressbar
            progress_width = int((time_left / 5.0) * (popup_width - 40))
            countdown_y = popup_y + 100
            
            # Draw progress bar background (light gray)
            cv2.rectangle(frame, 
                         (popup_x + 20, countdown_y), 
                         (popup_x + popup_width - 20, countdown_y + 20), 
                         (240, 240, 240), 
                         -1)
            
            # Draw progress bar (blue)
            cv2.rectangle(frame, 
                         (popup_x + 20, countdown_y), 
                         (popup_x + 20 + progress_width, countdown_y + 20), 
                         button_blue, 
                         -1)
            
            # Countdown text
            count_text = f"Confirmă ieșirea în {time_left:.1f} secunde"
            text_bbox = normal_font.getbbox(count_text)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = popup_x + (popup_width - text_width) // 2
            draw.text((text_x, countdown_y + 30), count_text, font=normal_font, fill=(0, 0, 0))
            
            # Add confirmation instructions with OK sign icon
            confirm_y = popup_y + 160
            confirm_text = "Arată semnul OK pentru CONFIRMARE"
            text_bbox = normal_font.getbbox(confirm_text)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = popup_x + (popup_width - text_width) // 2
            draw.text((text_x, confirm_y), confirm_text, font=normal_font, fill=(0, 0, 0))
            
            # Convert PIL image back to OpenCV format
            frame[:] = np.array(pil_img)
            
        else:
            # Fall back to OpenCV's fonts if PIL not available
            # Title text
            text_size = cv2.getTextSize(title_text, self.font, 0.9, 2)[0]
            cv2.putText(frame, 
                        title_text, 
                        (popup_x + (popup_width - text_size[0])//2, title_y), 
                        self.font, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
            
            # Add countdown with progressbar
            progress_width = int((time_left / 5.0) * (popup_width - 40))
            countdown_y = popup_y + 100
            
            # Draw progress bar background (light gray)
            cv2.rectangle(frame, 
                         (popup_x + 20, countdown_y), 
                         (popup_x + popup_width - 20, countdown_y + 20), 
                         (240, 240, 240), 
                         -1)
            
            # Draw progress bar (blue)
            cv2.rectangle(frame, 
                         (popup_x + 20, countdown_y), 
                         (popup_x + 20 + progress_width, countdown_y + 20), 
                         button_blue, 
                         -1)
                      
            # Add confirmation instructions with OK sign icon (black text)
            confirm_y = popup_y + 180
            confirm_text = "Arată semnul OK pentru CONFIRMARE"
            text_size = cv2.getTextSize(confirm_text, self.font, 0.7, 2)[0]
            cv2.putText(frame, 
                        confirm_text, 
                        (popup_x + (popup_width - text_size[0])//2, confirm_y), 
                        self.font, 0.7, (0, 0, 0), 2, cv2.LINE_AA)
        
        # Draw OK sign icon with blue color
        icon_center_x = popup_x + popup_width//2
        icon_center_y = confirm_y + 50  # Increased from 30 to 50 to move it down
        # Draw circle
        cv2.circle(frame, (icon_center_x, icon_center_y), 15, button_blue, 2)
        # Draw fingers
        cv2.line(frame, (icon_center_x-10, icon_center_y-5), (icon_center_x, icon_center_y+10), button_blue, 2)
        cv2.line(frame, (icon_center_x+10, icon_center_y-5), (icon_center_x, icon_center_y+10), button_blue, 2)
    
    def create_main_canvas(self, show_debug: bool, fullscreen_mode: bool, 
                  current_image: np.ndarray, camera_preview: np.ndarray,
                  current_index: int, total_images: int, exit_requested=False, time_left=0) -> np.ndarray:
        """Create the main display canvas.
        
        Args:
            show_debug: Whether debug mode is enabled
            fullscreen_mode: Whether to show fullscreen mode
            current_image: Current image to display
            camera_preview: Camera preview to display
            current_index: Current image index
            total_images: Total number of images
            exit_requested: Whether exit has been requested
            time_left: Time left for exit confirmation
            
        Returns:
            Main display canvas
        """
        # Store fullscreen mode state for button click detection
        self.fullscreen_mode = fullscreen_mode
        # Create base canvas - completely white background as requested
        canvas = np.ones((self.canvas_height, self.canvas_width, 3), dtype=np.uint8) * 255
        
        # Define the blue color for buttons (matching the header gradient)
        button_blue = (240, 170, 50)  # BGR format
        
        if fullscreen_mode:
            # In fullscreen mode, make the image as large as possible while maintaining aspect ratio
            # First, calculate the aspect ratio of the original image
            img_h, img_w = current_image.shape[:2]
            img_aspect = img_w / img_h if img_h > 0 else 1.0
            
            # Calculate dimensions for the maximized image
            canvas_aspect = self.canvas_width / self.canvas_height
            
            if img_aspect > canvas_aspect:
                # Image is wider than canvas (relative to height)
                new_width = self.canvas_width
                new_height = int(new_width / img_aspect)
            else:
                # Image is taller than canvas (relative to width)
                new_height = self.canvas_height
                new_width = int(new_height * img_aspect)
            
            # Make sure dimensions are valid
            new_width = max(1, min(new_width, self.canvas_width))
            new_height = max(1, min(new_height, self.canvas_height))
            
            # Resize the image
            max_image = cv2.resize(current_image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # Calculate position to center the image
            x_offset = (self.canvas_width - new_width) // 2
            y_offset = (self.canvas_height - new_height) // 2
            
            # Place the resized image on the canvas
            canvas[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = max_image
            
            # Add a small image counter in the bottom corner even in fullscreen mode
            counter_bg = self.create_counter_display(current_index, total_images)
            counter_width, counter_height = counter_bg.shape[1], counter_bg.shape[0]
            canvas[self.canvas_height-counter_height-10:self.canvas_height-10, 
                  self.canvas_width-counter_width-10:self.canvas_width-10] = counter_bg
            
            # If exit is requested, draw the exit confirmation popup (also in fullscreen mode)
            if exit_requested and time_left > 0:
                self.draw_exit_confirmation(canvas, time_left)
            
            return canvas
        else:
            # Normal mode with header and counter
            # Add header
            header = self.create_header(self.canvas_width, show_debug)
            header_height = header.shape[0]
            
            # Place header at the top
            if header_height > 0 and header.shape[1] == self.canvas_width:
                canvas[:header_height, :] = header
            
            # Create and position counter
            counter_bg = self.create_counter_display(current_index, total_images)
            canvas[self.counter_y:self.counter_y+30, self.counter_x:self.counter_x+100] = counter_bg
            
            # Place the image on the canvas
            canvas[self.image_y:self.image_y+self.image_height, 
                  self.image_x:self.image_x+self.image_width] = current_image
            
            # Add navigation buttons on the sides of the photo gallery
            button_width = 50
            button_height = 80
            
            # Position buttons vertically centered with the image
            button_y = self.image_y + (self.image_height - button_height) // 2
            
            # Adjust image width to accommodate buttons
            adjusted_image_width = self.image_width - 2*(button_width + 20)  # Allow space for buttons on both sides
            image_center_x = self.canvas_width // 2
            
            # Recalculate image x position to center with buttons
            adjusted_image_x = image_center_x - (adjusted_image_width // 2)
            
            # Make sure we don't try to modify the image again since we're just adjusting positions
            # (this would break if there's already an image placed)
            
            # Left (Previous) button - place within visible area
            left_button_x = adjusted_image_x - button_width - 5  # 5px gap
            
            # Draw left button (blue rectangle with left arrow)
            cv2.rectangle(canvas, 
                          (left_button_x, button_y), 
                          (left_button_x + button_width, button_y + button_height), 
                          button_blue, -1)  # Filled rectangle
            
            # Draw left arrow
            arrow_points = np.array([
                [left_button_x + 35, button_y + 15],  # Tip
                [left_button_x + 15, button_y + button_height//2],  # Middle
                [left_button_x + 35, button_y + button_height - 15]  # Bottom
            ], np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [arrow_points], True, (255, 255, 255), 2)
            
            # Right (Next) button - place within visible area
            right_button_x = adjusted_image_x + adjusted_image_width + 5  # 5px gap
            
            # Draw right button (blue rectangle with right arrow)
            cv2.rectangle(canvas, 
                           (right_button_x, button_y), 
                           (right_button_x + button_width, button_y + button_height), 
                           button_blue, -1)  # Filled rectangle
            
            # Draw right arrow
            arrow_points = np.array([
                [right_button_x + 15, button_y + 15],  # Top
                [right_button_x + 35, button_y + button_height//2],  # Middle
                [right_button_x + 15, button_y + button_height - 15]  # Bottom
            ], np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [arrow_points], True, (255, 255, 255), 2)
            
            # If exit is requested, draw the exit confirmation popup
            if exit_requested and time_left > 0:
                self.draw_exit_confirmation(canvas, time_left)
            
            return canvas
        
    def draw_gesture_info(self, frame: np.ndarray, gesture_name: str, show_debug: bool) -> None:
        """Draw gesture information on the camera preview.
        
        Args:
            frame: Frame to draw on
            gesture_name: Name of current gesture
            show_debug: Whether debug info should be shown
        """
        if not show_debug:
            return
            
        # Draw gesture name
        cv2.putText(frame, f"Gest: {gesture_name}", (10, 30), 
                   self.font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                   
    def is_debug_button_clicked(self, x: int, y: int) -> bool:
        """Check if the debug button in the header was clicked.
        
        Args:
            x: X-coordinate of the click
            y: Y-coordinate of the click
            
        Returns:
            True if debug button was clicked, False otherwise
        """
        # Debug button position in header
        button_x1 = self.canvas_width - 150
        button_x2 = self.canvas_width - 20
        button_y1 = 20
        button_y2 = 60
        
        # Check if click is within button bounds
        return (0 <= y < self.header_height and 
                button_x1 <= x <= button_x2 and 
                button_y1 <= y <= button_y2)
                
    def is_left_button_clicked(self, x: int, y: int) -> bool:
        """Check if the left navigation button was clicked.
        
        Args:
            x: X-coordinate of the click
            y: Y-coordinate of the click
            
        Returns:
            True if left navigation button was clicked, False otherwise
        """
        if self.fullscreen_mode:
            return False  # No navigation buttons in fullscreen mode
            
        # Calculate button position (same as in create_main_canvas)
        button_width = 50
        button_height = 80
        button_y = self.image_y + (self.image_height - button_height) // 2
        
        # Adjust image width to accommodate buttons
        adjusted_image_width = self.image_width - 2*(button_width + 20)
        image_center_x = self.canvas_width // 2
        adjusted_image_x = image_center_x - (adjusted_image_width // 2)
        
        # Left button position
        left_button_x = adjusted_image_x - button_width - 5
        
        # Check if click is within left button bounds
        return (left_button_x <= x <= left_button_x + button_width and
                button_y <= y <= button_y + button_height)
                
    def is_right_button_clicked(self, x: int, y: int) -> bool:
        """Check if the right navigation button was clicked.
        
        Args:
            x: X-coordinate of the click
            y: Y-coordinate of the click
            
        Returns:
            True if right navigation button was clicked, False otherwise
        """
        if self.fullscreen_mode:
            return False  # No navigation buttons in fullscreen mode
            
        # Calculate button position (same as in create_main_canvas)
        button_width = 50
        button_height = 80
        button_y = self.image_y + (self.image_height - button_height) // 2
        
        # Adjust image width to accommodate buttons
        adjusted_image_width = self.image_width - 2*(button_width + 20)
        image_center_x = self.canvas_width // 2
        adjusted_image_x = image_center_x - (adjusted_image_width // 2)
        
        # Right button position
        right_button_x = adjusted_image_x + adjusted_image_width + 5
        
        # Check if click is within right button bounds
        return (right_button_x <= x <= right_button_x + button_width and
                button_y <= y <= button_y + button_height)
