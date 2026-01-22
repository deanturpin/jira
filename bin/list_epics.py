#!/usr/bin/env python3
"""List all epics with remaining (not closed) story points."""

import os
import sys
from dotenv import load_dotenv
import requests

from jira_client import JiraClient


def get_epic_issues_by_jql(client: JiraClient, epic_key: str) -> list:
    """Try multiple JQL patterns to find issues linked to an epic."""
    # Different Jira versions use different fields for epic links
    jql_patterns = [
        f'"Parent Link" = {epic_key}',  # Newer Jira
        f'parent = {epic_key}',  # Some Jira versions
        f'"Epic Link" = {epic_key}',  # Older Jira (deprecated but might work)
        f'issue in childIssuesOf("{epic_key}")',  # Alternative syntax
    ]

    for jql in jql_patterns:
        try:
            response = requests.get(
                f'{client.url}/rest/api/3/search',
                auth=client.auth,
                headers=client.headers,
                params={
                    'jql': jql,
                    'maxResults': 100,
                    'fields': 'summary,status,customfield_10016,issuetype'
                }
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('total', 0) > 0:
                    return data.get('issues', [])
            elif response.status_code != 400 and response.status_code != 410:
                # If it's not a "bad request" or "gone", might be auth or other issue
                print(f"Unexpected status {response.status_code} for JQL: {jql}")

        except Exception as e:
            print(f"Error trying JQL pattern '{jql}': {e}")
            continue

    return []


def main():
    """List epics with remaining story points."""
    load_dotenv()

    required_vars = ['JIRA_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN', 'JIRA_BOARD_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    print("Connecting to Jira...")
    client = JiraClient(
        url=os.getenv('JIRA_URL'),
        email=os.getenv('JIRA_EMAIL'),
        api_token=os.getenv('JIRA_API_TOKEN')
    )

    board_id = int(os.getenv('JIRA_BOARD_ID'))

    print("Fetching epics...")
    epics = client.get_epics(board_id)
    print(f"Found {len(epics)} total epics")

    active_epics = [e for e in epics if not e.get('done', False)]
    print(f"Found {len(active_epics)} active (not done) epics\n")

    epic_summary = []

    for epic in active_epics:
        epic_key = epic.get('key', 'Unknown')
        epic_name = epic.get('name', 'Unnamed Epic')

        print(f"Fetching issues for {epic_key}: {epic_name}...")

        # Try to get issues using different JQL patterns
        issues = get_epic_issues_by_jql(client, epic_key)

        if not issues:
            print(f"  Warning: Could not find issues for {epic_key} (might have no child issues)")

        total_points = 0.0
        remaining_points = 0.0
        completed_points = 0.0
        issue_count = len(issues)
        remaining_count = 0

        for issue in issues:
            points = client.get_story_points(issue)
            total_points += points

            if client.is_issue_completed(issue):
                completed_points += points
            else:
                remaining_points += points
                remaining_count += 1

        epic_summary.append({
            'key': epic_key,
            'name': epic_name,
            'total_points': total_points,
            'completed_points': completed_points,
            'remaining_points': remaining_points,
            'total_issues': issue_count,
            'remaining_issues': remaining_count,
            'completion_pct': (completed_points / total_points * 100) if total_points > 0 else 0
        })

    # Sort by remaining points (descending)
    epic_summary.sort(key=lambda e: e['remaining_points'], reverse=True)

    # Print summary table
    print("\n" + "="*100)
    print("EPIC SUMMARY - REMAINING WORK")
    print("="*100)
    print(f"{'Epic Key':<15} {'Epic Name':<35} {'Remaining':<12} {'Completed':<12} {'Total':<12} {'%':<8}")
    print("-"*100)

    for epic in epic_summary:
        print(f"{epic['key']:<15} {epic['name'][:34]:<35} "
              f"{epic['remaining_points']:>10.1f}  "
              f"{epic['completed_points']:>10.1f}  "
              f"{epic['total_points']:>10.1f}  "
              f"{epic['completion_pct']:>6.1f}%")

    print("-"*100)
    total_remaining = sum(e['remaining_points'] for e in epic_summary)
    total_completed = sum(e['completed_points'] for e in epic_summary)
    total_all = sum(e['total_points'] for e in epic_summary)

    print(f"{'TOTAL':<15} {'':<35} "
          f"{total_remaining:>10.1f}  "
          f"{total_completed:>10.1f}  "
          f"{total_all:>10.1f}  "
          f"{(total_completed/total_all*100) if total_all > 0 else 0:>6.1f}%")
    print("="*100)

    # Highlight epics with work remaining
    if total_remaining > 0:
        print(f"\nTotal remaining work across all epics: {total_remaining:.1f} story points")
        epics_with_work = [e for e in epic_summary if e['remaining_points'] > 0]
        print(f"Epics with remaining work: {len(epics_with_work)}")


if __name__ == '__main__':
    main()
