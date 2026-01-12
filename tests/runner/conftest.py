"""Pytest configuration for runner tests"""
import sys
import os

# Add runner app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'runner'))
