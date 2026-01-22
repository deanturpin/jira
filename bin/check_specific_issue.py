#!/usr/bin/env python3
"""Check specific issue for story points."""

import os
import requests
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    url = os.getenv('JIRA_URL').rstrip('/')
    auth = (os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN'))
    
    # Check specific issue with story points
    import sys
    if len(sys.argv) < 2:
        print("Usage: python check_specific_issue.py <ISSUE_KEY>")
        sys.exit(1)
    issue_key = sys.argv[1]
    
    response = requests.get(
        f'{url}/rest/api/3/issue/{issue_key}',
        auth=auth,
        headers={'Accept': 'application/json'}
    )
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return
    
    issue = response.json()
    
    print(f"{issue_key}: {issue['fields'].get('summary', '')}\n")
    print("Numeric custom fields:")
    
    for field_id, value in sorted(issue['fields'].items()):
        if field_id.startswith('customfield_') and isinstance(value, (int, float)) and value != 0:
            print(f"  {field_id} = {value}")

if __name__ == '__main__':
    main()
