"""
RevenueOS test configuration.
Adds the project root to sys.path so all modules are importable during tests.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
