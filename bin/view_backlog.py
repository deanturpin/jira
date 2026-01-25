#!/usr/bin/env python3
"""View top issues from the backlog by story points."""

import os
import sys
from dotenv import load_dotenv
import requests
from jira_client import JiraClient
from velocity_calculator import VelocityCalculator

load_dotenv()


def get_backlog_top_issues(board_id, limit_points=None, limit_count=None):
    """Get top issues from backlog, limited by story points or count.

    Args:
        board_id: Jira board ID
        limit_points: Maximum total story points to fetch (optional)
        limit_count: Maximum number of issues to fetch (optional)
    """
    url = os.getenv('JIRA_URL').rstrip('/')
    auth = (os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN'))
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

    # Get backlog issues (not in active sprint)
    # Jira orders backlog by rank, so we get them in priority order
    response = requests.get(
        f'{url}/rest/agile/1.0/board/{board_id}/backlog',
        auth=auth,
        headers=headers,
        params={
            'maxResults': 100,
            'fields': 'summary,status,assignee,customfield_10016,customfield_10026,customfield_10031,priority,labels'
        }
    )

    if response.status_code != 200:
        print(f"Error fetching backlog: {response.status_code}")
        print(f"Response: {response.text}")
        return []

    issues = response.json().get('issues', [])

    if not issues:
        print("No issues found in backlog")
        return []

    # Extract and format issues
    backlog_items = []

    for issue in issues:
        # Try all common story point fields
        points = (issue['fields'].get('customfield_10016') or
                 issue['fields'].get('customfield_10026') or
                 issue['fields'].get('customfield_10031'))
        points = float(points) if points else 0.0

        status = issue['fields'].get('status', {}).get('name', 'Unknown')
        assignee = issue['fields'].get('assignee')
        assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
        priority = issue['fields'].get('priority', {}).get('name', 'None')
        labels = issue['fields'].get('labels', [])

        backlog_items.append({
            'key': issue['key'],
            'summary': issue['fields'].get('summary', 'No summary'),
            'points': points,
            'status': status,
            'assignee': assignee_name,
            'priority': priority,
            'labels': labels
        })

    # Sort by priority: Highest -> High -> Medium -> Low -> Minor -> Trivial -> None
    priority_order = {
        'Highest': 0,
        'High': 1,
        'Medium': 2,
        'Low': 3,
        'Minor': 4,
        'Trivial': 5,
        'None': 6
    }
    backlog_items.sort(key=lambda x: priority_order.get(x['priority'], 999))

    # Now apply limits after sorting
    filtered_items = []
    total_points = 0.0

    for item in backlog_items:
        # Check limits
        if limit_points and total_points + item['points'] > limit_points:
            # Only add if we haven't reached the count limit
            if not limit_count or len(filtered_items) < limit_count:
                filtered_items.append(item)
            break

        filtered_items.append(item)
        total_points += item['points']

        # Check count limit
        if limit_count and len(filtered_items) >= limit_count:
            break

    return filtered_items


def print_backlog_items(items, show_details=False):
    """Print backlog items in a formatted table."""
    if not items:
        return

    total_points = sum(item['points'] for item in items)

    print(f"\n📋 Top {len(items)} Backlog Issues")
    print(f"Total Story Points: {total_points:.0f}")
    print("=" * 100)

    for i, item in enumerate(items, 1):
        points_str = f"{item['points']:.0f}pts" if item['points'] > 0 else "No pts"

        print(f"\n{i}. {item['key']}: {item['summary'][:70]}")
        print(f"   Points: {points_str:8s} | Status: {item['status']:15s} | Assignee: {item['assignee']:20s}")

        if show_details:
            print(f"   Priority: {item['priority']}", end='')
            if item['labels']:
                print(f" | Labels: {', '.join(item['labels'])}", end='')
            print()

    print("\n" + "=" * 100)
    print(f"Total: {len(items)} issues, {total_points:.0f} story points\n")


def main():
    """Main function to view backlog."""
    if len(sys.argv) < 2:
        print("Usage: python view_backlog.py <board_id> [options]")
        print("\nOptions:")
        print("  --points <N>    Show issues up to N story points (e.g., --points 20)")
        print("  --count <N>     Show N issues (e.g., --count 10)")
        print("  --details       Show additional details (priority, labels)")
        print("\nDefault behaviour (no options):")
        print("  Uses average velocity from recent sprints as the point limit")
        print("  Perfect for sprint planning based on historical capacity")
        print("\nExamples:")
        print("  python view_backlog.py 123              # Use average velocity")
        print("  python view_backlog.py 123 --points 20  # Use specific limit")
        print("  python view_backlog.py 123 --count 15 --details")
        sys.exit(1)

    board_id = int(sys.argv[1])

    # Parse options
    limit_points = None
    limit_count = None
    show_details = False

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--points' and i + 1 < len(sys.argv):
            limit_points = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--count' and i + 1 < len(sys.argv):
            limit_count = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--details':
            show_details = True
            i += 1
        else:
            print(f"Unknown option: {sys.argv[i]}")
            sys.exit(1)

    # Validate credentials
    if not all([os.getenv('JIRA_URL'), os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN')]):
        print("Error: Missing Jira credentials in .env file")
        sys.exit(1)

    # If no limit specified, use velocity override or calculate average velocity
    if limit_points is None and limit_count is None:
        velocity_override = os.getenv('VELOCITY_OVERRIDE')

        if velocity_override:
            limit_points = float(velocity_override)

            # Calculate actual velocity to show in brackets
            print(f"📊 Calculating average velocity for board {board_id}...")
            client = JiraClient(
                os.getenv('JIRA_URL'),
                os.getenv('JIRA_EMAIL'),
                os.getenv('JIRA_API_TOKEN')
            )
            calc = VelocityCalculator(client)
            velocity_data = calc.get_historical_velocity(board_id, months=6)

            if velocity_data:
                velocity_stats = calc.calculate_velocity_stats(velocity_data)
                actual_velocity = velocity_stats['mean']
                print(f"   Actual velocity: {actual_velocity:.1f} story points")
                print(f"📊 Using target velocity: {limit_points:.1f} story points (actual: {actual_velocity:.1f})")
            else:
                print(f"📊 Using target velocity: {limit_points:.1f} story points")
        else:
            print(f"📊 Calculating average velocity for board {board_id}...")
            client = JiraClient(
                os.getenv('JIRA_URL'),
                os.getenv('JIRA_EMAIL'),
                os.getenv('JIRA_API_TOKEN')
            )
            calc = VelocityCalculator(client)
            velocity_data = calc.get_historical_velocity(board_id, months=6)

            if velocity_data:
                velocity_stats = calc.calculate_velocity_stats(velocity_data)
                limit_points = velocity_stats['mean']
                print(f"   Average velocity: {limit_points:.1f} story points")
            else:
                print("   Warning: Could not calculate velocity, showing all backlog items")

    print(f"\n🔍 Fetching backlog for board {board_id}...")
    if limit_points:
        print(f"   Limit: {limit_points:.1f} story points")
    if limit_count:
        print(f"   Limit: {limit_count} issues")

    items = get_backlog_top_issues(board_id, limit_points, limit_count)

    if items:
        print_backlog_items(items, show_details)
    else:
        print("\n❌ No backlog items found")


if __name__ == '__main__':
    main()
