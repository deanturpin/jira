#!/usr/bin/env python3
"""Close the active sprint on a Jira board."""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import requests
from jira_client import JiraClient

load_dotenv()


def get_active_sprint(client, board_id):
    """Get the currently active sprint for a board."""
    response = requests.get(
        f'{client.jira_url}/rest/agile/1.0/board/{board_id}/sprint',
        auth=(client.jira_email, client.jira_api_token),
        params={'state': 'active'}
    )
    response.raise_for_status()
    data = response.json()

    active_sprints = data.get('values', [])
    if not active_sprints:
        return None

    if len(active_sprints) > 1:
        print(f"Warning: Found {len(active_sprints)} active sprints. Using the first one.")

    return active_sprints[0]


def get_sprint_issues(client, sprint_id):
    """Get all issues in a sprint."""
    response = requests.get(
        f'{client.jira_url}/rest/agile/1.0/sprint/{sprint_id}/issue',
        auth=(client.jira_email, client.jira_api_token),
        params={'maxResults': 500}
    )
    response.raise_for_status()
    return response.json().get('issues', [])


def close_sprint(client, sprint_id):
    """Close a sprint."""
    response = requests.post(
        f'{client.jira_url}/rest/agile/1.0/sprint/{sprint_id}',
        auth=(client.jira_email, client.jira_api_token),
        headers={'Content-Type': 'application/json'},
        json={'state': 'closed'}
    )
    response.raise_for_status()
    return response.json()


def main():
    """Main function to close active sprint."""
    if len(sys.argv) < 2:
        print("Usage: python close_sprint.py <board_id>")
        print("\nExample:")
        print("  python close_sprint.py 123")
        print("\nTo find your board ID, look at your Jira board URL:")
        print("  https://your-domain.atlassian.net/.../boards/123")
        sys.exit(1)

    board_id = int(sys.argv[1])

    # Initialize Jira client
    jira_url = os.getenv('JIRA_URL')
    jira_email = os.getenv('JIRA_EMAIL')
    jira_api_token = os.getenv('JIRA_API_TOKEN')

    if not all([jira_url, jira_email, jira_api_token]):
        print("Error: Missing Jira credentials in .env file")
        sys.exit(1)

    client = JiraClient(jira_url, jira_email, jira_api_token)

    print(f"🔍 Looking for active sprint on board {board_id}...")

    # Get active sprint
    active_sprint = get_active_sprint(client, board_id)

    if not active_sprint:
        print("❌ No active sprint found on this board")
        sys.exit(1)

    sprint_id = active_sprint['id']
    sprint_name = active_sprint['name']
    sprint_start = active_sprint.get('startDate', 'Unknown')
    sprint_end = active_sprint.get('endDate', 'Unknown')

    print(f"\n📋 Active Sprint Details:")
    print(f"  ID: {sprint_id}")
    print(f"  Name: {sprint_name}")
    print(f"  Start: {sprint_start}")
    print(f"  End: {sprint_end}")

    # Get sprint issues
    print(f"\n📊 Fetching sprint issues...")
    issues = get_sprint_issues(client, sprint_id)

    # Categorize issues
    completed = []
    incomplete = []

    for issue in issues:
        status = issue['fields'].get('status', {}).get('name', '').lower()
        issue_key = issue['key']
        summary = issue['fields'].get('summary', '')

        if status in ['done', 'closed', 'resolved']:
            completed.append((issue_key, summary))
        else:
            incomplete.append((issue_key, summary, status))

    total = len(issues)
    completed_count = len(completed)
    incomplete_count = len(incomplete)

    print(f"\n📈 Sprint Summary:")
    print(f"  Total issues: {total}")
    print(f"  Completed: {completed_count} ({completed_count/total*100:.0f}%)" if total > 0 else "  Completed: 0")
    print(f"  Incomplete: {incomplete_count}")

    if incomplete:
        print(f"\n⚠️  Incomplete Issues (will move to backlog):")
        for key, summary, status in incomplete[:10]:  # Show first 10
            print(f"    {key}: {summary[:60]}{'...' if len(summary) > 60 else ''} [{status}]")
        if len(incomplete) > 10:
            print(f"    ... and {len(incomplete) - 10} more")

    # Confirmation
    print(f"\n⚠️  This will:")
    print(f"  1. Close sprint '{sprint_name}'")
    print(f"  2. Move {incomplete_count} incomplete issues to the backlog")
    print(f"  3. Archive {completed_count} completed issues with the sprint")

    confirm = input(f"\n❓ Are you sure you want to close this sprint? (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("\n🚫 Sprint closure cancelled")
        sys.exit(0)

    # Close the sprint
    print(f"\n🔄 Closing sprint...")
    try:
        result = close_sprint(client, sprint_id)
        print(f"\n✅ Sprint '{sprint_name}' closed successfully!")
        print(f"\n📦 Results:")
        print(f"  - Completed issues: {completed_count} (archived with sprint)")
        print(f"  - Incomplete issues: {incomplete_count} (moved to backlog)")
        print(f"\n🎉 Sprint closure complete!")

    except requests.exceptions.HTTPError as e:
        print(f"\n❌ Error closing sprint: {e}")
        print(f"Response: {e.response.text}")
        sys.exit(1)


if __name__ == '__main__':
    main()
