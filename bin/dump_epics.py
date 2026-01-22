#!/usr/bin/env python3
"""Dump raw epic data from Jira to understand structure."""

import os
import sys
import json
from dotenv import load_dotenv

from jira_client import JiraClient


def main():
    """Dump epic data."""
    load_dotenv()

    required_vars = ['JIRA_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN', 'JIRA_BOARD_ID']
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
    project_key = os.getenv('JIRA_PROJECT_KEY', 'project').lower()

    print("Fetching epics from board...")
    epics = client.get_epics(board_id)

    print(f"Found {len(epics)} total epics")
    print(f"\nSaving raw data to {project_key}_epics_dump.json...")

    # Save full JSON dump
    with open(f'../public/{project_key}_epics_dump.json', 'w') as f:
        json.dump(epics, f, indent=2)

    print(f"Saved {len(epics)} epics to {project_key}_epics_dump.json")

    # Print summary table
    print("\n" + "="*100)
    print("EPIC SUMMARY")
    print("="*100)
    print(f"{'Key':<15} {'Name':<40} {'Done':<10} {'ID':<10}")
    print("-"*100)

    active_count = 0
    done_count = 0

    for epic in epics:
        key = epic.get('key', 'N/A')
        name = epic.get('name', 'Unnamed')[:39]
        done = epic.get('done', False)
        epic_id = epic.get('id', 'N/A')

        if done:
            done_count += 1
        else:
            active_count += 1

        print(f"{key:<15} {name:<40} {'✓' if done else ' ':<10} {epic_id:<10}")

    print("-"*100)
    print(f"Active: {active_count}  |  Done: {done_count}  |  Total: {len(epics)}")
    print("="*100)

    print(f"\nCheck {project_key}_epics_dump.json for full epic structure")


if __name__ == '__main__':
    main()
