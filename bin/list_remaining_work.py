#!/usr/bin/env python3
"""List epics with remaining story points - batch approach."""

import os
import sys
from dotenv import load_dotenv

from jira_client import JiraClient


def main():
    """List epics with remaining work."""
    load_dotenv()

    required_vars = ['JIRA_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN', 'JIRA_BOARD_ID', 'JIRA_PROJECT_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    client = JiraClient(
        url=os.getenv('JIRA_URL'),
        email=os.getenv('JIRA_EMAIL'),
        api_token=os.getenv('JIRA_API_TOKEN')
    )

    board_id = int(os.getenv('JIRA_BOARD_ID'))
    project_key = os.getenv('JIRA_PROJECT_KEY')

    print("Fetching epics from board...")
    epics = client.get_epics(board_id)

    # Filter active epics
    active_epics = [e for e in epics if not e.get('done', False)]
    print(f"Found {len(active_epics)} active epics\n")

    if not active_epics:
        print("No active epics found.")
        return

    # Build epic summary
    epic_data = []

    for epic in active_epics:
        epic_key = epic['key']
        epic_name = epic.get('name', 'Unnamed')

        # Use the agile API to get epic issues directly
        # This uses the same endpoint the UI uses
        try:
            response = client._get(f'/epic/{epic["id"]}/issue', params={
                'fields': 'summary,status,customfield_10016',
                'maxResults': 200
            })
            issues = response.get('issues', [])
        except Exception:
            # If epic endpoint fails, skip this epic
            issues = []

        total_points = 0.0
        remaining_points = 0.0

        for issue in issues:
            points = client.get_story_points(issue)
            total_points += points

            if not client.is_issue_completed(issue):
                remaining_points += points

        epic_data.append({
            'key': epic_key,
            'name': epic_name,
            'total': total_points,
            'remaining': remaining_points,
            'completed': total_points - remaining_points,
            'pct': (total_points - remaining_points) / total_points * 100 if total_points > 0 else 0
        })

    # Sort by remaining work
    epic_data.sort(key=lambda e: e['remaining'], reverse=True)

    # Print table
    print("="*110)
    print(f"{'Epic':<15} {'Name':<40} {'Remaining':>12} {'Completed':>12} {'Total':>12} {'Progress':>10}")
    print("-"*110)

    for e in epic_data:
        print(f"{e['key']:<15} {e['name'][:39]:<40} {e['remaining']:>11.1f}  "
              f"{e['completed']:>11.1f}  {e['total']:>11.1f}  {e['pct']:>9.1f}%")

    print("-"*110)
    totals_remaining = sum(e['remaining'] for e in epic_data)
    totals_completed = sum(e['completed'] for e in epic_data)
    totals_all = sum(e['total'] for e in epic_data)

    print(f"{'TOTAL':<15} {'':<40} {totals_remaining:>11.1f}  "
          f"{totals_completed:>11.1f}  {totals_all:>11.1f}  "
          f"{(totals_completed/totals_all*100) if totals_all > 0 else 0:>9.1f}%")
    print("="*110)

    if totals_remaining > 0:
        print(f"\nTotal remaining work: {totals_remaining:.1f} story points across {len([e for e in epic_data if e['remaining'] > 0])} epics")


if __name__ == '__main__':
    main()
