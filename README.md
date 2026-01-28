# Jira Planning Tools

Automated Jira analysis generating velocity trends, epic timelines, and Gantt charts. Supports multiple projects and automatically detects story point custom fields.

## Quick Start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Jira credentials
make
```

## Features

- **Velocity Tracking**: Historical sprint velocity with 6-month lookback window (or use target velocity override)
- **Historical Trends**: Automatic statistics logging and trend visualisation to track estimate changes over time
- **Sprint Planning**: View top backlog issues based on team velocity
- **Sprint Automation**: Automated sprint closure with issue tracking
- **Epic Planning**: Remaining work breakdown with child task details
- **Timeline Projections**: Gantt charts showing parallel epic planning across developer swimlanes
- **PDF Reports**: Professional reports with flagged epic indicators and clickable Jira links
- **Epic Exclusion**: Filter out specific epics from all reports (useful for maintenance epics or out-of-scope work)
- **Multi-Project Support**: Configure multiple projects with numbered environment variables
- **Flexible Story Points**: Automatically detects story point fields (customfield_10016, 10026, 10031)
- **No Epic Tracking**: Identifies and tracks stories without parent epics

## Setup

### 1. Get Jira API Token

1. Visit <https://id.atlassian.com/manage-profile/security/api-tokens>
2. Click "Create API token"
3. Copy the token

### 2. Find Board ID

Look at your Jira board URL: `https://your-domain.atlassian.net/.../boards/123`

The number `123` is your Board ID.

### 3. Get Resend API Key (for email reports)

1. Visit <https://resend.com/api-keys>
2. Sign up or log in
3. Click "Create API Key"
4. Copy the key (starts with `re_`)

### 4. Configure Environment

Use numbered suffixes (`_1`, `_2`, etc.) for each project:

#### Add Projects

Update `.env` with your project and API info.

```env
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_token_here

JIRA_PROJECT_KEY_1=PROJ1
JIRA_BOARD_ID_1=123
TEAM_SIZE_1=4
SPRINT_LENGTH_WEEKS_1=2

JIRA_PROJECT_KEY_2=PROJ2
JIRA_BOARD_ID_2=456
TEAM_SIZE_2=3
SPRINT_LENGTH_WEEKS_2=1

# Target Velocity (optional, per-project)
# If set, uses this target velocity for planning instead of historical average
# Displays as "target velocity (actual: X)" in reports
# TARGET_VELOCITY_1=11
# TARGET_VELOCITY_2=15

# Exclude Epics (optional, per-project)
# Comma-separated epic numbers to exclude from all reports
# EXCLUDE_EPICS_1=123,456
# EXCLUDE_EPICS_2=789

RESEND_API_KEY=re_xxxxx

# Email Configuration (optional)
EMAIL_CC=colleague1@example.com,colleague2@example.com
```

## Usage

### Dashboard Generation

```bash
make              # Generate dashboard, Gantt chart, and PDF for all projects
make dashboard    # HTML dashboards only
make gantt        # Gantt charts only (also logs statistics)
make pdf          # PDF reports only
make velocity     # Velocity chart PNG only
make trends       # Generate trend charts from historical statistics
make clean        # Remove all generated files
make help         # Show all available commands
```

Outputs saved to `public/` directory.

### Sprint Planning

View top backlog issues for next sprint (based on velocity):

```bash
source venv/bin/activate
python bin/view_backlog.py [board_id]              # Use calculated or override velocity
python bin/view_backlog.py [board_id] --details    # Show priority and labels
python bin/view_backlog.py [board_id] --points 20  # Custom point limit
python bin/view_backlog.py [board_id] --count 10   # Custom issue count
```

### Sprint Closure

Close active sprint and move incomplete issues to backlog:

```bash
source venv/bin/activate
python bin/close_sprint.py [board_id]              # Interactive confirmation
python bin/close_sprint.py [board_id] --dry-run    # Preview without changes
python bin/close_sprint.py [board_id] --yes        # Skip confirmation
```

### Daily Email Reports

Generate and send PDF reports via email:

```bash
make                                                   # Generate reports first
source venv/bin/activate
python bin/send_daily_report.py your-email@example.com  # Send existing PDFs
```

Note: `send_daily_report.py` only sends existing PDFs from `public/`. Run `make` first to generate them.

Set up automated daily reports with cron - see [CRON_SETUP.md](CRON_SETUP.md) for instructions (handles both generation and sending).

## Output Files

### Generated Reports (public/)

