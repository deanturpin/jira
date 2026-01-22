#!/usr/bin/env python3
"""Check epic colours from Jira API."""

import os
import sys
from dotenv import load_dotenv
import requests

load_dotenv()

url = os.getenv('JIRA_URL').rstrip('/')
auth = (os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN'))

# Get board ID from command line or env
board_id = sys.argv[1] if len(sys.argv) > 1 else os.getenv('JIRA_BOARD_ID_1')

print(f"Fetching epics from board {board_id}...\n")

epic_response = requests.get(
    f'{url}/rest/agile/1.0/board/{board_id}/epic',
    auth=auth,
    headers={'Accept': 'application/json'},
    params={'maxResults': 100}
)

epics = epic_response.json().get('values', [])

print(f"{'Epic Key':<15} {'Name':<40} {'Colour Key':<15}")
print("=" * 70)

for epic in epics:
    if not epic.get('done', False):
        epic_key = epic['key']
        epic_name = epic.get('summary', epic.get('name', 'Unnamed'))[:40]
        colour_key = epic.get('color', {}).get('key', 'no colour')

        print(f"{epic_key:<15} {epic_name:<40} {colour_key:<15}")
