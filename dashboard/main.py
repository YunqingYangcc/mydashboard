import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Streamlit 入口文件 - 直接运行 Home
import streamlit as st
exec(open(ROOT_DIR / "dashboard" / "Dashboard.py").read())
