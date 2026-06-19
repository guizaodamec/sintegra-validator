#!/bin/bash
# Railway start script - try gunicorn, fallback to flask dev server
set -e

echo "Starting SINTEGRA Auto-Fix..."
echo "Python: $(python3 --version 2>/dev/null || python --version)"

# Install pip deps if needed
pip install -r requirements.txt --quiet 2>/dev/null || pip3 install -r requirements.txt --quiet

# Try gunicorn first
if command -v gunicorn &> /dev/null; then
    echo "Using gunicorn"
    exec gunicorn app:app --bind "0.0.0.0:${PORT:-5000}" --timeout 300
elif python3 -c "import gunicorn" 2>/dev/null; then
    echo "Using python -m gunicorn"
    exec python3 -m gunicorn app:app --bind "0.0.0.0:${PORT:-5000}" --timeout 300
else
    echo "gunicorn not found, using Flask dev server"
    exec python3 app.py
fi
