#!/usr/bin/env python3
"""Generate comprehensive HTML dashboard for project planning data."""

import os
import sys
import json
import base64
from datetime import datetime
from dotenv import load_dotenv
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import io

from jira_client import JiraClient
from velocity_calculator import VelocityCalculator


def get_jira_colour_hex(colour_key):
    """Map Jira colour keys to actual Jira hex values."""
    # Actual Jira epic colours from https://gist.github.com/jusuchin85/efa658429befb73916b40b1e1a773762
    colour_map = {
        'color_1': '#8d542e',   # Brown
        'color_2': '#ff8b00',   # Orange
        'color_3': '#ffab01',   # Light orange
        'color_4': '#0052cc',   # Blue (default)
        'color_5': '#505f79',   # Grey-blue
        'color_6': '#5fa321',   # Green
        'color_7': '#cd4288',   # Pink/Magenta
        'color_8': '#5143aa',   # Purple
        'color_9': '#ff8f73',   # Coral/Salmon
        'color_10': '#2584ff',  # Bright blue
        'color_11': '#018da6',  # Teal
        'color_12': '#6b778c',  # Grey
        'color_13': '#03875a',  # Dark green
        'color_14': '#de350a',  # Red/Orange-red
    }
    return colour_map.get(colour_key, colour_map['color_4'])


def get_status_badge_colour(status):
    """Get background and text colour for status badge."""
    status_lower = status.lower()

    # In Progress = cyan
    if 'in progress' in status_lower or 'in dev' in status_lower:
        return {'background': '#00b8d9', 'text': '#ffffff'}

    # Testing = green
    if 'test' in status_lower or 'qa' in status_lower or 'review' in status_lower:
        return {'background': '#36b37e', 'text': '#ffffff'}

    # Done/Complete = dark green
    if status_lower in ['done', 'closed', 'resolved', 'complete']:
        return {'background': '#00875a', 'text': '#ffffff'}

    # To Do = grey (default)
    return {'background': '#dfe6e9', 'text': '#636e72'}


def create_velocity_chart_base64(velocity_data, stats, actual_velocity=None):
    """Create velocity chart and return as base64 string.

    Args:
        velocity_data: List of sprint velocity data
        stats: Velocity statistics (may contain target velocity if set)
        actual_velocity: Actual historical velocity (if target velocity is active)
    """
    sprint_names = [v['sprint_name'] for v in velocity_data]
    completed_points = [v['completed_points'] for v in velocity_data]
    committed_points = [v['total_points'] for v in velocity_data]

    # Moving average
    window_size = 3
    moving_avg = []
    for i in range(len(completed_points)):
        start_idx = max(0, i - window_size + 1)
        window = completed_points[start_idx:i + 1]
        moving_avg.append(sum(window) / len(window))

    fig, ax = plt.subplots(figsize=(12, 6))

    x_positions = range(len(sprint_names))
    width = 0.35

    ax.bar([x - width/2 for x in x_positions], committed_points,
           width, label='Committed', color='lightblue', alpha=0.7)
    ax.bar([x + width/2 for x in x_positions], completed_points,
           width, label='Completed', color='darkblue', alpha=0.7)

    ax.plot(x_positions, moving_avg, color='red', linewidth=2,
            marker='o', label=f'{window_size}-Sprint Moving Average')

    # Show both target and actual velocity lines if target is set
    if actual_velocity is not None:
        # Target velocity line (using stats['mean'] which contains target)
        target_velocity = stats['mean']
        ax.axhline(y=target_velocity, color='orange', linestyle='--',
                   linewidth=2, label=f'Target ({target_velocity:.1f} pts)')
        # Actual velocity line
        ax.axhline(y=actual_velocity, color='green', linestyle='--',
                   linewidth=2, label=f'Actual Mean ({actual_velocity:.1f} pts)')
    else:
        # Just show mean velocity line
        mean_velocity = stats['mean']
        ax.axhline(y=mean_velocity, color='green', linestyle='--',
                   linewidth=2, label=f'Average ({mean_velocity:.1f} pts)')

    ax.set_xlabel('Sprint', fontsize=11, fontweight='bold')
    ax.set_ylabel('Story Points', fontsize=11, fontweight='bold')
    ax.set_title('Sprint Velocity Analysis', fontsize=14, fontweight='bold')
    ax.set_xticks(x_positions)
    ax.set_xticklabels(sprint_names, rotation=45, ha='right', fontsize=8)
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    plt.tight_layout()

    # Save to bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode()
    plt.close()

    return img_base64


