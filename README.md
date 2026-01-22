# Jira Planning Report Generator

Automated tool to extract story points, calculate velocity trends, and project epic timelines from Jira. Generates Excel reports with charts and Gantt-style visualisations to replace manual planning spreadsheets.

## Features

- **Velocity Analysis**: Historical sprint velocity with statistical metrics (mean, median, standard deviation)
- **Epic Timeline Projection**: Forecasts when epics will complete based on team capacity
- **Capacity Planning**: Shows future sprint allocations and available capacity
- **Excel Output**: Formatted spreadsheets with charts and colour-coded status indicators

## Prerequisites

- Python 3.9 or higher
- Jira account with API access
- Board ID from your Jira project

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Jira API Access

Create a `.env` file by copying the example:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Get these from your Jira instance
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_api_token_here

# Find your board ID in the URL when viewing your board
# Example: https://your-domain.atlassian.net/jira/software/projects/PROJ/boards/123
JIRA_BOARD_ID=123

# Optional configuration
NUM_HISTORICAL_SPRINTS=6      # Number of past sprints to analyse
NUM_FUTURE_SPRINTS=10         # Number of future sprints to project
CONFIDENCE_FACTOR=0.8         # Conservative multiplier for capacity (0.0-1.0)
```

### 3. Get Your Jira API Token

1. Go to <https://id.atlassian.com/manage-profile/security/api-tokens>
2. Click "Create API token"
3. Give it a name (e.g., "Planning Report Generator")
4. Copy the token to your `.env` file

### 4. Find Your Board ID

1. Open your Jira board in a browser
2. Look at the URL: `https://your-domain.atlassian.net/jira/software/projects/PROJ/boards/123`
3. The number at the end (`123`) is your Board ID

## Usage

Run the report generator:

```bash
python generate_report.py
```

This will:
1. Connect to Jira and fetch sprint data
2. Calculate velocity metrics from historical sprints
3. Project epic completion timelines
4. Generate an Excel file: `jira_planning_report_YYYYMMDD_HHMMSS.xlsx`

The Excel file contains four sheets:

- **Summary**: Key metrics overview and generation timestamp
- **Velocity History**: Historical sprint data with velocity trend chart
- **Epic Timeline**: Projected epic completion dates with work remaining chart
- **Capacity Planning**: Future sprint allocations and epic assignments

## Understanding the Output

### Velocity Statistics

- **Mean**: Average story points completed per sprint
- **Standard Deviation**: Variability in velocity (lower is more predictable)
- **Conservative Capacity**: Mean velocity × confidence factor (used for projections)

### Epic Timeline

- **Scheduled**: Epic fits within planning horizon
- **Beyond Horizon**: Epic extends beyond projected sprints (add more future sprints or reduce scope)

### Capacity Planning

Colour coding shows sprint utilisation:

- 🟢 Green: < 70% utilised (capacity available)
- 🟡 Yellow: 70-90% utilised (well-balanced)
- 🔴 Red: > 90% utilised (overcommitted)

## Customisation

### Story Points Field

The default story points field is `customfield_10016`. If your Jira uses a different field:

1. Find your field ID by inspecting an issue in the API:
   `https://your-domain.atlassian.net/rest/api/3/issue/PROJ-123`
2. Update [jira_client.py:98](jira_client.py#L98) with your field ID

### Sprint Length

The tool assumes 1-week sprints (configured for your workflow). To change this, modify [velocity_calculator.py:88](velocity_calculator.py#L88):

```python
sprint_end = sprint_start + timedelta(weeks=2)  # Change to 2 weeks
```

### Confidence Factor

Adjust `CONFIDENCE_FACTOR` in `.env`:

- `1.0`: Use full average velocity (optimistic)
- `0.8`: Use 80% of average (recommended, accounts for variability)
- `0.6`: Use 60% of average (conservative, high uncertainty)

## Troubleshooting

### "No completed sprints found"

- Ensure your board has closed sprints with story points
- Check that `JIRA_BOARD_ID` is correct

### "Missing required environment variables"

- Verify `.env` file exists and contains all required fields
- Check for typos in variable names

### API Authentication Errors

- Verify your API token is correct and not expired
- Ensure your email matches your Jira account

### Story Points Not Appearing

- Different Jira instances use different custom field IDs for story points
- Check your field ID and update `jira_client.py` accordingly

## Automation

### Scheduled Reports

Create a cron job to generate reports automatically:

```bash
# Generate report every Monday at 9am
0 9 * * 1 cd /path/to/jira && python generate_report.py
```

### CI/CD Integration

Add to your pipeline to track planning metrics over time:

```yaml
- name: Generate Jira Planning Report
  run: |
    pip install -r requirements.txt
    python generate_report.py
```

## Contributing

Suggestions and improvements welcome. This tool is designed to be extended with additional metrics and visualisations as needed.

## Licence

MIT
