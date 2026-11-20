import os
import sys
from pathlib import Path

# Fix for ChromaDB SQLite requirement on Linux (Streamlit Cloud)
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

# Add project root to sys.path so imports work seamlessly
root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

# Run the Streamlit application
from app.frontend import streamlit_app