def create_epic_chart_base64(epic_data):
    """Create epic progress chart and return as base64 string."""
    # Filter epics with story points
    epics_with_work = [e for e in epic_data if e['total'] > 0][:10]  # Top 10

    if not epics_with_work:
        return None

    epic_names = [f"{e['key']}\n{e['name'][:20]}" for e in epics_with_work]
    remaining = [e['remaining'] for e in epics_with_work]
    completed = [e['completed'] for e in epics_with_work]

    fig, ax = plt.subplots(figsize=(10, 6))

    y_positions = range(len(epic_names))
    ax.barh(y_positions, completed, label='Completed', color='green', alpha=0.7)
    ax.barh(y_positions, remaining, left=completed, label='Remaining', color='orange', alpha=0.7)

    ax.set_yticks(y_positions)
    ax.set_yticklabels(epic_names, fontsize=9)
    ax.set_xlabel('Story Points', fontsize=11, fontweight='bold')
    ax.set_title('Epic Progress (Top 10)', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right', fontsize=9)
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode()
    plt.close()

    return img_base64


def generate_html_dashboard(project_key, velocity_data, velocity_stats, epic_data, team_size=5, jira_url='', is_target_velocity=False, actual_velocity=None):
    """Generate complete HTML dashboard.

    Args:
        project_key: Project identifier
        velocity_data: List of sprint velocity data
        velocity_stats: Velocity statistics (may contain target velocity if set)
        epic_data: List of epic data
        team_size: Number of developers
        jira_url: Base Jira URL
        is_target_velocity: Whether target velocity is being used
        actual_velocity: Actual historical velocity (if target velocity is active)
    """

    # Generate charts
    velocity_chart = create_velocity_chart_base64(velocity_data, velocity_stats, actual_velocity)
    epic_chart = create_epic_chart_base64(epic_data)

    # Calculate metrics
    total_remaining = sum(e['remaining'] for e in epic_data)
    total_completed = sum(e['completed'] for e in epic_data)
    total_all = sum(e['total'] for e in epic_data)
    epics_with_work = [e for e in epic_data if e['remaining'] > 0]

    # Calculate projected completion
    avg_velocity = velocity_stats['mean']
    velocity_label = "Target Velocity" if is_target_velocity else "Average Velocity"
    sprints_remaining = int(total_remaining / avg_velocity) if avg_velocity > 0 else 999
    weeks_remaining = sprints_remaining  # 1-week sprints

    # Calculate completion date
    from datetime import timedelta
    if velocity_data:
        last_sprint_end = datetime.fromisoformat(velocity_data[-1]['end_date'].replace('Z', '+00:00'))
        projected_completion = last_sprint_end + timedelta(weeks=weeks_remaining)
        completion_date_str = projected_completion.strftime('%Y-%m-%d')
    else:
        completion_date_str = 'Unknown'
        last_sprint_end = datetime.now()

    # Calculate per-epic completion dates (one person working on each)
    for epic in epic_data:
        if epic['remaining'] > 0 and avg_velocity > 0:
            epic_weeks = epic['remaining'] / avg_velocity
            epic_completion = last_sprint_end + timedelta(weeks=epic_weeks)
            epic['est_completion'] = epic_completion.strftime('%Y-%m-%d')
        else:
            epic['est_completion'] = 'Done' if epic['remaining'] == 0 else 'N/A'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_key.upper()} Project Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f7fa;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .header .timestamp {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}
        .metric-card h3 {{
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .metric-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .metric-card .subvalue {{
            font-size: 14px;
            color: #888;
            margin-top: 5px;
        }}
        .section {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            font-size: 24px;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .chart-container {{
            margin: 20px 0;
            text-align: center;
        }}
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.5px;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-high {{ background: #fee; color: #c33; }}
        .badge-medium {{ background: #ffeaa7; color: #d63031; }}
        .badge-low {{ background: #dfe6e9; color: #636e72; }}
        .badge-done {{ background: #d5f4e6; color: #00b894; }}
        .footer {{
            text-align: center;
            color: #888;
            margin-top: 40px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{project_key.upper()} Project Dashboard</h1>
            <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Team Size</h3>
                <div class="value">{team_size}</div>
                <div class="subvalue">developers</div>
            </div>
            <div class="metric-card">
                <h3>{velocity_label}</h3>
                <div class="value">{velocity_stats['mean']:.0f}</div>
                <div class="subvalue">points/sprint ± {velocity_stats['std_dev']:.0f}</div>
            </div>
            <div class="metric-card">
                <h3>Remaining Work</h3>
                <div class="value">{total_remaining:.0f}</div>
                <div class="subvalue">{len(epics_with_work)} epics with work</div>
            </div>
            <div class="metric-card">
                <h3>Projected Completion</h3>
                <div class="value" style="font-size: 24px;">{completion_date_str}</div>
                <div class="subvalue">~{sprints_remaining} sprints / {weeks_remaining} weeks</div>
            </div>
        </div>

        <div class="section">
            <h2>📅 Epic Timeline (Gantt Chart)</h2>
            <div class="chart-container">
                <img src="./{project_key}_gantt.png" alt="Gantt Chart" style="max-width: 100%; height: auto;">
            </div>
            <p style="color: #666; font-size: 14px; margin-top: 15px;">
                Sequential timeline showing when each epic could complete. Epics are laid out end-to-end based on remaining story points and average velocity.
            </p>
        </div>
"""

    if epic_chart:
        html += f"""
        <div class="section">
            <h2>🎯 Epic Progress</h2>
            <div class="chart-container">
                <img src="data:image/png;base64,{epic_chart}" alt="Epic Chart">
            </div>
        </div>
"""

    # Calculate per-developer velocity
    per_dev_velocity = velocity_stats['mean'] / team_size if team_size > 0 else 0

    # Epic table
    html += """
        <div class="section">
            <h2>📋 Epic Breakdown</h2>
            <p style="color: #666; font-size: 14px; margin-bottom: 15px;">Sorted by remaining work (highest first). Time to complete assumes one person working at average velocity.</p>
            <table>
                <colgroup>
                    <col style="width: 8%;">
                    <col style="width: 25%;">
                    <col style="width: 10%;">
                    <col style="width: 10%;">
                    <col style="width: 8%;">
                    <col style="width: 25%;">
                    <col style="width: 14%;">
                </colgroup>
                <thead>
                    <tr>
                        <th>Epic</th>
                        <th>Name</th>
                        <th style="text-align: right;">Remaining</th>
                        <th style="text-align: right;">Completed</th>
                        <th style="text-align: right;">Total</th>
                        <th style="text-align: center;">Progress</th>
                        <th style="text-align: right;">Weeks (1 dev)</th>
                    </tr>
                </thead>
                <tbody>
"""

    for epic in epic_data:
        if epic['total'] == 0 or epic['remaining'] == 0:
            continue

        progress_pct = epic['pct']
        epic_colour = get_jira_colour_hex(epic.get('colour', 'color_4'))

        # Calculate weeks needed for 1 developer (sprints are 1 week each)
        weeks_needed = epic['remaining'] / per_dev_velocity if per_dev_velocity > 0 else 0

        epic_link = f'{jira_url}/browse/{epic["key"]}' if jira_url else '#'
        html += f"""
                    <tr>
                        <td style="background: {epic_colour}; border-left: 5px solid {epic_colour};"><strong><a href="{epic_link}" target="_blank" style="color: white; text-decoration: none;">{epic['key']}</a></strong></td>
                        <td>{epic['name']}</td>
                        <td style="text-align: right;">{epic['remaining']:.0f}</td>
                        <td style="text-align: right;">{epic['completed']:.0f}</td>
                        <td style="text-align: right;">{epic['total']:.0f}</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-bar-fill" style="width: {progress_pct}%"></div>
                            </div>
                            <div style="text-align: center; font-size: 12px; margin-top: 4px;">{progress_pct:.0f}%</div>
                        </td>
                        <td style="text-align: right;">{weeks_needed:.1f}w</td>
                    </tr>
"""

    html += f"""
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>📈 Velocity History Chart</h2>
            <div class="chart-container">
                <img src="./{project_key}_velocity_chart.png" alt="Velocity Chart" style="max-width: 100%; height: auto;">
            </div>
            <p style="color: #666; font-size: 14px; margin-top: 15px;">
                Historical velocity across all completed sprints showing committed vs completed points, 3-sprint moving average, and mean velocity line.
            </p>
        </div>

        <div class="section">
            <h2>🎯 Epic Timeline Overview (Grouped by Developer)</h2>
            <p style="color: #666; font-size: 14px; margin-bottom: 15px;">
                Detailed breakdown showing each developer's queue. Epics are worked on sequentially within each developer's track. Child tasks sorted by story points (largest first).
            </p>
"""

    # Group epics by assigned developer
    from collections import defaultdict
    epics_by_dev = defaultdict(list)
    for epic in epic_data:
        if epic['remaining'] > 0 and epic.get('assigned_dev'):
            epics_by_dev[epic['assigned_dev']].append(epic)

    # Display epics grouped by developer
    for dev_num in sorted(epics_by_dev.keys()):
        html += f"""
            <div style="margin-bottom: 30px;">
                <h3 style="margin: 0 0 15px 0; padding: 10px 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; font-size: 18px;">
                    👤 Developer {dev_num} Queue
                </h3>
"""

        for epic in epics_by_dev[dev_num]:
            epic_link = f'{jira_url}/browse/{epic["key"]}' if jira_url else '#'
            html += f"""
                <div style="margin-bottom: 20px; padding: 20px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">
                        <a href="{epic_link}" target="_blank" style="color: #667eea; text-decoration: none;">{epic['key']}</a>: {epic['name']}
                    </h4>
                    <p style="margin: 0 0 15px 0; color: #666; font-size: 14px;">
                        {epic['remaining']:.0f} points remaining • Est. completion: {epic.get('est_completion', 'N/A')}
                    </p>
"""

            if epic['child_tasks']:
                html += """
                    <table style="background: white; margin: 0;">
                        <thead>
                            <tr>
                                <th>Task</th>
                                <th>Summary</th>
                                <th style="text-align: center;">Status</th>
                                <th style="text-align: right;">Points</th>
                            </tr>
                        </thead>
                        <tbody>
"""
                for task in epic['child_tasks']:
                    task_link = f'{jira_url}/browse/{task["key"]}' if jira_url else '#'
                    points_display = f'{task["points"]:.0f}' if task['points'] > 0 else '-'
                    status_colours = get_status_badge_colour(task['status'])
                    html += f"""
                            <tr>
                                <td><a href="{task_link}" target="_blank" style="color: #667eea; text-decoration: none;">{task['key']}</a></td>
                                <td>{task['summary']}</td>
                                <td style="text-align: center;"><span class="badge" style="background: {status_colours['background']}; color: {status_colours['text']};">{task['status']}</span></td>
                                <td style="text-align: right;">{points_display}</td>
                            </tr>
"""
                html += """
                        </tbody>
                    </table>
"""
            else:
                html += """
                    <p style="color: #888; font-style: italic; margin: 0;">No remaining child tasks</p>
"""

            html += """
                </div>
"""

        html += """
            </div>
"""

    html += f"""
        </div>

        <div class="section">
            <h2>📊 Sprint Velocity Trend</h2>
            <div class="chart-container">
                <img src="data:image/png;base64,{velocity_chart}" alt="Velocity Chart">
            </div>
            <p style="color: #666; font-size: 14px; margin-top: 15px;">
                Showing {len(velocity_data)} most recent sprints.
                Latest sprint: {velocity_data[-1]['completed_points']:.0f} points.
                Coefficient of variation: {(velocity_stats['std_dev']/velocity_stats['mean']*100):.0f}%
            </p>
        </div>

        <div class="footer">
            <p>Generated by Jira Planning Tools</p>
            <p style="margin-top: 5px; font-size: 12px;">Data from Jira • Refresh this report by running generate_dashboard.py</p>
        </div>
    </div>
</body>
</html>
"""

    return html


def generate_project_dashboard(client, project_key, board_id, team_size, jira_url, target_velocity=None, exclude_epics=None):
    """Generate dashboard for a single project.

    Args:
        exclude_epics: List of epic numbers to exclude (e.g., ['123', '456'])
    """
    if exclude_epics is None:
        exclude_epics = []

    # Convert to full epic keys for filtering
    exclude_keys = {f"{project_key.upper()}-{num}" for num in exclude_epics}
    velocity_calc = VelocityCalculator(client)

    # Fetch velocity data (last 6 months)
    print("Fetching velocity data...")
    velocity_data = velocity_calc.get_historical_velocity(board_id, months=6)
    velocity_stats = velocity_calc.calculate_velocity_stats(velocity_data)

    # Apply target velocity if set (prefer parameter over environment variable)
    if target_velocity is None:
        target_velocity = os.getenv('TARGET_VELOCITY') or os.getenv('VELOCITY_OVERRIDE')  # Fallback to old name
        if target_velocity:
            target_velocity = float(target_velocity)

    is_target_velocity = bool(target_velocity)
    actual_velocity = None
    if target_velocity:
        actual_velocity = velocity_stats['mean']
        velocity_stats['mean'] = target_velocity
        print(f"  Target velocity: {velocity_stats['mean']:.1f} points/sprint (actual: {actual_velocity:.1f})")
    else:
        print(f"  Average velocity: {velocity_stats['mean']:.1f} points/sprint")

    # Fetch epic data
    print("Fetching epic data...")
    import requests

    url = os.getenv('JIRA_URL').rstrip('/')
    auth = (os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN'))
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

    # Fetch epics from board API (has colour info)
    board_epic_response = requests.get(
        f'{url}/rest/agile/1.0/board/{board_id}/epic',
        auth=auth,
        headers={'Accept': 'application/json'},
        params={'maxResults': 200}
    )

    board_epics = board_epic_response.json().get('values', []) if board_epic_response.status_code == 200 else []
    board_epic_keys = {e['key'] for e in board_epics}

    # Fetch all project epics via JQL to catch any not on board
    jql_response = requests.post(
        f'{url}/rest/api/3/search/jql',
        auth=auth,
        headers=headers,
        json={
            'jql': f'project = {project_key.upper()} AND type = Epic',
            'maxResults': 200,
            'fields': ['summary', 'status']
        }
    )

    # Combine: board epics have colour, JQL epics fill gaps
    epics = list(board_epics)  # Start with board epics (have colours)

    if jql_response.status_code == 200:
        jql_epics = jql_response.json().get('issues', [])
        # Add epics from JQL that aren't in board (won't have colour)
        for issue in jql_epics:
            if issue['key'] not in board_epic_keys:
                status_name = issue['fields'].get('status', {}).get('name', '').lower()
                is_done = status_name in ['done', 'closed', 'resolved']
                epics.append({
                    'key': issue['key'],
                    'summary': issue['fields'].get('summary', 'Unnamed'),
                    'name': issue['fields'].get('summary', 'Unnamed'),
                    'done': is_done,
                    'color': {'key': 'color_4'}  # default colour for non-board epics
                })

    print(f"  Found {len(epics)} total epics ({len(board_epics)} from board, {len(epics) - len(board_epics)} from project)")

    # Filter out excluded epics
    active_epics = [e for e in epics if not e.get('done', False) and e['key'] not in exclude_keys]
    if exclude_keys:
        print(f"  Excluding epics: {', '.join(sorted(exclude_keys))}")
    print(f"  Active epics: {len(active_epics)}")

    epic_data = []
    for epic in active_epics:
        epic_key = epic['key']
        epic_name = epic.get('summary', epic.get('name', 'Unnamed'))
        epic_colour = epic.get('color', {}).get('key', 'color_4')

        issue_response = requests.post(
            f'{url}/rest/api/3/search/jql',
            auth=auth,
            headers=headers,
            json={
                'jql': f'parent = {epic_key}',
                'maxResults': 200,
                'fields': ['summary', 'status', 'customfield_10016', 'customfield_10026', 'customfield_10031']
            }
        )

        if issue_response.status_code != 200:
            continue

        issues = issue_response.json().get('issues', [])

        total_points = 0.0
        completed_points = 0.0
        child_tasks = []

        for issue in issues:
            # Try all common story point fields
            points = issue['fields'].get('customfield_10016') or issue['fields'].get('customfield_10026') or issue['fields'].get('customfield_10031')
            points = float(points) if points else 0.0
            total_points += points

            status = issue['fields'].get('status', {}).get('name', '').lower()
            is_complete = status in ['done', 'closed', 'resolved']
            if is_complete:
                completed_points += points

            # Store child task details (only if not complete)
            if not is_complete:
                child_tasks.append({
                    'key': issue['key'],
                    'summary': issue['fields'].get('summary', 'Unnamed'),
                    'points': points,
                    'status': issue['fields'].get('status', {}).get('name', 'Unknown')
                })

        remaining_points = total_points - completed_points

        # Sort child tasks by points (largest first)
        child_tasks.sort(key=lambda t: t['points'], reverse=True)

        epic_data.append({
            'key': epic_key,
            'name': epic_name,
            'total': total_points,
            'completed': completed_points,
            'remaining': remaining_points,
            'pct': (completed_points / total_points * 100) if total_points > 0 else 0,
            'child_tasks': child_tasks,
            'colour': epic_colour
        })

    # Fetch stories without epics (no parent)
    print("Fetching stories without epics...")
    no_epic_response = requests.post(
        f'{url}/rest/api/3/search/jql',
        auth=auth,
        headers=headers,
        json={
            'jql': f'project = {project_key.upper()} AND parent is EMPTY AND type != Epic',
            'maxResults': 200,
            'fields': ['summary', 'status', 'customfield_10016', 'customfield_10026', 'customfield_10031']
        }
    )

    if no_epic_response.status_code == 200:
        no_epic_issues = no_epic_response.json().get('issues', [])

        if no_epic_issues:
            total_points = 0.0
            completed_points = 0.0
            child_tasks = []

            for issue in no_epic_issues:
                # Try all common story point fields
                points = issue['fields'].get('customfield_10016') or issue['fields'].get('customfield_10026') or issue['fields'].get('customfield_10031')
                points = float(points) if points else 0.0
                total_points += points

                status = issue['fields'].get('status', {}).get('name', '').lower()
                is_complete = status in ['done', 'closed', 'resolved']
                if is_complete:
                    completed_points += points

                # Store task details (only if not complete)
                if not is_complete:
                    child_tasks.append({
                        'key': issue['key'],
                        'summary': issue['fields'].get('summary', 'Unnamed'),
                        'points': points,
                        'status': issue['fields'].get('status', {}).get('name', 'Unknown')
                    })

            remaining_points = total_points - completed_points

            # Sort child tasks by points (largest first)
            child_tasks.sort(key=lambda t: t['points'], reverse=True)

            # Add special "No Epic" entry if there's remaining work
            if remaining_points > 0:
                epic_data.append({
                    'key': 'NO-EPIC',
                    'name': 'Stories without Epic',
                    'total': total_points,
                    'completed': completed_points,
                    'remaining': remaining_points,
                    'pct': (completed_points / total_points * 100) if total_points > 0 else 0,
                    'child_tasks': child_tasks,
                    'colour': 'color_4'  # Default blue for no-epic items
                })

    # Sort by remaining work (most first) to prioritise high-value epics
    epic_data.sort(key=lambda e: e['remaining'], reverse=True)

    # Calculate parallel completion dates using same logic as Gantt chart
    from datetime import datetime, timedelta
    if velocity_data:
        last_sprint_end = datetime.fromisoformat(velocity_data[-1]['end_date'].replace('Z', '+00:00'))
    else:
        last_sprint_end = datetime.now()

    project_start = last_sprint_end + timedelta(days=1)
    avg_velocity = velocity_stats['mean']
    velocity_per_person = avg_velocity / team_size if team_size > 0 else avg_velocity

    # Initialise tracks for parallel scheduling
    tracks = [project_start for _ in range(team_size)]

    # Calculate completion date for each epic
    for epic in epic_data:
        if epic['remaining'] > 0:
            # Calculate duration
            sprints_needed = epic['remaining'] / velocity_per_person if velocity_per_person > 0 else 0
            weeks_needed = sprints_needed  # 1-week sprints
            days_needed = int(weeks_needed * 7)
            if days_needed < 1:
                days_needed = 1

            # Assign to earliest available track
            earliest_track_idx = min(range(len(tracks)), key=lambda i: tracks[i])
            start_date = tracks[earliest_track_idx]
            end_date = start_date + timedelta(days=days_needed)

            # Store completion date and track assignment
            epic['est_completion'] = end_date.strftime('%Y-%m-%d')
            epic['assigned_dev'] = earliest_track_idx + 1  # 1-indexed for display

            # Update track
            tracks[earliest_track_idx] = end_date + timedelta(days=1)
        else:
            epic['est_completion'] = 'Completed'
            epic['assigned_dev'] = None

    # Calculate totals for summary
    total_remaining = sum(e['remaining'] for e in epic_data)

    # Generate HTML
    print(f"Generating HTML dashboard for {project_key.upper()}...")
    html = generate_html_dashboard(project_key, velocity_data, velocity_stats, epic_data, team_size, jira_url, is_target_velocity, actual_velocity)

    output_file = f'../public/{project_key}.html'
    with open(output_file, 'w') as f:
        f.write(html)

    print(f"✓ Dashboard generated: {output_file}")
    print(f"  Team size: {team_size} developers")
    print(f"  Remaining work: {total_remaining:.1f} story points")
    print(f"  Projected completion: {int(total_remaining / velocity_stats['mean']) if velocity_stats['mean'] > 0 else '∞'} sprints")

    return output_file


def main():
    """Generate HTML dashboards for all configured projects."""
    load_dotenv()

    # Check for shared credentials
    required_vars = ['JIRA_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    # Connect to Jira once
    print("Connecting to Jira...")
    client = JiraClient(
        url=os.getenv('JIRA_URL'),
        email=os.getenv('JIRA_EMAIL'),
        api_token=os.getenv('JIRA_API_TOKEN')
    )
    jira_url = os.getenv('JIRA_URL', '').rstrip('/')

    # Find all project configurations
    projects = []

    # Check for numbered project configs
    i = 1
    while True:
        project_key = os.getenv(f'JIRA_PROJECT_KEY_{i}')
        board_id = os.getenv(f'JIRA_BOARD_ID_{i}')

        if not project_key or not board_id:
            break

        team_size = int(os.getenv(f'TEAM_SIZE_{i}', '5'))
        projects.append({
            'key': project_key.lower(),
            'board_id': int(board_id),
            'team_size': team_size
        })
        i += 1

    # Fallback to non-numbered vars if no numbered ones found
    if not projects:
        project_key = os.getenv('JIRA_PROJECT_KEY')
        board_id = os.getenv('JIRA_BOARD_ID')

        if not project_key or not board_id:
            print("Error: No project configuration found (JIRA_PROJECT_KEY_1 and JIRA_BOARD_ID_1, or JIRA_PROJECT_KEY and JIRA_BOARD_ID)")
            sys.exit(1)

        team_size = int(os.getenv('TEAM_SIZE', '5'))
        projects.append({
            'key': project_key.lower(),
            'board_id': int(board_id),
            'team_size': team_size
        })

    print(f"\nFound {len(projects)} project(s) to process\n")

    # Generate dashboard for each project
    output_files = []
    for project in projects:
        print(f"{'='*60}")
        print(f"Processing project: {project['key'].upper()}")
        print(f"{'='*60}")

        output_file = generate_project_dashboard(
            client,
            project['key'],
            project['board_id'],
            project['team_size'],
            jira_url
        )
        output_files.append(output_file)
        print()

    print(f"\n{'='*60}")
    print(f"✓ All dashboards generated successfully")
    print(f"{'='*60}")
    for output_file in output_files:
        print(f"  {output_file}")


if __name__ == '__main__':
    main()
