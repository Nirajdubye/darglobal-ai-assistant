import os
import sys
from pathlib import Path

# Add project root to sys.path so imports work seamlessly
root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

# Run the Streamlit application
from app.frontend import streamlit_app
