#!/usr/bin/env python3
"""Check specific epic's child issues and story points."""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('JIRA_URL').rstrip('/')
auth = (os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN'))
headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

# Check epic passed as argument
if len(sys.argv) < 2:
    print("Usage: python check_epic.py <EPIC_KEY>")
    sys.exit(1)
epic_key = sys.argv[1]

response = requests.post(
    f'{url}/rest/api/3/search/jql',
    auth=auth,
    headers=headers,
    json={
        'jql': f'parent = {epic_key}',
        'maxResults': 200,
        'fields': ['summary', 'customfield_10016', 'customfield_10026', 'customfield_10031', 'status']
    }
)

if response.status_code == 200:
    issues = response.json().get('issues', [])
    print(f"\nEpic {epic_key} has {len(issues)} child issues:\n")

    total_remaining = 0.0
    total_all = 0.0
    for issue in issues:
        key = issue['key']
        summary = issue['fields']['summary'][:50]
        status = issue['fields'].get('status', {}).get('name', 'Unknown')

        # Check all three fields
        p1 = issue['fields'].get('customfield_10016')
        p2 = issue['fields'].get('customfield_10026')
        p3 = issue['fields'].get('customfield_10031')

        points = p1 or p2 or p3
        points = float(points) if points else 0.0

        # Only count if not complete
        status_lower = status.lower()
        is_complete = status_lower in ['done', 'closed', 'resolved']

        total_all += points
        if not is_complete and points > 0:
            total_remaining += points
            marker = "→"
        else:
            marker = " "

        print(f"  {marker} {key}: {summary:50} | Status: {status:15} | Points: {points}")

    print(f"\n  Total points (all): {total_all}")
    print(f"  Total remaining points: {total_remaining}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
