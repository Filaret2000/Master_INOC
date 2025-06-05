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
    increase_signal = pyqtSignal()
    decrease_signal = pyqtSignal()
    ok_signal = pyqtSignal()
    cancel_signal = pyqtSignal()
    menu_signal = pyqtSignal()
    home_signal = pyqtSignal()
    undo_signal = pyqtSignal()
    help_signal = pyqtSignal()
    
    # Signal for debug frame
    debug_frame_signal = pyqtSignal(QImage)
    
    # Signal for status updates
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
        hands_results = self.hands.process(rgb_frame)
        
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
        
        # Add debug info to frame
        y_pos = 30
        for line in self.debug_info.split('\n'):
            cv2.putText(debug_frame, line, (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            y_pos += 20
        
        # Convert to QImage for display in debug window
        h, w, ch = debug_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(debug_frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
        # Emit the debug frame
        self.debug_frame_signal.emit(qt_image)
    
    def process_gestures(self, pose_landmarks, hand_landmarks):
        # Find right hand index finger tip
        right_hand = None
        right_index_tip = None
        
        for i, hand in enumerate(hand_landmarks):
            # Determine if this is the right hand
            wrist = hand.landmark[self.mp_hands.HandLandmark.WRIST]
            if pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_SHOULDER].x > pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_SHOULDER].x:
                if wrist.x > pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_SHOULDER].x:
                    right_hand = hand
                    right_index_tip = hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    break
        
        # If no right hand detected, reset sequence and return
        if right_index_tip is None:
            self.sequence = []
            self.debug_info = "Right hand not detected"
            self.status_signal.emit("Waiting for right hand")
            return
        
        # Get left hand landmarks if available
        left_hand = None
        for i, hand in enumerate(hand_landmarks):
            wrist = hand.landmark[self.mp_hands.HandLandmark.WRIST]
            if pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_SHOULDER].x > pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_SHOULDER].x:
                if wrist.x < pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_SHOULDER].x:
                    left_hand = hand
                    break
        
        # Check for touches between right index finger and body parts
        current_touch = self.detect_touch(right_index_tip, pose_landmarks, left_hand)
        
        # If a touch is detected
        if current_touch:
            # If this is a new touch, add to sequence
            if not self.sequence or self.sequence[-1] != current_touch:
                # If this is the first touch in a sequence, record the start time
                if not self.sequence:
                    self.sequence_start_time = time.time()
                
                self.sequence.append(current_touch)
                self.debug_info = f"Touch detected: {current_touch}\nSequence: {self.sequence}"
                self.status_signal.emit(f"Touch: {current_touch}")
            
            # Check if sequence matches any command
            self.check_command_sequence()
        else:
            # If no touch for 2 seconds, reset sequence
            if self.sequence and time.time() - self.sequence_start_time > 2.0:
                self.sequence = []
                self.debug_info = "Sequence reset (timeout)"
                self.status_signal.emit("Ready")
    
    def detect_touch(self, right_index_tip, pose_landmarks, left_hand):
        """Detect if right index finger is touching a specific body part"""
        
        # Get 3D coordinates of right index finger tip
        tip_x, tip_y, tip_z = right_index_tip.x, right_index_tip.y, right_index_tip.z
        
        # Check right knee
        right_knee = pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_KNEE]
        if self.is_touching(tip_x, tip_y, right_knee.x, right_knee.y):
            return "right_knee"
        
        # Check left knee
        left_knee = pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_KNEE]
        if self.is_touching(tip_x, tip_y, left_knee.x, left_knee.y):
            return "left_knee"
        
        # Check chest (using mid-point between shoulders)
        chest_x = (pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_SHOULDER].x + 
                  pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_SHOULDER].x) / 2
        chest_y = (pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_SHOULDER].y + 
                  pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_SHOULDER].y) / 2 + 0.1
        if self.is_touching(tip_x, tip_y, chest_x, chest_y):
            return "chest"
        
        # Check belly (using mid-point of hips, slightly up)
        belly_x = (pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_HIP].x + 
                  pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_HIP].x) / 2
        belly_y = (pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_HIP].y + 
                  pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_HIP].y) / 2 - 0.1
        if self.is_touching(tip_x, tip_y, belly_x, belly_y):
            return "belly"
        
        # Check right temple
        right_temple_x = pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_EYE].x + 0.03
        right_temple_y = pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_EYE].y - 0.02
        if self.is_touching(tip_x, tip_y, right_temple_x, right_temple_y):
            return "right_temple"
        
        # Check left hand parts if left hand is detected
        if left_hand:
            # Check left palm center
            left_palm_x = (left_hand.landmark[self.mp_hands.HandLandmark.WRIST].x + 
                          left_hand.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP].x) / 2
            left_palm_y = (left_hand.landmark[self.mp_hands.HandLandmark.WRIST].y + 
                          left_hand.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y) / 2
            if self.is_touching(tip_x, tip_y, left_palm_x, left_palm_y):
                return "left_palm"
            
            # Check left wrist
            left_wrist = left_hand.landmark[self.mp_hands.HandLandmark.WRIST]
            if self.is_touching(tip_x, tip_y, left_wrist.x, left_wrist.y):
                return "left_wrist"
            
            # Check left index finger tip
            left_index_tip = left_hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
            if self.is_touching(tip_x, tip_y, left_index_tip.x, left_index_tip.y):
                return "left_index_tip"
            
            # Check left pinky finger tip
            left_pinky_tip = left_hand.landmark[self.mp_hands.HandLandmark.PINKY_FINGER_TIP]
            if self.is_touching(tip_x, tip_y, left_pinky_tip.x, left_pinky_tip.y):
                return "left_pinky_tip"
        
        # Check left elbow
        left_elbow = pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_ELBOW]
        if self.is_touching(tip_x, tip_y, left_elbow.x, left_elbow.y):
            return "left_elbow"
        
        return None
    
    def is_touching(self, x1, y1, x2, y2):
        """Check if two points are close enough to be considered touching"""
        distance = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
        return distance < self.touch_threshold
    
    def check_command_sequence(self):
        """Check if the current sequence matches any command pattern"""
        # Only check if we have at least one touch in the sequence
        if not self.sequence:
            return
            
        # Check for single-touch gestures
        if len(self.sequence) == 1:
            touch = self.sequence[0]
            
            # Next - right knee
            if touch == "right_knee":
                self.execute_command("Next", self.next_signal)
                
            # Previous - left knee
            elif touch == "left_knee":
                self.execute_command("Previous", self.previous_signal)
                
            # OK - Chest
            elif touch == "chest":
                self.execute_command("OK", self.ok_signal)
                
            # Cancel - Belly
            elif touch == "belly":
                self.execute_command("Cancel", self.cancel_signal)
                
        # Check for double-touch gestures (same location)
        elif len(self.sequence) == 2:
            touch1, touch2 = self.sequence
            
            # Menu - 2x center of left palm
            if touch1 == "left_palm" and touch2 == "left_palm":
                self.execute_command("Menu", self.menu_signal)
                
            # Help - 2x right temple
            elif touch1 == "right_temple" and touch2 == "right_temple":
                self.execute_command("Help", self.help_signal)
                
            # Increase - tip of left index finger
            elif touch1 == "left_index_tip":
                self.execute_command("Increase", self.increase_signal)
                
            # Decrease - tip of the left pinky finger
            elif touch1 == "left_pinky_tip":
                self.execute_command("Decrease", self.decrease_signal)
                
        # Check for two-part sequences
        elif len(self.sequence) >= 2:
            last_two = self.sequence[-2:]
            
            # Home - center of left palm, left wrist
            if last_two == ["left_palm", "left_wrist"]:
                self.execute_command("Home", self.home_signal)
                
            # Undo - center of left palm, left elbow
            elif last_two == ["left_palm", "left_elbow"]:
                self.execute_command("Undo", self.undo_signal)
    
    def execute_command(self, command_name, signal):
        """Execute a recognized command"""
        # Emit the corresponding signal
        signal.emit()
        
        # Update debug info
        self.debug_info = f"Executing command: {command_name}\nSequence: {self.sequence}"
        self.status_signal.emit(f"Command: {command_name}")
        
        # Reset sequence
        self.sequence = []
    
    def release(self):
        """Release resources"""
        if self.cap.isOpened():
            self.cap.release()
        
        self.pose.close()
        self.hands.close()
