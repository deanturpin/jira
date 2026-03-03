# GitLab CI/CD Setup

This guide explains how to set up automated Jira report generation using GitLab CI/CD and Pages.

## Architecture

- **GitLab CI**: Runs Python scripts on schedule to generate reports
- **GitLab Pages**: Hosts the generated HTML/PDF/PNG reports
- **Stats Persistence**: Previous run stats are fetched from Pages for delta tracking

## Setup Steps

### 1. Create GitLab Repository

1. Create a new private GitLab repository
2. Push this codebase to it:
   ```bash
   git remote add gitlab git@gitlab.com:your-username/jira-reports.git
   git push gitlab main
   ```

### 2. Configure CI/CD Variables

Go to **Settings → CI/CD → Variables** and add:

**Required:**
- `JIRA_URL` - Your Jira instance URL (e.g., `https://your-domain.atlassian.net`)
- `JIRA_EMAIL` - Your Jira email
- `JIRA_API_TOKEN` - Your Jira API token (masked)
- `JIRA_PROJECT_KEY_1` - Project key (e.g., `CIT`)
- `JIRA_BOARD_ID_1` - Board ID (e.g., `243`)
- `TEAM_SIZE_1` - Team size (e.g., `4`)

**Optional:**
- `TARGET_VELOCITY_1` - Target velocity override (e.g., `20`)
- `EXCLUDE_EPICS_1` - Comma-separated epic numbers to exclude (e.g., `621,629,636`)
- `SPRINT_LENGTH_WEEKS_1` - Sprint length in weeks (default: `1`)

**For multiple projects, add numbered suffixes:**
- `JIRA_PROJECT_KEY_2`, `JIRA_BOARD_ID_2`, etc.

### 3. Enable GitLab Pages

1. Go to **Settings → General → Visibility**
2. Enable **Pages** (can be private if repository is private)
3. Note: Pages URL will be `https://your-username.gitlab.io/jira-reports/`

### 4. Set Up Pipeline Schedules

Go to **CI/CD → Schedules** and create:

**Weekly Reports (Monday 1am GMT):**
- Description: `Weekly Planning Reports`
- Interval Pattern: `0 1 * * 1` (Monday 1am)
- Target branch: `main`
- Variables: (none needed, uses CI/CD variables)

**Optional - Sprint Close (Friday 5pm GMT):**
- Description: `Sprint Close`
- Interval Pattern: `0 17 * * 5` (Friday 5pm)
- Target branch: `main`
- Variables:
  - `SCHEDULE_TYPE` = `sprint_close`

### 5. Test the Pipeline

1. Go to **CI/CD → Pipelines**
2. Click **Run pipeline**
3. Select branch `main`
4. Click **Run pipeline**

After ~2-3 minutes, reports will be available at your Pages URL.

## How It Works

### Report Generation Flow

1. **Fetch previous stats** from GitLab Pages (for delta tracking)
2. **Generate reports**: Dashboard, Gantt, PDF, trends
3. **Log statistics** to `stats/*_history.csv`
4. **Deploy to Pages**: Reports and stats published

### Stats Persistence

- Previous run stats are downloaded from Pages before generation
- New stats are logged and uploaded back to Pages
- This provides continuity for delta tracking without needing a database

### Delta Tracking

The epic status traffic lights work by comparing:
- Current run: Fetched from Jira API
- Previous run: Downloaded from `https://your-pages-url/stats/cit_epics_history.csv`

First run shows `-` (no baseline), subsequent runs show coloured deltas.

## Accessing Reports

Reports are published to GitLab Pages at:
```
https://your-username.gitlab.io/jira-reports/
```

Files available:
- `{project}.html` - Interactive dashboard
- `{project}.pdf` - PDF report with all data
- `{project}_gantt.png` - Gantt chart
- `{project}_velocity_chart.png` - Velocity history
- `{project}_trends.png` - Historical planning trends
- `stats/{project}_history.csv` - Planning statistics over time
- `stats/{project}_epics_history.csv` - Per-epic progress tracking

## Troubleshooting

### Pipeline Fails: "Missing required environment variables"

Check that all required CI/CD variables are set in **Settings → CI/CD → Variables**.

### No Previous Stats Found

This is normal for the first run. Delta tracking will work from the second run onwards.

### Pages Not Deploying

Ensure the `pages` job completed successfully and check **Settings → Pages** is enabled.

### Stats Not Persisting

The `wget` command downloads previous stats from Pages. Check that:
- Pages URL is accessible
- Previous run published stats to `public/stats/`

## Manual Pipeline Triggers

All jobs can be run manually:

1. Go to **CI/CD → Pipelines**
2. Click **Run pipeline**
3. Jobs will show "manual" button to trigger individually

## Disabling Email Reports

Email sending is removed from this configuration since Resend API won't work from GitLab CI (external network restrictions). Reports are accessed via GitLab Pages instead.

If you want email reports, consider:
- Using GitLab's built-in email notification on pipeline success
- Adding a webhook to send reports via your own email service
- Accessing reports directly from Pages and sharing the link

## Security Notes

- Keep repository **private** if it contains sensitive project data
- Use **masked** variables for API tokens
- Pages can be set to private (requires authentication to access)
- Stats files are published to Pages but can be protected with authentication
