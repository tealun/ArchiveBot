#!/bin/bash
set -e

# Create required data directories at runtime (volume mount overwrites image-built dirs)
mkdir -p /app/data/backups /app/data/cache /app/data/temp /app/data/temp/ai_sessions

# Fix ownership so appuser can write to the mounted volume
chown -R appuser:appuser /app/data 2>/dev/null || true

# Drop privileges and run the bot
exec gosu appuser python main.py
