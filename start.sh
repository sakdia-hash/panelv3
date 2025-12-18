#!/bin/bash

# Apply migrations
python backend/clean_migrate.py

# Start application
# Host 0.0.0.0 is needed for Render
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
