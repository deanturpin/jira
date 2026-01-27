#!/usr/bin/env python3
"""Generate Gantt chart showing epic timeline based on team capacity."""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import requests

from jira_client import JiraClient
from velocity_calculator import VelocityCalculator


def get_jira_colour_hex(colour_key):
    """Map Jira colour keys to actual Jira hex values."""
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


def create_gantt_chart(epic_timeline, velocity_stats, project_key, team_size):
    """Create Gantt chart showing epic timeline with parallel swim lanes grouped by developer."""
    if not epic_timeline:
        print("No epics to display")
        return None

    # Group epics by track for visual organisation
    epics_with_work = [e for e in epic_timeline if e['remaining_points'] > 0]
    if not epics_with_work:
        print("No epics with remaining work to display")
        return None

    # Sort by track first, then by start date within each track
    epics_with_work.sort(key=lambda e: (e.get('track', 0), datetime.fromisoformat(e['start_date'])))

    fig, ax = plt.subplots(figsize=(16, max(8, len(epics_with_work) * 0.4)))

    # Define colours for different tracks/swim lanes
    track_colours = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe',
                     '#43e97b', '#fa709a', '#fee140', '#30cfd0', '#667eea']

    y_pos = 0
    y_labels = []
    y_ticks = []
    current_track = -1

    for epic in epics_with_work:
        start_date = datetime.fromisoformat(epic['start_date'])
        end_date = datetime.fromisoformat(epic['end_date'])
        duration = (end_date - start_date).days

        # Use epic's actual colour from Jira
        track = epic.get('track', 0)
        epic_colour_key = epic.get('colour', 'color_4')
        colour = get_jira_colour_hex(epic_colour_key)

        # Add separator line between tracks
        if track != current_track and current_track >= 0:
            ax.axhline(y=y_pos - 0.5, color='#666', linewidth=2, linestyle='-', alpha=0.5)
            current_track = track

        if current_track == -1:
            current_track = track

        # Draw rectangle for epic
        ax.barh(y_pos, duration, left=start_date, height=0.8,
                color=colour, alpha=0.7, edgecolor='black', linewidth=1)

        # Add epic label with developer assignment
        epic_name_short = epic['epic_name'][:25] if len(epic['epic_name']) > 25 else epic['epic_name']
        label = f"{epic['epic_key']}"
        points_label = f"{epic['remaining_points']:.0f} pts"
        dev_label = f"Dev {track + 1}"

        y_labels.append(f"[{dev_label}] {label}: {epic_name_short}\n({points_label})")
        y_ticks.append(y_pos)

        # Add epic name inside bar if there's room
        bar_mid = start_date + timedelta(days=duration/2)
        if duration > 10:  # Only add text if bar is wide enough
            # Show epic key + name if bar is very wide, otherwise just key
            if duration > 20:
                bar_label = f"{epic['epic_key']}: {epic_name_short}"
            else:
                bar_label = epic['epic_key']

            ax.text(bar_mid, y_pos, bar_label,
                   ha='center', va='center', fontweight='bold',
                   fontsize=9, color='white')

        y_pos += 1

    # Format x-axis as dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.xticks(rotation=45, ha='right')

    # Set y-axis labels
    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels, fontsize=10)

    # Labels and title
    ax.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax.set_ylabel('Epic (grouped by developer)', fontsize=12, fontweight='bold')
    ax.set_title(f'{project_key.upper()} Epic Timeline - Parallel Planning ({team_size} Developers)\n'
                f'Average Velocity: {velocity_stats["mean"]:.1f} pts/sprint (Team), '
                f'{velocity_stats["mean"]/team_size:.1f} pts/sprint (Per Developer)',
                fontsize=14, fontweight='bold', pad=20)

    # Add grid
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Invert y-axis so first epic is at top
    ax.invert_yaxis()

    plt.tight_layout()

    return fig


