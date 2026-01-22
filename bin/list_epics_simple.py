#!/usr/bin/env python3
"""List epics using direct issue search - simpler approach."""

import os
import sys
from dotenv import load_dotenv
import requests


def main():
    """List epics with their story points."""
    load_dotenv()

    required_vars = ['JIRA_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN', 'JIRA_PROJECT_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please add JIRA_PROJECT_KEY to your .env file (e.g., JIRA_PROJECT_KEY=CIT)")
        sys.exit(1)

    url = os.getenv('JIRA_URL').rstrip('/')
    email = os.getenv('JIRA_EMAIL')
    api_token = os.getenv('JIRA_API_TOKEN')
    project_key = os.getenv('JIRA_PROJECT_KEY')

    auth = (email, api_token)
    headers = {'Accept': 'application/json'}

    print(f"Searching for epics in project {project_key}...")

    # Search for all epics in the project
    jql = f'project = {project_key} AND type = Epic ORDER BY created DESC'

    response = requests.get(
        f'{url}/rest/api/3/search',
        auth=auth,
        headers=headers,
        params={
            'jql': jql,
            'maxResults': 100,
            'fields': 'summary,status,customfield_10016,customfield_10011,issuetype,created'
        }
    )

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        sys.exit(1)

    data = response.json()
    epics = data.get('issues', [])

    print(f"Found {len(epics)} epics\n")

    # Now for each epic, search for child issues
    print("="*100)
    print("EPIC SUMMARY - STORY POINTS")
    print("="*100)
    print(f"{'Epic Key':<15} {'Status':<15} {'Epic Summary':<40} {'Remaining':<12} {'Total':<12}")
    print("-"*100)

    total_remaining_all = 0.0
    total_all_all = 0.0

    for epic in epics:
        epic_key = epic['key']
        epic_summary = epic['fields']['summary']
        epic_status = epic['fields']['status']['name']

        # Skip done epics
        if epic_status.lower() in ['done', 'closed', 'cancelled']:
            continue

        # Search for issues that are children of this epic
        # Try the issues() API endpoint which should work
        child_jql = f'parent = {epic_key}'

        child_response = requests.get(
            f'{url}/rest/api/3/search',
            auth=auth,
            headers=headers,
            params={
                'jql': child_jql,
                'maxResults': 100,
                'fields': 'summary,status,customfield_10016'
            }
        )

        total_points = 0.0
        remaining_points = 0.0

        if child_response.status_code == 200:
            child_data = child_response.json()
            issues = child_data.get('issues', [])

            for issue in issues:
                # Get story points (customfield_10016 is typical, might be different)
                points_field = issue['fields'].get('customfield_10016')
                points = float(points_field) if points_field else 0.0
                total_points += points

                # Check if issue is not done
                issue_status = issue['fields']['status']['name'].lower()
                if issue_status not in ['done', 'closed', 'resolved']:
                    remaining_points += points

        print(f"{epic_key:<15} {epic_status:<15} {epic_summary[:39]:<40} "
              f"{remaining_points:>10.1f}  {total_points:>10.1f}")

        total_remaining_all += remaining_points
        total_all_all += total_points

    print("-"*100)
    print(f"{'TOTAL':<15} {'':<15} {'':<40} {total_remaining_all:>10.1f}  {total_all_all:>10.1f}")
    print("="*100)

    if total_remaining_all > 0:
        print(f"\nTotal remaining work: {total_remaining_all:.1f} story points")


if __name__ == '__main__':
    main()
