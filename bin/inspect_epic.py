#!/usr/bin/env python3
"""Inspect a single epic's issues to understand field structure."""

import os
import sys
import json
import requests
from dotenv import load_dotenv


def main():
    """Inspect epic issues."""
    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python inspect_epic.py <EPIC_KEY>")
        print("Example: python inspect_epic.py PROJ-123")
        sys.exit(1)

    epic_key = sys.argv[1]

    url = os.getenv('JIRA_URL').rstrip('/')
    email = os.getenv('JIRA_EMAIL')
    api_token = os.getenv('JIRA_API_TOKEN')
    project_key = os.getenv('JIRA_PROJECT_KEY', 'project').lower()

    auth = (email, api_token)
    headers = {'Accept': 'application/json'}

    print(f"Searching for issues related to epic {epic_key}...\n")

    # Try different JQL patterns
    jql_patterns = [
        f'"Epic Link" = {epic_key}',
        f'parent = {epic_key}',
        f'"Parent Link" = {epic_key}',
        f'issue in childIssuesOf("{epic_key}")',
    ]

    for jql in jql_patterns:
        print(f"Trying JQL: {jql}")

        # Use POST to /rest/api/3/search/jql as per migration guide
        response = requests.post(
            f'{url}/rest/api/3/search/jql',
            auth=auth,
            headers={**headers, 'Content-Type': 'application/json'},
            json={
                'jql': jql,
                'maxResults': 5,
                'fields': ['*all']
            }
        )

        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            print(f"  Found: {total} issues")

            if total > 0:
                print(f"\n✓ Success! This JQL pattern works: {jql}")
                print(f"\nSaving sample data to {project_key}_epic_{epic_key}_issues.json...")

                with open(f'{project_key}_epic_{epic_key}_issues.json', 'w') as f:
                    json.dump(data, f, indent=2)

                print(f"\nFirst issue fields:")
                first_issue = data['issues'][0]
                print(f"  Key: {first_issue['key']}")
                print(f"  Summary: {first_issue['fields'].get('summary', 'N/A')}")
                print(f"  Status: {first_issue['fields'].get('status', {}).get('name', 'N/A')}")

                # Check for story points
                for field_key, field_value in first_issue['fields'].items():
                    if field_key.startswith('customfield_') and isinstance(field_value, (int, float)):
                        print(f"  {field_key}: {field_value}")

                print(f"\nFull data saved to {project_key}_epic_{epic_key}_issues.json")
                return
        else:
            error_data = response.json()
            print(f"  Error: {error_data.get('errorMessages', [])}")

        print()

    print("No working JQL pattern found. Epic might have no child issues.")


if __name__ == '__main__':
    main()
