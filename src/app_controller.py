import cv2
import time
import numpy as np
from typing import Dict, Any
from src.gesture_detector import GestureDetector
from src.ui_manager import UIManager
from src.image_loader import ImageLoader

# Constants
CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240
MIN_SWIPE_DISTANCE = 160  # Half of camera width

class GestureGallery:
    """Main application class for the Gesture Gallery."""
    
    def __init__(self):
        """Initialize the Gesture Gallery application."""
        # Gesture interference prevention - Initialize these first to prevent attribute errors
        self.coming_from_debug_gesture = False  # Tracks if we're in the middle of a debug gesture
        self.debug_gesture_active = False  # Tracks if debug gesture is currently active
        self.debug_cooldown_frames = 0  # Count frames after debug gesture
        
        # Initialize components
        self.gesture_detector = GestureDetector(detection_con=0.8, max_hands=1)
        self.image_loader = ImageLoader()
        self.ui_manager = UIManager()
        
        # Initialize camera
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        
        # Gesture tracking variables
        self.gesture_start_x = None
        self.gesture_start_y = None
        self.gesture_distance = 0
        self.gesture_cooldown = 0
        self.current_gesture = "None"
        
        # Display state variables
        self.fullscreen_mode = False
        self.show_debug = True
        self.last_hand_state = ""
        self.last_debug_state = ""
        self.last_swipe_state = ""
        self.swipe_start_recorded = False
        
        # Exit handling
        self.exit_requested = False
        self.exit_request_time = 0
    
    def run(self):
        """Main application loop."""
        while True:
            success, frame = self.cap.read()
            if not success:
                break
                
            # Prepare camera preview (flip for mirroring)
            frame = cv2.flip(frame, 1)
            cam_preview = cv2.resize(frame, (CAMERA_WIDTH, CAMERA_HEIGHT))
            
            # Detect hands and process gestures
            hands, cam_preview = self.gesture_detector.find_hands(cam_preview)
            self.process_gesture(hands, cam_preview)
            
            # No cooldown mechanism anymore
            
            # Draw gesture info on camera preview
            self.ui_manager.draw_gesture_info(cam_preview, self.current_gesture, self.show_debug)
            
            # Calculate time left for exit confirmation if needed
            time_left = 0
            if self.exit_requested:
                time_left = 5.0 - (time.time() - self.exit_request_time)
                if time_left <= 0:
                    # If 5 seconds passed without OK confirmation, cancel exit
                    self.exit_requested = False
                    self.current_gesture = "Ieșire anulată - nu s-a confirmat cu OK"
            
            # Show camera preview in debug window if enabled
            if self.show_debug:
                cv2.imshow("Camera Feed", cam_preview)
            elif cv2.getWindowProperty("Camera Feed", cv2.WND_PROP_VISIBLE) >= 1:
                cv2.destroyWindow("Camera Feed")
            
            # Load current image
            current_image = self.image_loader.load_and_resize_image(
                self.ui_manager.image_width, 
                self.ui_manager.image_height
            )
            
            # Create and show main canvas
            canvas = self.ui_manager.create_main_canvas(
                self.show_debug,
                self.fullscreen_mode,
                current_image,
                cam_preview,
                self.image_loader.current_index,
                self.image_loader.get_total_images(),
                self.exit_requested,  # Pass exit request status
                time_left if self.exit_requested else 0  # Pass time left for confirmation
            )
            
            cv2.imshow("Gesture Photo Gallery", canvas)
            
            # Set mouse callback for button handling
            cv2.setMouseCallback("Gesture Photo Gallery", self.mouse_callback)
            
            # Check for exit conditions
            key = cv2.waitKey(1) & 0xFF
            # Only exit with ESC key, closed window, or explicit exit confirmation with OK gesture
            if key == 27 or cv2.getWindowProperty("Gesture Photo Gallery", cv2.WND_PROP_VISIBLE) < 1 or \
               (hasattr(self, 'exit_confirmed') and self.exit_confirmed):
                break
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()
    
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events for buttons."""
        if event == cv2.EVENT_LBUTTONDOWN:
            # Check if button click is on debug toggle
            if self.ui_manager.is_debug_button_clicked(x, y):
                self.show_debug = not self.show_debug
                debug_status = "PORNIT" if self.show_debug else "OPRIT"
                print(f"Debug mode toggled to {debug_status}")
            
            # Check if click is on navigation buttons
            elif self.ui_manager.is_left_button_clicked(x, y):
                # Left button clicked - go to previous image
                self.image_loader.prev_image()
                self.current_gesture = "Buton stânga apăsat - imaginea anterioară"
                print("Previous image (button click)")
            
            elif self.ui_manager.is_right_button_clicked(x, y):
                # Right button clicked - go to next image
                self.image_loader.next_image()
                self.current_gesture = "Buton dreapta apăsat - următoarea imagine"
                print("Next image (button click)")
    
    def process_gesture(self, hands, cam_preview):
        """Process detected hand gestures.
        
        Args:
            hands: List of detected hands
            cam_preview: Camera preview frame
        """
        # Reset gesture tracking if no hands detected
        if not hands or len(hands) == 0:
            # Reset all gesture states when hand disappears from view
            self._reset_gesture_tracking()
            self.last_hand_state = ""
            self.last_debug_state = ""
            self.last_swipe_state = ""
            self.swipe_start_recorded = False
            # Clear any cooldown flags
            if hasattr(self, 'coming_from_debug_gesture'):
                delattr(self, 'coming_from_debug_gesture')
            return
            
        # Process only the first hand detected (right hand preferred)
        # If a hand is detected, focus on gesture detection
        hand = hands[0]
        
        # Check if this is the right hand (cvzone's handType)
        if 'type' in hand and hand['type'] == 'Left':
            # Only process right hand (appears as left in mirrored view)
            return
            
        # Track and handle different gestures
        self._detect_swipe_gesture(hand, cam_preview)
        self._detect_fullscreen_gesture(hand, cam_preview)
        self._detect_debug_gesture(hand, cam_preview)
        
        # If exit is requested, check for cancellation
        if self.exit_requested:
            self._check_exit_cancel(hand, cam_preview)
        else:
            # Only check for exit gesture if not already requested
            self._detect_exit_gesture(hand, cam_preview)
    
    def _reset_gesture_tracking(self):
        """Reset gesture tracking variables when no hand is detected."""
        # Reset gesture tracking for swipe
        if hasattr(self, 'gesture_start_x'):
            delattr(self, 'gesture_start_x')
        if hasattr(self, 'gesture_start_y'):
            delattr(self, 'gesture_start_y')
        if hasattr(self, 'gesture_distance'):
            self.gesture_distance = 0
            
        # Also reset the swipe_completed flag when hand disappears
        # This is crucial for the new behavior: requiring finger to be lifted between swipes
        if hasattr(self, 'swipe_completed'):
            delattr(self, 'swipe_completed')
            
        # Reset swipe tracking
        self.swipe_start_recorded = False
        if hasattr(self, 'swipe_start_pos'):
            delattr(self, 'swipe_start_pos')
        self.last_swipe_state = ""
        
        if self.current_gesture != "None" and not self.exit_requested:
            self.current_gesture = "None"
    
    def _detect_swipe_gesture(self, hand, cam_preview):
        """Detect swipe gestures for navigation.
        Starts only when index finger up, all other fingers in a fist.
        Gesture resets if hand form changes during the swipe.
        
        Args:
            hand: Detected hand
            cam_preview: Camera preview frame
        """
        # Only process if exit is not requested
        if self.exit_requested:
            return
            
        # Check for swipe hand form - index finger up, rest in fist
        is_swipe_form = self.gesture_detector.detect_swipe_hand_form(hand)
        
        # Current state based on the hand form
        current_state = "swipe_form" if is_swipe_form else "other"
        
        # Display debug info
        if self.show_debug and cam_preview is not None:
            swipe_debug = f"Swipe form: {is_swipe_form}"
            cv2.putText(cam_preview, swipe_debug, (10, 80), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        # Get the hand position (index finger tip)
        lmList = hand['lmList']
        if len(lmList) < 21:  # Need all landmarks
            return

        # Use index finger tip position (landmark 8)
        index_tip = lmList[8]
        
        # Check if we're at the left or right border of the frame - don't start a gesture from there
        frame_height, frame_width = cam_preview.shape[:2] if cam_preview is not None else (480, 640)
        border_zone = int(frame_width * 0.2)  # Reduce border zone to make it easier to swipe
        in_border_zone = (index_tip[0] < border_zone or 
                         index_tip[0] > frame_width - border_zone)
        
        # Only reset the gesture if hand form has completely changed (not swipe form anymore)
        # This allows changing direction without canceling the gesture
        if self.last_swipe_state == "swipe_form" and current_state == "other" and self.swipe_start_recorded:
            # Complete the gesture if we've moved far enough
            if hasattr(self, 'swipe_start_pos'):
                x_diff = index_tip[0] - self.swipe_start_pos[0]
                swipe_threshold = int(frame_width * 0.2)  # Reduced threshold for easier detection
                
                if abs(x_diff) >= swipe_threshold:
                    # We've moved far enough, complete the gesture
                    if x_diff > 0:
                        # Swiped right
                        self.image_loader.next_image()
                        self.current_gesture = "Swipe dreapta - Următoarea imagine"
                    else:
                        # Swiped left
                        self.image_loader.prev_image()
                        self.current_gesture = "Swipe stânga - Imaginea anterioară"
                else:
                    # Not moved far enough, just cancel quietly
                    self.current_gesture = "None" if self.current_gesture.startswith("Index ridicat") else self.current_gesture
            
            # Always reset tracking variables to prepare for next gesture            
            self.swipe_start_recorded = False
            if hasattr(self, 'swipe_start_pos'):
                delattr(self, 'swipe_start_pos')
            self.last_swipe_state = ""
            return

        # If we're in swipe form, update status message and track position
        if current_state == "swipe_form":
            # Check if a swipe was recently completed and requires finger to be lifted
            # This prevents multiple swipes in one continuous movement
            if hasattr(self, 'swipe_completed') and self.swipe_completed:
                # Don't start a new swipe until the swipe_completed flag is cleared
                # This flag will be cleared when the hand disappears from view (finger lifted)
                self.current_gesture = "Ridicați degetul pentru un nou swipe"
                return
                
            # If this is the first frame in swipe form, check if we can start a gesture
            if not self.swipe_start_recorded:
                # Only start gesture if not in border zone
                if not in_border_zone:
                    self.swipe_start_pos = index_tip.copy()
                    self.swipe_start_recorded = True
                    self.current_gesture = "Index ridicat - pregătit pentru swipe"
                else:
                    # Don't show a message if in border zone - more natural experience
                    pass
            # If we've recorded start position, check for swipe completion
            elif self.swipe_start_recorded and hasattr(self, 'swipe_start_pos'):
                # Calculate horizontal movement
                x_diff = index_tip[0] - self.swipe_start_pos[0]
                
                # Threshold for swipe detection - reduced for more responsive detection
                swipe_threshold = int(frame_width * 0.2)
                
                # Display swipe progress only in debug mode
                if self.show_debug and cam_preview is not None:
                    # Draw start position
                    cv2.circle(cam_preview, (int(self.swipe_start_pos[0]), int(self.swipe_start_pos[1])), 5, (255, 0, 0), -1)
                    
                    # Draw line to current position (yellow color: 0, 255, 255 in BGR)
                    cv2.line(cam_preview, 
                            (int(self.swipe_start_pos[0]), int(self.swipe_start_pos[1])), 
                            (int(index_tip[0]), int(index_tip[1])), 
                            (0, 255, 255), 2)
                    
                    # Show distance
                    cv2.putText(cam_preview, f"Swipe dist: {abs(x_diff):.0f}/{swipe_threshold}", 
                               (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                    
                    # Show direction
                    direction = "dreapta" if x_diff > 0 else "stânga"
                    cv2.putText(cam_preview, f"Direcție: {direction}", 
                               (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                
                # If swipe distance exceeds threshold, trigger the gesture and allow multiple scrolls
                if abs(x_diff) >= swipe_threshold:
                    # Determine direction
                    if x_diff > 0:
                        # Swipe right - next image
                        self.image_loader.next_image()
                        self.current_gesture = "Swipe dreapta - Următoarea imagine"
                    else:
                        # Swipe left - previous image
                        self.image_loader.prev_image()
                        self.current_gesture = "Swipe stânga - Imaginea anterioară"
                    
                    # NEW BEHAVIOR: Completely reset swipe tracking after a swipe is completed
                    # This requires the finger to be lifted and detected again before allowing another swipe
                    # This prevents accidental multiple scrolls in one continuous movement
                    
                    # Set a flag to indicate swipe is completed and needs to be reset
                    self.swipe_completed = True
                    
                    # Reset tracking for next gesture
                    self.swipe_start_recorded = False
                    if hasattr(self, 'swipe_start_pos'):
                        delattr(self, 'swipe_start_pos')
        
        # Update last state
        else:
            # Reset swipe tracking if not in correct form and we haven't started a swipe
            if not self.swipe_start_recorded:
                self.last_swipe_state = ""
                
        # Update the last state
        self.last_swipe_state = current_state
    
    def _handle_swipe(self):
        """Handle completed swipe gestures."""
        # Handle based on swipe direction
        if self.gesture_distance > 0:
            # Swipe right - next image
            self.image_loader.next_image()
            self.current_gesture = "Swipe dreapta - Următoarea imagine"
        else:
            # Swipe left - previous image
            self.image_loader.prev_image()
            self.current_gesture = "Swipe stânga - Imaginea anterioară"
            
        # Reset for next gesture and set cooldown
        self.gesture_start_x = None
        self.gesture_start_y = None
        self.gesture_cooldown = 15  # Prevent rapid gesture recognition
    
    def _detect_fullscreen_gesture(self, hand, cam_preview):
        """Detect fullscreen toggle gestures.
        Starting form must be a fist which opens to a palm with spread fingers.
        Reverse for going back to normal view.
        Gesture resets if an intermediate state is detected.
        
        Args:
            hand: Detected hand
            cam_preview: Camera preview frame
        """
        # Initialize attributes if they don't exist
        if not hasattr(self, 'coming_from_debug_gesture'):
            self.coming_from_debug_gesture = False
        if not hasattr(self, 'debug_gesture_active'):
            self.debug_gesture_active = False
            
        # Only process if exit is not requested
        if self.exit_requested:
            return
            
        # Check for debug gesture to give it priority
        is_two_fingers = self.gesture_detector.detect_debug_start_form(hand)  # two fingers up
        
        # If we detect a debug gesture start, reset fullscreen gesture tracking
        if is_two_fingers:
            self.last_hand_state = ""
            self.coming_from_debug_gesture = True
            self.debug_gesture_active = True
            self.current_gesture = "Detectat început gest debug - anulare ecran complet"
            return
            
        # Check for specific hand forms for fullscreen toggle
        is_fist = self.gesture_detector.detect_fullscreen_start_form(hand)  # fist form
        is_palm = self.gesture_detector.detect_fullscreen_end_form(hand)    # open palm form
        
        # Determine current hand state
        if is_palm and not is_two_fingers:
            current_state = "palm"  # Palm state for fullscreen ON
        elif is_fist and not is_two_fingers:
            current_state = "fist"  # Fist state for fullscreen OFF
        else:
            current_state = "other"  # Ambiguous hand state
            
        # Display debug information
        if self.show_debug and cam_preview is not None:
            debug_text = f"Fullscreen Gesture: {current_state}"
            cv2.putText(cam_preview, debug_text, (10, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
        
        # If we detect an 'other' state while in the middle of a gesture, reset the gesture
        if self.last_hand_state in ["fist", "palm"] and current_state == "other":
            self.last_hand_state = ""
            self.current_gesture = "Gest ecran complet anulat"
            return
        
        # Only detect transitions between valid states, not continuous same state
        if self.last_hand_state != current_state:
            # If we're coming from a debug gesture, reset and return
            if self.coming_from_debug_gesture or self.debug_gesture_active:
                self.last_hand_state = ""
                self.current_gesture = "Anulat - detectat gest debug"
                self.coming_from_debug_gesture = False
                self.debug_gesture_active = False
                return
                
            # For entering fullscreen: must start from fist and end with palm
            if (self.last_hand_state == "fist" and 
                current_state == "palm" and 
                not self.fullscreen_mode):
                # Fist to palm - enter fullscreen
                self.fullscreen_mode = True
                self.current_gesture = "Pumn → Palmă - Ecran complet activat"
                print("Fullscreen mode ON")
                self.last_hand_state = ""
            
            # For exiting fullscreen: must start from palm and end with fist
            elif (self.last_hand_state == "palm" and 
                  current_state == "fist" and 
                  self.fullscreen_mode):
                # Palm to fist - exit fullscreen
                self.fullscreen_mode = False
                self.current_gesture = "Palmă → Pumn - Ecran normal"
                print("Fullscreen mode OFF")
                self.last_hand_state = ""
            
            # If transitioning to a valid state, show appropriate prompt
            elif current_state == "fist" and self.fullscreen_mode:
                self.current_gesture = "Pumn detectat - pregătit pentru ecran normal"
                self.last_hand_state = current_state
            elif current_state == "palm" and not self.fullscreen_mode:
                self.current_gesture = "Palmă detectată - pregătit pentru ecran complet"
                self.last_hand_state = current_state
                self.last_hand_state = current_state
            elif current_state in ["fist", "palm"]:
                self.last_hand_state = current_state
    
    def _detect_debug_gesture(self, hand, cam_preview):
        """Detect debug mode toggle gestures.
        Starts only with index and middle fingers raised, rest in a fist.
        Ends only when both fingers close into a fist.
        Gesture resets if an intermediate state is detected.
        
        Args:
            hand: Detected hand
            cam_preview: Camera preview frame
        """
        # Only process if exit is not requested
        if self.exit_requested:
            return
            
        # Check for debug gesture form first
        is_two_fingers = self.gesture_detector.detect_two_fingers(hand)
        is_fist = self.gesture_detector.detect_debug_end_form(hand)
        
        # Add extra verification by checking it's not a palm
        is_palm = self.gesture_detector.detect_fullscreen_end_form(hand)
        
        # More robust check for two fingers - must be exactly two fingers up
        if is_two_fingers and not is_palm:
            current_state = "two_fingers"
            # Set flags to prevent fullscreen gesture interference
            self.coming_from_debug_gesture = True
            self.debug_gesture_active = True
            # Reset any fullscreen gesture state
            self.last_hand_state = ""
        elif is_fist:
            current_state = "fist"
            # Only reset debug_gesture_active if we were in a debug gesture
            if self.debug_gesture_active:
                self.debug_gesture_active = False
        else:
            current_state = "other"
            # If we were in a debug gesture but now see something else, reset
            if self.debug_gesture_active:
                self.debug_gesture_active = False
                self.coming_from_debug_gesture = True
        
        # Display debug information if in debug mode
        if self.show_debug and cam_preview is not None:
            debug_text = f"Debug Gesture: {current_state}"
            cv2.putText(cam_preview, debug_text, (10, 140), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
        
        # If we detect an 'other' state while in the middle of a gesture, reset the gesture
        if self.last_debug_state == "two_fingers" and current_state == "other":
            self.last_debug_state = ""
            self.current_gesture = "Gest debug anulat"
            self.coming_from_debug_gesture = True
            return
        
        # Only detect valid transitions
        if self.last_debug_state != current_state:
            # If we're in a valid start state, show feedback
            if current_state == "two_fingers" and self.last_debug_state != "two_fingers":
                self.current_gesture = "Două degete - pregătit pentru debug toggle"
                self.last_debug_state = current_state
                # Reset fullscreen gesture tracking
                self.last_hand_state = ""
                # Set flags to prevent fullscreen gesture
                self.coming_from_debug_gesture = True
                self.debug_gesture_active = True
                return
                
            # Toggle debug mode when transitioning FROM two fingers TO fist position
            elif self.last_debug_state == "two_fingers" and current_state == "fist":
                # Two fingers to fist - toggle debug mode
                self.show_debug = not self.show_debug
                debug_status = "PORNIT" if self.show_debug else "OPRIT"
                self.current_gesture = f"Două degete → Pumn - Debug {debug_status}"
                print(f"Debug mode toggled to {debug_status}")
                self.last_debug_state = ""
                
                # Set flags to prevent fullscreen triggering right after debug gesture
                self.coming_from_debug_gesture = True
                self.debug_gesture_active = False
                
                # Clear any fullscreen gesture state to avoid conflicts
                if hasattr(self, 'fullscreen_gesture_active'):
                    delattr(self, 'fullscreen_gesture_active')
            
            # Update state tracking only for valid states
            elif current_state in ["two_fingers", "fist"]:
                self.last_debug_state = current_state
    
    def _detect_exit_gesture(self, hand, cam_preview):
        """Detect exit gesture - palm with all fingers together sliding to the left.
        The gesture starts with a palm with fingers together, then slides to the left.
        
        Args:
            hand: Detected hand
            cam_preview: Camera preview frame
        """
        # Get landmarks list for position tracking
        lmList = hand['lmList']
        if len(lmList) < 21:  # Need all landmarks
            return
        
        # Check if the hand is in the correct form (palm with fingers together/close palm)
        is_close_palm = self.gesture_detector.detect_close_palm_form(hand)
        
        # Also check if it's a spread palm to clearly differentiate from fullscreen gesture
        is_palm_spread = self.gesture_detector.detect_fullscreen_end_form(hand) and not is_close_palm
        
        # Removed all complex confirmation systems to simplify detection
            
        # Show debug info about palm state without confirmation counts
        if self.show_debug and cam_preview is not None:
            palm_state = "JOINED FINGERS" if is_close_palm else "SPREAD FINGERS" if is_palm_spread else "OTHER"
            cv2.putText(cam_preview, f"Exit palm: {palm_state}", (10, 200), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        # Use center of palm (0) for tracking position
        palm_center = lmList[0]  # Wrist position as palm center
        
        # Simplify exit gesture detection too - no more complex confirmation counters
        # Just proceed if it's clearly a close palm and not a spread palm
        if not is_close_palm or is_palm_spread:
            if self.current_gesture.startswith("Palmă cu degete lipite"):
                self.current_gesture = "Gest ieșire anulat - palmă instabilă"
            
            # Reset exit gesture tracking
            if hasattr(self, 'exit_start_pos'):
                delattr(self, 'exit_start_pos')
            if hasattr(self, 'exit_start_time'):
                delattr(self, 'exit_start_time')
            return
        
        # Start tracking palm position only after palm position has been confirmed stable
        if not hasattr(self, 'exit_start_pos'):
            # We have a confirmed stable palm with joined fingers
            self.exit_start_pos = palm_center.copy()
            self.exit_start_time = time.time()  # Track when the gesture started
            self.current_gesture = "Palmă cu degete lipite CONFIRMATĂ - glisați spre stânga"
            return
        
        # Calculate horizontal movement from starting position
        x_diff = palm_center[0] - self.exit_start_pos[0]
        elapsed_time = time.time() - self.exit_start_time  # How long the gesture has been active
        
        # Set horizontal threshold for left movement
        left_movement_threshold = 100  # pixels for left movement detection
        max_gesture_time = 2.0  # seconds - gesture must be completed within this time
        
        # Display debug info
        if self.show_debug and cam_preview is not None:
            # Draw start position
            cv2.circle(cam_preview, (int(self.exit_start_pos[0]), int(self.exit_start_pos[1])), 5, (255, 0, 0), -1)
            
            # Draw current position
            cv2.circle(cam_preview, (int(palm_center[0]), int(palm_center[1])), 5, (0, 0, 255), -1)
            
            # Draw line between positions
            cv2.line(cam_preview, 
                   (int(self.exit_start_pos[0]), int(self.exit_start_pos[1])), 
                   (int(palm_center[0]), int(palm_center[1])), 
                   (0, 255, 255), 2)  # Yellow line
            
            # Show horizontal movement and time
            cv2.putText(cam_preview, f"Movement: {x_diff:.1f}px (need < -{left_movement_threshold})", (10, 150), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(cam_preview, f"Time: {elapsed_time:.1f}s / {max_gesture_time}s", (10, 170), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        # Check if hand has moved sufficiently to the left (negative x_diff)
        # Using more lenient threshold for easier detection
        if x_diff < -70 and elapsed_time < max_gesture_time:  # Reduced threshold from 100 to 70
            # Simplify the condition for detecting horizontal movement
            y_diff = palm_center[1] - self.exit_start_pos[1]
            # Only check that horizontal movement is dominant
            if abs(x_diff) > abs(y_diff):
                # Gesture completed - request exit
                self.exit_requested = True
                self.exit_request_time = time.time()
                self.current_gesture = "Gest ieșire completat - confirmare ieșire"
                print("Exit gesture succeeded - confirmation needed")
            else:
                # Movement was diagonal or vertical, not primarily horizontal
                self.current_gesture = "Mișcați mâna orizontal spre stânga pentru ieșire"
            
            # Reset tracking for next time regardless
            if hasattr(self, 'exit_start_pos'):
                delattr(self, 'exit_start_pos')
            if hasattr(self, 'exit_start_time'):
                delattr(self, 'exit_start_time')
        
        # If gesture takes too long, reset it
        elif elapsed_time > max_gesture_time:
            if hasattr(self, 'exit_start_pos'):
                delattr(self, 'exit_start_pos')
            if hasattr(self, 'exit_start_time'):
                delattr(self, 'exit_start_time')
    
    def _check_exit_cancel(self, hand, cam_preview):
        """Check for OK sign to confirm exit.
        Looking for thumb and index finger tips touching to form an OK sign.
        If OK sign is detected within 5 seconds after exit request, confirm exit.
        Otherwise, exit will be automatically canceled after 5 seconds.
        
        Args:
            hand: Detected hand
            cam_preview: Camera preview frame
        """
        # Get hand landmarks
        lmList = hand['lmList']
        if len(lmList) < 21:  # Need all landmarks
            return
            
        # For OK sign we check if thumb and index finger tips are close together
        thumb_tip = lmList[4]
        index_tip = lmList[8]
        
        # Calculate distance between thumb and index tips
        distance = np.sqrt((thumb_tip[0] - index_tip[0])**2 + (thumb_tip[1] - index_tip[1])**2)
        
        # Display guidance for exit confirmation
        if self.show_debug and cam_preview is not None:
            # Draw circle between thumb and index
            midpoint = ((thumb_tip[0] + index_tip[0]) // 2, (thumb_tip[1] + index_tip[1]) // 2)
            cv2.circle(cam_preview, midpoint, 10, (0, 255, 255), 2)
            
            # Show distance and threshold
            cv2.putText(cam_preview, f"OK dist: {distance:.1f}", (10, 180), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        # If thumb and index finger form a circle (OK sign)
        if distance < 30:
            # Show confirmatory message
            self.current_gesture = "OK - Confirmare ieșire în curs..."
            
            # Add a small cooldown to confirm gesture intention
            if not hasattr(self, 'ok_sign_start_time'):
                self.ok_sign_start_time = time.time()
            elif time.time() - self.ok_sign_start_time > 0.5:  # Hold OK sign for half a second to confirm
                # Set the exit_confirmed flag to trigger application closure
                self.exit_confirmed = True
                self.current_gesture = "OK - Ieșire confirmată"
                print("Exit confirmed by OK sign")
                delattr(self, 'ok_sign_start_time')
        else:
            # Reset OK sign timer if fingers aren't close
            if hasattr(self, 'ok_sign_start_time'):
                delattr(self, 'ok_sign_start_time')
