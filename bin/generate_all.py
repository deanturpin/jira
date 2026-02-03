#!/usr/bin/env python3
"""Generate all planning outputs (dashboards and Gantt charts) in a single pass."""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

from jira_client import JiraClient
from velocity_calculator import VelocityCalculator
from stats_logger import StatsLogger

# Import generation functions from existing modules
from generate_dashboard import generate_project_dashboard
from generate_gantt import generate_project_gantt
from generate_pdf import generate_project_pdf


def main():
    """Generate all outputs for all configured projects in a single pass."""
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
    while i <= 10:  # Support up to 10 projects
        project_key = os.getenv(f'JIRA_PROJECT_KEY_{i}')
        board_id = os.getenv(f'JIRA_BOARD_ID_{i}')

        # Skip if project key or board ID is empty/null
        if project_key and board_id:
            team_size = int(os.getenv(f'TEAM_SIZE_{i}', '5'))
            target_velocity = os.getenv(f'TARGET_VELOCITY_{i}') or os.getenv('VELOCITY_OVERRIDE')  # Fallback to old name
            exclude_epics = os.getenv(f'EXCLUDE_EPICS_{i}', '')
            exclude_list = [epic.strip() for epic in exclude_epics.split(',') if epic.strip()]
            projects.append({
                'key': project_key.lower(),
                'board_id': int(board_id),
                'team_size': team_size,
                'target_velocity': float(target_velocity) if target_velocity else None,
                'exclude_epics': exclude_list
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
        target_velocity = os.getenv('TARGET_VELOCITY') or os.getenv('VELOCITY_OVERRIDE')  # Fallback to old name
        exclude_epics = os.getenv('EXCLUDE_EPICS', '')
        exclude_list = [epic.strip() for epic in exclude_epics.split(',') if epic.strip()]
        projects.append({
            'key': project_key.lower(),
            'board_id': int(board_id),
            'team_size': team_size,
            'target_velocity': float(target_velocity) if target_velocity else None,
            'exclude_epics': exclude_list
        })

    print(f"Found {len(projects)} project(s) to process\n")

    # Generate all outputs for each project
    dashboard_files = []
    gantt_files = []
    pdf_files = []

    for project in projects:
        print(f"{'='*60}")
        print(f"Processing project: {project['key'].upper()}")
        print(f"{'='*60}")

        # Generate dashboard
        print("\n📊 Generating dashboard...")
        dashboard_file = generate_project_dashboard(
            client,
            project['key'],
            project['board_id'],
            project['team_size'],
            jira_url,
            project.get('target_velocity'),
            project.get('exclude_epics', [])
        )
        dashboard_files.append(dashboard_file)

        # Generate Gantt chart (also logs statistics)
        print("\n📅 Generating Gantt chart...")
        gantt_file = generate_project_gantt(
            client,
            project['key'],
            project['board_id'],
            project['team_size'],
            project.get('target_velocity'),
            project.get('exclude_epics', [])
        )
        if gantt_file:
            gantt_files.append(gantt_file)

        # Generate trend chart from historical stats
        print("\n📈 Generating trend chart...")
        logger = StatsLogger()
        trends_file = logger.generate_trend_chart(project['key'])

        # Generate PDF report
        print("\n📄 Generating PDF report...")
        pdf_file = generate_project_pdf(
            client,
            project['key'],
            project['board_id'],
            project['team_size'],
            jira_url,
            project.get('target_velocity'),
            project.get('exclude_epics', [])
        )
        pdf_files.append(pdf_file)

        print()

    # Summary
    print(f"{'='*60}")
    print(f"✓ All outputs generated successfully")
    print(f"{'='*60}")
    print("\nDashboards:")
    for f in dashboard_files:
        print(f"  {f}")
    print("\nGantt charts:")
    for f in gantt_files:
        print(f"  {f}")
    print("\nPDF reports:")
    for f in pdf_files:
        print(f"  {f}")


if __name__ == '__main__':
    main()
