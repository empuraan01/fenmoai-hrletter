#!/usr/bin/env python3
"""
FenmoAI Entry Point for Deployment
This file serves as the main entry point for Streamlit Cloud deployment.
"""

import sys
import os
from pathlib import Path

src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    import subprocess
    
    subprocess.run([
        "streamlit", 
        "run", 
        "src/ui/streamlit_app.py",
        "--server.port=8501",
        "--server.address=0.0.0.0"
    ]) 