import cv2
import numpy as np
from cvzone.HandTrackingModule import HandDetector
from typing import Tuple, List, Dict, Any, Optional

class GestureDetector:
    """Handles hand tracking and gesture detection."""
    
    def __init__(self, detection_con=0.8, max_hands=1):
        """Initialize the gesture detector.
        
        Args:
            detection_con: Confidence threshold for hand detection
            max_hands: Maximum number of hands to detect
        """
        self.detector = HandDetector(detectionCon=detection_con, maxHands=max_hands)
        self.gesture_cooldown = 0
        self.last_hand_state = ""
        self.last_debug_state = ""
        self.current_gesture = "None"
        self.show_debug = True
        
        # Store previous positions for wave detection
        self.prev_palm_y = None
        
    def find_hands(self, frame):
        """Detect hands in the given frame.
        
        Args:
            frame: Camera frame to process
            
        Returns:
            Tuple of (hands, processed_frame)
        """
        return self.detector.findHands(frame, draw=True, flipType=False)
    
    def detect_palm_vs_fist(self, hand: Dict[str, Any]) -> str:
        """Detect if the hand is a palm or fist.
        
        Args:
            hand: Hand data from detector
            
        Returns:
            "palm" if open palm with spread fingers is detected,
            "fist" if closed hand is detected,
            "close_palm" if palm with fingers close together,
            "other" otherwise
        """
        # Get landmarks list
        lmList = hand['lmList']
        if len(lmList) < 21:  # Need all landmarks
            return "other"
            
        # Get finger positions
        thumb_tip = lmList[4]
        thumb_mcp = lmList[2]
        index_tip = lmList[8]
        index_pip = lmList[6]
        middle_tip = lmList[12]
        middle_pip = lmList[10]
        ring_tip = lmList[16]
        ring_pip = lmList[14]
        pinky_tip = lmList[20]
        pinky_pip = lmList[18]
        
        # For right hand: Check finger states
        # First, check if tips are above PIPs (finger extended)
        index_up = index_tip[1] < index_pip[1]
        middle_up = middle_tip[1] < middle_pip[1]
        ring_up = ring_tip[1] < ring_pip[1]
        pinky_up = pinky_tip[1] < pinky_pip[1]
        
        # For thumb: check if it's pointing outwards (for right hand)
        # For right hand facing camera: thumb_tip x value should be less than mcp x value
        thumb_out = thumb_tip[0] < thumb_mcp[0]
        
        # For right hand facing user: thumb_tip x value should be greater than mcp x value
        thumb_out_user_facing = thumb_tip[0] > thumb_mcp[0]
        
        # Calculate the distance between finger tips
        finger_tips = [index_tip, middle_tip, ring_tip, pinky_tip]
        distances = []
        for i in range(len(finger_tips)-1):
            for j in range(i+1, len(finger_tips)):
                dist = np.sqrt((finger_tips[i][0] - finger_tips[j][0])**2 + 
                              (finger_tips[i][1] - finger_tips[j][1])**2)
                distances.append(dist)
        
        # Calculate the average distance between fingertips
        avg_distance = sum(distances) / len(distances) if distances else 0
        
        # Detect palm with spread fingers (for camera-facing right hand)
        is_palm_spread = (index_up and middle_up and ring_up and pinky_up and thumb_out)
        
        # Detect palm with spread fingers (for user-facing right hand)
        is_palm_spread_user_facing = (index_up and middle_up and ring_up and pinky_up and thumb_out_user_facing)
        
        # Detect palm with close fingers - improved detection for exit gesture
        # Using a larger threshold to make detection more reliable
        is_palm_close = (index_up and middle_up and ring_up and pinky_up and avg_distance < 80)
        
        # Detect fist
        is_fist = not (index_up or middle_up or ring_up or pinky_up)
        
        # Return the detected state
        if is_palm_spread or is_palm_spread_user_facing:
            return "palm"
        elif is_palm_close:
            return "close_palm"
        elif is_fist:
            return "fist"
        else:
            return "other"
    
    def detect_index_finger_only(self, hand: Dict[str, Any]) -> bool:
        """Detect if only the index finger is up.
        
        Args:
            hand: Hand data from detector
            
        Returns:
            True if only index finger is up, False otherwise
        """
        # Get landmarks list
        lmList = hand['lmList']
        if len(lmList) < 21:  # Need all landmarks
            return False
            
        # Get finger positions
        index_tip = lmList[8]
        index_pip = lmList[6]
        middle_tip = lmList[12]
        middle_pip = lmList[10]
        ring_tip = lmList[16]
        ring_pip = lmList[14]
        pinky_tip = lmList[20]
        pinky_pip = lmList[18]
        
        # For right hand: Check if ONLY index finger is up
        index_up = index_tip[1] < index_pip[1]
        middle_down = middle_tip[1] > middle_pip[1]
        ring_down = ring_tip[1] > ring_pip[1]
        pinky_down = pinky_tip[1] > pinky_pip[1]
        
        return index_up and middle_down and ring_down and pinky_down
    
    def detect_two_fingers(self, hand: Dict[str, Any]) -> bool:
        """Detect if exactly two fingers (index and middle) are up.
        
        Args:
            hand: Hand data from detector
            
        Returns:
            True if exactly index and middle fingers are up, False otherwise
        """
        # Get landmarks list
        lmList = hand['lmList']
        if len(lmList) < 21:  # Need all landmarks
            return False
            
        # Get finger positions
        index_tip = lmList[8]
        index_pip = lmList[6]
        middle_tip = lmList[12]
        middle_pip = lmList[10]
        ring_tip = lmList[16]
        ring_pip = lmList[14]
        pinky_tip = lmList[20]
        pinky_pip = lmList[18]
        
        # For right hand: Check if ONLY index and middle fingers are up
        index_up = index_tip[1] < index_pip[1]
        middle_up = middle_tip[1] < middle_pip[1]
        ring_down = ring_tip[1] > ring_pip[1]
        pinky_down = pinky_tip[1] > pinky_pip[1]
        
        return index_up and middle_up and ring_down and pinky_down
        
    def detect_swipe_hand_form(self, hand: Dict[str, Any]) -> bool:
        """Detect if the hand is in the correct form for swipe gesture.
        Index finger up, all other fingers down (including thumb).
        
        Args:
            hand: Hand data from detector
            
        Returns:
            True if hand is in correct swipe form, False otherwise
        """
        # First try using the native fingersUp method from cvzone
        fingers_up = self.detector.fingersUp(hand)
        if fingers_up is not None:
            # Check if only index finger is up (index=1, all others=0)
            if fingers_up[1] == 1 and sum(fingers_up) == 1:
                return True
        
        # Fallback to our manual detection if cvzone method fails
        # Get landmarks list
        lmList = hand['lmList']
        if len(lmList) < 21:  # Need all landmarks
            return False
            
        # Get finger positions
        thumb_tip = lmList[4]
        thumb_pip = lmList[2]  # Using MCP joint as reference
        index_tip = lmList[8]
        index_pip = lmList[6]
        middle_tip = lmList[12]
        middle_pip = lmList[10]
        ring_tip = lmList[16]
        ring_pip = lmList[14]
        pinky_tip = lmList[20]
        pinky_pip = lmList[18]
        
        # For right hand: Check if ONLY index finger is up
        # Use more lenient detection for index finger - it must be significantly higher than its PIP
        index_up = index_tip[1] < index_pip[1] - 20
        
        # Make thumb detection more reliable
        thumb_down = thumb_tip[0] > thumb_pip[0]  # Right hand thumb points left when closed
        
        # Other fingers must be clearly down
        middle_down = middle_tip[1] > middle_pip[1]
        ring_down = ring_tip[1] > ring_pip[1]
        pinky_down = pinky_tip[1] > pinky_pip[1]
        
        # If clearly only index is up, return true
        return index_up and middle_down and ring_down and pinky_down
        
    def detect_fullscreen_start_form(self, hand: Dict[str, Any]) -> bool:
        """Detect if the hand is in the correct starting form for fullscreen gesture.
        This should be a fist (all fingers down).
        
        Args:
            hand: Hand data from detector
            
        Returns:
            True if hand is in fist form, False otherwise
        """
        # Use our palm_vs_fist detector to check for fist
        hand_state = self.detect_palm_vs_fist(hand)
        return hand_state == "fist"
        
    def detect_fullscreen_end_form(self, hand: Dict[str, Any]) -> bool:
        """Detect if the hand is in the correct ending form for fullscreen gesture.
        This should be an open palm with fingers up (any palm form).
        
        Args:
            hand: Hand data from detector
            
        Returns:
            True if hand is in any open palm form, False otherwise
        """
        # Simply check if it's a palm using our palm_vs_fist detector
        # This will accept both palms with spread fingers and with close fingers
        hand_state = self.detect_palm_vs_fist(hand)
        return hand_state == "palm" or hand_state == "close_palm"
        
    def detect_debug_start_form(self, hand: Dict[str, Any]) -> bool:
        """Detect if the hand is in the correct form for debug toggle gesture.
        Index and middle fingers up, all other fingers down.
        
        Args:
            hand: Hand data from detector
            
        Returns:
            True if exactly two fingers are up, False otherwise
        """
        # This is the same as our detect_two_fingers method
        return self.detect_two_fingers(hand)
        
    def detect_debug_end_form(self, hand: Dict[str, Any]) -> bool:
        """Detect if the hand is in the correct ending form for debug toggle.
        This should be a fist (all fingers down).
        
        Args:
            hand: Hand data from detector
            
        Returns:
            True if hand is in fist form, False otherwise
        """
        # Use our palm_vs_fist detector to check for fist
        hand_state = self.detect_palm_vs_fist(hand)
        return hand_state == "fist"
        
    def detect_close_palm_form(self, hand: Dict[str, Any]) -> bool:
        """Detect if the hand is in close palm form (fingers up but close together).
        This is specifically designed for the exit gesture - palm with joined fingers.
        
        Args:
            hand: Hand data from detector
            
        Returns:
            True if hand is in close palm form, False otherwise
        """
        # Get landmarks list
        lmList = hand['lmList']
        if len(lmList) < 21:  # Need all landmarks
            return False
            
        # Get finger positions
        index_tip = lmList[8]
        index_pip = lmList[6]
        middle_tip = lmList[12]
        middle_pip = lmList[10]
        ring_tip = lmList[16]
        ring_pip = lmList[14]
        pinky_tip = lmList[20]
        pinky_pip = lmList[18]
        
        # Check if all fingers are extended (up)
        index_up = index_tip[1] < index_pip[1]
        middle_up = middle_tip[1] < middle_pip[1]
        ring_up = ring_tip[1] < ring_pip[1]
        pinky_up = pinky_tip[1] < pinky_pip[1]
        
        all_fingers_up = index_up and middle_up and ring_up and pinky_up
        
        # Check if fingers are close together (specifically for exit gesture)
        # Calculate distances between adjacent fingertips
        adjacent_distances = [
            np.sqrt((index_tip[0] - middle_tip[0])**2 + (index_tip[1] - middle_tip[1])**2),
            np.sqrt((middle_tip[0] - ring_tip[0])**2 + (middle_tip[1] - ring_tip[1])**2),
            np.sqrt((ring_tip[0] - pinky_tip[0])**2 + (ring_tip[1] - pinky_tip[1])**2)
        ]
        
        # Use a lower threshold specifically for the exit gesture
        avg_adjacent_distance = sum(adjacent_distances) / len(adjacent_distances)
        fingers_close = avg_adjacent_distance < 45  # Tighter threshold for joined fingers
        
        return all_fingers_up and fingers_close
        
    def detect_wave_down_motion(self, hand: Dict[str, Any], threshold: int = 15) -> Optional[float]:
        """Detect a wave down motion with the hand in close palm form.
        
        Args:
            hand: Hand data from detector
            threshold: Minimum y-distance to consider a wave down
            
        Returns:
            Amount of downward movement if a wave down is detected, None otherwise
        """
        # First, check if the hand is in close palm form
        if not self.detect_close_palm_form(hand):
            # Reset tracking position if not in close palm form
            self.prev_palm_y = None
            return None
            
        # Get landmarks list
        lmList = hand['lmList']
        if len(lmList) < 21:  # Need all landmarks
            return None
            
        # Get wrist and finger tips
        wrist = lmList[0]
        finger_tips = [lmList[4], lmList[8], lmList[12], lmList[16], lmList[20]]
        
        # Calculate average finger tip position
        avg_tip_y = sum(tip[1] for tip in finger_tips) / len(finger_tips)
        
        # Check if we have a previous position to compare
        if self.prev_palm_y is not None:
            # Calculate vertical movement (positive y means moving down)
            y_movement = avg_tip_y - self.prev_palm_y
            
            # Store current position for next comparison
            self.prev_palm_y = avg_tip_y
            
            # If significant downward movement detected
            if y_movement > threshold:
                return y_movement
            else:
                return None
        else:
            # Store current position for next comparison
            self.prev_palm_y = avg_tip_y
            return None
    
    def get_finger_orientation(self, hand: Dict[str, Any]) -> Tuple[np.ndarray, float]:
        """Get the orientation of the hand/palm.
        
        Args:
            hand: Hand data from detector
            
        Returns:
            Tuple of (normal_vector, standard_deviation)
        """
        # Get landmarks list
        lmList = hand['lmList']
        if len(lmList) < 21:  # Need all landmarks
            return np.array([0, 0, 1]), 0
            
        # Get wrist and finger tips
        wrist = lmList[0]
        finger_tips = [lmList[4], lmList[8], lmList[12], lmList[16], lmList[20]]
        
        # Calculate average finger tip position
        avg_tip_x = sum(tip[0] for tip in finger_tips) / len(finger_tips)
        avg_tip_y = sum(tip[1] for tip in finger_tips) / len(finger_tips)
        
        # Calculate vector from wrist to avg tip position
        vector = np.array([avg_tip_x - wrist[0], avg_tip_y - wrist[1], 0])
        if np.linalg.norm(vector) > 0:
            vector = vector / np.linalg.norm(vector)
        
        # Calculate standard deviation of y values
        tip_y_values = [tip[1] for tip in finger_tips]
        y_std_dev = np.std(tip_y_values)
        
        return vector, y_std_dev