def generate_project_gantt(client, project_key, board_id, team_size, target_velocity=None, exclude_epics=None):
    """Generate Gantt chart for a single project.

    Args:
        exclude_epics: List of epic numbers to exclude (e.g., ['123', '456'])
    """
    if exclude_epics is None:
        exclude_epics = []

    # Convert to full epic keys for filtering
    exclude_keys = {f"{project_key.upper()}-{num}" for num in exclude_epics}

    # Get velocity data (last 6 months)
    print("Fetching velocity data...")
    velocity_calc = VelocityCalculator(client)
    velocity_data = velocity_calc.get_historical_velocity(board_id, months=6)
    velocity_stats = velocity_calc.calculate_velocity_stats(velocity_data)

    # Apply target velocity if set (prefer parameter over environment variable)
    if target_velocity is None:
        target_velocity = os.getenv('TARGET_VELOCITY') or os.getenv('VELOCITY_OVERRIDE')  # Fallback to old name
        if target_velocity:
            target_velocity = float(target_velocity)

    if target_velocity:
        actual_velocity = velocity_stats['mean']
        velocity_stats['mean'] = target_velocity
        avg_velocity = velocity_stats['mean']
        print(f"Target velocity: {avg_velocity:.1f} points/sprint (actual: {actual_velocity:.1f})")
    else:
        avg_velocity = velocity_stats['mean']
        print(f"Average velocity: {avg_velocity:.1f} points/sprint")

    # Get epic data
    print("Fetching epic data...")
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

    # Filter out excluded epics
    active_epics = [e for e in epics if not e.get('done', False) and e['key'] not in exclude_keys]
    if exclude_keys:
        print(f"  Excluding epics: {', '.join(sorted(exclude_keys))}")

    # Get remaining points for each epic
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
                'fields': ['customfield_10016', 'customfield_10026', 'customfield_10031', 'status']
            }
        )

        if issue_response.status_code != 200:
            continue

        issues = issue_response.json().get('issues', [])

        remaining_points = 0.0
        for issue in issues:
            # Try all common story point fields
            points = issue['fields'].get('customfield_10016') or issue['fields'].get('customfield_10026') or issue['fields'].get('customfield_10031')
            points = float(points) if points else 0.0

            status = issue['fields'].get('status', {}).get('name', '').lower()
            if status not in ['done', 'closed', 'resolved']:
                remaining_points += points

        if remaining_points > 0:
            epic_data.append({
                'epic_key': epic_key,
                'epic_name': epic_name,
                'remaining_points': remaining_points,
                'colour': epic_colour
            })

    # Sort by remaining points (largest first)
    epic_data.sort(key=lambda e: e['remaining_points'], reverse=True)

    print(f"Found {len(epic_data)} epics with remaining work")

    # Calculate timeline - lay epics out in parallel swim lanes based on team size
    # Each person works on one epic at a time, so team_size = number of parallel tracks
    if velocity_data:
        last_sprint_end = datetime.fromisoformat(velocity_data[-1]['end_date'].replace('Z', '+00:00'))
    else:
        last_sprint_end = datetime.now()

    project_start = last_sprint_end + timedelta(days=1)

    # Initialise swim lane tracks - each track represents one person's timeline
    tracks = [project_start for _ in range(team_size)]
    epic_timeline = []

    for epic in epic_data:
        # Calculate duration in weeks based on velocity per person
        # velocity is team velocity, so divide by team size to get per-person capacity
        velocity_per_person = avg_velocity / team_size if team_size > 0 else avg_velocity
        sprints_needed = epic['remaining_points'] / velocity_per_person if velocity_per_person > 0 else 0
        weeks_needed = sprints_needed  # 1-week sprints
        days_needed = int(weeks_needed * 7)

        if days_needed < 1:
            days_needed = 1

        # Assign to earliest available track
        earliest_track_idx = min(range(len(tracks)), key=lambda i: tracks[i])
        start_date = tracks[earliest_track_idx]
        end_date = start_date + timedelta(days=days_needed)

        epic_timeline.append({
            'epic_key': epic['epic_key'],
            'epic_name': epic['epic_name'],
            'remaining_points': epic['remaining_points'],
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'duration_days': days_needed,
            'sprints': sprints_needed,
            'track': earliest_track_idx,
            'colour': epic['colour']
        })

        # Update track end date
        tracks[earliest_track_idx] = end_date + timedelta(days=1)

    # Generate Gantt chart
    print(f"Generating Gantt chart for {project_key.upper()}...")
    fig = create_gantt_chart(epic_timeline, velocity_stats, project_key, team_size)

    if fig:
        output_file = f'../public/{project_key}_gantt.png'
        fig.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Gantt chart saved: {output_file}")

        # Print summary grouped by developer
        print("\nEpic Timeline Summary (Parallel Planning - Grouped by Developer):")

        # Group by track for summary output
        from collections import defaultdict
        epics_by_dev = defaultdict(list)
        for epic in epic_timeline:
            track = epic.get('track', 0)
            epics_by_dev[track].append(epic)

        for dev_idx in sorted(epics_by_dev.keys()):
            print(f"\n  Dev {dev_idx + 1}:")
            for epic in epics_by_dev[dev_idx]:
                print(f"    {epic['epic_key']}: {epic['start_date'][:10]} → {epic['end_date'][:10]} "
                      f"({epic['duration_days']} days, {epic['sprints']:.1f} sprints, {epic['remaining_points']:.0f} pts)")

        # Find the latest end date across all tracks
        final_date = max(e['end_date'][:10] for e in epic_timeline) if epic_timeline else 'N/A'
        print(f"\n  Projected completion: {final_date}")
        print(f"  Team size: {team_size} developers")
        print(f"  Average velocity: {avg_velocity:.1f} points/sprint (team), {avg_velocity/team_size:.1f} points/sprint (per developer)")

        return output_file

    return None


def main():
    """Generate Gantt charts for all configured projects."""
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

    # Generate Gantt chart for each project
    output_files = []
    for project in projects:
        print(f"{'='*60}")
        print(f"Processing project: {project['key'].upper()}")
        print(f"{'='*60}")

        output_file = generate_project_gantt(
            client,
            project['key'],
            project['board_id'],
            project['team_size']
        )
        if output_file:
            output_files.append(output_file)
        print()

    print(f"\n{'='*60}")
    print(f"✓ All Gantt charts generated successfully")
    print(f"{'='*60}")
    for output_file in output_files:
        print(f"  {output_file}")


if __name__ == '__main__':
    main()
