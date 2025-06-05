"""
Main application file for the Photo Gallery App with Gesture Recognition
"""
import sys
from PyQt5.QtWidgets import QApplication
from components.app import PhotoGalleryApp

def main():
    app = QApplication(sys.argv)
    window = PhotoGalleryApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
