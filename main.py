# Main entry point for the Gesture Gallery application
# This uses our modular architecture with separate components
from src.app_controller import GestureGallery

if __name__ == "__main__":
    # Create and run the gesture gallery application
    app = GestureGallery()
    app.run()
