import sys
import os

# Add the app directory to the Python path
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.append(path)

# Import the app as application
from app import app as application

# This allows the application to be run directly
if __name__ == '__main__':
    application.run() 