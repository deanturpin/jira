#!/usr/bin/env python3
"""Main script to generate Jira planning reports."""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

from jira_client import JiraClient
from velocity_calculator import VelocityCalculator
from epic_planner import EpicPlanner
from excel_generator import ExcelGenerator


def main():
    """Generate Jira planning report."""
    # Load environment variables
    load_dotenv()

    # Validate configuration
    required_vars = ['JIRA_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN', 'JIRA_BOARD_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please copy .env.example to .env and configure your settings.")
        sys.exit(1)

    # Initialize clients
    print("Connecting to Jira...")
    client = JiraClient(
        url=os.getenv('JIRA_URL'),
        email=os.getenv('JIRA_EMAIL'),
        api_token=os.getenv('JIRA_API_TOKEN')
    )

    velocity_calc = VelocityCalculator(client)
    epic_planner = EpicPlanner(client, velocity_calc)

    board_id = int(os.getenv('JIRA_BOARD_ID'))
    num_historical_sprints = int(os.getenv('NUM_HISTORICAL_SPRINTS', '6'))
    num_future_sprints = int(os.getenv('NUM_FUTURE_SPRINTS', '10'))
    confidence_factor = float(os.getenv('CONFIDENCE_FACTOR', '0.8'))

    # Fetch velocity data
    print(f"Fetching velocity data for last {num_historical_sprints} sprints...")
    velocity_data = velocity_calc.get_historical_velocity(board_id, num_historical_sprints)

    if not velocity_data:
        print("Warning: No completed sprints found. Cannot generate velocity report.")
        sys.exit(1)

    print(f"Found {len(velocity_data)} completed sprints")

    velocity_stats = velocity_calc.calculate_velocity_stats(velocity_data)
    print(f"Average velocity: {velocity_stats['mean']:.1f} points/sprint")

    # Project future capacity
    print(f"Projecting capacity for next {num_future_sprints} sprints...")
    sprint_projections = velocity_calc.project_sprint_capacity(
        velocity_data,
        num_future_sprints,
        confidence_factor
    )

    # Fetch and plan epics
    print("Fetching epic data...")
    epics = epic_planner.get_epic_data(board_id)
    print(f"Found {len(epics)} active epics")

    total_remaining = sum(e['remaining_points'] for e in epics)
    print(f"Total remaining work: {total_remaining:.1f} story points")

    print("Calculating epic timeline...")
    timeline, sprint_capacity = epic_planner.calculate_epic_timeline(epics, sprint_projections)

    # Generate Excel report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"jira_planning_report_{timestamp}.xlsx"

    print(f"Generating Excel report: {output_file}")
    excel = ExcelGenerator(output_file)

    excel.add_summary_sheet(velocity_data, velocity_stats)
    excel.add_velocity_sheet(velocity_data, velocity_stats)
    excel.add_epic_timeline_sheet(timeline, sprint_capacity)
    excel.add_capacity_planning_sheet(sprint_projections, sprint_capacity)

    saved_file = excel.save()
    print(f"\nReport generated successfully: {saved_file}")

    # Print summary to console
    print("\n=== Summary ===")
    print(f"Historical velocity: {velocity_stats['mean']:.1f} ± {velocity_stats['std_dev']:.1f} points/sprint")
    print(f"Conservative capacity: {velocity_stats['mean'] * confidence_factor:.1f} points/sprint")
    print(f"\nEpics scheduled:")
    for epic in timeline:
        if epic['status'] == 'scheduled':
            print(f"  - {epic['epic_key']}: Sprints {epic['start_sprint']}-{epic['end_sprint']} ({epic['remaining_points']:.0f} pts)")

    beyond_horizon = [e for e in timeline if e['status'] == 'beyond_horizon']
    if beyond_horizon:
        print(f"\nWarning: {len(beyond_horizon)} epic(s) extend beyond planning horizon")

    print(f"\nOpen the Excel file for detailed charts and timeline visualisation.")


if __name__ == '__main__':
    main()
