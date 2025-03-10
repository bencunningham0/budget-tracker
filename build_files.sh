#!/bin/bash
echo "BUILD START"

# Install dependencies
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# Ensure staticfiles directory exists
mkdir -p staticfiles

# Collect static files
python3 manage.py collectstatic --noinput --clear

echo "BUILD END"