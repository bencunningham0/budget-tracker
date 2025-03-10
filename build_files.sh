#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "BUILD START"

# Install dependencies
echo "Installing dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# Run database migrations
echo "Running database migrations..."
python3 manage.py migrate --noinput

# Collect static files with optimization
echo "Collecting static files..."
python3 manage.py collectstatic --noinput --clear

echo "BUILD END"