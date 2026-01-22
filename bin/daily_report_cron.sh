#!/bin/bash
# Daily Jira report cron job
# Generates reports and emails them

set -e

# Change to project directory
cd "$(dirname "$0")/.."

# Activate virtual environment
source venv/bin/activate

# Generate all reports
cd bin
python3 generate_all.py

# Send email reports
python3 send_daily_report.py dean.turpin@zenitel.com

# Log completion
echo "$(date): Daily reports generated and sent" >> /tmp/jira-daily-report.log
