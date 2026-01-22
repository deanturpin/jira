# Jira Planning Tools - Scripts

Scripts for automated Jira planning analysis. All outputs are generated in `../public/`.

## Main Tools

### generate_dashboard.py

The all-in-one dashboard generator.

Generates a comprehensive HTML dashboard combining velocity trends, epic progress, and completion projections.

```bash
python generate_dashboard.py
```

**Features:**

- Multi-project support via numbered environment variables
- Embedded velocity chart (base64 encoded)
- Links to external Gantt chart PNG
- Epic breakdown table (incomplete epics only)
- Epic timeline with child task details
- Special "No Epic" section for orphaned stories

**Output:** `../public/{project}.html`

### generate_gantt.py

Creates visual Gantt chart showing sequential epic timeline.

```bash
python generate_gantt.py
```

**Features:**

- Sequential epic layout (not parallel)
- Colour-coded bars
- Epic names embedded in bars when space permits
- Duration and story points shown

**Output:** `../public/{project}_gantt.png`

### plot_velocity.py

Sprint velocity visualisation with trend analysis.

```bash
python plot_velocity.py
```

**Output:** `../public/{project}_velocity_chart.png`

### generate_report.py

Excel report with velocity statistics and charts.

```bash
python generate_report.py
```

**Output:** `../public/{project}_planning_report_{timestamp}.xlsx`

### list_epic_work.py

Console output of epic remaining work breakdown.

```bash
python list_epic_work.py
```

## Debug Tools

### inspect_fields.py

Shows all custom fields in a sample issue to identify story point field IDs.

```bash
python inspect_fields.py [board_id]
```

**Use this when:**

- Story points aren't appearing in dashboards
- Setting up a new project
- Different boards use different custom fields

**Output:** Console listing of all customfield_* values

### debug_sprint_details.py

Shows last 5 completed sprints with issue counts and completed points.

```bash
python debug_sprint_details.py
```

**Use this when:**

- Velocity seems incorrect
- Investigating sprint completion data
- Verifying story point fields are correct

**Output:** Console table with sprint summary

## Utility Scripts

- **dump_epics.py** - Export all epic metadata to JSON
- **inspect_epic.py** - Inspect specific epic's child issues
- **list_epics.py** - Various epic listing approaches (testing)
- **list_epics_simple.py** - Simplified epic listing
- **list_remaining_work.py** - Alternative remaining work calculator

## Core Modules

### jira_client.py

Jira REST API client with methods for:

- Fetching board sprints
- Getting sprint issues
- Extracting story points from multiple custom fields
- Epic retrieval

**Story Point Field Support:**

- customfield_10016 (default)
- customfield_10026 (alternative)
- customfield_10031 (alternative)

### velocity_calculator.py

Sprint velocity calculations including:

- Historical velocity (configurable lookback period)
- Statistical metrics (mean, median, std dev)
- 6-month rolling window by default

**Key Configuration:**

- Sprint length: 1 week (hardcoded line 119)
- Lookback window: 6 months (configurable via `months` parameter)

### epic_planner.py

Epic timeline projections and capacity planning.

### excel_generator.py

Excel report generation with charts and statistics.

## Running from bin/

All scripts should be run from within the `bin/` directory:

```bash
cd bin
source ../venv/bin/activate
python generate_dashboard.py
```

Or from the project root:

```bash
source venv/bin/activate
cd bin && python generate_dashboard.py
```

## Technical Notes

### Story Point Detection

The code checks multiple custom field IDs to support different Jira configurations. If story points aren't appearing:

1. Run `inspect_fields.py [board_id]`
2. Look for numeric fields with point values
3. The field ID will be something like `customfield_10031`
4. Update `jira_client.py` if using a different field

### Multi-Project Configuration

Projects are discovered by checking for numbered environment variables:

- `JIRA_PROJECT_KEY_1`, `JIRA_BOARD_ID_1`, `TEAM_SIZE_1`
- `JIRA_PROJECT_KEY_2`, `JIRA_BOARD_ID_2`, `TEAM_SIZE_2`
- etc.

Falls back to non-numbered variables if none found.

### Velocity vs Team Size

Team size is displayed but not used in velocity calculations. Historical velocity already reflects the team's actual output (which inherently includes their size). This approach is valid as long as:

- Team size remains stable
- Historical data reflects current team composition
- Estimates are consistently calibrated

### "No Epic" Detection

Stories without parent epics are identified using JQL:

```jql
project = {KEY} AND parent is EMPTY AND type != Epic
```

These appear as a special "NO-EPIC" entry in dashboards if they have remaining work.
