# Photo Gallery App with Gesture Recognition

This modern photo gallery application features intuitive hand gesture control, leveraging computer vision technology to recognize specific gestures for navigation and interaction. The app detects when the index finger of the right hand touches different parts of the body to execute various commands, providing an accessible and engaging user experience.

## Features

- **Modern UI Design**: Clean interface with harmonious color scheme and responsive layouts
- **Intuitive Navigation**: Browse through images with simple hand gestures
- **Fullscreen Mode**: Toggle between regular and fullscreen viewing with gestures
- **Advanced Gesture Recognition**: Precise detection of hand and body landmarks
- **Visual Feedback**: Image counter and button visibility adapt to current mode
- **Debug Window**: Optional visualization of camera feed with landmarks for development
- **Hip Points Visualization**: Added landmarks for improved gesture detection accuracy

## Technical Improvements

- **Enhanced Help Gesture**: Improved temple touch detection using 2D distance calculation
- **Mirrored Frame Handling**: Proper landmark mapping accounting for horizontally flipped camera feed
- **Fullscreen Toggle**: Single-tap gesture to enter/exit fullscreen with fixed zoom factor
- **Persistent Gesture Recognition**: Text feedback remains until new gesture is detected
- **UI Refinements**: Removed redundant debug text, improved image counter formatting

## Requirements

- Python 3.7+
- Webcam
- Dependencies listed in `requirements.txt`

## Installation

1. Clone this repository
2. Install the required packages:

```
pip install -r requirements.txt
```

## Usage

Run the application:

```
python main.py
```

## Gesture Commands

The application recognizes the following gestures:

| Command   | Gesture Description                                            | Effect |
|-----------|---------------------------------------------------------------|-------|
| Next      | Touch right knee with right index finger                      | Move to next image |
| Previous  | Touch left knee with right index finger                       | Move to previous image |
| Increase  | Touch tip of left index finger with right index finger        | Enter fullscreen mode |
| Decrease  | Touch tip of left pinky finger with right index finger        | Exit fullscreen mode |
| Help      | Touch right temple twice with right index finger              | Toggle debug window visibility |

## UI Elements

- **Image Counter**: Displays current position as "1/8" format
- **Navigation Buttons**: Modern styled buttons for Previous and Next
- **Increase/Decrease**: Contextual buttons that appear based on current mode
- **Debug Window**: Shows camera feed with landmarks and gesture detection information

## Project Structure

- `main.py`: Entry point of the application
- `components/`: Directory containing the application components
  - `app.py`: Main application component with modern UI styling
  - `gallery.py`: Component for displaying and navigating images with fullscreen toggle
  - `gesture_recognizer.py`: Component for recognizing gestures with enhanced detection
  - `debug_window.py`: Component for displaying the debug window with landmarks
  - `utils.py`: Utility functions and command information
