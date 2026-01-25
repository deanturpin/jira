# Jira Planning Tools - Project Context

This project generates automated Jira planning dashboards with velocity tracking, epic timelines, and Gantt charts.

## Project Architecture

- **Language**: Python 3
- **Sprint Cadence**: 1-week sprints
- **Velocity Window**: Last 6 months of completed sprints
- **Multi-Project**: Supports multiple projects via numbered environment variables

## Key Files

- `bin/generate_dashboard.py` - Main dashboard generator (HTML output)
- `bin/generate_gantt.py` - Gantt chart generator (PNG output)
- `bin/jira_client.py` - Jira REST API client
- `bin/velocity_calculator.py` - Sprint velocity calculations
- `bin/view_backlog.py` - Sprint planning tool (shows top backlog issues by velocity)
- `bin/close_sprint.py` - Sprint closure automation tool
- `bin/inspect_fields.py` - Debug tool for identifying custom field IDs
- `bin/debug_sprint_details.py` - Debug tool for sprint analysis

## Story Point Custom Fields

Different Jira boards use different custom field IDs for story points. The code checks:

- `customfield_10016` (default Story Points field)
- `customfield_10026` (Story point estimate)
- `customfield_10031` (alternative Story Points field)

When adding support for new boards, use `inspect_fields.py [board_id]` to identify the correct field.

## Important Technical Details

### Velocity Calculation

- Uses last 6 months of completed sprints by default
- Only counts story points from completed issues (status: done/closed/resolved)
- Calculates mean, median, and standard deviation
- Does NOT factor in team size (historical velocity already reflects team capacity)
- **Target Velocity**: Set `TARGET_VELOCITY_N` (per-project) in `.env` to use a target velocity for planning instead of calculating from historical sprints (useful for setting ambitious goals or when historical data is unreliable; displays as "target velocity (actual: X)" in reports)

### Epic Timeline Projection

- Epics laid out sequentially (NOT in parallel)
- Sorted by remaining work (largest first)
- Uses average velocity for duration estimates
- Completion dates are projections, not commitments

### "No Epic" Tracking

Stories without parent epics are tracked separately using JQL:

```jql
project = {KEY} AND parent is EMPTY AND type != Epic
```

These appear as a special "NO-EPIC" entry if they have remaining work.

### Multi-Project Support

Projects are discovered by checking numbered environment variables:

```
JIRA_PROJECT_KEY_1, JIRA_BOARD_ID_1, TEAM_SIZE_1
JIRA_PROJECT_KEY_2, JIRA_BOARD_ID_2, TEAM_SIZE_2
...
```

Falls back to non-numbered variables (`JIRA_PROJECT_KEY`, `JIRA_BOARD_ID`, `TEAM_SIZE`) if no numbered ones found.

## Security Considerations

- **Project names are sensitive** - do not include actual project names in documentation or commit messages
- API tokens stored in `.env` (not committed to git)
- `.env` should contain credentials only, no sensitive project details in comments

## Story Point Estimation Calibration

**Important Note**: Story point estimates often take ~2x longer than intuitive time estimates due to overhead:

- Meetings, code reviews, context switching
- Testing, debugging, deployment
- Production issues, tech debt
- Documentation, handoffs

This is normal and expected. The velocity-based planning automatically accounts for this overhead, so there's no need to recalibrate estimates as long as:

- Estimation approach remains consistent
- Team size is stable
- Historical velocity reflects current team composition

Example: If you estimate "5 points = 1 week of work" but velocity shows "11 points per week for 4 people", the projections will still be accurate because they use the actual historical velocity.

## Code Patterns

### When modifying story point extraction

Always check all three custom fields:

```python
points = issue['fields'].get('customfield_10016') or \
         issue['fields'].get('customfield_10026') or \
         issue['fields'].get('customfield_10031')
```

### When adding new API calls

Use the JiraClient methods:

```python
client.get_board_sprints(board_id)
client.get_sprint_issues(sprint_id)
client.get_story_points(issue)
```

### When filtering completed issues

Standard statuses:

```python
status = issue['fields'].get('status', {}).get('name', '').lower()
is_complete = status in ['done', 'closed', 'resolved']
```

## Common Troubleshooting

### Story points not appearing

1. Run: `python bin/inspect_fields.py [board_id]`
2. Identify the custom field with numeric story point values
3. Add to `jira_client.py` get_story_points() if not already present
4. Add to field requests in generate_dashboard.py and generate_gantt.py

### Velocity appears too low

- Verify correct custom field is being checked
- Run `debug_sprint_details.py` to see sprint-by-sprint breakdown
- Check if recent sprints show 0 points (indicates wrong field)

### Completed epics still showing

- Dashboard filters `remaining == 0`
- If epic shows, it has incomplete child tasks
- Check child task statuses in Jira

## Development Workflow

1. Make changes in `bin/` directory
2. Test with: `make` (generates dashboards for all projects)
3. Check output in `public/` directory
4. Verify HTML renders correctly and links work
5. Run debug tools if velocity/points look incorrect

## Output Files

All generated in `public/`:

- `{project}.html` - Interactive dashboard
- `{project}_gantt.png` - Gantt chart
- `{project}_velocity_chart.png` - Velocity history chart

## Testing

When making changes:

1. Run `make clean` to clear old outputs
2. Run `make` to regenerate everything
3. Open HTML files in browser to verify
4. Check console output for errors or warnings
5. Verify story points appear correctly
6. Check epic completion dates are reasonable

## Future Enhancements to Consider

- Make sprint length configurable via environment variable
- Add support for parallel epic timelines (not just sequential)
- Team size change detection and velocity adjustment
- Historical team size tracking
- Confidence intervals for completion dates
- What-if scenario planning
- Sprint capacity planning tool
- Burndown chart integration
