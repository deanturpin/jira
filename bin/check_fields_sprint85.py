#!/usr/bin/env python3
"""Check what custom fields are populated in Sprint 85 issues."""

import os
import requests
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    url = os.getenv('JIRA_URL').rstrip('/')
    auth = (os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN'))
    
    # Sprint 85 ID from the output above
    sprint_id = 5207
    
    response = requests.get(
        f'{url}/rest/agile/1.0/sprint/{sprint_id}/issue',
        auth=auth,
        headers={'Accept': 'application/json'},
        params={'maxResults': 5}
    )
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return
    
    issues = response.json().get('issues', [])
    
    print(f"Checking first few issues from Sprint 85:\n")
    
    for issue in issues[:3]:
        print(f"\n{issue['key']}: {issue['fields'].get('summary', 'No summary')[:60]}")
        print(f"Status: {issue['fields'].get('status', {}).get('name', 'Unknown')}")
        print(f"\nCustom fields with values:")
        
        for field_id, value in issue['fields'].items():
            if field_id.startswith('customfield_') and value is not None:
                # Truncate long values
                value_str = str(value)[:100]
                print(f"  {field_id}: {value_str}")
        
        # Specifically check our story point fields
        sp1 = issue['fields'].get('customfield_10016')
        sp2 = issue['fields'].get('customfield_10026')
        print(f"\nStory point fields:")
        print(f"  customfield_10016 (Story Points): {sp1}")
        print(f"  customfield_10026 (Story point estimate): {sp2}")

if __name__ == '__main__':
    main()
