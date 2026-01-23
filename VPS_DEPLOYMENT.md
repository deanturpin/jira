# VPS Deployment Guide

Deploy Jira Planning Tools to your VPS for automated daily reports.

## Prerequisites

- Ubuntu VPS (sornhub: 87.106.148.67)
- SSH access: `ssh sornhub`
- Git repository access

## Step 1: Install Dependencies on VPS

```bash
ssh sornhub

# Install Python 3 and pip
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

# Install system dependencies for ReportLab/Pillow
sudo apt install -y python3-dev libfreetype6-dev libjpeg-dev
```

## Step 2: Clone Repository

```bash
# Create application directory
sudo mkdir -p /var/www/jira-reports
sudo chown sorn:sorn /var/www/jira-reports

# Switch to sorn user
sudo su - sorn

# Clone repository
cd /var/www/jira-reports
git clone https://github.com/deanturpin/jira.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Configure Environment Variables

```bash
# Create secure .env file
sudo nano /root/.jira-env
```

Add your configuration:

```env
# Jira Configuration
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_api_token_here

# Project 1
JIRA_PROJECT_KEY_1=PROJ1
JIRA_BOARD_ID_1=123
TEAM_SIZE_1=4
SPRINT_LENGTH_WEEKS_1=2

# Project 2
JIRA_PROJECT_KEY_2=PROJ2
JIRA_BOARD_ID_2=456
TEAM_SIZE_2=3
SPRINT_LENGTH_WEEKS_2=1

# Email Configuration
RESEND_API_KEY=re_xxxxx
EMAIL_CC=colleague1@example.com,colleague2@example.com
```

Secure the file:

```bash
sudo chmod 600 /root/.jira-env
```

## Step 4: Create Systemd Service

Create `/etc/systemd/system/jira-reports.service`:

```ini
[Unit]
Description=Generate and send Jira daily reports
After=network.target

[Service]
Type=oneshot
User=sorn
WorkingDirectory=/var/www/jira-reports
EnvironmentFile=/root/.jira-env

# Generate reports
ExecStart=/var/www/jira-reports/venv/bin/python /var/www/jira-reports/bin/generate_all.py

# Send emails (hardcode recipient or add to env file)
ExecStartPost=/var/www/jira-reports/venv/bin/python /var/www/jira-reports/bin/send_daily_report.py dean.turpin@zenitel.com

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=jira-reports
```

## Step 5: Create Systemd Timer

Create `/etc/systemd/system/jira-reports.timer`:

```ini
[Unit]
Description=Run Jira reports daily at 3am
Requires=jira-reports.service

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true
RandomizedDelaySec=60

[Install]
WantedBy=timers.target
```

## Step 6: Enable and Start Timer

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable timer to start on boot
sudo systemctl enable jira-reports.timer

# Start timer
sudo systemctl start jira-reports.timer

# Check timer status
sudo systemctl status jira-reports.timer
sudo systemctl list-timers | grep jira-reports
```

## Step 7: Test Manually

Test the service before waiting for the timer:

```bash
# Run service manually
sudo systemctl start jira-reports.service

# Check logs
sudo journalctl -u jira-reports.service -n 50

# Check if PDFs were generated
ls -lh /var/www/jira-reports/public/*.pdf
```

## Monitoring

### View Logs

```bash
# Recent logs
sudo journalctl -u jira-reports.service -n 100

# Follow logs in real-time
sudo journalctl -u jira-reports.service -f

# Logs from today
sudo journalctl -u jira-reports.service --since today
```

### Check Timer Status

```bash
# When will it run next?
sudo systemctl list-timers | grep jira-reports

# Timer status
sudo systemctl status jira-reports.timer
```

### Manual Trigger

```bash
# Run immediately (useful for testing)
sudo systemctl start jira-reports.service
```

## Updating the Code

```bash
# SSH to VPS
ssh sornhub

# Switch to sorn user
sudo su - sorn

# Pull latest changes
cd /var/www/jira-reports
git pull

# Update dependencies if needed
source venv/bin/activate
pip install -r requirements.txt

# Test manually
sudo systemctl start jira-reports.service
```

## Troubleshooting

### Service fails to start

Check logs:
```bash
sudo journalctl -u jira-reports.service -n 50
```

Common issues:
- Missing environment variables in `/root/.jira-env`
- Invalid Jira credentials
- Missing Python dependencies
- Network connectivity issues

### No emails received

Check:
- RESEND_API_KEY is valid
- Email address is correct in service file
- PDFs were generated in `public/` directory
- Service logs for email sending errors

### Timer not running

```bash
# Check if timer is enabled
sudo systemctl is-enabled jira-reports.timer

# Check timer status
sudo systemctl status jira-reports.timer

# Re-enable if needed
sudo systemctl enable jira-reports.timer
sudo systemctl start jira-reports.timer
```

## Security Notes

- Environment file (`/root/.jira-env`) is only readable by root
- Service runs as `sorn` user (non-root)
- API tokens should be rotated regularly
- Consider using fail2ban if exposing any services

## Alternative: One-Shot Email Recipient

If you want to configure the email recipient in the environment file instead of hardcoding it in the service:

Add to `/root/.jira-env`:
```env
REPORT_EMAIL=dean.turpin@zenitel.com
```

Update service ExecStartPost line:
```ini
ExecStartPost=/bin/bash -c '/var/www/jira-reports/venv/bin/python /var/www/jira-reports/bin/send_daily_report.py $REPORT_EMAIL'
```
