import sys
from pathlib import Path

# Ensure backend directory is in sys.path for smooth resolution whether running from root or backend/
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
