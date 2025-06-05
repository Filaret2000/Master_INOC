"""
Gesture Recognizer component that processes camera input and detects gestures
"""
import cv2
import numpy as np
import mediapipe as mp
import time
from PyQt5.QtCore import QObject, pyqtSignal, QThread, Qt
from PyQt5.QtGui import QImage

class GestureRecognizer(QObject):
    # Define signals for each gesture command
    next_signal = pyqtSignal()
    previous_signal = pyqtSignal()
    increase_signal = pyqtSignal()  # Signal for increase gesture in zoom mode
    decrease_signal = pyqtSignal()  # Signal for decrease gesture in zoom mode
    help_signal = pyqtSignal()
    debug_frame_signal = pyqtSignal(QImage)
    debug_text_signal = pyqtSignal(str)  # Signal for sending debug text to debug window
    status_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        # Initialize MediaPipe Pose and Hands modules
        self.mp_pose = mp.solutions.pose
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Initialize pose and hands detectors
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5)
            
        self.hands = self.mp_hands.Hands(
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            max_num_hands=2)
        
        # Initialize camera
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.status_signal.emit("Error: Could not open camera")
            return
            
        # Set camera resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Gesture recognition parameters
        self.touch_threshold = 0.08  # Distance threshold for touch detection
        self.sequence = []  # Store sequence of touches
        self.sequence_start_time = 0
        self.sequence_timeout = 2.0  # Seconds before sequence resets
        self.last_touch_time = 0  # Track time of last touch for double tap detection
        self.double_tap_threshold = 0.8  # Maximum seconds between taps to be considered a double tap
        
        # Starting pose detection
        self.in_starting_pose = False  # Flag to track if hand is in starting pose
        self.waiting_for_gesture = False  # Flag to track if we're waiting for a gesture after starting pose
        self.gesture_performed = False  # Flag to track if a gesture was performed
        
        # Special mode for increase/decrease gestures
        self.in_zoom_mode = False  # Flag to track if both hands are in the special zoom mode pose
        
        # Track if right hand was visible in previous frame
        self.right_hand_was_visible = False
        self.hands_results = None  # Store hand detection results
        
        # State tracking variables
        self.last_gesture = None
        self.gesture_start_time = 0
        self.sequence = []
        self.sequence_start_time = 0
        self.touch_threshold = 0.1  # Distance threshold for touch detection
        
        # Debug info
        self.debug_info = ""
        
        # Start the worker thread
        self.running = True
        
    def process_frame(self):
        if not self.cap.isOpened():
            return
            
        ret, frame = self.cap.read()
        if not ret:
            return
            
        # Flip the frame horizontally for a selfie-view
        frame = cv2.flip(frame, 1)
        
        # Convert the BGR image to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        pose_results = self.pose.process(rgb_frame)
        self.hands_results = self.hands.process(rgb_frame)
        hands_results = self.hands_results
        
        # Create debug frame
        debug_frame = frame.copy()
        
        # Draw pose landmarks
        if pose_results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                debug_frame,
                pose_results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style())
        
        # Draw hand landmarks
        if hands_results.multi_hand_landmarks:
            for hand_landmarks in hands_results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    debug_frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_hand_landmarks_style())
        
        # Process gestures if both pose and hands are detected
        if pose_results.pose_landmarks and hands_results.multi_hand_landmarks:
            self.process_gestures(pose_results.pose_landmarks, hands_results.multi_hand_landmarks)
        
        # Send debug info to debug window text area instead of drawing on frame
        self.debug_text_signal.emit(self.debug_info)
        
        # Convert to QImage for display in debug window
        h, w, ch = debug_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(debug_frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
        # Emit the debug frame without text overlay
        self.debug_frame_signal.emit(qt_image)
    
    def detect_starting_pose(self, right_hand):
        """Detect if right hand is in starting pose: fist with index finger pointing up"""
        if right_hand is None:
            return False
            
        # Get landmarks for each finger
        index_tip = right_hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        index_pip = right_hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_PIP]
        index_mcp = right_hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_MCP]
        
        # These should be curled in a fist
        middle_tip = right_hand.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
        ring_tip = right_hand.landmark[self.mp_hands.HandLandmark.RING_FINGER_TIP]
        pinky_tip = right_hand.landmark[self.mp_hands.HandLandmark.PINKY_TIP]
        
        # Knuckle positions for reference
        middle_mcp = right_hand.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
        ring_mcp = right_hand.landmark[self.mp_hands.HandLandmark.RING_FINGER_MCP]
        pinky_mcp = right_hand.landmark[self.mp_hands.HandLandmark.PINKY_MCP]
        
        # Check if index is extended (pointing up) - more reliable check
        # The index finger should be significantly higher than the knuckle
        index_extended = index_tip.y < index_mcp.y - 0.1
        
        # Check if other fingers are curled in (should be below their respective MCPs)
        fingers_curled = (
            middle_tip.y > middle_mcp.y and
            ring_tip.y > ring_mcp.y and
            pinky_tip.y > pinky_mcp.y
        )
        
        is_in_starting_pose = index_extended and fingers_curled
        
        return is_in_starting_pose
        
    def detect_left_hand_spread_fingers(self, left_hand):
        """Detect if left hand has all fingers spread with palm facing the user"""
        if left_hand is None:
            return False
            
        # Get landmarks for each finger tip
        thumb_tip = left_hand.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
        index_tip = left_hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        middle_tip = left_hand.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
        ring_tip = left_hand.landmark[self.mp_hands.HandLandmark.RING_FINGER_TIP]
        pinky_tip = left_hand.landmark[self.mp_hands.HandLandmark.PINKY_TIP]
        
        # Get landmarks for each finger MCP (knuckle)
        thumb_mcp = left_hand.landmark[self.mp_hands.HandLandmark.THUMB_CMC]
        index_mcp = left_hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_MCP]
        middle_mcp = left_hand.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
        ring_mcp = left_hand.landmark[self.mp_hands.HandLandmark.RING_FINGER_MCP]
        pinky_mcp = left_hand.landmark[self.mp_hands.HandLandmark.PINKY_MCP]
        
        # Check if all fingers are extended (tips should be above the knuckles)
        fingers_extended = (
            thumb_tip.y < thumb_mcp.y and
            index_tip.y < index_mcp.y and
            middle_tip.y < middle_mcp.y and
            ring_tip.y < ring_mcp.y and
            pinky_tip.y < pinky_mcp.y
        )
        
        # Check if fingers are reasonably spread apart
        # Calculate distances between adjacent fingertips
        thumb_index_dist = abs(thumb_tip.x - index_tip.x)
        index_middle_dist = abs(index_tip.x - middle_tip.x)
        middle_ring_dist = abs(middle_tip.x - ring_tip.x)
        ring_pinky_dist = abs(ring_tip.x - pinky_tip.x)
        
        # Fingers should have some minimum distance between them
        min_dist = 0.03
        fingers_spread = (
            thumb_index_dist > min_dist and
            index_middle_dist > min_dist and
            middle_ring_dist > min_dist and
            ring_pinky_dist > min_dist
        )
        
        return fingers_extended and fingers_spread
        
    def detect_left_hand_fist(self, left_hand):
        """Detect if left hand is in a fist"""
        if left_hand is None:
            return False
            
        # Get landmarks for each finger tip
        index_tip = left_hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        middle_tip = left_hand.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
        ring_tip = left_hand.landmark[self.mp_hands.HandLandmark.RING_FINGER_TIP]
        pinky_tip = left_hand.landmark[self.mp_hands.HandLandmark.PINKY_TIP]
        
        # Get landmarks for palm
        wrist = left_hand.landmark[self.mp_hands.HandLandmark.WRIST]
        middle_mcp = left_hand.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
        
        # Fingers should be curled in (tips should be below the middle of palm)
        palm_mid_y = (wrist.y + middle_mcp.y) / 2
        fingers_curled = (
            index_tip.y > palm_mid_y and
            middle_tip.y > palm_mid_y and
            ring_tip.y > palm_mid_y and
            pinky_tip.y > palm_mid_y
        )
        
        return fingers_curled
        
    def detect_left_hand_facing_user(self, left_hand):
        """Detect if left hand is facing the user with fingers spread"""
        if left_hand is None:
            return False
            
        # For the hand to be facing the user, the z-coordinates (depth) of the knuckles
        # should be closer to the camera than the wrist
        wrist_z = left_hand.landmark[self.mp_hands.HandLandmark.WRIST].z
        mcp_z = left_hand.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP].z
        
        # Check if palm is facing the camera (z-depth difference)
        is_palm_facing = mcp_z < wrist_z
        
        # Get landmarks for each finger tip
        index_tip = left_hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        middle_tip = left_hand.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
        ring_tip = left_hand.landmark[self.mp_hands.HandLandmark.RING_FINGER_TIP]
        pinky_tip = left_hand.landmark[self.mp_hands.HandLandmark.PINKY_TIP]
        
        # Get landmarks for each finger MCP (knuckle)
        index_mcp = left_hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_MCP]
        middle_mcp = left_hand.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
        ring_mcp = left_hand.landmark[self.mp_hands.HandLandmark.RING_FINGER_MCP]
        pinky_mcp = left_hand.landmark[self.mp_hands.HandLandmark.PINKY_MCP]
        
        # Check if fingers are spread
        is_index_extended = index_tip.y < index_mcp.y
        is_middle_extended = middle_tip.y < middle_mcp.y
        is_ring_extended = ring_tip.y < ring_mcp.y
        is_pinky_extended = pinky_tip.y < pinky_mcp.y
        
        # Consider hand to be facing user with spread fingers if palm is facing and at least 3 fingers are extended
        fingers_extended = sum([is_index_extended, is_middle_extended, is_ring_extended, is_pinky_extended])
        
        self.debug_info += f"\nLeft hand facing: {is_palm_facing}, fingers extended: {fingers_extended}"
        return is_palm_facing and fingers_extended >= 3
            
    def process_gestures(self, pose_landmarks, hand_landmarks):
        """Process detected hand and pose landmarks for gesture recognition"""
        # Find right hand and left hand
        right_hand = None
        left_hand = None
        right_index_tip = None
        
        # Debug information
        self.debug_info = f"Detected {len(hand_landmarks)} hand(s)"
        
        # Use multi_handedness from hands_results instead
        if hasattr(self.hands_results, 'multi_handedness') and self.hands_results.multi_handedness:
            for i, handedness in enumerate(self.hands_results.multi_handedness):
                # Check if we have enough hand landmarks
                if i < len(hand_landmarks):
                    # Get handedness label (LEFT or RIGHT)
                    hand_label = handedness.classification[0].label
                    
                    if hand_label == "Right":
                        right_hand = hand_landmarks[i]
                        # Get right index finger tip for touch detection
                        if right_hand:
                            right_index_tip = right_hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                        self.debug_info += "\nRight hand detected"
                    else:  # Left hand
                        left_hand = hand_landmarks[i]
                        self.debug_info += "\nLeft hand detected"
        
        # If no pose landmarks detected, can't do anything with pose, but don't reset sequence
        if not pose_landmarks:
            self.debug_info += "\nNo pose landmarks detected"
            return
            
        # Check for starting pose (right hand fist with index finger pointing up)
        is_in_starting_pose = False
        if right_hand:
            is_in_starting_pose = self.detect_starting_pose(right_hand)
            if is_in_starting_pose:
                self.debug_info += "\nStarting pose detected"
        
        # Check for left hand facing user with fingers spread
        left_hand_facing_user = False
        if left_hand:
            left_hand_facing_user = self.detect_left_hand_facing_user(left_hand)
            if left_hand_facing_user:
                self.debug_info += "\nLeft hand facing user detected"
        
        # Special gesture mode logic - requires left hand facing user with fingers spread
        if is_in_starting_pose and left_hand_facing_user and self.waiting_for_gesture:
            if not self.in_zoom_mode:
                self.in_zoom_mode = True
                self.debug_info += "\n*** ENTERING INCREASE/DECREASE MODE ***"
                self.status_signal.emit("Increase/decrease mode activated")
        
        # Track if right hand was visible in the previous frame
        self.right_hand_was_visible = (right_hand is not None)
        
        # STATE MACHINE LOGIC:
        # 1. If right hand is missing - CONTINUE looking for gestures, don't reset
        # 2. If right hand is visible but NOT in starting pose - ONLY THEN reset the sequence
        # 3. After a gesture is performed, require starting pose again before next gesture
        
        # Important states to track:
        # - waiting_for_gesture: We've seen the starting pose and are waiting for a gesture
        # - gesture_performed: We've performed a gesture and need to see starting pose again
        
        # Case 1: If right hand is visible but NOT in starting pose, reset sequence
        if right_hand and not is_in_starting_pose and self.waiting_for_gesture:
            self.debug_info += "\nHand visible but NOT in starting pose - resetting sequence"
            self.sequence = []
            
        # Case 2: If we haven't seen starting pose yet or need to see it again after gesture
        if not self.waiting_for_gesture or self.gesture_performed:
            if is_in_starting_pose:
                # Starting pose detected
                self.waiting_for_gesture = True
                if self.gesture_performed:
                    self.gesture_performed = False
                    self.debug_info += "\nStarting pose detected again after gesture. Ready for new gesture."
                    self.status_signal.emit("Ready for new gesture!")
                else:
                    self.debug_info += "\nStarting pose detected. Ready for gesture."
                    self.status_signal.emit("Ready for gesture!")
            else:
                # No starting pose yet
                if self.gesture_performed:
                    self.debug_info += "\nWaiting for starting pose again before next gesture"
                else:
                    self.debug_info += "\nWaiting for starting pose..."
                return  # Exit early if we need to see starting pose first
            
        # Process gestures only if we're in the waiting_for_gesture state
        if self.waiting_for_gesture:
            current_time = time.time()
            
            # Check if the finger is touching any part
            current_touch = None
            if right_index_tip:  # Only try touch detection if we have a right index finger
                current_touch = self.detect_touch(right_index_tip, pose_landmarks, left_hand)
            
            self.debug_info += f"\nCurrent touch: {current_touch if current_touch else 'None'}"
            
            # Reset sequence if timeout has passed
            if self.sequence and (current_time - self.sequence_start_time > self.sequence_timeout):
                self.debug_info += "\nSequence timeout, resetting"
                self.sequence = []
                # We don't reset waiting_for_gesture even when timeout happens
                # This allows gestures to continue until hand explicitly leaves the starting pose
                return
            
            # If a touch is detected
            if current_touch:
                # If this is a new touch or a repeat of the last touch after a brief pause
                if not self.sequence or (
                    current_touch == self.sequence[-1] and 
                    current_time - self.last_touch_time > 0.3 and  # Ignore immediate repeats (less than 0.3s)
                    current_time - self.last_touch_time < self.double_tap_threshold  # Must be within double tap window
                ) or (
                    current_touch != self.sequence[-1]  # Different touch
                ):
                    # If this is the first touch in a sequence, record the start time
                    if not self.sequence:
                        self.sequence_start_time = current_time
                    
                    # Add to sequence and update last touch time
                    self.sequence.append(current_touch)
                    self.last_touch_time = current_time
                    
                    # Update debug info
                    time_since_last = ""
                    if len(self.sequence) > 1:
                        time_since_last = f"\nTime since last: {current_time - self.sequence_start_time:.2f}s"
                    
                    self.debug_info += f"\nTouch detected: {current_touch}\nSequence: {self.sequence}{time_since_last}"
                    self.status_signal.emit(f"Touch: {current_touch}")
                
                # Check if sequence matches any command
                self.check_command_sequence()
            else:
                # If no touch is detected but we have a sequence in progress
                if self.sequence:
                    time_since_last_touch = current_time - self.last_touch_time
                    if time_since_last_touch > 1.5:  # 1.5 seconds with no touches
                        self.debug_info += "\nNo touch detected for too long, resetting sequence"
                        self.sequence = []
                        # Don't reset waiting_for_gesture - we only do that when hand is explicitly not in starting pose
                        # This is the key change to maintain gesture recognition capability
    
    def detect_touch(self, right_index_tip, pose_landmarks, left_hand):
        """Detect if right index finger is touching a specific body part or left hand"""
        
        # Get 3D coordinates of right index finger tip
        tip_x, tip_y, tip_z = right_index_tip.x, right_index_tip.y, right_index_tip.z
        
        # Check for touches of left hand fingers in zoom mode
        if self.in_zoom_mode and left_hand:
            # Check if touching left index finger (for increase gesture)
            left_index_tip = left_hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
            left_index_distance = ((tip_x - left_index_tip.x) ** 2 + (tip_y - left_index_tip.y) ** 2) ** 0.5
            if left_index_distance < self.touch_threshold:
                self.debug_info += f"\nLeft index finger touched (distance: {left_index_distance:.3f})"
                return "left_index_tip"
            
            # Check if touching left pinky finger (for decrease gesture)
            left_pinky_tip = left_hand.landmark[self.mp_hands.HandLandmark.PINKY_TIP]
            left_pinky_distance = ((tip_x - left_pinky_tip.x) ** 2 + (tip_y - left_pinky_tip.y) ** 2) ** 0.5
            if left_pinky_distance < self.touch_threshold:
                self.debug_info += f"\nLeft pinky finger touched (distance: {left_pinky_distance:.3f})"
                return "left_pinky_tip"
        
        # Enhanced detection for right hip - for PREVIOUS gesture
        right_hip = pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_HIP]
        # Use a slightly larger threshold for hip detection
        hip_threshold = self.touch_threshold * 1.5
        hip_distance = ((tip_x - right_hip.x) ** 2 + (tip_y - right_hip.y) ** 2) ** 0.5
        if hip_distance < hip_threshold:
            self.debug_info += f"\nRight hip touched (distance: {hip_distance:.3f})"
            return "right_hip"
        
        # Enhanced detection for left hip - for NEXT gesture
        left_hip = pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_HIP]
        hip_distance = ((tip_x - left_hip.x) ** 2 + (tip_y - left_hip.y) ** 2) ** 0.5
        if hip_distance < hip_threshold:
            self.debug_info += f"\nLeft hip touched (distance: {hip_distance:.3f})"
            return "left_hip"
        
        # MediaPipe's RIGHT_EYE is actually on the left side of the image when the person is facing the camera
        # So for the user's right temple (from their perspective), we need to use LEFT_EYE
        right_temple_x = pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_EYE].x + 0.03
        right_temple_y = pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_EYE].y - 0.02
        if self.is_touching(tip_x, tip_y, right_temple_x, right_temple_y):
            # THIS is the actual right temple from the user's perspective
            self.debug_info += "\nUser's right temple touch detected"
            return "right_temple"
        
        return None
    
    def is_touching(self, x1, y1, x2, y2):
        """Check if two points are close enough to be considered touching"""
        distance = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
        return distance < self.touch_threshold
        
    # Elbow detection method removed - using hip touches for next/previous gestures
    
    def check_command_sequence(self):
        """Check the sequence of gestures and execute commands"""
        self.debug_info += f"\nCurrent sequence: {self.sequence}"
        
        # Check if we're in zoom mode (special mode for increase/decrease gestures)
        if self.in_zoom_mode:
            self.debug_info += "\nIn INCREASE/DECREASE MODE - checking finger touches"
            
            # In zoom mode, we only recognize specific gestures
            if len(self.sequence) == 1:
                touch = self.sequence[0]
                
                # Increase - touch left index finger tip
                if touch == "left_index_tip":
                    self.debug_info += "\nINCREASE gesture detected (touched left index finger)"
                    self.execute_command("Increase", self.increase_signal)
                    
                # Decrease - touch left pinky finger tip
                elif touch == "left_pinky_tip":
                    self.debug_info += "\nDECREASE gesture detected (touched left pinky finger)"
                    self.execute_command("Decrease", self.decrease_signal)
            
            return  # Don't process normal gestures while in zoom mode
        
        # Normal mode - check for single-touch gestures
        if len(self.sequence) == 1:
            touch = self.sequence[0]
            self.debug_info += f"\nChecking normal mode gesture: {touch}"
            
            # Next - left hip
            if touch == "left_hip":
                self.debug_info += "\nNEXT gesture detected (left hip)"
                self.execute_command("Next", self.next_signal)
                
            # Previous - right hip
            elif touch == "right_hip":
                self.debug_info += "\nPREVIOUS gesture detected (right hip)"
                self.execute_command("Previous", self.previous_signal)
        
        # Check for double taps (two of the same touch in sequence)
        elif len(self.sequence) == 2:
            touch1, touch2 = self.sequence
            self.debug_info += f"\nDouble tap check: {touch1}, {touch2}"
            
            # Check if it's a double tap (same touch twice)
            if touch1 == touch2:
                # Double tap right temple - Help
                if touch1 == "right_temple":
                    self.debug_info += "\nHELP gesture detected (double tap right temple)"
                    self.execute_command("Help", self.help_signal)
    
    def execute_command(self, command_name, signal):
        """Execute a recognized command"""
        self.debug_info += f"\nCommand: {command_name}"
        self.status_signal.emit(f"Command: {command_name}")
        
        # Reset the sequence after executing a command
        self.sequence = []
        
        # Mark that we need the starting pose again before next gesture
        self.waiting_for_gesture = False
        self.gesture_performed = True
        
        # Emit the corresponding signal
        signal.emit()
        
    def release(self):
        """Release resources"""
        if self.cap.isOpened():
            self.cap.release()
        
        self.pose.close()
        self.hands.close()
