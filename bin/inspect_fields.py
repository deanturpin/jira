#!/usr/bin/env python3
"""Inspect custom fields in a Jira issue to identify story point field IDs."""

import os
import sys
from dotenv import load_dotenv
import requests
import json


def main():
    """Fetch a sample issue and display all custom fields."""
    load_dotenv()

    url = os.getenv('JIRA_URL')
    email = os.getenv('JIRA_EMAIL')
    api_token = os.getenv('JIRA_API_TOKEN')
    # Allow specifying which board to inspect via command line argument
    import sys
    if len(sys.argv) > 1:
        board_id = sys.argv[1]
    else:
        board_id = os.getenv('JIRA_BOARD_ID_1') or os.getenv('JIRA_BOARD_ID')

    if not all([url, email, api_token, board_id]):
        print("Error: Missing required environment variables")
        sys.exit(1)

    url = url.rstrip('/')
    auth = (email, api_token)
    headers = {'Accept': 'application/json'}

    # Get a recent issue from the board
    print(f"Fetching issues from board {board_id}...")
    response = requests.get(
        f'{url}/rest/agile/1.0/board/{board_id}/issue',
        auth=auth,
        headers=headers,
        params={'maxResults': 1}
    )

    if response.status_code != 200:
        print(f"Error fetching issues: {response.status_code}")
        print(response.text)
        sys.exit(1)

    issues = response.json().get('issues', [])
    if not issues:
        print("No issues found on board")
        sys.exit(1)

    issue = issues[0]
    issue_key = issue['key']
    print(f"\nInspecting issue: {issue_key}")
    print(f"Summary: {issue['fields'].get('summary', 'N/A')}")
    print("\n" + "="*80)
    print("CUSTOM FIELDS (customfield_*)")
    print("="*80)

    # Find and display all custom fields
    custom_fields = {}
    for field_id, value in issue['fields'].items():
        if field_id.startswith('customfield_'):
            if value is not None:
                custom_fields[field_id] = value

    # Sort by field ID
    for field_id in sorted(custom_fields.keys()):
        value = custom_fields[field_id]

        # Format value nicely
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value, indent=2)
        else:
            value_str = str(value)

        # Truncate long values
        if len(value_str) > 100:
            value_str = value_str[:100] + "..."

        print(f"\n{field_id}:")
        print(f"  Value: {value_str}")
        print(f"  Type: {type(value).__name__}")

    print("\n" + "="*80)
    print("LOOK FOR STORY POINTS FIELD")
    print("="*80)
    print("\nLikely story point fields (numeric values):")

    for field_id in sorted(custom_fields.keys()):
        value = custom_fields[field_id]
        if isinstance(value, (int, float)) and value > 0:
            print(f"  {field_id} = {value}")

    print("\nUpdate jira_client.py get_story_points() to use the correct field ID(s)")


if __name__ == '__main__':
    main()
