"""
Gesture recognizer component for detecting and interpreting hand gestures
"""
import cv2
import numpy as np
import time
import mediapipe as mp
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QImage

class GestureRecognizer(QObject):
    """
    Gesture recognizer class using MediaPipe for hand tracking and gesture detection
    """
    # Define signals that will be emitted when gestures are recognized
    next_signal = pyqtSignal()
    previous_signal = pyqtSignal()
    help_signal = pyqtSignal()
    increase_signal = pyqtSignal()
    decrease_signal = pyqtSignal()
    status_signal = pyqtSignal(str)
    debug_frame_signal = pyqtSignal(QImage)
    debug_text_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        # Initialize MediaPipe solutions
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.mp_hands = mp.solutions.hands
        self.mp_pose = mp.solutions.pose
        
        # Initialize webcam
        self.cap = cv2.VideoCapture(0)
        
        # Initialize MediaPipe Hands and Pose detection
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        # Variable to store current gesture text (for persistent display)
        self.current_gesture_text = ""
        
        # Initialize variables for gesture detection
        self.last_gesture_time = time.time()
        self.gesture_cooldown = 1.0  # Cooldown period between gestures in seconds
        
        # Frame dimensions
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Debug information
        self.debug_info = ""
        
        # Touch detection thresholds
        self.touch_threshold = 0.08  # General threshold for detecting touch
        self.finger_touch_threshold = 0.07  # Increased threshold for better finger-to-finger detection
        
        # State variables for double tap detection (for help gesture)
        self.help_state = "WAITING"  # States: WAITING, FIRST_TAP, BETWEEN_TAPS, SECOND_TAP
        self.first_tap_time = 0
        self.help_max_time = 1.5  # Maximum time to complete double tap (seconds)
        self.help_min_between_time = 0.3  # Minimum time between taps (seconds)
        
        # Zoom mode state
        self.zoom_mode_active = False
        
        # Emit initial status
        self.status_signal.emit("Gesture recognition started")
        
    def release(self):
        """Release camera resources"""
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
    
    def process_frame(self):
        """Process the current frame and detect gestures"""
        if not self.cap.isOpened():
            self.status_signal.emit("Error: Camera not available")
            return
        
        # Read frame from webcam
        ret, frame = self.cap.read()
        if not ret:
            return
        
        # Mirror the frame horizontally for more intuitive interaction
        frame = cv2.flip(frame, 1)
        
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Clone the original BGR frame for drawing landmarks and debug info
        # Using BGR frame for display to keep original camera colors
        debug_frame = frame.copy()
        
        # Reset debug info for detection, but keep gesture recognition message
        old_gesture = None
        if hasattr(self, 'current_gesture_text') and self.current_gesture_text:
            old_gesture = self.current_gesture_text
        self.debug_info = ""
        
        # Process the frame with MediaPipe Hands and Pose
        hand_results = self.hands.process(rgb_frame)
        pose_results = self.pose.process(rgb_frame)
        
        # Clear debug info for this frame but keep it structured
        self.debug_info = "Gesture Recognition Status\n"
        self.debug_info += "======================\n"
        
        # Add persistent gesture text if it exists
        if hasattr(self, 'current_gesture_text') and self.current_gesture_text:
            self.debug_info += "\n------------------------\n"
            self.debug_info += f"{self.current_gesture_text}\n"
            self.debug_info += "------------------------\n"
        
        # Check for gestures if the cooldown period has passed
        current_time = time.time()
        
        if current_time - self.last_gesture_time >= self.gesture_cooldown:
            # Analyze hand poses and detect gestures
            self.detect_gestures(hand_results, pose_results, debug_frame)
        
        # Draw hand landmarks on debug frame
        if hand_results.multi_hand_landmarks:
            for hand_landmarks in hand_results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    debug_frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )
        
        # Only draw the temple point on the right side of the mirrored frame
        if pose_results.pose_landmarks:
            # Extract the temple coordinates (using LEFT_EYE_OUTER since the frame is mirrored)
            pose_landmarks = pose_results.pose_landmarks.landmark
            temple_point = pose_landmarks[self.mp_pose.PoseLandmark.LEFT_EYE_OUTER.value]
            
            # Convert normalized coordinates to pixel coordinates
            h, w, _ = debug_frame.shape
            temple_x = int(temple_point.x * w)
            temple_y = int(temple_point.y * h)
            
            # Draw a circle at the temple location
            cv2.circle(debug_frame, (temple_x, temple_y), 8, (0, 0, 255), -1)  # Larger red circle
            cv2.circle(debug_frame, (temple_x, temple_y), 4, (0, 255, 0), -1)  # Smaller green inner circle
        
        # Convert the BGR debug frame to RGB for QImage
        rgb_debug_frame = cv2.cvtColor(debug_frame, cv2.COLOR_BGR2RGB)
        
        # Convert the debug frame to QImage for display in debug window
        h, w, ch = rgb_debug_frame.shape
        bytes_per_line = ch * w
        convert_to_qt_format = QImage(rgb_debug_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        qt_image = convert_to_qt_format.scaled(640, 480)
        
        # Emit the signals for debug window
        self.debug_frame_signal.emit(qt_image)
        self.debug_text_signal.emit(self.debug_info)

    def detect_gestures(self, hand_results, pose_results, debug_frame):
        """Detect gestures based on hand and pose landmarks"""
        # Initialize empty landmarks for left and right hands
        left_hand = None
        right_hand = None
        pose_landmarks = pose_results.pose_landmarks.landmark if pose_results.pose_landmarks else None
        
        if not hand_results.multi_hand_landmarks:
            return
            
        # Identify left and right hands based on MediaPipe's classification
        for i, hand_landmarks in enumerate(hand_results.multi_hand_landmarks):
            if i >= len(hand_results.multi_handedness):
                continue
                
            # Extract handedness information correctly
            handedness = hand_results.multi_handedness[i].classification[0].label
            landmarks = hand_landmarks.landmark
            
            # Store landmarks based on handedness - corrected assignment
            if handedness == "Left":  # Left hand in the camera view
                left_hand = landmarks
                self.debug_info += "Hand detected: LEFT\n"
            elif handedness == "Right":  # Right hand in the camera view
                right_hand = landmarks
                self.debug_info += "Hand detected: RIGHT\n"
        
        # Add zoom mode status if active
        if self.zoom_mode_active:
            self.debug_info += "ZOOM MODE ACTIVE\n"
        
        # Detect Help gesture (double tap on right temple)
        if right_hand:
            self.detect_help_gesture(right_hand, pose_landmarks)
        
        # Detect Increase/Decrease gestures if both hands are visible
        if left_hand and right_hand:
            self.detect_zoom_gestures(left_hand, right_hand)
        
        # Detect Next gesture (touch left hip with right index)
        if right_hand and pose_landmarks:
            self.detect_next_gesture(right_hand, pose_landmarks)
            
        # Detect Previous gesture (touch right hip with right index)
        if right_hand and pose_landmarks:
            self.detect_previous_gesture(right_hand, pose_landmarks)

    def calculate_distance(self, point1, point2):
        """Calculate Euclidean distance between two points in 3D space"""
        return np.sqrt((point1.x - point2.x)**2 + 
                    (point1.y - point2.y)**2 + 
                    (point1.z - point2.z)**2)

    def is_finger_extended(self, landmarks, finger_tip_idx, finger_pip_idx):
        """Check if a finger is extended by comparing the y-coordinates of tip and PIP joint"""
        return landmarks[finger_tip_idx].y < landmarks[finger_pip_idx].y

    def update_debug_and_trigger(self, gesture_name):
        """Update the last gesture time, add to debug info, and emit status signal"""
        self.last_gesture_time = time.time()
        
        # Store the current gesture text for persistent display
        self.current_gesture_text = f"GESTURE RECOGNIZED: {gesture_name}"
        
        # Make the gesture detection more prominent in the debug window
        self.debug_info += "\n------------------------\n"
        self.debug_info += f"GESTURE RECOGNIZED: {gesture_name}\n"
        self.debug_info += "------------------------\n"
        
        self.status_signal.emit(f"Gesture: {gesture_name}")
        
    def calculate_temple_distance(self, index_tip, temple):
        """Calculate 2D distance between finger tip and temple (ignoring Z)"""
        # Focus mainly on X-Y plane as depth (Z) is less reliable
        return np.sqrt((index_tip.x - temple.x)**2 + (index_tip.y - temple.y)**2) * 1.5
    
    def detect_help_gesture(self, right_hand, pose_landmarks):
        """Detect Help gesture: Double tap on right temple with right index finger"""
        # Make sure we have pose landmarks for the temple
        if not pose_landmarks:
            return
            
        # Get the coordinates of the right index finger tip and the temple area
        # Using LEFT_EYE_OUTER landmark since the frame is mirrored
        index_tip = right_hand[8]  # Index finger tip
        temple = pose_landmarks[self.mp_pose.PoseLandmark.LEFT_EYE_OUTER.value]  # Temple area in mirrored view
        
        # Define temple threshold for help gesture (more sensitive than general touch)  
        temple_threshold = 0.1
        
        # Use specialized 2D distance calculation for temple touch
        distance = self.calculate_temple_distance(index_tip, temple)
        
        # Add debug info for temple distance
        self.debug_info += f"Temple touch distance: {distance:.4f} (threshold: {temple_threshold:.4f})\n"
        
        # State machine for double tap detection
        current_time = time.time()
        
        # Check for timeout in any intermediate state
        if self.help_state != "WAITING" and current_time - self.first_tap_time > self.help_max_time:
            self.help_state = "WAITING"
            self.debug_info += "Help gesture timed out\n"
        
        # State machine logic
        if self.help_state == "WAITING":
            # Check for first tap
            if distance < temple_threshold:
                self.help_state = "FIRST_TAP"
                self.first_tap_time = current_time
                self.debug_info += "First tap detected\n"
        
        elif self.help_state == "FIRST_TAP":
            # Check if finger is moved away from temple
            if distance > temple_threshold * 1.5:
                self.help_state = "BETWEEN_TAPS"
                self.debug_info += "Finger moved away from temple\n"
        
        elif self.help_state == "BETWEEN_TAPS":
            # Check minimum time between taps
            time_between = current_time - self.first_tap_time
            if time_between >= self.help_min_between_time:
                # Check for second tap
                if distance < temple_threshold:
                    self.help_state = "SECOND_TAP"
                    self.debug_info += "Second tap detected\n"
                    # Emit help signal
                    self.help_signal.emit()
                    self.update_debug_and_trigger("Help (Double tap on right temple)")
            else:
                self.debug_info += f"Waiting for minimum tap interval: {time_between:.2f}s\n"
        
        elif self.help_state == "SECOND_TAP":
            # Reset state if finger moved away
            if distance > temple_threshold * 1.5:
                self.help_state = "WAITING"
                self.debug_info += "Help gesture completed\n"
    
    def detect_zoom_mode(self, left_hand):
        """Detect Zoom Mode Activation: Left hand palm facing user with all fingers spread"""
        # Check if all fingers are extended
        thumb_extended = left_hand[4].y < left_hand[3].y  # Thumb tip is higher than thumb IP
        index_extended = self.is_finger_extended(left_hand, 8, 6)  # Index tip vs PIP
        middle_extended = self.is_finger_extended(left_hand, 12, 10)  # Middle tip vs PIP
        ring_extended = self.is_finger_extended(left_hand, 16, 14)  # Ring tip vs PIP
        pinky_extended = self.is_finger_extended(left_hand, 20, 18)  # Pinky tip vs PIP
        
        # Check if fingers are sufficiently spread apart
        thumb_to_index = self.calculate_distance(left_hand[4], left_hand[8])
        index_to_middle = self.calculate_distance(left_hand[8], left_hand[12])
        middle_to_ring = self.calculate_distance(left_hand[12], left_hand[16])
        ring_to_pinky = self.calculate_distance(left_hand[16], left_hand[20])
        
        # Palm facing detection - simplified check based on relative z positions of palm and knuckles
        palm_point = left_hand[0]  # Palm base landmark
        index_mcp = left_hand[5]  # Index finger MCP (knuckle)
        
        # Check if palm is facing camera (palm point should be further from camera than knuckles)
        palm_facing = palm_point.z < index_mcp.z
        
        # Simplified - removed detailed debug information
        
        # All conditions must be true to activate zoom mode
        all_fingers_extended = thumb_extended and index_extended and middle_extended and ring_extended and pinky_extended
        fingers_spread = thumb_to_index > 0.05 and index_to_middle > 0.03 and middle_to_ring > 0.03 and ring_to_pinky > 0.03
        
        if all_fingers_extended and fingers_spread and palm_facing and not self.zoom_mode_active:
            # Activate zoom mode
            self.zoom_mode_active = True
            self.update_debug_and_trigger("Zoom Mode Activated")
        elif not (all_fingers_extended and fingers_spread and palm_facing) and self.zoom_mode_active:
            # Deactivate zoom mode
            self.zoom_mode_active = False
            self.update_debug_and_trigger("Zoom Mode Deactivated")
    
    def detect_zoom_gestures(self, left_hand, right_hand):
        """Detect Increase/Decrease gestures based on finger touches"""
        # Get finger tips
        right_index_tip = right_hand[8]  # Right hand index finger tip
        left_index_tip = left_hand[8]  # Left hand index finger tip
        left_pinky_tip = left_hand[20]  # Left hand pinky finger tip
        
        # Calculate distances
        right_to_left_index = self.calculate_distance(right_index_tip, left_index_tip)
        right_to_left_pinky = self.calculate_distance(right_index_tip, left_pinky_tip)
        
        # Add debug info for distances
        self.debug_info += f"Index-to-Index distance: {right_to_left_index:.4f} (threshold: {self.finger_touch_threshold:.4f})\n"
        self.debug_info += f"Index-to-Pinky distance: {right_to_left_pinky:.4f} (threshold: {self.finger_touch_threshold:.4f})\n"
        
        # Detect Increase/Fullscreen - right index touches left index
        if right_to_left_index < self.finger_touch_threshold:
            self.increase_signal.emit()
            self.update_debug_and_trigger("Fullscreen Mode Activated")
        
        # Detect Decrease/Normal view - right index touches left pinky
        elif right_to_left_pinky < self.finger_touch_threshold:
            self.decrease_signal.emit()
            self.update_debug_and_trigger("Normal View Restored")
    
    def detect_next_gesture(self, right_hand, pose_landmarks):
        """Detect Next gesture: touch left hip with right index finger"""
        # Get the coordinates of the right index finger tip and the left hip
        index_tip = right_hand[8]  # Index finger tip
        left_hip = pose_landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
        
        # Calculate distance
        distance = self.calculate_distance(index_tip, left_hip)
        
        # Detect touch
        if distance < self.touch_threshold:
            self.next_signal.emit()
            self.update_debug_and_trigger("Next (Left Hip Touch)")
    
    def detect_previous_gesture(self, right_hand, pose_landmarks):
        """Detect Previous gesture: touch right hip with right index finger"""
        # Get the coordinates of the right index finger tip and the right hip
        index_tip = right_hand[8]  # Index finger tip
        right_hip = pose_landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value]
        
        # Calculate distance
        distance = self.calculate_distance(index_tip, right_hip)
        
        # Detect touch
        if distance < self.touch_threshold:
            self.previous_signal.emit()
            self.update_debug_and_trigger("Previous (Right Hip Touch)")
