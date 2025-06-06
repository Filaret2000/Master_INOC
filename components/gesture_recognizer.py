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
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
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
        self.finger_touch_threshold = 0.05  # More precise threshold for finger-to-finger touches
        
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
        success, frame = self.cap.read()
        if not success:
            self.status_signal.emit("Error: Couldn't read frame from camera")
            return
        
        # Mirror the frame horizontally for more intuitive interaction
        frame = cv2.flip(frame, 1)
        
        # Convert the frame from BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame with MediaPipe Hands and Pose
        hand_results = self.hands.process(frame_rgb)
        pose_results = self.pose.process(frame_rgb)
        
        # Create a copy of the frame for visualization
        debug_frame = frame.copy()
        
        # Clear debug info for this frame - simplified version
        self.debug_info = "Gesture Recognition Status\n"
        self.debug_info += "======================\n"
        
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
        
        # Draw pose landmarks on debug frame
        if pose_results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                debug_frame,
                pose_results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing_styles.get_default_pose_landmarks_style()
            )
        
        # Convert the debug frame to QImage for display in debug window
        h, w, ch = debug_frame.shape
        bytes_per_line = ch * w
        convert_to_qt_format = QImage(debug_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        qt_image = convert_to_qt_format.scaled(640, 480)
        
        # Emit the signals for debug window
        self.debug_frame_signal.emit(qt_image)
        self.debug_text_signal.emit(self.debug_info)

    def detect_gestures(self, hand_results, pose_results, debug_frame):
        """Detect various gestures based on hand and pose landmarks"""
        # Check if we have both hand landmarks and pose landmarks
        if not hand_results.multi_hand_landmarks or not pose_results.pose_landmarks:
            self.debug_info += "No hand or pose landmarks detected\n"
            return
        
        # Get pose landmarks
        pose_landmarks = pose_results.pose_landmarks.landmark
        
        # Process hands
        left_hand = None
        right_hand = None
        
        # Identify left and right hands based on MediaPipe's classification
        for i, hand_landmarks in enumerate(hand_results.multi_hand_landmarks):
            if i >= len(hand_results.multi_handedness):
                continue
                
            # Extract handedness information correctly
            handedness = hand_results.multi_handedness[i].classification[0].label
            landmarks = hand_landmarks.landmark
            
            # Store landmarks based on handedness
            if handedness == "Left":  # This is actually right hand in mirrored view
                right_hand = landmarks
            elif handedness == "Right":  # This is actually left hand in mirrored view
                left_hand = landmarks
        
        # Add simplified debug information about detected hands
        self.debug_info += f"Left hand detected: {left_hand is not None}\n"
        self.debug_info += f"Right hand detected: {right_hand is not None}\n"
        if self.zoom_mode_active:
            self.debug_info += f"ZOOM MODE ACTIVE\n"
        
        # Detect Help gesture (double tap on right temple)
        if right_hand:
            self.detect_help_gesture(right_hand, pose_landmarks)
        
        # Detect Zoom Mode Activation (left palm facing camera)
        if left_hand:
            self.detect_zoom_mode(left_hand)
            
        # If zoom mode is active, detect zoom in/out gestures
        if self.zoom_mode_active and left_hand and right_hand:
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
        self.debug_info += f"GESTURE DETECTED: {gesture_name}\n"
        self.status_signal.emit(f"Gesture: {gesture_name}")
        
    def detect_help_gesture(self, right_hand, pose_landmarks):
        """Detect Help gesture: Double tap on right temple with right index finger"""
        # Get the coordinates of the right index finger tip and the right temple area
        index_tip = right_hand[8]  # Index finger tip
        temple = pose_landmarks[self.mp_pose.PoseLandmark.RIGHT_EYE_OUTER.value]  # Right temple area
        
        # Calculate distance between index tip and temple
        distance = self.calculate_distance(index_tip, temple)
        
        # Simplified debug info - removed detailed measurements
        
        # State machine for double tap detection
        current_time = time.time()
        
        # Check for timeout in any intermediate state
        if self.help_state != "WAITING" and current_time - self.first_tap_time > self.help_max_time:
            # Simplified - removed detailed state tracking
            self.help_state = "WAITING"
        
        # State machine logic
        if self.help_state == "WAITING":
            # Check for first tap
            if distance < self.touch_threshold:
                self.help_state = "FIRST_TAP"
                self.first_tap_time = current_time
                # Simplified - removed detailed state tracking
        
        elif self.help_state == "FIRST_TAP":
            # Check if finger is moved away from temple
            if distance > self.touch_threshold * 1.5:
                self.help_state = "BETWEEN_TAPS"
                # Simplified - removed detailed state tracking
        
        elif self.help_state == "BETWEEN_TAPS":
            # Check minimum time between taps
            time_between = current_time - self.first_tap_time
            if time_between >= self.help_min_between_time:
                # Check for second tap
                if distance < self.touch_threshold:
                    self.help_state = "SECOND_TAP"
                    # Simplified - removed detailed state tracking
                    # Emit help signal
                    self.help_signal.emit()
                    self.update_debug_and_trigger("Help (Double tap on right temple)")
            else:
                pass  # Simplified - removed detailed timing information
        
        elif self.help_state == "SECOND_TAP":
            # Reset state if finger moved away
            if distance > self.touch_threshold * 1.5:
                self.help_state = "WAITING"
                # Simplified - removed detailed state tracking
    
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
        """Detect Zoom In/Out gestures when zoom mode is active"""
        # Only process these gestures if zoom mode is active
        if not self.zoom_mode_active:
            return
        
        # Get finger tips
        right_index_tip = right_hand[8]  # Right hand index finger tip
        left_index_tip = left_hand[8]  # Left hand index finger tip
        left_pinky_tip = left_hand[20]  # Left hand pinky finger tip
        
        # Calculate distances
        right_to_left_index = self.calculate_distance(right_index_tip, left_index_tip)
        right_to_left_pinky = self.calculate_distance(right_index_tip, left_pinky_tip)
        
        # Simplified - removed detailed debug information
        
        # Detect Zoom In (Increase) - right index touches left index
        if right_to_left_index < self.finger_touch_threshold:
            self.increase_signal.emit()
            self.update_debug_and_trigger("Zoom In (Increase)")
        
        # Detect Zoom Out (Decrease) - right index touches left pinky
        elif right_to_left_pinky < self.finger_touch_threshold:
            self.decrease_signal.emit()
            self.update_debug_and_trigger("Zoom Out (Decrease)")
    
    def detect_next_gesture(self, right_hand, pose_landmarks):
        """Detect Next gesture: touch left hip with right index finger"""
        # Get the coordinates of the right index finger tip and the left hip
        index_tip = right_hand[8]  # Index finger tip
        left_hip = pose_landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
        
        # Calculate distance
        distance = self.calculate_distance(index_tip, left_hip)
        
        # Simplified - removed detailed debug information
        
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
        
        # Simplified - removed detailed debug information
        
        # Detect touch
        if distance < self.touch_threshold:
            self.previous_signal.emit()
            self.update_debug_and_trigger("Previous (Right Hip Touch)")
