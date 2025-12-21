#!/bin/bash
# Clear Python cache and compiled files

echo "Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete

echo "Cache cleared!"
echo "Now running: python main.py"

python main.py
