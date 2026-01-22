#!/usr/bin/env python3
"""List all epics with remaining (not closed) story points."""

import os
import sys
import json
import requests
from dotenv import load_dotenv


def main():
    """List epics with remaining work."""
    load_dotenv()

    required_vars = ['JIRA_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN', 'JIRA_PROJECT_KEY', 'JIRA_BOARD_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    url = os.getenv('JIRA_URL').rstrip('/')
    email = os.getenv('JIRA_EMAIL')
    api_token = os.getenv('JIRA_API_TOKEN')
    project_key = os.getenv('JIRA_PROJECT_KEY')
    board_id = int(os.getenv('JIRA_BOARD_ID'))

    auth = (email, api_token)
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

    # Get epics from board using agile API
    print("Fetching epics from board...")
    epic_response = requests.get(
        f'{url}/rest/agile/1.0/board/{board_id}/epic',
        auth=auth,
        headers={'Accept': 'application/json'},
        params={'maxResults': 100}
    )

    if epic_response.status_code != 200:
        print(f"Error fetching epics: {epic_response.status_code}")
        print(epic_response.text)
        sys.exit(1)

    epics = epic_response.json().get('values', [])
    active_epics = [e for e in epics if not e.get('done', False)]

    print(f"Found {len(active_epics)} active epics")

    # For each epic, get child issues
    epic_data = []

    for epic in active_epics:
        epic_key = epic['key']
        epic_name = epic.get('summary', epic.get('name', 'Unnamed'))[:50]

        # Search for issues with this epic as parent using new endpoint
        jql = f'parent = {epic_key}'

        issue_response = requests.post(
            f'{url}/rest/api/3/search/jql',
            auth=auth,
            headers=headers,
            json={
                'jql': jql,
                'maxResults': 200,
                'fields': ['summary', 'status', 'customfield_10016', 'issuetype']
            }
        )

        if issue_response.status_code != 200:
            print(f"Warning: Could not fetch issues for {epic_key}")
            continue

        issues = issue_response.json().get('issues', [])

        total_points = 0.0
        completed_points = 0.0
        remaining_points = 0.0

        for issue in issues:
            # Get story points (customfield_10016 is common)
            points = issue['fields'].get('customfield_10016')
            points = float(points) if points else 0.0
            total_points += points

            # Check if completed
            status = issue['fields'].get('status', {}).get('name', '').lower()
            if status in ['done', 'closed', 'resolved']:
                completed_points += points
            else:
                remaining_points += points

        epic_data.append({
            'key': epic_key,
            'name': epic_name,
            'total': total_points,
            'completed': completed_points,
            'remaining': remaining_points,
            'issue_count': len(issues),
            'pct': (completed_points / total_points * 100) if total_points > 0 else 0
        })

    # Sort by remaining work
    epic_data.sort(key=lambda e: e['remaining'], reverse=True)

    # Print table
    print("\n" + "="*120)
    print(f"{'Epic Key':<15} {'Epic Name':<52} {'Remaining':>12} {'Completed':>12} {'Total':>12} {'Progress':>10}")
    print("-"*120)

    for e in epic_data:
        print(f"{e['key']:<15} {e['name']:<52} {e['remaining']:>11.1f}  "
              f"{e['completed']:>11.1f}  {e['total']:>11.1f}  {e['pct']:>9.1f}%")

    print("-"*120)

    total_remaining = sum(e['remaining'] for e in epic_data)
    total_completed = sum(e['completed'] for e in epic_data)
    total_all = sum(e['total'] for e in epic_data)

    print(f"{'TOTAL':<15} {'':<52} {total_remaining:>11.1f}  "
          f"{total_completed:>11.1f}  {total_all:>11.1f}  "
          f"{(total_completed/total_all*100) if total_all > 0 else 0:>9.1f}%")
    print("="*120)

    # Summary
    epics_with_work = [e for e in epic_data if e['remaining'] > 0]
    epics_with_issues = [e for e in epic_data if e['issue_count'] > 0]

    print(f"\nSummary:")
    print(f"  Total epics: {len(epic_data)}")
    print(f"  Epics with linked issues: {len(epics_with_issues)}")
    print(f"  Epics with remaining work: {len(epics_with_work)}")
    print(f"  Total remaining story points: {total_remaining:.1f}")

    if total_remaining > 0:
        print(f"\nTop epics by remaining work:")
        for e in epic_data[:5]:
            if e['remaining'] > 0:
                print(f"  {e['key']}: {e['remaining']:.1f} points - {e['name']}")


if __name__ == '__main__':
    main()
