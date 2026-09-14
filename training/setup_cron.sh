#!/bin/bash

# Get absolute path of current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Cron Schedule: 12:00 AM Daily (0 0 * * *)
# Command: cd to dir -> activate venv -> run pipeline >> log
CRON_JOB="0 0 * * * cd $DIR && source venv/bin/activate && python train_pipeline.py >> training.log 2>&1"

# Check if job already exists to avoid duplicates
(crontab -l 2>/dev/null | grep -F "train_pipeline.py") && echo "❌ Job already scheduled." || (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Cron Job Configured for 12:00 AM Daily!"
echo "📂 Working Directory: $DIR"
echo "📝 Logging to: training.log"
