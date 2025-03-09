#!/bin/bash
echo "BUILD START"

# Install dependencies
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# Ensure staticfiles directory exists
mkdir -p staticfiles

# Collect static files
python3 manage.py collectstatic --noinput --clear

# Apply database migrations
python3 manage.py migrate

# Reset database sequences
python3 manage.py sqlsequencereset budgetapp | python3 manage.py dbshell

echo "BUILD END"