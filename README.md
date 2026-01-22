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

- **Velocity Tracking**: Historical sprint velocity with 6-month lookback window
- **Epic Planning**: Remaining work breakdown with child task details
- **Timeline Projections**: Gantt charts showing sequential epic completion dates
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

### 3. Configure Environment

Use numbered suffixes (`_1`, `_2`, etc.) for each project:

#### Single Project

```env
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_token_here

JIRA_PROJECT_KEY_1=PROJ
JIRA_BOARD_ID_1=123
TEAM_SIZE_1=4
SPRINT_LENGTH_WEEKS_1=2
```

#### Multiple Projects

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

# Add RESEND_API_KEY for email reports
RESEND_API_KEY=re_xxxxx
```

## Usage

```bash
make              # Generate dashboard and Gantt chart for all projects
make dashboard    # HTML dashboards only
make gantt        # Gantt charts only
make velocity     # Velocity chart PNG only
make clean        # Remove all generated files
make help         # Show all available commands
```

Outputs saved to `public/` directory.

### Daily Email Reports

Send PDF reports via email:

```bash
source venv/bin/activate
python bin/send_daily_report.py your-email@example.com
```

Set up automated daily reports with cron - see [CRON_SETUP.md](CRON_SETUP.md) for instructions.

## Output Files

- `public/{project}.html` - Interactive dashboard with:
  - Team size and average velocity
  - Remaining work breakdown
  - Projected completion date
  - Embedded velocity trend chart
  - Epic breakdown table (incomplete epics only)
  - Epic timeline with child task details
- `public/{project}_gantt.png` - Visual Gantt chart showing sequential epic timeline
- `public/{project}_velocity_chart.png` - Standalone velocity history chart

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

- Uses last 6 months of completed sprints
- Calculates mean, median, and standard deviation
- Only counts story points from completed issues (status: done/closed/resolved)

### Epic Timeline Projection

- Lays out epics sequentially (not in parallel)
- Uses average velocity for duration estimates
- Sorts epics by remaining work (largest first)

### Story Point Estimation Calibration

Note: Story point estimates often take ~2x longer than intuitive time estimates due to overhead (meetings, code reviews, testing, debugging, etc.). This is normal and expected - velocity-based planning accounts for this automatically.

## Debug Tools

- `bin/inspect_fields.py [board_id]` - Show all custom fields in a sample issue
- `bin/debug_sprint_details.py` - Show last 5 sprints with completion data

## Licence

MIT
