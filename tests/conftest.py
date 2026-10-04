"""
RevenueOS test configuration.
Adds the project root to sys.path so all modules are importable during tests.
"""
import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "backend"))