- `{project}.html` - Interactive dashboard with:
  - Team size and average velocity
  - Remaining work breakdown
  - Projected completion date
  - Embedded velocity trend chart
  - Epic breakdown table (incomplete epics only, excludes configured epics)
  - Epic timeline with child task details
- `{project}.pdf` - Professional PDF report with:
  - Flagged epic indicators (red background with stop sign emoji)
  - Clickable Jira links for epics
  - Generation timestamp
  - Landscape Gantt chart page
- `{project}_gantt.png` - Visual Gantt chart showing parallel epic planning across developer swimlanes
- `{project}_velocity_chart.png` - Standalone velocity history chart
- `{project}_trends.png` - Historical trend visualisation (generated with `make trends`)

### Historical Data (stats/)

- `{project}_history.csv` - Automatically logged planning statistics:
  - Timestamp, epic count, total points, completion date
  - Team size, velocity metrics (mean, median, stddev)
  - Target velocity and actual velocity tracking

## Dashboard Features

### Metrics Summary

- Team size
- Average velocity (points/sprint ± std dev)
- Total remaining work
- Projected completion date

### Epic Breakdown Table

- Shows only epics with remaining work
- Progress percentage
- Story points (remaining/completed/total)
- Estimated completion date

### Epic Timeline Overview

- Detailed child task listings
- Tasks sorted by story points (largest first)
- Only shows incomplete tasks
- Clickable links to Jira tickets

### Special "No Epic" Section

- Automatically tracks stories without parent epics
- Helps identify unorganised work

## Troubleshooting

### Identifying Story Point Fields

Run the field inspector to identify which custom field contains story points:

```bash
source venv/bin/activate
python bin/inspect_fields.py [board_id]
```

The tool checks these fields by default:

- `customfield_10016` - Story Points
- `customfield_10026` - Story point estimate
- `customfield_10031` - Alternative story points field

### Velocity Appears Too Low

If velocity seems incorrect, verify story points are in the right custom field. Different Jira boards can use different custom field IDs.

### Sprint Length

Default is 1-week sprints. The tool uses this for:

- Gantt chart timeline calculations
- Sprint-to-date conversions

Sprint length is hardcoded in [bin/velocity_calculator.py:119](bin/velocity_calculator.py#L119).

### Completed Epics Still Showing

The dashboard filters out epics where `remaining == 0`. If an epic still appears, it has incomplete child tasks.

## Technical Details

### Velocity Calculation

- Uses last 6 months of completed sprints by default
- Calculates mean, median, and standard deviation
- Only counts story points from completed issues (status: done/closed/resolved)
- **Target Velocity**: Set `TARGET_VELOCITY_N` (per-project) in `.env` to use a target velocity for planning (useful for setting ambitious goals or when historical data is unreliable; displays as "target velocity (actual: X)" in reports)

### Epic Timeline Projection

- Lays out epics in parallel across developer swimlanes (based on team size)
- Uses average velocity per developer for duration estimates
- Sorts epics by remaining work (largest first)
- Assigns each epic to earliest available developer track

### Epic Exclusion

Configure `EXCLUDE_EPICS_N` in `.env` to filter specific epics from all reports:

```env
# Exclude epics by number (not full key)
EXCLUDE_EPICS_1=433,621,629
```

Useful for:

- Maintenance epics that run continuously
- Out-of-scope work tracked in Jira but not part of project timeline
- Epics on hold or blocked indefinitely

### Historical Statistics and Trends

Planning statistics are automatically logged to `stats/{project}_history.csv` each time reports are generated. Generate trend charts to visualise how estimates change over time:

```bash
make trends
```

Trend charts show three key metrics over time:

- Total remaining story points (scope tracking)
- Number of active epics (work breakdown visibility)
- Projected completion date (timeline drift detection)

Use historical trends to:

- Detect scope creep (increasing points/epics over time)
- Track velocity changes (compare target vs actual velocity)
- Measure estimate accuracy (how completion dates shift)
- Identify planning patterns across sprints

### Story Point Estimation Calibration

Note: Story point estimates often take ~2x longer than intuitive time estimates due to overhead (meetings, code reviews, testing, debugging, etc.). This is normal and expected - velocity-based planning accounts for this automatically.

## Debug Tools

- `bin/inspect_fields.py [board_id]` - Show all custom fields in a sample issue
- `bin/debug_sprint_details.py` - Show last 5 sprints with completion data
- `bin/view_backlog.py [board_id]` - Sprint planning tool (view top backlog issues)
- `bin/close_sprint.py [board_id]` - Sprint closure automation tool

## Licence

MIT
