import os
import sys

# Add the project root directory to the Python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app

# Vercel's Python runtime discovers and serves the `app` WSGI callable
if __name__ == "__main__":
    app.run()
