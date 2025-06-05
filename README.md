# Photo Gallery App with Gesture Recognition

This application is a photo gallery that can be controlled using hand gestures. It uses computer vision to recognize specific gestures where the index finger of the right hand touches different parts of the body to execute various commands.

## Features

- Browse through a gallery of images
- Zoom in and out of images
- Navigation using hand gestures
- Separate debug window to view the camera feed and gesture detection

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

| Command   | Gesture Description                                            |
|-----------|---------------------------------------------------------------|
| Next      | Touch right knee with right index finger                      |
| Previous  | Touch left knee with right index finger                       |
| Increase  | Touch tip of left index finger with right index finger        |
| Decrease  | Touch tip of left pinky finger with right index finger        |
| OK        | Touch chest with right index finger                           |
| Cancel    | Touch belly with right index finger                           |
| Menu      | Touch center of left palm twice with right index finger       |
| Home      | Touch center of left palm, then left wrist with right index finger |
| Undo      | Touch center of left palm, then left elbow crease with right index finger |
| Help      | Touch right temple twice with right index finger              |

## Project Structure

- `main.py`: Entry point of the application
- `components/`: Directory containing the application components
  - `app.py`: Main application component
  - `gallery.py`: Component for displaying and navigating images
  - `gesture_recognizer.py`: Component for recognizing gestures
  - `debug_window.py`: Component for displaying the debug window
  - `utils.py`: Utility functions and command information
