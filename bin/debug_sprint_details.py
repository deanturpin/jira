#!/usr/bin/env python3
"""Debug script to show detailed sprint completion data."""

import os
import sys
from dotenv import load_dotenv
from jira_client import JiraClient

def main():
    load_dotenv()
    
    # Use project 2 (IVEMCS)
    board_id = os.getenv('JIRA_BOARD_ID_2')
    
    if not board_id:
        print("Error: JIRA_BOARD_ID_2 not found")
        sys.exit(1)
    
    client = JiraClient(
        url=os.getenv('JIRA_URL'),
        email=os.getenv('JIRA_EMAIL'),
        api_token=os.getenv('JIRA_API_TOKEN')
    )
    
    print(f"Fetching sprints for board {board_id}...\n")

    # Get all sprints using JiraClient
    all_sprints = client.get_board_sprints(int(board_id), max_results=50)

    # Get last 5 completed sprints
    completed_sprints = [s for s in all_sprints if s.get('state') == 'closed']
    recent_sprints = completed_sprints[-5:]

    print(f"Last 5 completed sprints:\n")
    print(f"{'Sprint Name':<25} {'Sprint ID':<12} {'Issues':<10} {'Completed Points':<20}")
    print("=" * 70)

    for sprint in recent_sprints:
        sprint_id = sprint['id']
        sprint_name = sprint['name']

        # Get issues in this sprint using JiraClient
        issues = client.get_sprint_issues(sprint_id)
        
        # Calculate completed points
        completed_points = 0.0
        total_issues = len(issues)
        
        for issue in issues:
            status = issue['fields'].get('status', {}).get('name', '').lower()
            if status in ['done', 'closed', 'resolved']:
                points = client.get_story_points(issue)
                completed_points += points
        
        print(f"{sprint_name:<25} {sprint_id:<12} {total_issues:<10} {completed_points:<20.1f}")
        
        # Show first few issues for the most recent sprint
        if sprint == recent_sprints[-1]:
            print(f"\n  Sample issues from {sprint_name}:")
            for issue in issues[:10]:
                key = issue['key']
                summary = issue['fields'].get('summary', 'No summary')[:50]
                status = issue['fields'].get('status', {}).get('name', 'Unknown')
                points = client.get_story_points(issue)
                print(f"    {key}: {summary:<50} | Status: {status:<15} | Points: {points}")
            if len(issues) > 10:
                print(f"    ... and {len(issues) - 10} more issues")

if __name__ == '__main__':
    main()
